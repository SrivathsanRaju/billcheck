"""
Universal contract extractor — works for ANY logistics provider.
Supports CSV, PDF, and image contract formats.
"""
import os
import json
import base64
import re
from app.models.schemas import ContractData

CONTRACT_EXTRACTION_PROMPT = """
You are a logistics billing expert. Extract the rate card from this contract document.

The contract may be from ANY Indian logistics provider: BlueDart, Delhivery, DTDC, Ekart,
Shadowfax, XpressBees, FedEx, DHL, Ecom Express, Smartr, or any other courier.

Extract ALL weight slabs for ALL zones. Zone names may be letters (A/B/C/D/E),
words (Local/Metro/Regional/National/Remote), or numbers (1/2/3/4/5) — normalize to letters.

Return ONLY this JSON structure, no other text:
{
  "provider": "provider name from document",
  "weight_slabs": [
    {"zone": "A", "min": 0, "max": 0.5, "base_rate": 80, "per_extra_kg": 0},
    {"zone": "A", "min": 0.5, "max": 1, "base_rate": 120, "per_extra_kg": 0},
    {"zone": "B", "min": 0, "max": 0.5, "base_rate": 110, "per_extra_kg": 0}
  ],
  "cod_rate": 2.5,
  "rto_rate": 50,
  "fuel_surcharge_pct": 12,
  "gst_pct": 18
}

CRITICAL:
- cod_rate = NUMBER like 2.5 (means 2.5 percent, NOT 0.025)
- rto_rate = NUMBER like 50 (means 50 percent, NOT 0.5)
- fuel_surcharge_pct = NUMBER like 12 (means 12 percent, NOT 0.12)
- gst_pct = NUMBER like 18 (means 18 percent, NOT 0.18)
- Extract EVERY weight slab row from EVERY zone
- per_extra_kg = 0 if flat rate slab
- Return ONLY valid JSON, no markdown, no explanation
"""

# Zone name normalization — words → letters
ZONE_NORMALIZE = {
    "local": "A", "same_city": "A", "city": "A", "metro": "B",
    "regional": "C", "region": "C", "national": "D", "pan_india": "D",
    "remote": "E", "special": "E", "oda": "E",
    "1": "A", "2": "B", "3": "C", "4": "D", "5": "E",
    "i": "A", "ii": "B", "iii": "C", "iv": "D", "v": "E",
}

# Contract rate defaults per Indian logistics standards
DEFAULTS = {
    "cod_rate":           2.5,
    "rto_rate":           50.0,
    "fuel_surcharge_pct": 12.0,
    "gst_pct":            18.0,
}

# Validation bounds — if Gemini returns outside these, it's wrong
VALID_BOUNDS = {
    "cod_rate":           (0.1,  15.0),
    "rto_rate":           (5.0,  100.0),
    "fuel_surcharge_pct": (1.0,  35.0),
    "gst_pct":            (5.0,  28.0),
}


def _normalize_zone(z: str) -> str:
    z = z.strip().upper()
    if z in ("A", "B", "C", "D", "E"):
        return z
    lower = z.lower().replace(" ", "_").replace("-", "_")
    return ZONE_NORMALIZE.get(lower, z[0] if z else "B")


def _validate_rates(data: dict) -> dict:
    """Fix rates that are out of bounds — usually Gemini returning 0.025 instead of 2.5."""
    for field, (lo, hi) in VALID_BOUNDS.items():
        val = data.get(field)
        try:
            val = float(val)
            if lo <= val <= hi:
                data[field] = val
            elif lo <= val * 100 <= hi:
                # Gemini returned decimal (0.025) instead of percent (2.5)
                data[field] = round(val * 100, 2)
            else:
                data[field] = DEFAULTS[field]
        except (TypeError, ValueError):
            data[field] = DEFAULTS[field]
    return data


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
    """
    Universal CSV contract parser.
    Handles structured CSV with sections (FREIGHT RATES / ADDITIONAL CHARGES)
    and simple flat Zone,Rate,... format.
    """
    with open(file_path, "r", encoding="utf-8-sig", errors="replace") as f:
        content = f.read()

    lines = content.splitlines()
    weight_slabs = []
    cod_rate = rto_rate = fuel_surcharge_pct = gst_pct = None
    provider = None

    # Try to detect provider from first few lines
    for line in lines[:6]:
        s = line.strip()
        if s and not s.startswith(",") and len(s) > 3:
            # First non-empty non-csv line is likely provider name
            p = re.split(r'[-–,]', s)[0].strip()
            if p and not any(c.isdigit() for c in p[:4]):
                provider = p
                break

    in_freight  = False
    in_surcharge = False

    for line in lines:
        s = line.strip()
        if not s:
            continue
        upper = s.upper()

        # Section detection
        if any(kw in upper for kw in ["FREIGHT RATE", "RATE CARD", "WEIGHT SLAB", "BASE RATE"]):
            in_freight = True
            in_surcharge = False
            continue
        if any(kw in upper for kw in ["ADDITIONAL CHARGE", "SURCHARGE", "OTHER CHARGE", "APPLICABLE CHARGE"]):
            in_freight = False
            in_surcharge = True
            continue

        # Parse freight slab rows
        if in_freight and s.count(",") >= 3:
            parts = [p.strip() for p in s.split(",")]
            try:
                zone = _normalize_zone(parts[0])
                if not zone or parts[0].lower() in ("zone", "z", "zone_name", ""):
                    continue
                mn     = float(parts[1])
                mx     = float(parts[2])
                base   = float(parts[3])
                per_kg = float(parts[4]) if len(parts) > 4 and parts[4] else 0
                weight_slabs.append({
                    "zone": zone, "min": mn, "max": mx,
                    "base_rate": base, "per_extra_kg": per_kg,
                })
            except (ValueError, IndexError):
                pass

        # Parse surcharge rows
        if in_surcharge and "," in s:
            parts = [p.strip() for p in s.split(",")]
            if len(parts) >= 2:
                key = parts[0].lower().replace(" ", "_").replace("%", "")
                try:
                    val = float(parts[1].replace("%", "").strip())
                except ValueError:
                    continue
                if any(k in key for k in ["cod", "cash_on_delivery"]):
                    cod_rate = val
                elif any(k in key for k in ["rto", "return"]):
                    rto_rate = val
                elif any(k in key for k in ["fuel", "fsc"]):
                    fuel_surcharge_pct = val
                elif any(k in key for k in ["gst", "tax", "igst"]):
                    gst_pct = val

    # Fallback: simple flat CSV format
    if not weight_slabs:
        weight_slabs, cod_rate, rto_rate, fuel_surcharge_pct, gst_pct = _parse_flat_csv(content)

    return ContractData(
        provider=provider,
        weight_slabs=weight_slabs,
        cod_rate=           cod_rate            if cod_rate is not None            else DEFAULTS["cod_rate"],
        rto_rate=           rto_rate            if rto_rate is not None            else DEFAULTS["rto_rate"],
        fuel_surcharge_pct= fuel_surcharge_pct  if fuel_surcharge_pct is not None  else DEFAULTS["fuel_surcharge_pct"],
        gst_pct=            gst_pct             if gst_pct is not None             else DEFAULTS["gst_pct"],
        raw_data={"weight_slabs": weight_slabs},
    )


def _parse_flat_csv(content: str):
    """Parse simple flat Zone,Rate,COD%,RTO%,Fuel%,GST% CSV format."""
    import csv, io
    reader = csv.DictReader(io.StringIO(content.strip()))
    weight_slabs = []
    cod_rate = rto_rate = fuel_pct = gst_pct = None

    def norm_key(k):
        return re.sub(r'[^a-z0-9]', '_', str(k).lower().strip()).strip('_')

    for row in reader:
        normed = {norm_key(k): str(v).strip() for k, v in row.items() if k}
        zone = normed.get("zone") or normed.get("zone_name") or ""
        if not zone:
            continue
        zone = _normalize_zone(zone)
        try:
            mn  = float(normed.get("min_weight") or normed.get("min") or normed.get("from_weight") or 0)
            mx  = float(normed.get("max_weight") or normed.get("max") or normed.get("to_weight") or 999)
            base= float(normed.get("base_rate") or normed.get("rate") or normed.get("base_rate_inr") or 0)
            pkg = float(normed.get("per_extra_kg") or normed.get("per_kg") or 0)
            weight_slabs.append({"zone": zone, "min": mn, "max": mx, "base_rate": base, "per_extra_kg": pkg})
        except Exception:
            pass
        # Pick up surcharge rates if present in same row
        try:
            if normed.get("cod_percentage") or normed.get("cod_rate"):
                cod_rate = float(normed.get("cod_percentage") or normed.get("cod_rate"))
            if normed.get("rto_percentage") or normed.get("rto_rate"):
                rto_rate = float(normed.get("rto_percentage") or normed.get("rto_rate"))
            if normed.get("fuel_surcharge_percentage") or normed.get("fuel_pct"):
                fuel_pct = float(normed.get("fuel_surcharge_percentage") or normed.get("fuel_pct"))
            if normed.get("gst_percentage") or normed.get("gst_pct"):
                gst_pct  = float(normed.get("gst_percentage") or normed.get("gst_pct"))
        except Exception:
            pass

    return weight_slabs, cod_rate, rto_rate, fuel_pct, gst_pct


def parse_contract_response(text: str) -> ContractData:
    """Parse and validate Gemini's contract JSON response."""
    text = text.strip()
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0]
    elif "```" in text:
        text = text.split("```")[1].split("```")[0]
    try:
        data = json.loads(text)
        data = _validate_rates(data)

        # Normalize zone names in weight slabs
        for slab in data.get("weight_slabs", []):
            if "zone" in slab:
                slab["zone"] = _normalize_zone(str(slab["zone"]))

        data["raw_data"] = data.copy()
        valid_fields = ContractData.model_fields.keys()
        return ContractData(**{k: v for k, v in data.items() if k in valid_fields})
    except Exception:
        return ContractData(**DEFAULTS)


async def extract_contract(file_path: str) -> ContractData:
    ext = os.path.splitext(file_path)[1].lower()

    # CSV — always direct parse first, most reliable
    if ext == ".csv":
        result = parse_csv_contract(file_path)
        if result.weight_slabs or result.cod_rate:
            return result

    # PDF — try pdfplumber text extraction first
    if ext == ".pdf":
        try:
            from app.services.pdf_extractor import extract_contract_from_pdf
            result = extract_contract_from_pdf(file_path)
            if result.weight_slabs and len(result.weight_slabs) > 2:
                # Validate rates even from pdfplumber
                result.cod_rate           = _validate_rates({"cod_rate": result.cod_rate})["cod_rate"]
                result.rto_rate           = _validate_rates({"rto_rate": result.rto_rate})["rto_rate"]
                result.fuel_surcharge_pct = _validate_rates({"fuel_surcharge_pct": result.fuel_surcharge_pct})["fuel_surcharge_pct"]
                return result
        except Exception:
            pass

    # Gemini fallback for PDF / image / unknown
    model = _get_gemini_model()
    if not model:
        return ContractData(**DEFAULTS)

    try:
        if ext == ".pdf":
            with open(file_path, "rb") as f:
                pdf_b64 = base64.b64encode(f.read()).decode()
            response = model.generate_content([
                {"mime_type": "application/pdf", "data": pdf_b64},
                CONTRACT_EXTRACTION_PROMPT,
            ])
        elif ext in [".jpg", ".jpeg", ".png", ".webp"]:
            mime_map = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}
            with open(file_path, "rb") as f:
                img_b64 = base64.b64encode(f.read()).decode()
            response = model.generate_content([
                {"mime_type": mime_map.get(ext, "image/jpeg"), "data": img_b64},
                CONTRACT_EXTRACTION_PROMPT,
            ])
        else:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                text = f.read()
            response = model.generate_content([
                f"Extract contract data from this logistics rate card:\n\n{text}\n\n{CONTRACT_EXTRACTION_PROMPT}"
            ])

        result = parse_contract_response(response.text)
        if not result.weight_slabs:
            return ContractData(**DEFAULTS)
        return result

    except Exception:
        return ContractData(**DEFAULTS)
