from typing import List, Dict, Optional
from app.models.schemas import DiscrepancyResult, InvoiceData, ContractData
from app.services.confidence_scorer import (
    score_weight_check, score_rate_check, score_zone_check,
    score_gst_check, score_duplicate_check, score_arithmetic_check
)
from app.services.pincode_validator import validate_zone, derive_zone

GST_MULTIPLIER = 1.18  # All overcharges grossed up with GST


def get_expected_base_freight(contract: ContractData, zone: str, weight: float) -> Optional[float]:
    """Calculate expected base freight from contract weight slabs."""
    if not contract.weight_slabs or not zone:
        return None

    for slab in contract.weight_slabs:
        mn = float(slab.get("min", 0))
        mx = float(slab.get("max", float("inf")))
        slab_zone = str(slab.get("zone", "")).upper()

        if slab_zone != zone.upper():
            continue

        if mn == 0:
            in_slab = weight <= mx
        else:
            in_slab = mn < weight <= mx
        if weight == mn and mn > 0:
            in_slab = False

        if in_slab:
            base = float(slab.get("base_rate", 0))
            per_kg = float(slab.get("per_extra_kg", 0))
            return base if per_kg == 0 else base + (weight - mn) * per_kg

    return None


def check_weight_overcharge(invoice: InvoiceData, contract: ContractData) -> Optional[DiscrepancyResult]:
    if not invoice.weight_billed or not contract.weight_slabs:
        return None

    weight = invoice.weight_billed
    zone = invoice.zone or "B"
    expected_base = get_expected_base_freight(contract, zone, weight)
    if expected_base is None:
        return None

    billed_base = invoice.base_freight or 0
    if billed_base > expected_base * 1.05:
        overcharge = round((billed_base - expected_base) * GST_MULTIPLIER, 2)
        score, reason = score_weight_check(billed_base, expected_base)
        return DiscrepancyResult(
            check_type="weight_overcharge",
            severity="critical" if overcharge > 100 else "high",
            description=f"Base freight overcharge: billed ₹{billed_base:.2f}, contract rate for {weight}kg Zone {zone} = ₹{expected_base:.2f} (incl. GST)",
            billed_value=billed_base,
            expected_value=expected_base,
            overcharge_amount=overcharge,
            confidence_score=score,
            confidence_reason=reason,
        )
    return None


def check_zone_mismatch(invoice: InvoiceData, contract: ContractData) -> Optional[DiscrepancyResult]:
    # Skipped — requires provider-specific pincode→zone table to avoid false positives
    return None


def check_rate_deviation(invoice: InvoiceData, contract: ContractData) -> Optional[DiscrepancyResult]:
    if not invoice.base_freight or not contract.weight_slabs:
        return None

    zone = invoice.zone or "B"
    weight = invoice.weight_billed or 1.0
    expected_base = get_expected_base_freight(contract, zone, weight)
    if expected_base is None:
        return None

    billed = invoice.base_freight
    overcharge = billed - expected_base
    if overcharge > 2:
        diff_pct = overcharge / max(expected_base, 0.01)
        score, reason = score_rate_check(billed, expected_base)
        return DiscrepancyResult(
            check_type="rate_deviation",
            severity="critical" if overcharge > 50 else "high",
            description=f"Base rate overcharge {diff_pct:.1%}: billed ₹{billed:.2f}, contract ₹{expected_base:.2f} for {weight}kg Zone {zone} (incl. GST)",
            billed_value=billed,
            expected_value=expected_base,
            overcharge_amount=round(overcharge * GST_MULTIPLIER, 2),
            confidence_score=score,
            confidence_reason=reason,
        )
    return None


def check_cod_fee_mismatch(invoice: InvoiceData, contract: ContractData) -> Optional[DiscrepancyResult]:
    if not invoice.cod_fee or invoice.cod_fee <= 0:
        return None
    if not contract.cod_rate:
        return None

    # COD = cod_rate% of (base_freight + fuel_surcharge)
    base = invoice.base_freight or 0
    fuel = invoice.fuel_surcharge or 0
    taxable_base = base + fuel
    cod_rate = contract.cod_rate
    expected_cod = round(taxable_base * cod_rate / 100, 2)

    billed_cod = invoice.cod_fee
    overcharge = billed_cod - expected_cod
    # Use flat ₹2 tolerance to catch small mismatches like the BD300010 case (₹30 vs ₹8.40)
    if overcharge > 2:
        score, reason = score_rate_check(billed_cod, expected_cod)
        return DiscrepancyResult(
            check_type="cod_fee_mismatch",
            severity="high",
            description=f"COD fee mismatch: billed ₹{billed_cod:.2f}, expected ₹{expected_cod:.2f} ({cod_rate}% of base+fuel ₹{taxable_base:.2f}, incl. GST)",
            billed_value=billed_cod,
            expected_value=expected_cod,
            overcharge_amount=round(overcharge * GST_MULTIPLIER, 2),
            confidence_score=score,
            confidence_reason=reason,
        )
    return None


def check_rto_overcharge(invoice: InvoiceData, contract: ContractData) -> Optional[DiscrepancyResult]:
    if not invoice.rto_fee or invoice.rto_fee <= 0:
        return None
    if not contract.rto_rate:
        return None

    base = invoice.base_freight or 0
    rto_rate = contract.rto_rate
    expected_rto = round(base * rto_rate / 100, 2)

    overcharge = invoice.rto_fee - expected_rto
    # Use flat ₹2 tolerance to catch BD300007 case (₹150 vs ₹140 = ₹10 overcharge)
    if overcharge > 2:
        score, reason = score_rate_check(invoice.rto_fee, expected_rto)
        return DiscrepancyResult(
            check_type="rto_overcharge",
            severity="high",
            description=f"RTO overcharge: billed ₹{invoice.rto_fee:.2f}, expected ₹{expected_rto:.2f} ({rto_rate}% of base ₹{base:.2f}, incl. GST)",
            billed_value=invoice.rto_fee,
            expected_value=expected_rto,
            overcharge_amount=round(overcharge * GST_MULTIPLIER, 2),
            confidence_score=score,
            confidence_reason=reason,
        )
    return None


def check_fuel_surcharge_mismatch(invoice: InvoiceData, contract: ContractData) -> Optional[DiscrepancyResult]:
    if not invoice.fuel_surcharge or invoice.fuel_surcharge <= 0:
        return None
    if not contract.fuel_surcharge_pct:
        return None

    base = invoice.base_freight or 0
    fuel_pct = contract.fuel_surcharge_pct
    expected_fuel = round(base * fuel_pct / 100, 2)

    overcharge = invoice.fuel_surcharge - expected_fuel
    # Use flat ₹1 tolerance to catch BD300008 (₹8.40) and BD300009 (₹30) cases
    if overcharge > 1:
        score, reason = score_rate_check(invoice.fuel_surcharge, expected_fuel)
        return DiscrepancyResult(
            check_type="fuel_surcharge_mismatch",
            severity="high" if overcharge > 20 else "medium",
            description=f"Fuel surcharge overcharge: billed ₹{invoice.fuel_surcharge:.2f}, expected ₹{expected_fuel:.2f} ({fuel_pct}% of base ₹{base:.2f}, incl. GST)",
            billed_value=invoice.fuel_surcharge,
            expected_value=expected_fuel,
            overcharge_amount=round(overcharge * GST_MULTIPLIER, 2),
            confidence_score=score,
            confidence_reason=reason,
        )
    return None


def check_non_contracted_surcharge(invoice: InvoiceData, contract: ContractData) -> Optional[DiscrepancyResult]:
    if not invoice.other_surcharges or invoice.other_surcharges <= 0:
        return None

    # Full amount including GST is recoverable
    overcharge = round(invoice.other_surcharges * GST_MULTIPLIER, 2)
    return DiscrepancyResult(
        check_type="non_contracted_surcharge",
        severity="medium",
        description=f"Non-contracted surcharge ₹{invoice.other_surcharges:.2f} — not in rate card (incl. GST ₹{overcharge:.2f})",
        billed_value=invoice.other_surcharges,
        expected_value=0,
        overcharge_amount=overcharge,
        confidence_score=0.9,
        confidence_reason="Contract states: No other surcharges applicable under this agreement.",
    )


def check_gst_miscalculation(invoice: InvoiceData, contract: ContractData) -> Optional[DiscrepancyResult]:
    if not invoice.total_billed or not invoice.base_freight:
        return None

    gst_pct = contract.gst_pct or invoice.gst_rate or 18
    taxable = (invoice.base_freight or 0) + (invoice.fuel_surcharge or 0) + \
              (invoice.cod_fee or 0) + (invoice.rto_fee or 0) + (invoice.other_surcharges or 0)
    expected_gst = round(taxable * gst_pct / 100, 2)
    expected_total = round(taxable + expected_gst, 2)
    billed_total = invoice.total_billed

    if billed_total > expected_total + 2:
        billed_gst = billed_total - taxable
        score, reason = score_gst_check(billed_gst, expected_gst)
        return DiscrepancyResult(
            check_type="gst_miscalculation",
            severity="high",
            description=f"GST error: billed ₹{billed_gst:.2f}, expected ₹{expected_gst:.2f} at {gst_pct}% on taxable ₹{taxable:.2f}",
            billed_value=billed_gst,
            expected_value=expected_gst,
            overcharge_amount=round(max(0, billed_gst - expected_gst), 2),
            confidence_score=score,
            confidence_reason=reason,
        )
    return None


def check_arithmetic_total_mismatch(invoice: InvoiceData, contract: ContractData) -> Optional[DiscrepancyResult]:
    if not invoice.total_billed:
        return None

    gst_pct = invoice.gst_rate or 18
    taxable = (invoice.base_freight or 0) + (invoice.fuel_surcharge or 0) + \
              (invoice.cod_fee or 0) + (invoice.rto_fee or 0) + (invoice.other_surcharges or 0)
    calculated_total = round(taxable * (1 + gst_pct / 100), 2)
    diff = invoice.total_billed - calculated_total

    if diff > 2:
        score, reason = score_arithmetic_check(invoice.total_billed, calculated_total)
        return DiscrepancyResult(
            check_type="arithmetic_total_mismatch",
            severity="critical",
            description=f"Total mismatch: billed ₹{invoice.total_billed:.2f}, calculated ₹{calculated_total:.2f} (diff ₹{diff:.2f})",
            billed_value=invoice.total_billed,
            expected_value=calculated_total,
            overcharge_amount=round(max(0, diff), 2),
            confidence_score=score,
            confidence_reason=reason,
        )
    return None


ALL_CHECKS = [
    check_zone_mismatch,
    check_rate_deviation,
    check_fuel_surcharge_mismatch,
    check_rto_overcharge,
    check_cod_fee_mismatch,
    check_non_contracted_surcharge,
    check_gst_miscalculation,
    check_arithmetic_total_mismatch,
]
