"""
illegibility_rules.py
Rules that detect illegibility in the prescription.

Key design decision:
- IL001 (low overall confidence) → always Illegibility regardless of confidence level
- IL002 (illegible_fields list from GPT) → Illegibility ONLY if overall confidence is low;
  if OCR is legible overall (confidence >= threshold) but GPT still flagged specific fields
  as unreadable, we reclassify those as Omission (the prescription is readable but the
  field is simply absent/missing).
- IL003 (garbled drug names) → Illegibility
"""
from app.config import settings


def _illegibility(rule_id: str, description: str, severity: str = "HIGH") -> dict:
    return {"rule_id": rule_id, "description": description, "severity": severity, "type": "Illegibility"}


def _omission(rule_id: str, description: str, severity: str = "MEDIUM") -> dict:
    return {"rule_id": rule_id, "description": description, "severity": severity, "type": "Omission"}


def check_low_overall_confidence(fields: dict, ocr_confidence: float) -> list[dict]:
    if ocr_confidence < settings.ocr_confidence_threshold:
        return [_illegibility(
            "IL001",
            f"Overall OCR confidence is {ocr_confidence:.0%} — prescription may be too illegible to process reliably",
            severity="CRITICAL",
        )]
    return []


def check_illegible_fields(fields: dict, ocr_confidence: float) -> list[dict]:
    """
    Flag fields that GPT could not read.

    If overall OCR legibility is good (>= threshold) but specific fields are missing,
    those are more likely absent (omission) than truly unreadable (illegibility).
    We only raise Illegibility for individual fields when the prescription is
    globally hard to read.
    """
    illegible = fields.get("illegible_fields") or []
    if not illegible:
        return []

    findings = []
    legible_overall = ocr_confidence >= settings.ocr_confidence_threshold

    for field in illegible:
        readable_name = field.replace("_", " ").title()
        if legible_overall:
            # Prescription is readable overall — missing field is an omission
            findings.append(_omission(
                "IL002",
                f"'{readable_name}' was not found on the prescription (OCR legibility is adequate)",
                severity="MEDIUM",
            ))
        else:
            # Prescription is globally hard to read — flag as illegibility
            findings.append(_illegibility(
                "IL002",
                f"Field '{readable_name}' could not be read due to illegibility",
            ))

    return findings


def check_unreadable_drug_names(fields: dict) -> list[dict]:
    """Flag drug entries where the name is suspiciously short or garbled."""
    findings = []
    for drug in (fields.get("drugs") or []):
        name = (drug.get("drug_name") or "").strip()
        if len(name) <= 2:
            findings.append(_illegibility(
                "IL003",
                f"Drug name '{name}' is too short — likely illegible handwriting",
            ))
    return findings


def run_illegibility_rules(fields: dict, ocr_confidence: float) -> list[dict]:
    findings = []
    findings.extend(check_low_overall_confidence(fields, ocr_confidence))
    findings.extend(check_illegible_fields(fields, ocr_confidence))
    findings.extend(check_unreadable_drug_names(fields))
    return findings
