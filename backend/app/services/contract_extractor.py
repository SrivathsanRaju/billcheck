import os
import json
import base64
import csv
import io
from app.models.schemas import ContractData

CONTRACT_EXTRACTION_PROMPT = """
Extract the rate card / contract data from this logistics contract document.

Return a JSON object with this EXACT structure:
{
  "provider": "logistics provider name",
  "weight_slabs": [
    {"zone": "A", "min": 0, "max": 0.5, "base_rate": 45, "per_extra_kg": 0}
  ],
  "cod_rate": 2.5,
  "rto_rate": 50,
  "fuel_surcharge_pct": 12,
  "gst_pct": 18
}

Return ONLY valid JSON, no other text.
"""


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


def parse_csv_contract(file_path: str) -> ContractData:
    """Parse the CSV contract format directly without Gemini."""
    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
        content = f.read()

    lines = content.splitlines()
    weight_slabs = []
    cod_rate = None
    rto_rate = None
    fuel_surcharge_pct = None
    gst_pct = None
    provider = None

    # Detect provider from first non-empty lines
    for line in lines[:5]:
        stripped = line.strip()
        if stripped and not stripped.startswith("Zone") and not stripped.startswith(",") and "," in stripped:
            pass
        elif stripped and not stripped.startswith(","):
            provider = stripped.split("-")[0].strip()
            break

    in_freight_section = False
    in_additional_section = False

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        upper = stripped.upper()
        if "FREIGHT RATE" in upper:
            in_freight_section = True
            in_additional_section = False
            continue
        if "ADDITIONAL CHARGE" in upper:
            in_freight_section = False
            in_additional_section = True
            continue

        # Parse freight rate rows: Zone,Min,Max,Base Rate,Per Extra KG
        if in_freight_section:
            parts = [p.strip() for p in stripped.split(",")]
            if len(parts) >= 4 and parts[0].upper() in ["A","B","C","D","E","F","LOCAL","ZONE_A","ZONE_B","ZONE_C","ZONE_D"]:
                try:
                    zone = parts[0].upper()
                    mn = float(parts[1])
                    mx = float(parts[2])
                    base = float(parts[3])
                    per_kg = float(parts[4]) if len(parts) > 4 and parts[4] else 0.0
                    weight_slabs.append({
                        "zone": zone, "min": mn, "max": mx,
                        "base_rate": base, "per_extra_kg": per_kg,
                    })
                except (ValueError, IndexError):
                    pass

        # Parse additional charges
        if in_additional_section:
            parts = [p.strip() for p in stripped.split(",")]
            if len(parts) >= 2:
                key = parts[0].lower()
                try:
                    val = float(parts[1])
                except ValueError:
                    continue
                if "cod" in key:
                    cod_rate = val
                elif "rto" in key:
                    rto_rate = val
                elif "fuel" in key:
                    fuel_surcharge_pct = val
                elif "gst" in key:
                    gst_pct = val

    # Also try simple Zone,Rate format (our sample contract)
    if not weight_slabs:
        weight_slabs, cod_rate, rto_rate, fuel_surcharge_pct, gst_pct = _parse_simple_zone_csv(content)

    return ContractData(
        provider=provider,
        weight_slabs=weight_slabs,
        cod_rate=cod_rate if cod_rate is not None else 1.5,
        rto_rate=rto_rate if rto_rate is not None else 50.0,
        fuel_surcharge_pct=fuel_surcharge_pct if fuel_surcharge_pct is not None else 12.0,
        gst_pct=gst_pct if gst_pct is not None else 18.0,
        raw_data={"weight_slabs": weight_slabs},
    )


def _parse_simple_zone_csv(content: str):
    """Handle simple Zone,Rate,COD%,RTO%,Fuel%,GST% format."""
    import csv as csv_mod
    import io as io_mod
    reader = csv_mod.DictReader(io_mod.StringIO(content.strip()))
    weight_slabs = []
    cod_rate = rto_rate = fuel_pct = gst_pct = None

    for row in reader:
        norm = {k.lower().strip().replace(" ", "_").replace("%", "").replace("(", "").replace(")", ""): str(v).strip()
                for k, v in row.items() if k}
        zone = norm.get("zone") or norm.get("zone_name") or ""
        if not zone:
            continue
        try:
            rate = float(norm.get("rate") or norm.get("base_rate") or 0)
            weight_slabs.append({"zone": zone.upper(), "min": 0, "max": 999, "base_rate": rate, "per_extra_kg": 0})
        except Exception:
            pass
        try:
            if norm.get("cod_percentage"):
                cod_rate = float(norm["cod_percentage"])
            if norm.get("rto_percentage"):
                rto_rate = float(norm["rto_percentage"])
            if norm.get("fuel_surcharge_percentage"):
                fuel_pct = float(norm["fuel_surcharge_percentage"])
            if norm.get("gst_percentage"):
                gst_pct = float(norm["gst_percentage"])
        except Exception:
            pass

    return weight_slabs, cod_rate, rto_rate, fuel_pct, gst_pct


async def extract_contract(file_path: str) -> ContractData:
    ext = os.path.splitext(file_path)[1].lower()

    # CSV: always try direct parsing first
    if ext == ".csv":
        result = parse_csv_contract(file_path)
        if result.weight_slabs or result.cod_rate:
            return result

    # PDF/image or CSV fallback: use Gemini if available
    model = _get_gemini_model()
    if not model:
        # Return defaults if no Gemini
        return ContractData()

    try:
        if ext == ".pdf":
            # Try pdfplumber first
            try:
                from app.services.pdf_extractor import extract_contract_from_pdf
                result = extract_contract_from_pdf(file_path)
                if result.weight_slabs or result.cod_rate:
                    return result
            except Exception:
                pass
            if not model:
                return ContractData()
            with open(file_path, "rb") as f:
                pdf_b64 = base64.b64encode(f.read()).decode()
            response = model.generate_content([
                {"mime_type": "application/pdf", "data": pdf_b64},
                CONTRACT_EXTRACTION_PROMPT
            ])
        elif ext in [".jpg", ".jpeg", ".png", ".webp"]:
            mime_map = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}
            with open(file_path, "rb") as f:
                img_b64 = base64.b64encode(f.read()).decode()
            response = model.generate_content([
                {"mime_type": mime_map.get(ext, "image/jpeg"), "data": img_b64},
                CONTRACT_EXTRACTION_PROMPT
            ])
        else:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                text = f.read()
            response = model.generate_content([
                f"Extract contract data:\n\n{text}\n\n{CONTRACT_EXTRACTION_PROMPT}"
            ])
        return parse_contract_response(response.text)
    except Exception:
        return ContractData()


def parse_contract_response(text: str) -> ContractData:
    text = text.strip()
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0]
    elif "```" in text:
        text = text.split("```")[1].split("```")[0]
    try:
        data = json.loads(text)
        data["raw_data"] = data.copy()
        valid_fields = ContractData.model_fields.keys()
        return ContractData(**{k: v for k, v in data.items() if k in valid_fields})
    except Exception:
        return ContractData()
