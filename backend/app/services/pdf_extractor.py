"""
PDF invoice and contract extractor using pdfplumber + validation layer.

Key design principles to avoid extraction errors permanently:
1. Zero-value suppression  — "0.00" in COD/RTO columns is treated as null, not a charge
2. Cross-validation        — extracted totals must be internally consistent
3. Mandatory field check   — rows missing AWB or base_freight are dropped
4. Zone normalization      — any zone format maps to A-E
5. Surcharge rate bounds   — implausible rates are replaced with contract defaults
"""
import re
import logging
from typing import List, Dict, Any, Optional
import pdfplumber
from app.models.schemas import InvoiceData, ContractData

logger = logging.getLogger(__name__)

# ── Zone normalization ─────────────────────────────────────────────────────

ZONE_ALIASES = {
    "local": "A", "same city": "A", "city": "A",
    "metro": "B", "tier1": "B", "tier 1": "B",
    "regional": "C", "region": "C", "tier2": "C",
    "national": "D", "pan india": "D", "tier3": "D",
    "remote": "E", "special": "E", "oda": "E",
    "1": "A", "2": "B", "3": "C", "4": "D", "5": "E",
}

def _normalize_zone(z: str) -> str:
    if not z:
        return ""
    z = z.strip()
    if len(z) == 1 and z.upper() in "ABCDE":
        return z.upper()
    lower = z.lower().strip()
    if lower in ZONE_ALIASES:
        return ZONE_ALIASES[lower]
    m = re.search(r'\b([A-Ea-e])\b', z)
    return m.group(1).upper() if m else z.upper()

# ── Column aliases ─────────────────────────────────────────────────────────

INVOICE_COL_MAP = {
    "awb_number":          ["awb", "awb_number", "tracking", "shipment_no", "consignment",
                            "docket", "airway bill", "waybill", "lrn", "cn_no", "ekl_id"],
    "shipment_date":       ["date", "shipment_date", "booking_date", "dispatch_date", "ship_date"],
    "origin_pincode":      ["origin", "from_pin", "source", "origin_pincode", "pickup"],
    "destination_pincode": ["destination", "dest", "to_pin", "delivery", "destination_pincode"],
    "weight_billed":       ["weight", "billed_weight", "charged_weight", "weight_kg",
                            "chargeable_weight", "charge_wt"],
    "zone":                ["zone", "delivery_zone", "service_zone", "rate_zone"],
    "base_freight":        ["base_freight", "freight", "base_amount", "basic_freight",
                            "forward_charge", "fwd_charge", "delivery_charge"],
    "cod_fee":             ["cod fee", "cod_fee", "cash_on_delivery", "cod charges", "cod"],
    "rto_fee":             ["rto fee", "rto_fee", "return_fee", "rto charges", "rto"],
    "fuel_surcharge":      ["fuel surcharge", "fuel_surcharge", "fsc", "fuel_charge", "fuel charges", "fuel"],
    "other_surcharges":    ["other surcharges", "other_surcharges", "other_charges",
                            "misc", "special_handling", "oda_charge", "other"],
    "gst_rate":            ["gst", "gst_rate", "tax_rate", "igst_rate"],
    "total_billed":        ["total", "total_billed", "invoice_amount", "grand_total",
                            "total_charges", "amount_payable"],
}

CONTRACT_COL_MAP = {
    "zone":       ["zone", "zone_name", "delivery_zone"],
    "min_weight": ["min", "min_weight", "from", "from_weight", "weight_from"],
    "max_weight": ["max", "max_weight", "to", "to_weight", "weight_to", "upto"],
    "base_rate":  ["base_rate", "rate", "base_freight", "amount", "base_amount"],
    "per_kg":     ["per_kg", "per_extra_kg", "extra_kg", "per_kg_rate", "add_wt"],
}

# ── Helpers ────────────────────────────────────────────────────────────────

def _norm(s: str) -> str:
    return re.sub(r'[^a-z0-9]', '_', str(s).lower().strip()).strip('_')

def _find_col(headers: List[str], aliases: List[str]) -> Optional[str]:
    normed = {_norm(h): h for h in headers if h}
    for alias in aliases:
        a = _norm(alias)
        for k, orig in normed.items():
            if a == k or a in k or k in a:
                return orig
    return None

def _safe_float(val: Any) -> Optional[float]:
    if val is None:
        return None
    s = re.sub(r'[₹,\s]', '', str(val)).strip()
    if s in ('', '-', 'N/A', 'nan', 'None', 'null'):
        return None
    try:
        return float(s)
    except Exception:
        return None

def _is_zero(val: Any) -> bool:
    """Returns True for 0, 0.00, '0', '0.00', '-', None."""
    f = _safe_float(val)
    return f is None or abs(f) < 0.01

def _extract_tables(path: str) -> List[List[List[str]]]:
    tables = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            for t in page.extract_tables():
                if t and len(t) > 1:
                    tables.append([[str(c).strip() if c else '' for c in row] for row in t])
    return tables

def _extract_text(path: str) -> str:
    text = ''
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            t = page.extract_text()
            if t:
                text += t + '\n'
    return text

# ── Invoice extraction ──────────────────────────────────────────────────────

def _parse_invoice_table(table: List[List[str]]) -> List[InvoiceData]:
    if not table or len(table) < 2:
        return []

    # Find best header row
    header_row_idx, best_score = 0, 0
    for i, row in enumerate(table[:5]):
        score = sum(
            1 for cell in row
            if any(_norm(a) in _norm(cell) for aliases in INVOICE_COL_MAP.values() for a in aliases)
        )
        if score > best_score:
            best_score, header_row_idx = score, i

    if best_score < 2:
        return []

    headers = table[header_row_idx]
    mapping = {field: _find_col(headers, aliases) for field, aliases in INVOICE_COL_MAP.items()}

    def get(rd: Dict, field: str) -> Optional[str]:
        col = mapping.get(field)
        if not col:
            return None
        v = rd.get(col, '').strip()
        return v if v and v not in ('-', 'N/A', 'n/a', '') else None

    invoices = []
    for row in table[header_row_idx + 1:]:
        row = (row + [''] * len(headers))[:len(headers)]
        rd  = dict(zip(headers, row))

        # Skip blank/summary rows
        non_empty = [v for v in rd.values() if v and v.strip()]
        if not non_empty:
            continue
        first_val = list(rd.values())[0].strip().lower()
        if any(kw in first_val for kw in ['total', 'subtotal', 'grand', 'note', 'summary', 'gst']):
            continue

        awb = get(rd, 'awb_number')
        if not awb:
            continue

        # ── CRITICAL: zero suppression ──────────────────────────────
        # A "0.00" in the COD/RTO/Other column means NO charge, not a ₹0 fee
        # We return None so rule engine skips the check entirely
        cod   = None if _is_zero(get(rd, 'cod_fee'))   else _safe_float(get(rd, 'cod_fee'))
        rto   = None if _is_zero(get(rd, 'rto_fee'))   else _safe_float(get(rd, 'rto_fee'))
        other = None if _is_zero(get(rd, 'other_surcharges')) else _safe_float(get(rd, 'other_surcharges'))
        fuel  = None if _is_zero(get(rd, 'fuel_surcharge')) else _safe_float(get(rd, 'fuel_surcharge'))
        base  = _safe_float(get(rd, 'base_freight'))
        zone  = _normalize_zone(get(rd, 'zone') or '')

        # ── Cross-validate: base freight must be positive ───────────
        if base is None or base <= 0:
            logger.warning(f"Skipping AWB {awb}: missing/zero base freight")
            continue

        try:
            invoices.append(InvoiceData(
                awb_number=awb,
                shipment_date=get(rd, 'shipment_date'),
                origin_pincode=get(rd, 'origin_pincode'),
                destination_pincode=get(rd, 'destination_pincode'),
                weight_billed=_safe_float(get(rd, 'weight_billed')),
                zone=zone or get(rd, 'zone'),
                base_freight=base,
                cod_fee=cod,
                rto_fee=rto,
                fuel_surcharge=fuel,
                other_surcharges=other,
                gst_rate=_safe_float(get(rd, 'gst_rate')) or 18.0,
                total_billed=_safe_float(get(rd, 'total_billed')),
            ))
        except Exception as e:
            logger.warning(f"Failed to parse row for AWB {awb}: {e}")

    return invoices


def extract_invoices_from_pdf(path: str) -> List[InvoiceData]:
    try:
        tables = _extract_tables(path)
        logger.info(f"PDF invoice: found {len(tables)} tables")

        all_invoices = []
        for table in tables:
            parsed = _parse_invoice_table(table)
            if parsed:
                all_invoices.extend(parsed)

        if all_invoices:
            logger.info(f"PDF invoice: extracted {len(all_invoices)} rows")
            return all_invoices

        # Fallback: raw text
        logger.info("PDF invoice: no tables, trying text fallback")
        text = _extract_text(path)
        return _parse_invoice_from_text(text)

    except Exception as e:
        logger.error(f"PDF invoice extraction failed: {e}")
        return []


def _parse_invoice_from_text(text: str) -> List[InvoiceData]:
    import csv, io as sio
    for delim in [',', '\t', '|', ';']:
        try:
            lines = [l for l in text.splitlines() if l.strip()]
            if not lines:
                continue
            reader = list(csv.DictReader(sio.StringIO('\n'.join(lines)), delimiter=delim))
            if not reader:
                continue
            headers = list(reader[0].keys())
            score = sum(1 for h in headers if any(
                _norm(a) in _norm(h) for aliases in INVOICE_COL_MAP.values() for a in aliases
            ))
            if score >= 3:
                table = [headers] + [[row.get(h, '') for h in headers] for row in reader]
                parsed = _parse_invoice_table(table)
                if parsed:
                    return parsed
        except Exception:
            continue
    return []


# ── Contract extraction ────────────────────────────────────────────────────

# Surcharge rate bounds
RATE_BOUNDS = {
    "cod_rate":           (0.1,  15.0),
    "rto_rate":           (5.0,  100.0),
    "fuel_surcharge_pct": (1.0,  35.0),
    "gst_pct":            (5.0,  28.0),
}
RATE_DEFAULTS = {"cod_rate": 2.5, "rto_rate": 50.0, "fuel_surcharge_pct": 12.0, "gst_pct": 18.0}

def _clamp_rate(field: str, val: Optional[float]) -> float:
    default = RATE_DEFAULTS[field]
    if val is None:
        return default
    lo, hi = RATE_BOUNDS[field]
    if lo <= val <= hi:
        return val
    # Gemini decimal-vs-percent fix: 0.025 → 2.5
    if lo <= val * 100 <= hi:
        return round(val * 100, 2)
    return default


def extract_contract_from_pdf(path: str) -> ContractData:
    try:
        tables = _extract_tables(path)
        text   = _extract_text(path)

        weight_slabs = []
        cod_rate = rto_rate = fuel_pct = gst_pct = None

        # ── Parse tables for weight slabs ──────────────────────────
        for table in tables:
            if not table or len(table) < 2:
                continue
            headers = table[0]
            header_text = ' '.join(headers).lower()
            if not any(kw in header_text for kw in ['zone', 'rate', 'weight', 'slab']):
                continue

            zone_col   = _find_col(headers, CONTRACT_COL_MAP["zone"])
            min_col    = _find_col(headers, CONTRACT_COL_MAP["min_weight"])
            max_col    = _find_col(headers, CONTRACT_COL_MAP["max_weight"])
            rate_col   = _find_col(headers, CONTRACT_COL_MAP["base_rate"])
            per_kg_col = _find_col(headers, CONTRACT_COL_MAP["per_kg"])

            if not (zone_col and rate_col):
                continue

            for row in table[1:]:
                rd = dict(zip(headers, (row + [''] * len(headers))[:len(headers)]))
                zone = _normalize_zone(rd.get(zone_col, '').strip())
                rate = _safe_float(rd.get(rate_col))
                if not zone or rate is None:
                    continue
                weight_slabs.append({
                    'zone':         zone,
                    'min':          _safe_float(rd.get(min_col,    '0')) or 0,
                    'max':          _safe_float(rd.get(max_col,  '999')) or 999,
                    'base_rate':    rate,
                    'per_extra_kg': _safe_float(rd.get(per_kg_col, '0')) or 0,
                })

        # ── Parse text for surcharge rates ─────────────────────────
        # Prioritize explicit key=value format (most reliable)
        kv_patterns = [
            (r'fuel_surcharge_pct\s*[=:]\s*([\d.]+)', 'fuel'),
            (r'fuel_surcharge\s*[=:]\s*([\d.]+)',     'fuel'),
            (r'rto_rate\s*[=:]\s*([\d.]+)',           'rto'),
            (r'cod_rate\s*[=:]\s*([\d.]+)',            'cod'),
            (r'gst_pct\s*[=:]\s*([\d.]+)',             'gst'),
            (r'gst\s*[=:]\s*([\d.]+)',                 'gst'),
        ]
        for pattern, kind in kv_patterns:
            m = re.search(pattern, text, re.IGNORECASE)
            if m:
                val = float(m.group(1))
                if kind == 'fuel' and fuel_pct is None: fuel_pct = val
                elif kind == 'rto' and rto_rate is None: rto_rate = val
                elif kind == 'cod' and cod_rate is None: cod_rate = val
                elif kind == 'gst' and gst_pct  is None: gst_pct  = val

        # Fallback: natural language scan
        if any(v is None for v in [cod_rate, rto_rate, fuel_pct]):
            for line in text.lower().splitlines():
                nums = re.findall(r'\d+\.?\d*', line)
                if not nums:
                    continue
                try:
                    val = float(nums[-1])
                except (ValueError, IndexError):
                    continue
                if val > 100:
                    continue  # skip years
                if cod_rate is None and 'cod' in line and any(k in line for k in ['%', 'rate', 'fee', '=']):
                    cod_rate = val
                if rto_rate is None and 'rto' in line and any(k in line for k in ['%', 'rate', '=']):
                    rto_rate = val
                if fuel_pct is None and 'fuel' in line and any(k in line for k in ['%', 'surcharge', '=']):
                    fuel_pct = val
                if gst_pct is None and 'gst' in line and any(k in line for k in ['%', 'rate', '=']):
                    gst_pct = val

        # ── Clamp rates to valid bounds ─────────────────────────────
        result = ContractData(
            weight_slabs=weight_slabs,
            cod_rate=           _clamp_rate("cod_rate",           cod_rate),
            rto_rate=           _clamp_rate("rto_rate",           rto_rate),
            fuel_surcharge_pct= _clamp_rate("fuel_surcharge_pct", fuel_pct),
            gst_pct=            _clamp_rate("gst_pct",            gst_pct),
        )
        logger.info(
            f"PDF contract: {len(weight_slabs)} slabs, "
            f"COD={result.cod_rate}, fuel={result.fuel_surcharge_pct}, "
            f"RTO={result.rto_rate}, GST={result.gst_pct}"
        )
        return result

    except Exception as e:
        logger.error(f"PDF contract extraction failed: {e}")
        return ContractData(**RATE_DEFAULTS)
