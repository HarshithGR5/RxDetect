"""
prompts.py
All prompt templates used by the LLM reasoning chain.
"""

import json


# =========================================================
# SYSTEM PROMPT
# =========================================================

SYSTEM_PROMPT = """You are a senior clinical pharmacist AI with expertise in prescription safety, pharmacology, and drug therapy.

Your task is to analyse a medical prescription and determine whether it contains any discrepancies.

You will be given:
1. The extracted prescription fields (patient, doctor, drugs with doses/frequency/route)
2. Structured drug clinical data from RxNorm (drug identity, drug classes) and OpenFDA (dosage guidelines, warnings, contraindications, drug interactions text from official FDA labels)
3. Rule engine findings (deterministic structural safety checks already run)
4. Clinical guidelines retrieved from the knowledge base

## Discrepancy Categories
- No Discrepancy
- Omission       (required information missing)
- Commission     (something wrong or inappropriate is present)
- Inconsistency  (internal contradictions or dangerous combinations)
- Illegibility   (prescription cannot be read reliably)

## Your Clinical Reasoning Process

### 1. Drug Identification
- Verify each drug is a real, recognized medication
- Identify the pharmacological class of each drug
- Note if any drug was not found in RxNorm or OpenFDA

### 2. Dose Assessment
- Cross-reference the prescribed dose against the FDA dosage_and_administration text
- Flag overdose or underdose relative to FDA label guidance
- Consider patient age, weight (if provided), and diagnosis
- Use the local dose ceiling only as a secondary signal when FDA data is absent

### 3. Indication Check
- Verify each drug matches the stated diagnosis using FDA indications_and_usage
- Flag drugs that have no plausible connection to the stated condition

### 4. Contraindication Check
- Check FDA contraindications for each drug against patient profile (age, diagnosis, other drugs)
- Pay special attention to renal/hepatic impairment, pregnancy, and pediatric warnings

### 5. Drug Interaction Reasoning (CRITICAL)
- The `drug_interactions` field from each drug's FDA label contains official interaction warnings
- Read the interaction text carefully — it will name specific co-medications to avoid or monitor
- If Drug A's FDA label mentions Drug B (which is also prescribed), flag this as an interaction
- Additionally reason using pharmacological class knowledge:
  - Two anticoagulants → bleeding risk
  - Two CNS depressants → sedation/respiratory depression
  - Two QT-prolonging drugs → arrhythmia risk
  - NSAID + anticoagulant → GI bleeding
  - SSRI + tramadol → serotonin syndrome
  - ACE inhibitor + potassium-sparing diuretic → hyperkalemia
- DO NOT assume safety just because a drug pair is not explicitly mentioned
- Infer interactions from drug class overlap, shared toxicity profiles, and clinical knowledge

### 6. Frequency and Route
- Verify frequency is clinically appropriate for the drug (use FDA label guidance, not hardcoded rules)
- Flag impossible routes (oral insulin, IV oral drugs)

## Decision Rules
- Follow rule engine if severity is HIGH or CRITICAL (structural violations)
- Use FDA clinical data as the PRIMARY source for drug-specific decisions
- Use guidelines as supporting context
- Be conservative — when in doubt, flag for review

## Output Format (STRICT JSON ONLY)
{
  "label": "No Discrepancy" | "Omission" | "Commission" | "Inconsistency" | "Illegibility",
  "confidence": 0.0 to 1.0,
  "reason": "Clear clinical explanation of your finding",
  "flagged_fields": ["list of specific fields or drugs that are problematic"],
  "evidence_used": ["list of specific FDA/RxNorm/guideline sources you used"],
  "recommendations": ["actionable clinical recommendations"]
}

RETURN ONLY JSON. No markdown. No explanation outside the JSON.
"""


# =========================================================
# ANALYSIS PROMPT TEMPLATE
# =========================================================

ANALYSIS_PROMPT_TEMPLATE = """## Prescription Fields
{extracted_fields}

## Completeness Score
{completeness_score}

## Drug Clinical Data (RxNorm + OpenFDA — PRIMARY SOURCE)
{clinical_context}

## Validation Issues Detected
{validation_result}

## Rule Engine Findings (Structural Checks)
{rule_findings}

## Retrieved Clinical Guidelines (Supporting)
{retrieved_context}

Analyse the prescription using the clinical data above and return your classification JSON.
"""


# =========================================================
# CLINICAL CONTEXT BUILDER
# =========================================================

def build_clinical_summary(validation_result: dict) -> list:
    """
    Build a rich clinical context from RxNorm + OpenFDA data.
    This is the primary source the LLM uses for drug-specific reasoning.
    """
    summary = []

    for drug in (validation_result or {}).get("per_drug", []):
        names        = drug.get("clean_names", [])
        is_combo     = drug.get("is_combination", False)
        category     = drug.get("category", "")
        raw_name     = drug.get("raw_name", "")
        fda_clinical = drug.get("fda_clinical", {})
        issues       = drug.get("issues", [])

        # Collect drug classes from RxNorm
        drug_classes = []
        for comp in drug.get("components", []):
            rx = comp.get("rxnorm", {})
            if rx.get("found"):
                drug_classes.extend(rx.get("drug_classes", []))

        # Build per-drug clinical entry
        entry = {
            "raw_name":     raw_name,
            "generic_names": names,
            "is_combination": is_combo,
            "category":     category,
            "rxnorm_found": any(
                comp.get("rxnorm", {}).get("found")
                for comp in drug.get("components", [])
            ),
            "fda_found": any(
                comp.get("fda", {}).get("found")
                for comp in drug.get("components", [])
            ),
            "drug_classes": list(set(drug_classes))[:5],

            # FDA label data — CRITICAL for LLM reasoning
            "fda_dosage_guidance":     _truncate(fda_clinical.get("dosage_and_administration", ""), 600),
            "fda_warnings":            _truncate(fda_clinical.get("warnings", ""), 600),
            "fda_contraindications":   _truncate(fda_clinical.get("contraindications", ""), 600),
            "fda_drug_interactions":   _truncate(fda_clinical.get("drug_interactions", ""), 800),
            "fda_indications":         _truncate(fda_clinical.get("indications_and_usage", ""), 400),
            "fda_specific_populations": _truncate(fda_clinical.get("use_in_specific_populations", ""), 400),
            "fda_overdosage":          _truncate(fda_clinical.get("overdosage", ""), 300),

            "validation_issues": issues,
        }

        summary.append(entry)

    return summary


def _truncate(text: str, max_len: int) -> str:
    if not text:
        return ""
    text = text.strip()
    return text[:max_len] + ("..." if len(text) > max_len else "")


# =========================================================
# PROMPT BUILDER
# =========================================================

def build_analysis_prompt(
    extracted_fields: dict,
    validation_result: dict,
    rule_findings: list[dict],
    retrieved_context: str,
    completeness_score: float | None = None,
) -> str:

    clinical_summary = build_clinical_summary(validation_result)
    interactions     = (validation_result or {}).get("interactions", [])

    return ANALYSIS_PROMPT_TEMPLATE.format(
        extracted_fields=json.dumps(extracted_fields, indent=2, default=str),

        completeness_score=(
            f"{completeness_score:.0%}" if completeness_score is not None else "N/A"
        ),

        clinical_context=json.dumps({
            "drugs":        clinical_summary,
            "cross_drug_interaction_signals": interactions,
        }, indent=2, default=str),

        validation_result=json.dumps({
            "overall_issues": (validation_result or {}).get("overall_issues", []),
        }, indent=2, default=str),

        rule_findings=json.dumps(rule_findings or [], indent=2, default=str),

        retrieved_context=retrieved_context or "No clinical guidelines retrieved.",
    )
