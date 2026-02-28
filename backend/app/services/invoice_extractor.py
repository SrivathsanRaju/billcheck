"""
Universal invoice extractor — works for ANY logistics provider.
Supports: BlueDart, Delhivery, DTDC, Ekart, Shadowfax, XpressBees,
          FedEx, DHL, Ecom Express, Smartr, Borzo, and more.
Input formats: CSV, PDF, JPG/PNG/WEBP
"""
import os
import json
import base64
from typing import List, Optional
from app.models.schemas import InvoiceData

INVOICE_EXTRACTION_PROMPT = """
You are a logistics billing expert. Extract ALL shipment line items from this invoice document.

The document may come from ANY Indian logistics provider: BlueDart, Delhivery, DTDC, Ekart,
Shadowfax, XpressBees, FedEx, DHL, Ecom Express, Smartr, or any other courier company.

Column names vary by provider. Map them intelligently:
- AWB / Docket / Tracking / Consignment / Shipment No → awb_number
- Date / Booking Date / Dispatch Date / Invoice Date → shipment_date  
- Origin / From Pin / Pickup Pincode / Source → origin_pincode
- Destination / To Pin / Delivery Pincode / Consignee Pin → destination_pincode
- Weight (kg) / Chargeable Weight / Billed Weight / Charged Wt → weight_billed (numeric kg)
- Zone / Service Zone / Delivery Zone / Rate Zone → zone (single letter: A/B/C/D/E)
- Base Freight / Freight / Basic Freight / Transport Charge → base_freight (numeric ₹)
- Fuel Surcharge / FSC / Fuel / Fuel Levy → fuel_surcharge (numeric ₹, null if absent)
- COD / COD Fee / Cash on Delivery Charge → cod_fee (numeric ₹, null if absent)
- RTO / Return / RTO Fee / Return Charge → rto_fee (numeric ₹, null if absent)
- Other / Misc / Special Handling / Surcharge / DG Charge → other_surcharges (numeric ₹, null if absent)
- GST / Tax / IGST / CGST+SGST rate → gst_rate (numeric %, default 18 if not found)
- Total / Amount / Invoice Amount / Grand Total / Billed Amount → total_billed (numeric ₹)

Return a JSON ARRAY where each element is one shipment:
[
  {
    "awb_number": "BD12345678",
    "shipment_date": "15-Jan-2025",
    "origin_pincode": "110001",
    "destination_pincode": "400001",
    "weight_billed": 2.5,
    "zone": "B",
    "base_freight": 280.00,
    "fuel_surcharge": 33.60,
    "cod_fee": null,
    "rto_fee": null,
    "other_surcharges": null,
    "gst_rate": 18,
    "total_billed": 370.30
  }
]

RULES:
- Return ONLY a valid JSON array, no other text
- numeric fields must be numbers not strings
- null for absent charges, NOT 0
- Include every single row/shipment in the document
- If zone is missing, infer from context or leave null
"""

# ─── Universal CSV column aliases — covers all major Indian providers ──────

UNIVERSAL_COL_MAP = {
    "awb_number": [
        "awb", "awb_number", "awb_no", "tracking", "tracking_no", "tracking_number",
        "shipment_no", "shipment_number", "consignment", "consignment_no", "docket",
        "docket_no", "airway_bill", "waybill", "waybill_no", "lrn", "cn_no",
        # Delhivery
        "order_id", "reference_no",
        # DTDC
        "dtdc_consignment",
        # Ekart
        "ekl_id", "tracking_id",
        # Shadowfax
        "sfx_order_id",
    ],
    "shipment_date": [
        "date", "shipment_date", "booking_date", "dispatch_date", "ship_date",
        "pickup_date", "invoice_date", "order_date", "manifest_date",
    ],
    "origin_pincode": [
        "origin", "origin_pincode", "origin_pin", "from_pin", "from_pincode",
        "source_pin", "source_pincode", "pickup_pin", "pickup_pincode",
        "sender_pincode", "shipper_pincode",
    ],
    "destination_pincode": [
        "destination", "destination_pincode", "dest_pin", "to_pin", "to_pincode",
        "delivery_pin", "delivery_pincode", "consignee_pin", "consignee_pincode",
        "receiver_pincode",
    ],
    "weight_billed": [
        "weight", "weight_kg", "billed_weight", "charged_weight", "chargeable_weight",
        "billable_weight", "actual_weight", "volumetric_weight", "wt_kg",
        # Delhivery uses
        "charge_wt",
        # DTDC uses
        "billed_wt",
    ],
    "zone": [
        "zone", "delivery_zone", "service_zone", "rate_zone", "zone_code",
        "origin_zone", "dest_zone",
    ],
    "base_freight": [
        "base_freight", "freight", "basic_freight", "freight_charge", "freight_amount",
        "base_amount", "transport_charge", "forwarding_charge",
        # Delhivery
        "forward_charge", "fwd_charge",
        # DTDC
        "basic_charge", "air_freight",
        # Ecom Express
        "delivery_charge",
    ],
    "fuel_surcharge": [
        "fuel_surcharge", "fuel", "fsc", "fuel_charge", "fuel_levy",
        "fuel_surcharge_amount", "fuel_surcharge_inr",
        # Delhivery
        "fuel_charges",
        # DTDC
        "fuel_surcharge_amt",
    ],
    "cod_fee": [
        "cod", "cod_fee", "cod_charge", "cod_amount", "cash_on_delivery",
        "cod_collection_fee", "cod_handling",
        # Delhivery
        "cod_charges",
    ],
    "rto_fee": [
        "rto", "rto_fee", "rto_charge", "rto_amount", "return_fee",
        "return_charge", "return_to_origin", "rto_forward_charge",
        # Delhivery
        "rto_charges",
    ],
    "other_surcharges": [
        "other", "other_surcharges", "other_charges", "misc", "miscellaneous",
        "additional_charges", "special_handling", "dg_charge", "oda_charge",
        "remote_area", "oversize", "surcharge", "special_service",
        # Delhivery
        "other_charges",
        # DTDC
        "misc_charges",
    ],
    "gst_rate": [
        "gst", "gst_rate", "gst_pct", "gst_percent", "tax_rate",
        "igst_rate", "sgst_rate", "cgst_rate",
    ],
    "total_billed": [
        "total", "total_billed", "total_amount", "invoice_amount", "billed_amount",
        "grand_total", "payable_amount", "net_amount", "amount_payable",
        "total_inr", "total_billed_inr",
        # Delhivery
        "total_charges",
        # DTDC
        "invoice_value",
    ],
}


def _get_gemini_model():
    try:
        from app.core.config import settings
        if not settings.GEMINI_API_KEY:
            return None
        import google.generativeai as genai
        genai.configure(api_key=settings.GEMINI_API_KEY)
        return genai.GenerativeModel("gemini-1.5-flash")
    except Exception:
        return None


def _clean_numeric(val) -> Optional[float]:
    if val is None:
        return None
    s = str(val).replace(",", "").replace("₹", "").replace("INR", "").replace(" ", "").strip()
    if s in ("", "-", "N/A", "nan", "None", "null"):
        return None
    try:
        return float(s)
    except ValueError:
        return None


def _find_col(columns: list, aliases: list) -> Optional[str]:
    """Fuzzy column matcher — case insensitive, ignores spaces/special chars."""
    import re
    def norm(s): return re.sub(r'[^a-z0-9]', '', str(s).lower())
    normed_cols = {norm(c): c for c in columns if c}
    for alias in aliases:
        a = norm(alias)
        for k, orig in normed_cols.items():
            if a == k or a in k or k in a:
                return orig
    return None


def _csv_direct_map(file_path: str) -> List[InvoiceData]:
    """Universal direct CSV parser — tries multiple header row offsets."""
    try:
        import pandas as pd
    except ImportError:
        return []

    df = None
    for skip in range(0, 8):
        try:
            candidate = pd.read_csv(
                file_path, skiprows=skip,
                on_bad_lines='warn',
                engine='python',
                encoding='utf-8-sig',
            )
            cols = " ".join(str(c).lower() for c in candidate.columns)
            has_key_col = any(kw in cols for kw in [
                "awb", "tracking", "consignment", "docket", "waybill",
                "weight", "freight", "total", "zone", "shipment"
            ])
            if has_key_col and len(candidate) > 0:
                df = candidate
                break
        except Exception:
            continue

    if df is None or df.empty:
        return []

    cols = list(df.columns)
    mapping = {field: _find_col(cols, aliases) for field, aliases in UNIVERSAL_COL_MAP.items()}

    invoices = []
    numeric_fields = {
        "weight_billed", "base_freight", "cod_fee", "rto_fee",
        "fuel_surcharge", "other_surcharges", "gst_rate", "total_billed"
    }

    for _, row in df.iterrows():
        data = {}
        for field, col in mapping.items():
            if col is None:
                data[field] = None
                continue
            val = row.get(col)
            str_val = str(val).strip() if val is not None else ""
            if str_val in ("nan", "None", "", "-", "N/A", "n/a"):
                data[field] = None
            elif field in numeric_fields:
                data[field] = _clean_numeric(str_val)
            else:
                data[field] = str_val

        awb = data.get("awb_number")
        if not awb or str(awb).lower() in ("awb number", "awb", "nan", "none", ""):
            continue

        # Default GST to 18 if missing
        if not data.get("gst_rate"):
            data["gst_rate"] = 18.0

        try:
            invoices.append(InvoiceData(**data))
        except Exception:
            pass

    return invoices


async def extract_from_csv(file_path: str) -> List[InvoiceData]:
    direct = _csv_direct_map(file_path)
    if direct:
        return direct

    model = _get_gemini_model()
    if not model:
        raise ValueError("Could not parse CSV. Ensure column headers are present or set GEMINI_API_KEY.")

    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
        csv_text = f.read()
    lines = csv_text.splitlines()
    if len(lines) > 201:
        csv_text = "\n".join(lines[:201])

    response = model.generate_content([
        f"Here is a logistics invoice CSV from an Indian logistics provider. Column names may vary by provider.\n\n{csv_text}\n\n{INVOICE_EXTRACTION_PROMPT}"
    ])
    return parse_invoice_response(response.text)


async def extract_from_pdf(file_path: str) -> List[InvoiceData]:
    # Try pdfplumber first (no API key)
    try:
        from app.services.pdf_extractor import extract_invoices_from_pdf
        invoices = extract_invoices_from_pdf(file_path)
        if invoices:
            return invoices
    except Exception:
        pass

    # Fallback to Gemini
    model = _get_gemini_model()
    if not model:
        raise ValueError("Could not extract from PDF. Ensure PDF has selectable text or set GEMINI_API_KEY.")

    with open(file_path, "rb") as f:
        pdf_b64 = base64.b64encode(f.read()).decode()

    response = model.generate_content([
        {"mime_type": "application/pdf", "data": pdf_b64},
        INVOICE_EXTRACTION_PROMPT,
    ])
    return parse_invoice_response(response.text)


async def extract_from_image(file_path: str) -> List[InvoiceData]:
    model = _get_gemini_model()
    if not model:
        raise ValueError("Image extraction requires GEMINI_API_KEY.")

    ext = os.path.splitext(file_path)[1].lower()
    mime_map = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}
    mime = mime_map.get(ext, "image/jpeg")

    with open(file_path, "rb") as f:
        img_b64 = base64.b64encode(f.read()).decode()

    response = model.generate_content([
        {"mime_type": mime, "data": img_b64},
        INVOICE_EXTRACTION_PROMPT,
    ])
    return parse_invoice_response(response.text)


async def extract_invoice(file_path: str) -> List[InvoiceData]:
    ext = os.path.splitext(file_path)[1].lower()
    try:
        if ext == ".pdf":
            return await extract_from_pdf(file_path)
        elif ext in [".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff"]:
            return await extract_from_image(file_path)
        else:
            return await extract_from_csv(file_path)
    except Exception:
        return []


def parse_invoice_response(text: str) -> List[InvoiceData]:
    text = text.strip()
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0]
    elif "```" in text:
        text = text.split("```")[1].split("```")[0]
    try:
        data = json.loads(text)
        if isinstance(data, dict):
            data = [data]
        invoices = []
        for item in data:
            try:
                # Default GST to 18 if missing
                if not item.get("gst_rate"):
                    item["gst_rate"] = 18.0
                invoices.append(InvoiceData(**{
                    k: v for k, v in item.items()
                    if k in InvoiceData.model_fields
                }))
            except Exception:
                pass
        return invoices
    except Exception:
        return []
