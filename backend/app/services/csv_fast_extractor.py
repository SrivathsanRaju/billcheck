import csv
import io
import logging
from typing import List, Optional
from app.models.schemas import InvoiceData, ContractData, WeightSlab

logger = logging.getLogger(__name__)

INVOICE_COL_MAP = {
    "awb_number":          ["awb number", "awb", "awb_number", "tracking id", "tracking number", "shipment id"],
    "shipment_date":       ["shipment date", "date", "dispatch date", "booking date"],
    "origin_pincode":      ["origin pincode", "origin pin", "from pincode", "source pincode", "origin_pincode"],
    "destination_pincode": ["destination pincode", "dest pincode", "to pincode", "destination_pincode", "dest pin"],
    "weight_billed":       ["weight (kg)", "weight", "billed weight", "weight_billed", "chargeable weight"],
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


def _clean_float(val) -> Optional[float]:
    if val is None or str(val).strip() in ('', '-', 'N/A', 'n/a', 'NA'):
        return None
    try:
        return float(str(val).replace(',', '').replace('₹', '').replace('INR', '').strip())
    except Exception:
        return None


def _map_headers(headers: List[str], col_map: dict) -> dict:
    headers_lower = {h.lower().strip(): h for h in headers if h}
    result = {}
    for canonical, aliases in col_map.items():
        for alias in aliases:
            if alias.lower() in headers_lower:
                result[canonical] = headers_lower[alias.lower()]
                break
    return result


def is_csv(file_path: str) -> bool:
    return file_path.lower().endswith('.csv')


def extract_invoices_from_csv(file_path: str) -> List[InvoiceData]:
    with open(file_path, 'r', encoding='utf-8-sig', errors='replace') as f:
        content = f.read()

    lines = content.splitlines()
    csv_start = 0
    for i, line in enumerate(lines):
        if line.count(',') >= 4:
            csv_start = i
            break

    csv_content = '\n'.join(lines[csv_start:])
    reader = csv.DictReader(io.StringIO(csv_content))
    headers = reader.fieldnames or []

    if not headers:
        raise ValueError("No headers found in CSV")

    mapping = _map_headers([h for h in headers if h], INVOICE_COL_MAP)
    logger.info(f"CSV fast extract: mapped fields = {list(mapping.keys())}")

    if 'awb_number' not in mapping and 'total_billed' not in mapping:
        raise ValueError("CSV doesn't look like an invoice — missing AWB or total columns")

    invoices = []
    for row in reader:
        values = [str(v).strip() for v in row.values() if v]
        if not values or all(v in ('', '-') for v in values):
            continue
        first_val = (list(row.values())[0] or '').strip().lower()
        if any(kw in first_val for kw in ['total', 'note', 'logistics', 'invoice', 'provider', 'date:']):
            continue

        def get(field):
            col = mapping.get(field)
            if col is None:
                return None
            val = row.get(col)
            return str(val).strip() if val is not None else None

        awb = get('awb_number')
        if not awb or awb.lower() in ('awb number', 'awb', ''):
            continue

        invoices.append(InvoiceData(
            awb_number=awb,
            shipment_date=get('shipment_date'),
            origin_pincode=get('origin_pincode'),
            destination_pincode=get('destination_pincode'),
            weight_billed=_clean_float(get('weight_billed')),
            zone=get('zone'),
            base_freight=_clean_float(get('base_freight')),
            cod_fee=_clean_float(get('cod_fee')),
            rto_fee=_clean_float(get('rto_fee')),
            fuel_surcharge=_clean_float(get('fuel_surcharge')),
            other_surcharges=_clean_float(get('other_surcharges')),
            gst_rate=_clean_float(get('gst_rate')) or 18.0,
            total_billed=_clean_float(get('total_billed')),
        ))

    logger.info(f"CSV fast extract: {len(invoices)} invoices parsed")
    return invoices


def extract_contract_from_csv(file_path: str) -> ContractData:
    with open(file_path, 'r', encoding='utf-8-sig', errors='replace') as f:
        content = f.read()

    weight_slabs = []
    cod_rate = None
    cod_rate_type = "percentage"
    rto_rate = None
    fuel_pct = None
    gst_pct = 18.0

    lines = content.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if not line:
            i += 1
            continue
        line_lower = line.lower()

        if 'cod_rate' in line_lower or ('cod' in line_lower and 'rate' in line_lower):
            for p in line.split(','):
                try:
                    cod_rate = float(p.strip())
                    break
                except Exception:
                    pass
            if 'fixed' in line_lower:
                cod_rate_type = 'fixed'

        elif 'rto_rate' in line_lower or ('rto' in line_lower and 'rate' in line_lower):
            for p in line.split(','):
                try:
                    rto_rate = float(p.strip())
                    break
                except Exception:
                    pass

        elif 'fuel' in line_lower and ('pct' in line_lower or 'surcharge' in line_lower or '%' in line_lower):
            for p in line.split(','):
                try:
                    fuel_pct = float(p.strip())
                    break
                except Exception:
                    pass

        elif 'gst' in line_lower and ('pct' in line_lower or '%' in line_lower or 'rate' in line_lower):
            for p in line.split(','):
                try:
                    gst_pct = float(p.strip())
                    break
                except Exception:
                    pass

        elif line.count(',') >= 3:
            try:
                reader = csv.DictReader(io.StringIO('\n'.join(lines[i:])))
                headers = [h for h in (reader.fieldnames or []) if h]
                mapping = _map_headers(headers, CONTRACT_COL_MAP)

                if 'zone' in mapping and 'base_rate' in mapping:
                    for row in reader:
                        def get(field):
                            col = mapping.get(field)
                            if col is None:
                                return None
                            val = row.get(col)
                            return str(val).strip() if val is not None else None

                        zone = get('zone')
                        base_rate = _clean_float(get('base_rate'))
                        min_w = _clean_float(get('min_weight'))
                        max_w = _clean_float(get('max_weight'))

                        if zone and base_rate is not None and min_w is not None:
                            weight_slabs.append(WeightSlab(
                                zone=zone.upper(),
                                min_weight=min_w,
                                max_weight=max_w or 999.0,
                                base_rate=base_rate,
                                per_kg_rate=_clean_float(get('per_kg_rate')) or 0.0,
                            ))
                    break
            except Exception:
                pass

        i += 1

    logger.info(f"CSV contract: {len(weight_slabs)} slabs, COD={cod_rate}, fuel={fuel_pct}, GST={gst_pct}")

    return ContractData(
        weight_slabs=weight_slabs,
        cod_rate=cod_rate if cod_rate is not None else 1.5,
        cod_rate_type=cod_rate_type,
        rto_rate=rto_rate if rto_rate is not None else 50.0,
        fuel_surcharge_pct=fuel_pct if fuel_pct is not None else 12.0,
        gst_pct=gst_pct,
    )


# Legacy function aliases used by processor.py
def parse_invoice_csv(content: str) -> list:
    """Legacy: parse invoice CSV from string content."""
    import tempfile, os
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, encoding='utf-8') as f:
        f.write(content)
        tmp = f.name
    try:
        invoices = extract_invoices_from_csv(tmp)
        return [inv.model_dump() for inv in invoices]
    finally:
        os.unlink(tmp)


def parse_contract_csv(content: str) -> dict:
    """Legacy: parse contract CSV from string content."""
    import tempfile, os
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, encoding='utf-8') as f:
        f.write(content)
        tmp = f.name
    try:
        contract = extract_contract_from_csv(tmp)
        # Convert to the dict format expected by discrepancy_engine
        zones = {}
        for slab in contract.weight_slabs:
            zones[slab.zone] = slab.base_rate
        return {
            "zones": zones,
            "cod_percentage": contract.cod_rate or 1.5,
            "rto_percentage": contract.rto_rate or 50.0,
            "fuel_surcharge_percentage": contract.fuel_surcharge_pct or 12.0,
            "gst_percentage": contract.gst_pct,
            "contracted_surcharges": [],
        }
    finally:
        os.unlink(tmp)
