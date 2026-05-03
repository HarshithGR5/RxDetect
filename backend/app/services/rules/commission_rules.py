"""
commission_rules.py

Structural commission error rules.
Drug-specific clinical checks (wrong indication, overdose, etc.)
are handled by the LLM using live RxNorm + OpenFDA data.

Commission = something that should NOT be there or is clearly wrong.
"""

# Physically impossible / universally invalid drug-form combinations
# These are structural facts, not drug-specific clinical judgements
INVALID_FORMS: list[tuple[str, str, str]] = [
    ("insulin", "tablet",  "Insulin cannot be taken as a tablet — must be injectable or inhaled"),
    ("insulin", "capsule", "Insulin capsule is not a valid dosage form"),
    ("warfarin", "injection", "Warfarin injection is not a standard form — oral tablets are the standard route"),
    ("heparin", "oral",    "Heparin is not absorbed orally — must be parenteral"),
    ("heparin", "tablet",  "Heparin tablet is not a valid form"),
]

# Age-based contraindications with strong clinical consensus
# Aspirin in children → Reye's syndrome (established, universal guideline)
ASPIRIN_NAMES = ["aspirin", "acetylsalicylic acid", "ecosprin", "disprin"]

# High-risk drugs in very young infants (< 2 years)
INFANT_HIGH_RISK_DRUGS = [
    "methotrexate", "warfarin", "lithium", "amiodarone",
    "valproate", "sodium valproate", "phenytoin",
]


def _finding(rule_id: str, description: str, severity: str = "HIGH") -> dict:
    return {
        "rule_id":     rule_id,
        "description": description,
        "severity":    severity,
        "type":        "Commission",
    }


def check_invalid_dosage_form(fields: dict) -> list[dict]:
    """Flag physically impossible drug-form combinations."""
    findings = []
    for drug in (fields.get("drugs") or []):
        dose_str  = (drug.get("dose")      or "").lower()
        route_str = (drug.get("route")     or "").lower()
        name      = (drug.get("drug_name") or "").lower()

        combined = dose_str + " " + route_str

        for drug_key, form_key, msg in INVALID_FORMS:
            if drug_key in name and form_key in combined:
                findings.append(_finding("CM002", msg, severity="CRITICAL"))

    return findings


def check_age_contraindications(fields: dict) -> list[dict]:
    """Flag drugs with universally recognized age-related contraindications."""
    findings = []
    age = fields.get("patient_age")
    if age is None:
        return findings

    for drug in (fields.get("drugs") or []):
        drug_name = (drug.get("drug_name") or "").lower()

        # Aspirin in under-16s → Reye's syndrome risk
        if age < 16 and any(a in drug_name for a in ASPIRIN_NAMES):
            findings.append(_finding(
                "CM003",
                f"Aspirin is contraindicated in patients under 16 years (Reye's syndrome risk). "
                f"Patient age: {age}. Consider alternative analgesic/antipyretic.",
                severity="CRITICAL",
            ))

        # High-risk drugs in very young infants
        if age < 2 and any(d in drug_name for d in INFANT_HIGH_RISK_DRUGS):
            findings.append(_finding(
                "CM004",
                f"'{drug.get('drug_name')}' requires extreme caution or is contraindicated "
                f"in patients under 2 years. Patient age: {age}. Verify dosing and indication urgently.",
                severity="CRITICAL",
            ))

    return findings


def check_duplicate_drugs(fields: dict) -> list[dict]:
    """Flag duplicate drug names within the same prescription."""
    findings = []
    seen = {}
    for drug in (fields.get("drugs") or []):
        name = (drug.get("drug_name") or "").lower().strip()
        if not name:
            continue
        if name in seen:
            findings.append(_finding(
                "CM005",
                f"Drug '{drug.get('drug_name')}' appears more than once on this prescription — "
                f"possible duplication error or accidental double-prescribing",
                severity="HIGH",
            ))
        else:
            seen[name] = True

    return findings


def check_oral_insulin(fields: dict) -> list[dict]:
    """Explicit check: insulin prescribed via oral route."""
    findings = []
    for drug in (fields.get("drugs") or []):
        name  = (drug.get("drug_name") or "").lower()
        route = (drug.get("route")     or "").upper()
        if "insulin" in name and route == "PO":
            findings.append(_finding(
                "CM006",
                "Insulin is prescribed via oral route (PO) — insulin is destroyed by gastric acid "
                "and cannot be absorbed orally. This is a critical commission error.",
                severity="CRITICAL",
            ))
    return findings


def run_commission_rules(fields: dict) -> list[dict]:
    findings = []
    findings.extend(check_invalid_dosage_form(fields))
    findings.extend(check_age_contraindications(fields))
    findings.extend(check_duplicate_drugs(fields))
    findings.extend(check_oral_insulin(fields))
    return findings
