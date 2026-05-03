"""
consistency_rules.py

Structural consistency rules — checks internal contradictions within
the prescription itself.

Drug-specific frequency/dose guideline checking is handled by the LLM
using live OpenFDA dosage data. Local hardcoded frequency tables are removed.
"""


def _finding(rule_id: str, description: str, severity: str = "MEDIUM") -> dict:
    return {
        "rule_id":     rule_id,
        "description": description,
        "severity":    severity,
        "type":        "Inconsistency",
    }


def check_contradictory_frequency_text(fields: dict) -> list[dict]:
    """
    Detect when the frequency field contradicts the special_instructions text.
    e.g. frequency='BD' but instructions say 'take once daily'.
    """
    findings = []
    contradictions = [
        (["OD"],  ["twice", "b.d", "bd", "two times", "2 times"]),
        (["BD"],  ["once", "o.d", "od", "one time", "once daily"]),
        (["TDS"], ["once", "twice", "one time", "two times"]),
        (["QID"], ["once", "twice", "thrice", "three times"]),
    ]
    for drug in (fields.get("drugs") or []):
        freq  = (drug.get("frequency")            or "")
        instr = (drug.get("special_instructions") or "").lower()
        if not instr or not freq:
            continue
        for freq_labels, conflict_words in contradictions:
            if freq in freq_labels and any(w in instr for w in conflict_words):
                findings.append(_finding(
                    "IC002",
                    f"Frequency '{freq}' conflicts with instruction text '{instr}' "
                    f"for '{drug.get('drug_name')}' — internal inconsistency",
                    severity="HIGH",
                ))
    return findings


def check_drug_interaction_inconsistency(fields: dict, validation_result: dict) -> list[dict]:
    """
    Flag cross-drug interactions detected from OpenFDA label text.
    These are sourced from the drug validator's FDA label cross-check.
    """
    findings = []
    interactions = (validation_result or {}).get("interactions", [])

    for ix in interactions:
        if not ix.get("interaction_text"):
            continue
        source = ", ".join(ix.get("source_drug", []))
        mentioned = ", ".join(ix.get("mentions_drugs", []))
        summary = ix.get("summary", "")

        if mentioned:
            severity = "HIGH"
            desc = (
                f"Potential drug interaction: {source} FDA label mentions interaction "
                f"with {mentioned} (co-prescribed). LLM will assess clinical significance. "
                f"Details: {ix['interaction_text'][:300]}"
            )
        else:
            severity = "MEDIUM"
            desc = f"Drug interaction label present for {source}: {ix['interaction_text'][:200]}"

        findings.append(_finding("IC003", desc, severity=severity))

    return findings


def check_dose_frequency_coherence(fields: dict) -> list[dict]:
    """
    Flag if the dose string embeds a frequency that contradicts the frequency field.
    e.g. dose='500mg once daily' but frequency='BD'
    """
    import re
    embedded_freq_map = {
        "once daily":    "OD",
        "twice daily":   "BD",
        "thrice daily":  "TDS",
        "three times":   "TDS",
        "four times":    "QID",
        "every 8 hours": "TDS",
        "every 6 hours": "QID",
        "every 12 hours": "BD",
    }
    findings = []
    for drug in (fields.get("drugs") or []):
        dose = (drug.get("dose") or "").lower()
        freq = (drug.get("frequency") or "")
        if not dose or not freq:
            continue
        for phrase, mapped in embedded_freq_map.items():
            if phrase in dose and freq and freq != mapped:
                findings.append(_finding(
                    "IC004",
                    f"Dose field says '{phrase}' (implying {mapped}) but frequency field is '{freq}' "
                    f"for '{drug.get('drug_name')}' — internal inconsistency",
                    severity="HIGH",
                ))
    return findings


def check_duplicate_active_ingredient(fields: dict) -> list[dict]:
    """
    Flag when two drugs share the same active ingredient
    (e.g., Paracetamol + Combiflam which also contains Paracetamol).
    """
    findings = []
    seen_generics = set()

    for drug in (fields.get("drugs") or []):
        name = (drug.get("drug_name") or "").lower().strip()
        if not name:
            continue

        # Check for obvious overlaps in the drug name itself
        common_ingredients = [
            "paracetamol", "ibuprofen", "aspirin", "tramadol",
            "amoxicillin", "metformin", "atorvastatin",
        ]
        for ingredient in common_ingredients:
            if ingredient in name:
                if ingredient in seen_generics:
                    findings.append(_finding(
                        "IC005",
                        f"Active ingredient '{ingredient}' appears in multiple drugs on this "
                        f"prescription — risk of unintentional double-dosing",
                        severity="HIGH",
                    ))
                seen_generics.add(ingredient)

    return findings


def run_consistency_rules(fields: dict, validation_result: dict = None) -> list[dict]:
    findings = []
    findings.extend(check_contradictory_frequency_text(fields))
    findings.extend(check_drug_interaction_inconsistency(fields, validation_result or {}))
    findings.extend(check_dose_frequency_coherence(fields))
    findings.extend(check_duplicate_active_ingredient(fields))
    return findings
