import csv
import io
import logging
from typing import List, Optional
from app.models.schemas import InvoiceData, ContractData

logger = logging.getLogger(__name__)

INVOICE_COL_MAP = {
    "awb_number":          ["awb number", "awb", "awb_number", "tracking id", "tracking number", "shipment id"],
    "shipment_date":       ["shipment date", "date", "dispatch date", "booking date"],
    "origin_pincode":      ["origin pincode", "origin pin", "from pincode", "source pincode", "origin_pincode"],
    "destination_pincode": ["destination pincode", "dest pincode", "to pincode", "destination_pincode", "dest pin"],
    "weight_billed":       ["weight (kg)", "weight", "billed weight", "weight_billed", "chargeable weight", "charged weight"],
    "zone":                ["zone", "delivery zone", "service zone"],
    "base_freight":        ["base freight (inr)", "base freight", "freight", "base_freight", "basic freight"],
    "cod_fee":             ["cod fee (inr)", "cod fee", "cod", "cod_fee", "cash on delivery"],
    "rto_fee":             ["rto fee (inr)", "rto fee", "rto", "rto_fee", "return fee"],
    "fuel_surcharge":      ["fuel surcharge (inr)", "fuel surcharge", "fuel", "fuel_surcharge", "fuel charge"],
    "other_surcharges":    ["other surcharges (inr)", "other surcharges", "other charges", "other_surcharges", "misc"],
    "gst_rate":            ["gst rate (%)", "gst rate", "gst%", "gst_rate", "tax rate"],
    "total_billed":        ["total billed (inr)", "total billed", "total", "total_billed", "invoice amount", "amount"],
}

CONTRACT_COL_MAP = {
    "zone":        ["zone"],
    "min_weight":  ["min weight (kg)", "min weight", "min_weight", "from weight"],
    "max_weight":  ["max weight (kg)", "max weight", "max_weight", "to weight"],
    "base_rate":   ["base rate (inr)", "base rate", "base_rate", "rate"],
    "per_kg_rate": ["per extra kg (inr)", "per extra kg", "per_kg_rate", "per kg rate", "extra kg rate"],
}

# Fees realistically never exceed this — anything above is a misread pincode or junk
_MAX_FEE = 5000.0

# Keywords that must appear in the header row for it to be treated as the CSV start
_INVOICE_HEADER_KEYWORDS = {"awb", "shipment", "freight", "weight", "zone", "billed", "cod", "total"}


def _clean_float(val) -> Optional[float]:
    if val is None or str(val).strip() in ("", "-", "N/A", "n/a", "NA"):
        return None
    try:
        return float(str(val).replace(",", "").replace("₹", "").replace("INR", "").strip())
    except Exception:
        return None


def _safe_fee(val: Optional[float], field: str, awb: str) -> Optional[float]:
    """Reject fee values that are unrealistically large (likely a misread pincode)."""
    if val is not None and val > _MAX_FEE:
        logger.warning(
            f"AWB {awb}: {field}={val} exceeds max fee threshold ({_MAX_FEE}) "
            f"— likely a misread pincode, setting to None"
        )
        return None
    return val


def _map_headers(headers: List[str], col_map: dict) -> dict:
    headers_lower = {h.lower().strip(): h for h in headers if h}
    result = {}
    for canonical, aliases in col_map.items():
        for alias in aliases:
            if alias.lower() in headers_lower:
                result[canonical] = headers_lower[alias.lower()]
                break
    return result


def _find_csv_start(lines: List[str], keyword_set: set) -> int:
    """
    Return the index of the first line that:
      - has >= 4 commas (likely a CSV row), AND
      - contains at least one keyword from keyword_set (confirms it is a header row).
    Falls back to the first line with >= 4 commas if no keyword match is found.
    """
    fallback = None
    for i, line in enumerate(lines):
        if line.count(",") >= 4:
            if fallback is None:
                fallback = i
            if any(kw in line.lower() for kw in keyword_set):
                return i
    return fallback or 0


def is_csv(file_path: str) -> bool:
    return file_path.lower().endswith(".csv")


# ---------------------------------------------------------------------------
# Invoice extractor
# ---------------------------------------------------------------------------

def extract_invoices_from_csv(file_path: str) -> List[InvoiceData]:
    with open(file_path, "r", encoding="utf-8-sig", errors="replace") as f:
        content = f.read()

    lines = content.splitlines()
    csv_start = _find_csv_start(lines, _INVOICE_HEADER_KEYWORDS)

    csv_content = "\n".join(lines[csv_start:])
    reader = csv.DictReader(io.StringIO(csv_content))

    # Strip None / empty / whitespace-only keys produced by trailing commas
    headers = [h for h in (reader.fieldnames or []) if h and h.strip()]
    logger.info(f"CSV invoice: detected headers = {headers}")

    if not headers:
        raise ValueError("No headers found in CSV")

    mapping = _map_headers(headers, INVOICE_COL_MAP)
    logger.info(f"CSV invoice: mapped fields = {list(mapping.keys())}")

    if "awb_number" not in mapping and "total_billed" not in mapping:
        raise ValueError("CSV doesn't look like an invoice — missing AWB or total columns")

    invoices = []
    for row in reader:
        # Skip completely empty rows
        values = [str(v).strip() for v in row.values() if v]
        if not values or all(v in ("", "-") for v in values):
            continue

        # Skip footer / metadata rows
        first_val = (list(row.values())[0] or "").strip().lower()
        if any(kw in first_val for kw in ["total", "note", "logistics", "invoice", "provider", "date:"]):
            continue

        def get(field):
            col = mapping.get(field)
            if col is None:
                return None
            val = row.get(col)
            return str(val).strip() if val is not None else None

        awb = get("awb_number")
        if not awb or awb.lower() in ("awb number", "awb", ""):
            continue

        # Parse numeric fee fields with pincode-misread guard
        base  = _safe_fee(_clean_float(get("base_freight")),     "base_freight",     awb)
        cod   = _safe_fee(_clean_float(get("cod_fee")),          "cod_fee",          awb)
        rto   = _safe_fee(_clean_float(get("rto_fee")),          "rto_fee",          awb)
        fuel  = _safe_fee(_clean_float(get("fuel_surcharge")),   "fuel_surcharge",   awb)
        other = _safe_fee(_clean_float(get("other_surcharges")), "other_surcharges", awb)

        invoices.append(InvoiceData(
            awb_number=awb,
            shipment_date=get("shipment_date"),
            origin_pincode=get("origin_pincode"),
            destination_pincode=get("destination_pincode"),
            weight_billed=_clean_float(get("weight_billed")),
            zone=get("zone"),
            base_freight=base,
            cod_fee=cod,
            rto_fee=rto,
            fuel_surcharge=fuel,
            other_surcharges=other,
            gst_rate=_clean_float(get("gst_rate")) or 18.0,
            total_billed=_clean_float(get("total_billed")),
        ))

    logger.info(f"CSV invoice: {len(invoices)} invoices parsed")
    return invoices


# ---------------------------------------------------------------------------
# Contract extractor
# ---------------------------------------------------------------------------

def extract_contract_from_csv(file_path: str) -> ContractData:
    with open(file_path, "r", encoding="utf-8-sig", errors="replace") as f:
        content = f.read()

    weight_slabs  = []
    cod_rate      = None
    cod_rate_type = "percentage"
    rto_rate      = None
    fuel_pct      = None
    gst_pct       = 18.0

    lines = content.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if not line:
            i += 1
            continue
        line_lower = line.lower()

        if "cod_rate" in line_lower or ("cod" in line_lower and "rate" in line_lower):
            for p in line.split(","):
                try:
                    cod_rate = float(p.strip())
                    break
                except Exception:
                    pass
            if "fixed" in line_lower:
                cod_rate_type = "fixed"

        elif "rto_rate" in line_lower or ("rto" in line_lower and "rate" in line_lower):
            for p in line.split(","):
                try:
                    rto_rate = float(p.strip())
                    break
                except Exception:
                    pass

        elif "fuel" in line_lower and ("pct" in line_lower or "surcharge" in line_lower or "%" in line_lower):
            for p in line.split(","):
                try:
                    fuel_pct = float(p.strip())
                    break
                except Exception:
                    pass

        elif "gst" in line_lower and ("pct" in line_lower or "%" in line_lower or "rate" in line_lower):
            for p in line.split(","):
                try:
                    gst_pct = float(p.strip())
                    break
                except Exception:
                    pass

        elif line.count(",") >= 3:
            try:
                reader = csv.DictReader(io.StringIO("\n".join(lines[i:])))
                headers = [h for h in (reader.fieldnames or []) if h and h.strip()]
                mapping = _map_headers(headers, CONTRACT_COL_MAP)

                logger.info(f"CSV contract: detected headers = {headers}")
                logger.info(f"CSV contract: mapped fields = {list(mapping.keys())}")

                if "zone" in mapping and "base_rate" in mapping:
                    for row in reader:
                        def get(field):
                            col = mapping.get(field)
                            if col is None:
                                return None
                            val = row.get(col)
                            return str(val).strip() if val is not None else None

                        zone      = get("zone")
                        base_rate = _clean_float(get("base_rate"))
                        min_wt    = _clean_float(get("min_weight")) or 0
                        max_wt    = _clean_float(get("max_weight")) or 999999
                        per_kg    = _clean_float(get("per_kg_rate")) or 0

                        if zone and base_rate is not None:
                            weight_slabs.append({
                                "zone":         zone,
                                "min":          min_wt,
                                "max":          max_wt,
                                "base_rate":    base_rate,
                                "per_extra_kg": per_kg,
                            })
                    break
            except Exception:
                pass

        i += 1

    logger.info(
        f"CSV contract: {len(weight_slabs)} slabs, COD={cod_rate}, "
        f"RTO={rto_rate}, fuel={fuel_pct}, GST={gst_pct}"
    )

    return ContractData(
        weight_slabs=weight_slabs,
        cod_rate=cod_rate if cod_rate is not None else 2.5,
        cod_rate_type=cod_rate_type,
        rto_rate=rto_rate if rto_rate is not None else 50.0,
        fuel_surcharge_pct=fuel_pct if fuel_pct is not None else 12.0,
        gst_pct=gst_pct,
    )


# ---------------------------------------------------------------------------
# Public helpers (used by the API layer)
# ---------------------------------------------------------------------------

def parse_invoice_csv(content: str) -> list:
    import tempfile, os
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, encoding="utf-8") as f:
        f.write(content)
        tmp = f.name
    try:
        invoices = extract_invoices_from_csv(tmp)
        return [inv.model_dump() for inv in invoices]
    finally:
        os.unlink(tmp)


def parse_contract_csv(content: str) -> dict:
    import tempfile, os
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, encoding="utf-8") as f:
        f.write(content)
        tmp = f.name
    try:
        contract = extract_contract_from_csv(tmp)
        zones = {slab.get("zone"): slab.get("base_rate") for slab in contract.weight_slabs}
        return {
            "zones":                     zones,
            "cod_percentage":            contract.cod_rate or 2.5,
            "rto_percentage":            contract.rto_rate or 50.0,
            "fuel_surcharge_percentage": contract.fuel_surcharge_pct or 12.0,
            "gst_percentage":            contract.gst_pct,
            "contracted_surcharges":     [],
        }
    finally:
        os.unlink(tmp)
