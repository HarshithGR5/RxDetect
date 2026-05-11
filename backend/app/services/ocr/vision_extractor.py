"""
vision_extractor.py
Calls GPT-4o Vision to extract structured prescription fields from an image or PDF.
Handles stamp/letterhead doctor info, therapy suggestions, and generates 27-param checklist.
"""

import base64
import json
import re
import structlog
from pathlib import Path
from openai import OpenAI

from app.config import settings
from app.services.ocr.text_cleaner import clean_extracted_fields

log = structlog.get_logger(__name__)
client = OpenAI(api_key=settings.openai_api_key)


# =========================================================
# SYSTEM PROMPT — OCR EXTRACTION
# =========================================================

SYSTEM_PROMPT = """You are an expert clinical pharmacist AI and medical document analyst trained to read all types of medical prescriptions.

Your task is to extract ALL structured fields from the prescription image provided.

## CRITICAL INSTRUCTIONS FOR DOCTOR / PRESCRIBER INFORMATION

Prescription pads may present doctor information in MULTIPLE formats:
1. LETTERHEAD: Doctor name, qualification, registration number printed at the TOP of the page in the header
2. RUBBER STAMP: Doctor details stamped at the BOTTOM, SIDE, or anywhere on the prescription
3. HANDWRITTEN: Doctor details written by hand anywhere on the document
4. PRE-PRINTED: Part of the prescription pad design

You MUST scan the ENTIRE image — top, bottom, left, right, corners, margins — for prescriber details.
If you see a stamp or letterhead with doctor information, extract it as VALID data even if it looks like a design element.

## FIELD EXTRACTION SCHEMA

Return ONLY a valid JSON object with ALL of these keys (use null for missing/illegible fields):

{
  "patient_name": string | null,
  "patient_age": integer | null,
  "patient_gender": string | null,
  "patient_weight": string | null,
  "date": string | null,

  "doctor_name": string | null,
  "doctor_qualification": string | null,
  "doctor_registration_no": string | null,
  "hospital_clinic": string | null,
  "clinic_address": string | null,
  "contact_details": string | null,
  "signature_present": boolean,

  "diagnosis": string | null,
  "allergy_history": string | null,
  "previous_medical_history": string | null,

  "drugs": [
    {
      "drug_name": string,
      "generic_name": string | null,
      "brand_name": string | null,
      "dose": string | null,
      "route": string | null,
      "frequency": string | null,
      "duration": string | null,
      "special_instructions": string | null
    }
  ],

  "therapy_suggestions": [
    {
      "type": "physiotherapy" | "dietary" | "lifestyle" | "referral" | "device" | "other",
      "description": string
    }
  ],

  "illegible_fields": [string],
  "overall_legibility_score": float
}

## FIELD RULES

- overall_legibility_score: 0.0 (completely illegible) to 1.0 (perfectly clear)
- illegible_fields: list only field names that are TRULY UNREADABLE (do NOT list fields that appear in stamps/letterheads)
- doctor_qualification: extract degrees/specialisations (e.g. "MBBS, MD (Pharmacology)", "MBChB")
- doctor_registration_no: any registration, license, or council number (GMC, NMC, HPCSA, etc.)
- clinic_address: full address if visible in letterhead or stamp
- contact_details: phone, fax, email of clinic/doctor if visible
- patient_weight: weight if written (e.g. "68 kg", "70kg")
- allergy_history: any allergy or NKDA/NKA notation
- previous_medical_history: any past medical conditions, co-morbidities, or relevant history mentioned (e.g. "h/o diabetes", "known hypertensive", "prior MI", "CKD", "liver disease") — null if not mentioned
- generic_name: the INN/generic if both generic and brand are written; null if only one name visible
- brand_name: the proprietary/brand name if written; null if only generic used
- therapy_suggestions: NON-DRUG recommendations such as:
  * Physiotherapy / physical therapy
  * Dietary changes (low salt, high fibre, diabetic diet, etc.)
  * Lifestyle modifications (exercise, weight loss, smoking cessation)
  * Specialist referrals (e.g. "refer to cardiologist")
  * Medical devices (e.g. spacer, CPAP, orthotic insole, compression stockings)
  * Other non-pharmacological advice written on the prescription

## CRITICAL RULES

- Do NOT guess values
- Do NOT mark stamp/letterhead fields as illegible — they ARE readable
- If a field appears in a stamp or letterhead, extract it as valid
- Do NOT normalize drug names — extract EXACT text
- If unsure about a specific field, set it to null and add to illegible_fields
- Extract therapy_suggestions even if written informally (e.g. "physio", "low salt diet", "refer physio")

Return ONLY JSON. No markdown. No explanation.
"""


# =========================================================
# CHECKLIST SYSTEM PROMPT — 27-Parameter Clinical Audit
# =========================================================

CHECKLIST_SYSTEM_PROMPT = """You are a senior clinical pharmacist performing a structured prescription audit.

Based on the extracted prescription fields provided, evaluate each of the 27 clinical checklist parameters.

For each parameter return:
- "result": "yes" | "no" | "partial" | "na"
  * yes = requirement clearly met
  * no = requirement clearly NOT met or missing
  * partial = partially met or ambiguous
  * na = not applicable to this prescription
- "reasoning": brief, specific clinical explanation (1-2 sentences, reference actual values)

Return ONLY a JSON array. No markdown. No explanation outside the array.

[
  {
    "id": "P01",
    "parameter": "Patient name present",
    "category": "patient",
    "result": "yes|no|partial|na",
    "reasoning": "..."
  },
  ...27 items total...
]
"""

CHECKLIST_PARAMETERS = [
    ("P01", "patient",      "Patient name is present and legible"),
    ("P02", "patient",      "Patient age is documented"),
    ("P03", "patient",      "Patient gender is documented"),
    ("P04", "patient",      "Patient weight is documented (for weight-based dosing)"),
    ("P05", "patient",      "Allergy history documented or NKDA noted"),
    ("P06", "prescriber",   "Doctor name is present and legible"),
    ("P07", "prescriber",   "Doctor qualification is documented"),
    ("P08", "prescriber",   "Doctor registration/license number is present"),
    ("P09", "prescriber",   "Hospital or clinic name is present"),
    ("P10", "prescriber",   "Clinic address or contact details are present"),
    ("P11", "prescriber",   "Doctor signature or stamp is present"),
    ("P12", "completeness", "Prescription date is present"),
    ("P13", "completeness", "Diagnosis or clinical indication is stated"),
    ("P14", "drug",         "All drug names are clearly legible"),
    ("P15", "drug",         "Generic name used where applicable (not just brand)"),
    ("P16", "drug",         "Dose is specified for all drugs"),
    ("P17", "drug",         "Dose is appropriate for patient age and weight"),
    ("P18", "drug",         "Route of administration is specified for all drugs"),
    ("P19", "drug",         "Frequency of administration is specified for all drugs"),
    ("P20", "drug",         "Duration of therapy is specified for all drugs"),
    ("P21", "drug",         "Special instructions are documented where required"),
    ("P22", "safety",       "No apparent drug-drug interaction risk detected"),
    ("P23", "safety",       "No contraindication for patient profile detected"),
    ("P24", "safety",       "Polypharmacy risk assessed (5+ drugs — check if warranted)"),
    ("P25", "safety",       "Controlled/scheduled substance requirements met if applicable"),
    ("P26", "safety",       "Prescription legibility score is adequate (≥ 0.70)"),
    ("P27", "completeness", "Non-drug/therapy suggestions included where clinically indicated"),
]


# =========================================================
# PDF → IMAGE CONVERSION
# =========================================================

def _pdf_to_images(file_path: str) -> list[bytes]:
    """
    Convert the first page of a PDF to a PNG image for GPT-4o Vision.
    Tries pdf2image first, falls back to pypdf rendering if available.
    """
    try:
        from pdf2image import convert_from_path
        pages = convert_from_path(file_path, dpi=200, first_page=1, last_page=1)
        if pages:
            import io
            buf = io.BytesIO()
            pages[0].save(buf, format="PNG")
            return [buf.getvalue()]
    except ImportError:
        log.warning("vision_extractor.pdf2image_not_available")

    try:
        import fitz  # PyMuPDF
        doc = fitz.open(file_path)
        page = doc[0]
        mat = fitz.Matrix(2.0, 2.0)  # 2x scale for clarity
        pix = page.get_pixmap(matrix=mat)
        return [pix.tobytes("png")]
    except ImportError:
        log.warning("vision_extractor.pymupdf_not_available")

    raise RuntimeError(
        "Cannot render PDF: install pdf2image (with poppler) or PyMuPDF (pip install pymupdf)"
    )


# =========================================================
# FILE ENCODER
# =========================================================

def _encode_image(file_path: str) -> tuple[str, str]:
    """
    Encode image as base64. For PDFs, convert first page to PNG first.
    Returns (base64_data, media_type).
    """
    path   = Path(file_path)
    suffix = path.suffix.lower()

    if suffix == ".pdf":
        pages = _pdf_to_images(file_path)
        data  = base64.b64encode(pages[0]).decode("utf-8")
        return data, "image/png"

    media_map = {
        ".jpg":  "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png":  "image/png",
        ".webp": "image/webp",
        ".gif":  "image/gif",
    }
    media_type = media_map.get(suffix, "image/jpeg")

    with open(file_path, "rb") as f:
        data = base64.b64encode(f.read()).decode("utf-8")

    return data, media_type


# =========================================================
# CHECKLIST GENERATOR
# =========================================================

def generate_checklist(extracted_fields: dict) -> list[dict]:
    """
    Run a second GPT-4o call to evaluate the 27-parameter clinical checklist.
    Returns list of checklist items with result and reasoning.
    """
    params_text = "\n".join(
        f'  {{"id": "{pid}", "parameter": "{param}", "category": "{cat}"}}'
        for pid, cat, param in CHECKLIST_PARAMETERS
    )

    user_msg = f"""Extracted Prescription Fields:
{json.dumps(extracted_fields, indent=2, default=str)}

Evaluate each of the following 27 checklist parameters:
[
{params_text}
]

Return ONLY a JSON array with all 27 items evaluated. Each item must have:
  "id", "parameter", "category", "result" ("yes"|"no"|"partial"|"na"), "reasoning"
"""

    try:
        resp = client.chat.completions.create(
            model=settings.openai_reasoning_model,
            messages=[
                {"role": "system",  "content": CHECKLIST_SYSTEM_PROMPT},
                {"role": "user",    "content": user_msg},
            ],
            max_tokens=2500,
            temperature=0.0,
        )
    except Exception as e:
        log.error("checklist.api_error", error=str(e))
        return []

    raw  = resp.choices[0].message.content.strip()
    clean = re.sub(r"^```(?:json)?|```$", "", raw, flags=re.MULTILINE).strip()

    try:
        items = json.loads(clean)
        if not isinstance(items, list):
            raise ValueError("Expected list")
        return items
    except Exception as e:
        log.warning("checklist.json_error", error=str(e), raw=raw[:200])
        return []


# =========================================================
# MAIN EXTRACTOR
# =========================================================

def extract_prescription_fields(file_path: str) -> dict:

    log.info("vision_extractor.start", file=file_path)

    try:
        b64_data, media_type = _encode_image(file_path)
    except Exception as e:
        log.error("vision_extractor.encode_error", error=str(e))
        return _error(str(e))

    try:
        response = client.chat.completions.create(
            model=settings.openai_vision_model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{media_type};base64,{b64_data}",
                                "detail": "high",
                            },
                        }
                    ],
                },
            ],
            max_tokens=2500,
            temperature=0.0,
        )
    except Exception as e:
        log.error("vision_extractor.api_error", error=str(e))
        return _error(str(e))

    raw_text = response.choices[0].message.content.strip()
    clean    = re.sub(r"^```(?:json)?|```$", "", raw_text, flags=re.MULTILINE).strip()

    try:
        fields = json.loads(clean)
    except Exception as e:
        log.warning("vision_extractor.json_error", error=str(e))
        return _error("JSON parse failed", raw_text)

    fields = clean_extracted_fields(fields)

    ocr_confidence = float(fields.get("overall_legibility_score") or 0.0)

    log.info(
        "vision_extractor.done",
        drugs=[d.get("drug_name") for d in fields.get("drugs", [])],
        confidence=ocr_confidence,
        therapy_suggestions=len(fields.get("therapy_suggestions", [])),
    )

    # ── Checklist (second GPT call) ──────────────────────────────────────────
    checklist_items = generate_checklist(fields)
    log.info("checklist.done", count=len(checklist_items))

    return {
        "extracted_fields":  fields,
        "raw_text":          raw_text,
        "ocr_confidence":    ocr_confidence,
        "checklist_items":   checklist_items,
        "error":             None,
    }


def _error(msg: str, raw: str = "") -> dict:
    return {
        "extracted_fields":  None,
        "raw_text":          raw,
        "ocr_confidence":    0.0,
        "checklist_items":   [],
        "error":             msg,
    }
