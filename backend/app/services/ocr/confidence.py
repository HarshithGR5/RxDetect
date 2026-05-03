"""
confidence.py

Separates:
1. OCR confidence → readability
2. Completeness → missing data
"""

from app.config import settings

ILLEGIBILITY_PENALTY = 0.08

# ---------------------------------------------------
# OCR CONFIDENCE (ONLY LEGIBILITY)
# ---------------------------------------------------

def compute_ocr_confidence(extracted_fields: dict, model_legibility_score: float) -> float:
    if not extracted_fields:
        return 0.0

    score = float(model_legibility_score or 0.0)

    illegible = extracted_fields.get("illegible_fields", []) or []
    score -= len(illegible) * ILLEGIBILITY_PENALTY

    return max(0.0, min(1.0, round(score, 4)))


# ---------------------------------------------------
# COMPLETENESS SCORE (IMPORTANT)
# ---------------------------------------------------

REQUIRED_FIELDS = ["patient_name", "doctor_name", "drugs", "date"]


def compute_completeness_score(extracted_fields: dict) -> dict:
    if not extracted_fields:
        return {
            "completeness_score": 0.0,
            "missing_fields": REQUIRED_FIELDS
        }

    missing = []

    # Top-level fields
    for f in REQUIRED_FIELDS:
        if not extracted_fields.get(f):
            missing.append(f)

    # Drug-level checks
    drugs = extracted_fields.get("drugs", []) or []

    for i, d in enumerate(drugs):
        if not d.get("drug_name"):
            missing.append(f"drug_{i}_name")
        if not d.get("dose"):
            missing.append(f"drug_{i}_dose")
        if not d.get("frequency"):
            missing.append(f"drug_{i}_frequency")

    score = 1.0 - (len(missing) * 0.08)

    return {
        "completeness_score": max(0.0, round(score, 4)),
        "missing_fields": missing
    }


# ---------------------------------------------------
# THRESHOLD
# ---------------------------------------------------

def is_below_legibility_threshold(confidence: float) -> bool:
    return confidence < settings.ocr_confidence_threshold