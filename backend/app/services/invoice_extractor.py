import os
import json
import base64
import io
from typing import List, Dict, Optional
from app.models.schemas import InvoiceData

INVOICE_EXTRACTION_PROMPT = """
Extract all logistics invoice data from this document. Return a JSON array where each element is one invoice/shipment.

For each shipment extract:
{
  "awb_number": "AWB/tracking number",
  "shipment_date": "date as string",
  "origin_pincode": "6-digit origin pincode",
  "destination_pincode": "6-digit destination pincode",
  "weight_billed": numeric_kg,
  "zone": "zone like A/B/C/D or local",
  "base_freight": numeric_rupees,
  "cod_fee": numeric_rupees_or_null,
  "rto_fee": numeric_rupees_or_null,
  "fuel_surcharge": numeric_rupees_or_null,
  "other_surcharges": numeric_rupees_or_null,
  "gst_rate": numeric_percentage,
  "total_billed": numeric_rupees
}

Return ONLY a valid JSON array, no other text.
"""


def _get_gemini_model():
    """Lazy-load Gemini — only if API key is configured."""
    try:
        from app.core.config import settings
        if not settings.GEMINI_API_KEY:
            return None
        import google.generativeai as genai
        genai.configure(api_key=settings.GEMINI_API_KEY)
        return genai.GenerativeModel("gemini-1.5-flash")
    except Exception:
        return None


async def extract_from_pdf(file_path: str) -> List[InvoiceData]:
    # Try pdfplumber first (no API key needed)
    try:
        from app.services.pdf_extractor import extract_invoices_from_pdf
        invoices = extract_invoices_from_pdf(file_path)
        if invoices:
            return invoices
    except Exception:
        pass
    # Fallback to Gemini if available
    model = _get_gemini_model()
    if not model:
        raise ValueError("Could not extract invoices from PDF. Ensure the PDF has selectable text/tables, or set GEMINI_API_KEY for AI-based extraction.")
    with open(file_path, "rb") as f:
        pdf_b64 = base64.b64encode(f.read()).decode()
    response = model.generate_content([
        {"mime_type": "application/pdf", "data": pdf_b64},
        INVOICE_EXTRACTION_PROMPT
    ])
    return parse_invoice_response(response.text)


async def extract_from_image(file_path: str) -> List[InvoiceData]:
    model = _get_gemini_model()
    if not model:
        raise ValueError("Image extraction requires GEMINI_API_KEY to be set.")
    ext = os.path.splitext(file_path)[1].lower()
    mime_map = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}
    mime = mime_map.get(ext, "image/jpeg")
    with open(file_path, "rb") as f:
        img_b64 = base64.b64encode(f.read()).decode()
    response = model.generate_content([
        {"mime_type": mime, "data": img_b64},
        INVOICE_EXTRACTION_PROMPT
    ])
    return parse_invoice_response(response.text)


async def extract_from_csv(file_path: str) -> List[InvoiceData]:
    # First try direct parsing (fast, reliable)
    direct = _csv_direct_map(file_path)
    if direct:
        return direct

    # Fallback: send to Gemini if available
    model = _get_gemini_model()
    if not model:
        raise ValueError("Could not parse CSV with direct mapping and no GEMINI_API_KEY set.")

    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
        csv_text = f.read()
    lines = csv_text.splitlines()
    if len(lines) > 201:
        csv_text = "\n".join(lines[:201])

    response = model.generate_content([
        f"Here is a logistics invoice CSV file. The column names may vary.\n\n{csv_text}\n\n{INVOICE_EXTRACTION_PROMPT}"
    ])
    return parse_invoice_response(response.text)


def _csv_direct_map(file_path: str) -> List[InvoiceData]:
    """Direct CSV parsing with fuzzy column matching. Skips non-data header rows."""
    try:
        import pandas as pd
    except ImportError:
        return []

    df = None
    for skip in range(0, 6):
        try:
            candidate = pd.read_csv(
                file_path, skiprows=skip,
                on_bad_lines='warn',   # keep rows with extra cols (e.g. Notes column)
                engine='python',       # python engine handles ragged CSVs
            )
            cols = [str(c).lower() for c in candidate.columns]
            has_data_cols = any(
                kw in " ".join(cols)
                for kw in ["awb", "tracking", "consignment", "weight", "freight", "total", "zone"]
            )
            if has_data_cols and len(candidate) > 0:
                df = candidate
                break
        except Exception:
            continue

    if df is None or df.empty:
        return []

    def find_col(df_cols, *keywords):
        for kw in keywords:
            for col in df_cols:
                normalized = col.lower().replace(" ", "_").replace("-", "_").replace("(", "").replace(")", "")
                if kw in normalized:
                    return col
        return None

    cols = list(df.columns)
    mapping = {
        "awb_number":           find_col(cols, "awb_number", "awb", "tracking", "shipment_no", "consignment", "docket"),
        "shipment_date":        find_col(cols, "shipment_date", "date", "booking_date", "ship_date"),
        "origin_pincode":       find_col(cols, "origin_pincode", "origin", "from_pin", "source_pin", "pickup_pin"),
        "destination_pincode":  find_col(cols, "destination_pincode", "destination", "dest_pin", "to_pin", "delivery_pin"),
        "weight_billed":        find_col(cols, "weight_kg", "charged_weight", "billed_weight", "weight"),
        "zone":                 find_col(cols, "zone"),
        "base_freight":         find_col(cols, "base_freight_inr", "base_freight", "freight_charge", "freight", "base_amount"),
        "cod_fee":              find_col(cols, "cod_fee_inr", "cod_fee", "cod_charge", "cod_amount", "cod"),
        "rto_fee":              find_col(cols, "rto_fee_inr", "rto_fee", "rto_charge", "rto_amount", "rto"),
        "fuel_surcharge":       find_col(cols, "fuel_surcharge_inr", "fuel_surcharge", "fuel_charge", "fsc", "fuel"),
        "other_surcharges":     find_col(cols, "other_surcharges_inr", "other_surcharges", "other_surcharge", "other_charge", "misc", "other"),
        "gst_rate":             find_col(cols, "gst_rate", "gst_pct", "gst_percent", "tax_rate", "gst"),
        "total_billed":         find_col(cols, "total_billed_inr", "total_billed", "total_amount", "invoice_amount", "grand_total", "total"),
    }

    invoices = []
    for _, row in df.iterrows():
        data = {}
        for field, col in mapping.items():
            if col is None:
                data[field] = None
                continue
            val = row.get(col)
            str_val = str(val).strip() if val is not None else ""
            if str_val in ("nan", "None", "", "-", "N/A"):
                data[field] = None
            else:
                numeric_fields = {"weight_billed", "base_freight", "cod_fee", "rto_fee",
                                  "fuel_surcharge", "other_surcharges", "gst_rate", "total_billed"}
                if field in numeric_fields:
                    try:
                        data[field] = float(str_val.replace(",", "").replace("INR", "").replace("₹", "").strip())
                    except ValueError:
                        data[field] = None
                else:
                    data[field] = str_val

        awb = data.get("awb_number")
        if not awb or str(awb).lower() in ("awb number", "awb", "nan", "none", ""):
            continue

        try:
            invoices.append(InvoiceData(**data))
        except Exception:
            pass

    return invoices


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
                invoices.append(InvoiceData(**{k: v for k, v in item.items() if k in InvoiceData.model_fields}))
            except Exception:
                pass
        return invoices
    except Exception:
        return []
