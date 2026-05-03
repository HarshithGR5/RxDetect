"""
feature_extractor.py
Converts extracted prescription fields into a flat numeric feature vector
suitable for the XGBoost classifier.
"""
from app.services.ocr.text_cleaner import FREQUENCY_MAP

EXPECTED_FEATURE_NAMES = [
    "has_patient_name",
    "has_patient_age",
    "has_doctor_name",
    "has_signature",
    "has_date",
    "has_diagnosis",
    "drug_count",
    "missing_dose_count",
    "missing_freq_count",
    "missing_duration_count",
    "has_invalid_freq",
    "ocr_confidence",
    "illegible_field_count",
    "drug_not_in_rxnorm_count",
    "dose_error_count",
    "interaction_count",
]

VALID_FREQUENCIES = set(FREQUENCY_MAP.values())


def extract_features(
    extracted_fields: dict,
    validation_result: dict,
    ocr_confidence: float,
) -> dict:
    """
    Build a flat feature dict from prescription data.
    All values are numeric (int or float).
    """
    fields   = extracted_fields or {}
    drugs    = fields.get("drugs") or []
    val      = validation_result or {}
    per_drug = val.get("per_drug") or []

    missing_dose = sum(1 for d in drugs if not (d.get("dose")      or "").strip())
    missing_freq = sum(1 for d in drugs if not (d.get("frequency") or "").strip())
    missing_dur  = sum(1 for d in drugs if not (d.get("duration")  or "").strip())

    invalid_freq = sum(
        1 for d in drugs
        if d.get("frequency") and d["frequency"] not in VALID_FREQUENCIES
    )

    # Count drugs not found in RxNorm across all components
    drug_not_found = 0
    for pd in per_drug:
        rxnorm_list = pd.get("rxnorm") or []
        if isinstance(rxnorm_list, list):
            if all(not r.get("found", True) for r in rxnorm_list):
                drug_not_found += 1
        elif isinstance(rxnorm_list, dict):
            if not rxnorm_list.get("found", True):
                drug_not_found += 1

    dose_errors = sum(
        1 for pd in per_drug
        for comp in (pd.get("components") or [])
        if (comp.get("dose_check") or {}).get("status") == "error"
    )

    interactions = len(val.get("interactions") or [])

    # FIXED: signature_present=None means unknown → treat as absent (0)
    sig = fields.get("signature_present")
    has_sig = 1 if sig is True else 0

    return {
        "has_patient_name":      int(bool((fields.get("patient_name") or "").strip())),
        "has_patient_age":       int(fields.get("patient_age") is not None),
        "has_doctor_name":       int(bool((fields.get("doctor_name") or "").strip())),
        "has_signature":         has_sig,
        "has_date":              int(bool((fields.get("date") or "").strip())),
        "has_diagnosis":         int(bool((fields.get("diagnosis") or "").strip())),
        "drug_count":            len(drugs),
        "missing_dose_count":    missing_dose,
        "missing_freq_count":    missing_freq,
        "missing_duration_count": missing_dur,
        "has_invalid_freq":      int(invalid_freq > 0),
        "ocr_confidence":        round(ocr_confidence, 4),
        "illegible_field_count": len(fields.get("illegible_fields") or []),
        "drug_not_in_rxnorm_count": drug_not_found,
        "dose_error_count":      dose_errors,
        "interaction_count":     interactions,
    }


def features_to_vector(features: dict) -> list[float]:
    """Return features in a consistent order as a list of floats."""
    return [float(features.get(name, 0.0)) for name in EXPECTED_FEATURE_NAMES]
