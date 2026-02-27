"""PDF invoice and contract extractor using pdfplumber — no API key required."""
import io
import logging
import re
from typing import List, Dict, Any, Optional
import pdfplumber
from app.models.schemas import InvoiceData, ContractData

logger = logging.getLogger(__name__)

INVOICE_COL_MAP = {
    "awb_number":           ["awb", "awb_number", "tracking", "shipment_no", "consignment", "docket", "airway bill"],
    "shipment_date":        ["date", "shipment_date", "booking_date", "dispatch_date"],
    "origin_pincode":       ["origin", "from_pin", "source", "origin_pincode", "pickup"],
    "destination_pincode":  ["destination", "dest", "to_pin", "delivery", "destination_pincode"],
    "weight_billed":        ["weight", "billed_weight", "charged_weight", "weight_kg"],
    "zone":                 ["zone", "delivery_zone", "service_zone"],
    "base_freight":         ["base_freight", "freight", "base_amount", "basic_freight"],
    "cod_fee":              ["cod", "cod_fee", "cash_on_delivery"],
    "rto_fee":              ["rto", "rto_fee", "return_fee"],
    "fuel_surcharge":       ["fuel", "fuel_surcharge", "fsc", "fuel_charge"],
    "other_surcharges":     ["other", "misc", "other_surcharges", "other_charges"],
    "gst_rate":             ["gst", "gst_rate", "tax_rate", "gst_pct"],
    "total_billed":         ["total", "total_billed", "amount", "invoice_amount", "grand_total"],
}


def _norm(s: str) -> str:
    return re.sub(r'[^a-z0-9]', '_', str(s).lower().strip()).strip('_')


def _find_col(headers: List[str], aliases: List[str]) -> Optional[str]:
    normed = {_norm(h): h for h in headers if h}
    for alias in aliases:
        a = _norm(alias)
        for k, orig in normed.items():
            if a in k or k in a:
                return orig
    return None


def _safe_float(val: Any) -> Optional[float]:
    if val is None:
        return None
    s = re.sub(r'[₹,\s]', '', str(val)).strip()
    if s in ('', '-', 'N/A', 'nan', 'None'):
        return None
    try:
        return float(s)
    except Exception:
        return None


def _extract_tables_from_pdf(path: str) -> List[List[List[str]]]:
    """Return list of tables, each table is list of rows, each row is list of cells."""
    tables = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            for table in page.extract_tables():
                if table and len(table) > 1:
                    tables.append([[str(c).strip() if c else '' for c in row] for row in table])
    return tables


def _extract_text_from_pdf(path: str) -> str:
    text = ''
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            t = page.extract_text()
            if t:
                text += t + '\n'
    return text


def _parse_invoice_table(table: List[List[str]]) -> List[InvoiceData]:
    """Try to parse a table as an invoice table."""
    if not table or len(table) < 2:
        return []

    # Find header row — look for row with most recognizable column names
    header_row_idx = 0
    best_score = 0
    for i, row in enumerate(table[:5]):
        score = sum(
            1 for cell in row
            if any(_norm(alias) in _norm(cell) for aliases in INVOICE_COL_MAP.values() for alias in aliases)
        )
        if score > best_score:
            best_score = score
            header_row_idx = i

    if best_score < 2:
        return []

    headers = table[header_row_idx]
    mapping = {field: _find_col(headers, aliases) for field, aliases in INVOICE_COL_MAP.items()}

    def get(row_dict: Dict, field: str) -> Optional[str]:
        col = mapping.get(field)
        if col is None:
            return None
        val = row_dict.get(col, '')
        return val if val and val not in ('-', 'N/A', '') else None

    invoices = []
    for row in table[header_row_idx + 1:]:
        if len(row) != len(headers):
            # Pad or trim
            row = row[:len(headers)] + [''] * max(0, len(headers) - len(row))
        row_dict = dict(zip(headers, row))

        # Skip empty or subtotal rows
        values = [v for v in row_dict.values() if v and v.strip()]
        if not values:
            continue
        first = list(row_dict.values())[0].strip().lower()
        if any(kw in first for kw in ['total', 'subtotal', 'grand', 'note', 'summary']):
            continue

        awb = get(row_dict, 'awb_number')
        if not awb:
            continue

        try:
            invoices.append(InvoiceData(
                awb_number=awb,
                shipment_date=get(row_dict, 'shipment_date'),
                origin_pincode=get(row_dict, 'origin_pincode'),
                destination_pincode=get(row_dict, 'destination_pincode'),
                weight_billed=_safe_float(get(row_dict, 'weight_billed')),
                zone=get(row_dict, 'zone'),
                base_freight=_safe_float(get(row_dict, 'base_freight')),
                cod_fee=_safe_float(get(row_dict, 'cod_fee')),
                rto_fee=_safe_float(get(row_dict, 'rto_fee')),
                fuel_surcharge=_safe_float(get(row_dict, 'fuel_surcharge')),
                other_surcharges=_safe_float(get(row_dict, 'other_surcharges')),
                gst_rate=_safe_float(get(row_dict, 'gst_rate')) or 18.0,
                total_billed=_safe_float(get(row_dict, 'total_billed')),
            ))
        except Exception:
            pass

    return invoices


def extract_invoices_from_pdf(path: str) -> List[InvoiceData]:
    """Extract invoices from PDF using table detection."""
    try:
        tables = _extract_tables_from_pdf(path)
        logger.info(f"PDF: found {len(tables)} tables")

        all_invoices = []
        for table in tables:
            invoices = _parse_invoice_table(table)
            if invoices:
                all_invoices.extend(invoices)
                logger.info(f"PDF table parsed: {len(invoices)} invoices")

        if all_invoices:
            return all_invoices

        # Fallback: try to parse raw text as CSV-like content
        logger.info("PDF: no tables found, trying text extraction")
        text = _extract_text_from_pdf(path)
        return _parse_invoice_from_text(text)

    except Exception as e:
        logger.error(f"PDF invoice extraction failed: {e}")
        return []


def _parse_invoice_from_text(text: str) -> List[InvoiceData]:
    """Last-resort: try to parse whitespace-delimited text as invoice data."""
    import csv
    import io as sio
    # Try reading as CSV with various delimiters
    for delimiter in [',', '\t', '|', ';']:
        try:
            lines = [l for l in text.splitlines() if l.strip()]
            if not lines:
                continue
            sample = '\n'.join(lines)
            reader = list(csv.DictReader(sio.StringIO(sample), delimiter=delimiter))
            if not reader:
                continue
            headers = list(reader[0].keys())
            score = sum(
                1 for h in headers
                if any(_norm(alias) in _norm(h) for aliases in INVOICE_COL_MAP.values() for alias in aliases)
            )
            if score >= 3:
                table = [headers] + [[row.get(h, '') for h in headers] for row in reader]
                invoices = _parse_invoice_table(table)
                if invoices:
                    return invoices
        except Exception:
            continue
    return []


def extract_contract_from_pdf(path: str) -> ContractData:
    """Extract contract/rate card from PDF."""
    try:
        tables = _extract_tables_from_pdf(path)
        text = _extract_text_from_pdf(path)

        weight_slabs = []
        cod_rate = None
        rto_rate = None
        fuel_pct = None
        gst_pct = 18.0

        # Parse tables for rate card data
        for table in tables:
            if not table or len(table) < 2:
                continue
            headers = table[0]
            header_text = ' '.join(headers).lower()

            # Detect weight slab table
            if any(kw in header_text for kw in ['zone', 'rate', 'weight', 'slab']):
                zone_col = _find_col(headers, ['zone'])
                min_col = _find_col(headers, ['min', 'from', 'min_weight'])
                max_col = _find_col(headers, ['max', 'to', 'max_weight', 'upto'])
                rate_col = _find_col(headers, ['rate', 'base_rate', 'base_freight', 'amount'])
                per_kg_col = _find_col(headers, ['per_kg', 'per_extra', 'extra_kg'])

                if zone_col and rate_col:
                    for row in table[1:]:
                        row_dict = dict(zip(headers, row + [''] * max(0, len(headers) - len(row))))
                        zone = row_dict.get(zone_col, '').strip().upper()
                        rate = _safe_float(row_dict.get(rate_col))
                        if zone and rate is not None:
                            weight_slabs.append({
                                'zone': zone,
                                'min': _safe_float(row_dict.get(min_col, '0')) or 0,
                                'max': _safe_float(row_dict.get(max_col, '999')) or 999,
                                'base_rate': rate,
                                'per_extra_kg': _safe_float(row_dict.get(per_kg_col, '0')) or 0,
                            })

        # Parse text for surcharge rates
        lines = text.lower().splitlines()
        for line in lines:
            line = line.strip()
            nums = re.findall(r'[\d.]+', line)
            if not nums:
                continue
            val = float(nums[0])

            if 'cod' in line and ('rate' in line or '%' in line or 'charge' in line):
                cod_rate = val
            elif 'rto' in line and ('rate' in line or '%' in line):
                rto_rate = val
            elif 'fuel' in line and ('surcharge' in line or '%' in line or 'pct' in line):
                fuel_pct = val
            elif 'gst' in line and ('%' in line or 'rate' in line or 'pct' in line):
                gst_pct = val

        logger.info(f"PDF contract: {len(weight_slabs)} slabs, COD={cod_rate}, fuel={fuel_pct}, GST={gst_pct}")

        return ContractData(
            weight_slabs=weight_slabs,
            cod_rate=cod_rate if cod_rate is not None else 1.5,
            rto_rate=rto_rate if rto_rate is not None else 50.0,
            fuel_surcharge_pct=fuel_pct if fuel_pct is not None else 12.0,
            gst_pct=gst_pct,
        )

    except Exception as e:
        logger.error(f"PDF contract extraction failed: {e}")
        return ContractData()
