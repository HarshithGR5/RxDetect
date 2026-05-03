"""
omission_rules.py

Rules that detect missing (omitted) required fields.
Enhanced with completeness_score awareness.
"""

from typing import Optional


# ---------------------------------------------------
# HELPER
# ---------------------------------------------------

def _finding(rule_id: str, description: str, severity: str = "HIGH") -> dict:
    return {
        "rule_id":     rule_id,
        "description": description,
        "severity":    severity,
        "type":        "Omission",
    }


# ---------------------------------------------------
# FIELD-LEVEL RULES
# ---------------------------------------------------

def check_missing_patient_name(fields: dict) -> Optional[dict]:
    if not (fields.get("patient_name") or "").strip():
        return _finding("OM001", "Patient name is missing — required for prescription validity")
    return None


def check_missing_patient_age(fields: dict) -> Optional[dict]:
    if fields.get("patient_age") is None:
        return _finding("OM002", "Patient age is missing — required for dosage safety assessment")
    return None


def check_missing_doctor_name(fields: dict) -> Optional[dict]:
    if not (fields.get("doctor_name") or "").strip():
        return _finding("OM003", "Prescribing doctor name is missing")
    return None


def check_missing_signature(fields: dict) -> Optional[dict]:
    # FIXED: default is None (unknown), not True (assumed present)
    # signature_present=False → signature absent (flag it)
    # signature_present=None  → not detected (flag it)
    # signature_present=True  → signature present (OK)
    sig = fields.get("signature_present")
    if sig is False or sig is None:
        severity = "HIGH" if sig is False else "MEDIUM"
        msg = (
            "Doctor signature is absent — prescription may be invalid"
            if sig is False
            else "Doctor signature presence could not be confirmed"
        )
        return _finding("OM004", msg, severity=severity)
    return None


def check_missing_date(fields: dict) -> Optional[dict]:
    if not (fields.get("date") or "").strip():
        return _finding("OM005", "Prescription date is missing", severity="MEDIUM")
    return None


def check_missing_diagnosis(fields: dict) -> Optional[dict]:
    if not (fields.get("diagnosis") or "").strip():
        return _finding("OM006", "Diagnosis / indication is missing", severity="MEDIUM")
    return None


def check_drugs_present(fields: dict) -> Optional[dict]:
    drugs = fields.get("drugs") or []
    if not drugs:
        return _finding(
            "OM007",
            "No drugs found on prescription — possible extraction failure or blank Rx",
            severity="CRITICAL",
        )
    return None


# ---------------------------------------------------
# DRUG-LEVEL RULES
# ---------------------------------------------------

def check_drug_dose_missing(fields: dict) -> list[dict]:
    findings = []
    for drug in (fields.get("drugs") or []):
        if not (drug.get("dose") or "").strip():
            findings.append(_finding(
                "OM008",
                f"Dose is missing for '{drug.get('drug_name', 'Unknown')}' — cannot verify safety",
            ))
    return findings


def check_drug_frequency_missing(fields: dict) -> list[dict]:
    findings = []
    for drug in (fields.get("drugs") or []):
        if not (drug.get("frequency") or "").strip():
            findings.append(_finding(
                "OM009",
                f"Frequency is missing for '{drug.get('drug_name', 'Unknown')}' — incomplete dosing instruction",
            ))
    return findings


def check_drug_duration_missing(fields: dict) -> list[dict]:
    findings = []
    for drug in (fields.get("drugs") or []):
        if not (drug.get("duration") or "").strip():
            findings.append(_finding(
                "OM010",
                f"Duration is missing for '{drug.get('drug_name', 'Unknown')}'",
                severity="MEDIUM",
            ))
    return findings


# ---------------------------------------------------
# GLOBAL COMPLETENESS RULE
# ---------------------------------------------------

def check_overall_incomplete(completeness_score: float | None) -> Optional[dict]:
    """Escalates omission severity based on overall completeness score."""
    if completeness_score is None:
        return None

    if completeness_score < 0.6:
        return _finding(
            "OM_GLOBAL",
            f"Prescription is significantly incomplete (completeness score: {completeness_score:.0%}) "
            f"— multiple required fields are missing",
            severity="CRITICAL",
        )
    elif completeness_score < 0.8:
        return _finding(
            "OM_GLOBAL",
            f"Prescription has notable missing information (completeness score: {completeness_score:.0%})",
            severity="HIGH",
        )

    return None


# ---------------------------------------------------
# RULE REGISTRY
# ---------------------------------------------------

ALL_OMISSION_RULES = [
    check_missing_patient_name,
    check_missing_patient_age,
    check_missing_doctor_name,
    check_missing_signature,
    check_missing_date,
    check_missing_diagnosis,
    check_drugs_present,
]

ALL_OMISSION_LIST_RULES = [
    check_drug_dose_missing,
    check_drug_frequency_missing,
    check_drug_duration_missing,
]


# ---------------------------------------------------
# MAIN RUNNER
# ---------------------------------------------------

def run_omission_rules(
    fields: dict,
    completeness_score: float | None = None,
    missing_fields: list[str] | None = None,
) -> list[dict]:

    findings = []

    # 1. Global completeness
    overall = check_overall_incomplete(completeness_score)
    if overall:
        findings.append(overall)

    # 2. Field-level rules
    for rule in ALL_OMISSION_RULES:
        result = rule(fields)
        if result:
            findings.append(result)

    # 3. Drug-level rules
    for rule in ALL_OMISSION_LIST_RULES:
        findings.extend(rule(fields))

    return findings
