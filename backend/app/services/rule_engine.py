"""
Universal Rule Engine — provider-agnostic billing audit.

Works for: BlueDart, Delhivery, DTDC, Ekart, Shadowfax, XpressBees,
           FedEx, DHL, Ecom Express, Smartr, and any other provider.

Calculation rules (applied from CONTRACT rates, not hardcoded):
  Base freight  = contract weight slab lookup (zone + weight bracket)
  Fuel          = contract.fuel_surcharge_pct % of expected base freight
  RTO           = contract.rto_rate % of expected base freight
  COD           = contract.cod_rate % of (expected base + expected fuel)
  GST           = 18% grossed up on every overcharge amount
  Other         = 0 allowed (full amount is overcharge)

Overcharge = (billed - expected) × (1 + gst/100)
Each check fires MAXIMUM ONCE per AWB. Tolerance = ₹1.
"""
import re
from typing import Optional
from app.models.schemas import DiscrepancyResult, InvoiceData, ContractData

TOLERANCE = 1.0   # ₹1 rounding tolerance

# Default rates used ONLY when contract doesn't specify
DEFAULT_FUEL_PCT  = 12.0
DEFAULT_RTO_PCT   = 50.0
DEFAULT_COD_PCT   = 2.5
DEFAULT_GST_PCT   = 18.0

# Zone alias normalization — handles any provider's zone naming
ZONE_ALIASES: dict[str, str] = {
    # Words → letter
    "local": "A",   "same city": "A",  "same_city": "A",  "city": "A",
    "metro": "B",   "tier1": "B",      "tier 1": "B",
    "regional": "C","region": "C",     "tier2": "C",      "tier 2": "C",
    "national": "D","pan india": "D",  "pan_india": "D",  "tier3": "D",  "tier 3": "D",
    "remote": "E",  "special": "E",    "oda": "E",        "tier4": "E",  "tier 4": "E",
    # Numbers → letter
    "1": "A", "2": "B", "3": "C", "4": "D", "5": "E",
    # Roman → letter
    "i": "A", "ii": "B", "iii": "C", "iv": "D", "v": "E",
    # Delhivery zones
    "z1": "A", "z2": "B", "z3": "C", "z4": "D", "z5": "E",
    # Common numeric zone codes
    "zone a": "A", "zone b": "B", "zone c": "C", "zone d": "D", "zone e": "E",
    "zone 1": "A", "zone 2": "B", "zone 3": "C", "zone 4": "D", "zone 5": "E",
}


def _normalize_zone(z: str) -> str:
    """Normalize any zone name to a single letter A-E."""
    if not z:
        return ""
    z = z.strip()
    # Already a single letter
    if len(z) == 1 and z.upper() in "ABCDE":
        return z.upper()
    lower = z.lower().strip()
    if lower in ZONE_ALIASES:
        return ZONE_ALIASES[lower]
    # Partial match — e.g. "Zone_B" → "B"
    match = re.search(r'\b([A-Ea-e1-5])\b', z)
    if match:
        c = match.group(1).upper()
        if c in "ABCDE":
            return c
        return ZONE_ALIASES.get(c, c)
    return z.upper()


def _gst_multiplier(contract: ContractData) -> float:
    """GST gross-up factor from contract (default 1.18)."""
    pct = contract.gst_pct if contract.gst_pct else DEFAULT_GST_PCT
    return 1 + pct / 100


def get_expected_base_freight(contract: ContractData, zone: str, weight: float) -> Optional[float]:
    """
    Look up expected base freight from contract weight slabs.
    Handles zone normalization — e.g. 'Metro' → 'B', 'Zone 2' → 'B'.
    """
    if not contract.weight_slabs or not zone or weight <= 0:
        return None

    norm_zone = _normalize_zone(zone)

    for slab in contract.weight_slabs:
        slab_zone = _normalize_zone(str(slab.get("zone", "")))
        if slab_zone != norm_zone:
            continue
        mn     = float(slab.get("min", 0))
        mx     = float(slab.get("max", float("inf")))
        per_kg = float(slab.get("per_extra_kg", 0))
        base   = float(slab.get("base_rate", 0))

        # Slab match: weight falls in (mn, mx] — first slab starts from 0
        in_slab = (mn == 0 and weight <= mx) or (mn > 0 and mn < weight <= mx)
        if not in_slab:
            continue

        if per_kg > 0:
            return round(base + (weight - mn) * per_kg, 2)
        return base

    return None


# ─── Internal helpers ──────────────────────────────────────────────────

def _fuel_pct(contract: ContractData) -> float:
    return contract.fuel_surcharge_pct if contract.fuel_surcharge_pct else DEFAULT_FUEL_PCT

def _rto_pct(contract: ContractData) -> float:
    return contract.rto_rate if contract.rto_rate else DEFAULT_RTO_PCT

def _cod_pct(contract: ContractData) -> float:
    return contract.cod_rate if contract.cod_rate else DEFAULT_COD_PCT

def _exp_fuel(base: float, contract: ContractData) -> float:
    return round(base * _fuel_pct(contract) / 100, 2)

def _exp_rto(base: float, contract: ContractData) -> float:
    return round(base * _rto_pct(contract) / 100, 2)

def _exp_cod(base: float, fuel: float, contract: ContractData) -> float:
    return round((base + fuel) * _cod_pct(contract) / 100, 2)


# ─── Check 1: Base freight deviation ──────────────────────────────────

def check_base_freight(invoice: InvoiceData, contract: ContractData) -> Optional[DiscrepancyResult]:
    billed = invoice.base_freight or 0
    if billed <= 0:
        return None
    zone   = (invoice.zone or "").strip()
    weight = invoice.weight_billed or 0
    if not zone or weight <= 0:
        return None

    expected = get_expected_base_freight(contract, zone, weight)
    if expected is None:
        return None

    diff = billed - expected
    if diff <= TOLERANCE:
        return None

    gst  = _gst_multiplier(contract)
    overcharge = round(diff * gst, 2)
    pct_over   = diff / max(expected, 0.01) * 100

    return DiscrepancyResult(
        check_type="rate_deviation",
        severity="critical" if overcharge > 100 else "high",
        description=(
            f"Base freight overcharge: billed ₹{billed:.2f}, contract rate "
            f"for {weight}kg Zone {_normalize_zone(zone)} = ₹{expected:.2f} "
            f"(+{pct_over:.1f}%, overcharge incl. GST = ₹{overcharge:.2f})"
        ),
        billed_value=billed, expected_value=expected, overcharge_amount=overcharge,
        confidence_score=0.95,
        confidence_reason=f"Direct contract rate lookup — zone {_normalize_zone(zone)} + {weight}kg slab match.",
    )


# ─── Check 2: Fuel surcharge ───────────────────────────────────────────

def check_fuel_surcharge(invoice: InvoiceData, contract: ContractData) -> Optional[DiscrepancyResult]:
    billed = invoice.fuel_surcharge or 0
    if billed <= 0:
        return None

    zone, weight = (invoice.zone or "").strip(), invoice.weight_billed or 0
    exp_base = get_expected_base_freight(contract, zone, weight) if zone and weight > 0 else None
    base_ref = exp_base if exp_base is not None else (invoice.base_freight or 0)
    if base_ref <= 0:
        return None

    pct      = _fuel_pct(contract)
    expected = round(base_ref * pct / 100, 2)
    diff     = billed - expected
    if diff <= TOLERANCE:
        return None

    gst        = _gst_multiplier(contract)
    overcharge = round(diff * gst, 2)

    return DiscrepancyResult(
        check_type="fuel_surcharge_mismatch",
        severity="high" if overcharge > 20 else "medium",
        description=(
            f"Fuel surcharge overcharge: billed ₹{billed:.2f}, "
            f"expected ₹{expected:.2f} ({pct:.0f}% of base ₹{base_ref:.2f}, "
            f"overcharge incl. GST = ₹{overcharge:.2f})"
        ),
        billed_value=billed, expected_value=expected, overcharge_amount=overcharge,
        confidence_score=0.92,
        confidence_reason=f"Contract fuel surcharge rate is {pct:.0f}% of base freight.",
    )


# ─── Check 3: RTO fee ──────────────────────────────────────────────────

def check_rto(invoice: InvoiceData, contract: ContractData) -> Optional[DiscrepancyResult]:
    billed = invoice.rto_fee or 0
    if billed <= 0:
        return None

    zone, weight = (invoice.zone or "").strip(), invoice.weight_billed or 0
    exp_base = get_expected_base_freight(contract, zone, weight) if zone and weight > 0 else None
    base_ref = exp_base if exp_base is not None else (invoice.base_freight or 0)
    if base_ref <= 0:
        return None

    pct      = _rto_pct(contract)
    expected = round(base_ref * pct / 100, 2)
    diff     = billed - expected
    if diff <= TOLERANCE:
        return None

    gst        = _gst_multiplier(contract)
    overcharge = round(diff * gst, 2)

    return DiscrepancyResult(
        check_type="rto_overcharge",
        severity="high",
        description=(
            f"RTO overcharge: billed ₹{billed:.2f}, "
            f"expected ₹{expected:.2f} ({pct:.0f}% of base ₹{base_ref:.2f}, "
            f"overcharge incl. GST = ₹{overcharge:.2f})"
        ),
        billed_value=billed, expected_value=expected, overcharge_amount=overcharge,
        confidence_score=0.93,
        confidence_reason=f"Contract RTO rate is {pct:.0f}% of base freight.",
    )


# ─── Check 4: COD fee ──────────────────────────────────────────────────

def check_cod(invoice: InvoiceData, contract: ContractData) -> Optional[DiscrepancyResult]:
    billed = invoice.cod_fee or 0
    if billed <= 0:
        return None

    zone, weight = (invoice.zone or "").strip(), invoice.weight_billed or 0
    exp_base  = get_expected_base_freight(contract, zone, weight) if zone and weight > 0 else None
    base_ref  = exp_base if exp_base is not None else (invoice.base_freight or 0)
    if base_ref <= 0:
        return None

    fuel_ref  = _exp_fuel(base_ref, contract)
    pct       = _cod_pct(contract)
    expected  = _exp_cod(base_ref, fuel_ref, contract)
    diff      = billed - expected
    if diff <= TOLERANCE:
        return None

    gst        = _gst_multiplier(contract)
    overcharge = round(diff * gst, 2)

    return DiscrepancyResult(
        check_type="cod_fee_mismatch",
        severity="high",
        description=(
            f"COD fee overcharge: billed ₹{billed:.2f}, "
            f"expected ₹{expected:.2f} ({pct:.1f}% of base+fuel "
            f"₹{base_ref + fuel_ref:.2f}, overcharge incl. GST = ₹{overcharge:.2f})"
        ),
        billed_value=billed, expected_value=expected, overcharge_amount=overcharge,
        confidence_score=0.92,
        confidence_reason=f"Contract COD rate is {pct:.1f}% of (base freight + fuel surcharge).",
    )


# ─── Check 5: Non-contracted surcharges ───────────────────────────────

def check_non_contracted_surcharge(invoice: InvoiceData, contract: ContractData) -> Optional[DiscrepancyResult]:
    other = invoice.other_surcharges or 0
    if other <= TOLERANCE:
        return None

    gst        = _gst_multiplier(contract)
    overcharge = round(other * gst, 2)

    return DiscrepancyResult(
        check_type="non_contracted_surcharge",
        severity="medium",
        description=(
            f"Non-contracted surcharge ₹{other:.2f} billed — "
            f"contract permits only base freight, fuel, RTO, COD and GST. "
            f"Full amount recoverable incl. GST = ₹{overcharge:.2f}"
        ),
        billed_value=other, expected_value=0, overcharge_amount=overcharge,
        confidence_score=0.95,
        confidence_reason="Contract explicitly prohibits unlisted surcharges.",
    )



# ─── Check 6: Weight overcharge ───────────────────────────────────────
# Fires only when invoice has BOTH weight_billed AND actual_weight.
# If billed weight > actual weight by more than rounding tolerance (0.5 kg),
# the provider is padding weight. Overcharge = difference × contracted rate/kg.

def check_weight_overcharge(invoice: InvoiceData, contract: ContractData) -> Optional[DiscrepancyResult]:
    billed_wt = invoice.weight_billed
    actual_wt  = invoice.actual_weight

    # Only run when both weights are present
    if billed_wt is None or actual_wt is None:
        return None
    if actual_wt <= 0 or billed_wt <= 0:
        return None

    # Allow 0.5 kg rounding tolerance (industry standard)
    WEIGHT_TOLERANCE = 0.5
    padding = billed_wt - actual_wt
    if padding <= WEIGHT_TOLERANCE:
        return None

    # Calculate overcharge: find per-kg rate from contract slab for actual weight
    zone  = (invoice.zone or "").strip()
    nzone = _normalize_zone(zone)

    rate_per_kg = 0.0
    for slab in contract.weight_slabs:
        slab_zone = _normalize_zone(str(slab.get("zone", "")))
        if slab_zone and nzone and slab_zone != nzone:
            continue
        lo = float(slab.get("min", 0))
        hi = float(slab.get("max", 999999))
        if lo <= actual_wt <= hi:
            base    = float(slab.get("base_rate", 0))
            per_kg  = float(slab.get("per_extra_kg", 0))
            slab_wt = hi - lo if hi < 999999 else actual_wt - lo
            if per_kg > 0:
                rate_per_kg = per_kg
            elif slab_wt > 0 and base > 0:
                rate_per_kg = base / max(slab_wt, 1)
            break

    # If no slab found, estimate from base_freight / weight_billed
    if rate_per_kg <= 0 and invoice.base_freight and billed_wt > 0:
        rate_per_kg = invoice.base_freight / billed_wt

    gst        = _gst_multiplier(contract)
    overcharge = round(padding * rate_per_kg * gst, 2) if rate_per_kg > 0 else round(
        # Fallback: prorate base freight
        (padding / billed_wt) * (invoice.base_freight or 0) * gst, 2
    )

    if overcharge <= TOLERANCE:
        return None

    return DiscrepancyResult(
        check_type="weight_overcharge",
        severity="high",
        description=(
            f"Billed weight {billed_wt:.2f} kg exceeds actual weight {actual_wt:.2f} kg "
            f"by {padding:.2f} kg. Weight padding detected — "
            f"overcharge ₹{overcharge:.2f} incl. GST."
        ),
        billed_value=billed_wt,
        expected_value=actual_wt,
        overcharge_amount=overcharge,
        confidence_score=0.97,
        confidence_reason=f"Direct comparison: billed {billed_wt:.2f} kg vs actual {actual_wt:.2f} kg — {padding:.2f} kg padding.",
    )

# ─── Exported check list — order matters, each fires MAX ONCE per AWB ──

ALL_CHECKS = [
    check_base_freight,
    check_fuel_surcharge,
    check_rto,
    check_cod,
    check_non_contracted_surcharge,
    check_weight_overcharge,
]
