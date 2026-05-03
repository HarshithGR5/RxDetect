"""
illegibility_rules.py
Rules that detect illegibility in the prescription.
"""
from app.config import settings


def _finding(rule_id: str, description: str, severity: str = "HIGH") -> dict:
    return {"rule_id": rule_id, "description": description, "severity": severity, "type": "Illegibility"}


def check_low_overall_confidence(fields: dict, ocr_confidence: float) -> list[dict]:
    if ocr_confidence < settings.ocr_confidence_threshold:
        return [_finding(
            "IL001",
            f"Overall OCR confidence is {ocr_confidence:.0%} — prescription may be too illegible to process reliably",
            severity="CRITICAL",
        )]
    return []


def check_illegible_fields(fields: dict) -> list[dict]:
    illegible = fields.get("illegible_fields") or []
    if not illegible:
        return []
    findings = []
    for field in illegible:
        findings.append(_finding(
            "IL002",
            f"Field '{field}' could not be read due to illegibility",
        ))
    return findings


def check_unreadable_drug_names(fields: dict) -> list[dict]:
    """Flag drug entries where the name is suspiciously short or garbled."""
    findings = []
    for drug in (fields.get("drugs") or []):
        name = (drug.get("drug_name") or "").strip()
        if len(name) <= 2:
            findings.append(_finding(
                "IL003",
                f"Drug name '{name}' is too short — likely illegible handwriting",
            ))
    return findings


def run_illegibility_rules(fields: dict, ocr_confidence: float) -> list[dict]:
    findings = []
    findings.extend(check_low_overall_confidence(fields, ocr_confidence))
    findings.extend(check_illegible_fields(fields))
    findings.extend(check_unreadable_drug_names(fields))
    return findings