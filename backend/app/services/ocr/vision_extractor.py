"""
vision_extractor.py
Calls GPT-4o Vision to extract structured prescription fields from an image or PDF page.
"""

import base64
import json
import re
import structlog
from pathlib import Path
from openai import OpenAI

from app.config import settings
from app.services.ocr.text_cleaner import clean_extracted_fields  # ✅ IMPORTANT

log = structlog.get_logger(__name__)
client = OpenAI(api_key=settings.openai_api_key)


SYSTEM_PROMPT = """You are an expert clinical pharmacist AI trained to read medical prescriptions.

Your task is to extract all structured fields from the prescription image provided.

Return ONLY a valid JSON object with these keys (use null for missing/illegible fields):
{
  "patient_name": string | null,
  "patient_age": integer | null,
  "patient_gender": string | null,
  "date": string | null,
  "doctor_name": string | null,
  "doctor_registration_no": string | null,
  "hospital_clinic": string | null,
  "signature_present": boolean,
  "diagnosis": string | null,
  "drugs": [
    {
      "drug_name": string,
      "dose": string | null,
      "route": string | null,
      "frequency": string | null,
      "duration": string | null,
      "special_instructions": string | null
    }
  ],
  "illegible_fields": [string],
  "overall_legibility_score": float
}

Rules:
- overall_legibility_score: 0.0 (completely illegible) to 1.0 (perfectly clear)
- illegible_fields: list any field names you could NOT read

CRITICAL:
- Do NOT guess values
- If unsure, return null
- Add missing fields to illegible_fields
- Do NOT normalize drug names
- Extract EXACT text from prescription

Return ONLY JSON. No markdown. No explanation.
"""


def _encode_image(file_path: str) -> tuple[str, str]:
    path = Path(file_path)
    suffix = path.suffix.lower()

    media_map = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".pdf": "application/pdf",
    }

    media_type = media_map.get(suffix, "image/jpeg")

    with open(file_path, "rb") as f:
        data = base64.b64encode(f.read()).decode("utf-8")

    return data, media_type


def extract_prescription_fields(file_path: str) -> dict:

    log.info("vision_extractor.start", file=file_path)

    try:
        b64_data, media_type = _encode_image(file_path)
    except Exception as e:
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
            max_tokens=1500,
            temperature=0.0,
        )
    except Exception as e:
        log.error("vision_extractor.api_error", error=str(e))
        return _error(str(e))

    raw_text = response.choices[0].message.content.strip()

    # Remove ```json fences
    clean = re.sub(r"^```(?:json)?|```$", "", raw_text, flags=re.MULTILINE).strip()

    try:
        fields = json.loads(clean)
    except Exception as e:
        log.warning("vision_extractor.json_error", error=str(e))
        return _error("JSON parse failed", raw_text)

    # ✅ CLEANING STEP (CRITICAL)
    fields = clean_extracted_fields(fields)

    ocr_confidence = float(fields.get("overall_legibility_score") or 0.0)

    log.info(
        "vision_extractor.done",
        drugs=[d.get("drug_name") for d in fields.get("drugs", [])],
        confidence=ocr_confidence,
    )

    return {
        "extracted_fields": fields,
        "raw_text": raw_text,
        "ocr_confidence": ocr_confidence,
        "error": None,
    }


def _error(msg, raw=""):
    return {
        "extracted_fields": None,
        "raw_text": raw,
        "ocr_confidence": 0.0,
        "error": msg,
    }