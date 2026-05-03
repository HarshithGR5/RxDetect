"""
drug_validator.py

Full prescription drug validation:
1. Brand → generic normalization (CSV + fuzzy, handles combinations)
2. RxNorm lookup → RxCUI, canonical name, drug classes
3. OpenFDA lookup → dosage, warnings, contraindications, drug interactions text
4. Dose safety check (local fallback only when FDA has no dosage info)
5. Route safety check
6. All data passed to LLM for expert clinical reasoning
"""

import re
import structlog

from app.services.validation.rxnorm_client import validate_drug
from app.services.validation.openfda_client import validate_drug_fda
from app.services.validation.drug_normalizer import normalize_drug_name

log = structlog.get_logger(__name__)


# ---------------------------------------------------------
# Local dose ceiling fallback
# ONLY used when OpenFDA has no dosage information
# ---------------------------------------------------------

LOCAL_MAX_DAILY_DOSE_MG = {
    "paracetamol":    4000,
    "acetaminophen":  4000,
    "ibuprofen":      3200,
    "aspirin":        4000,
    "amoxicillin":    3000,
    "metformin":      2000,
    "atorvastatin":   80,
    "ciprofloxacin":  1500,
    "azithromycin":   500,
    "omeprazole":     80,
    "pantoprazole":   80,
    "prednisolone":   60,
    "warfarin":       10,
    "methotrexate":   25,
    "tramadol":       400,
    "codeine":        240,
    "diclofenac":     150,
    "naproxen":       1250,
    "cetirizine":     10,
    "levocetirizine": 5,
}

FREQUENCY_DOSES_PER_DAY = {
    "OD": 1, "BD": 2, "TDS": 3, "QID": 4,
    "SOS": 1, "STAT": 1, "HS": 1,
}


# ---------------------------------------------------------
# Helpers
# ---------------------------------------------------------

def _parse_dose_mg(dose_str: str):
    if not dose_str:
        return None
    match = re.search(r"(\d+(?:\.\d+)?)\s*(?:mg|milligram)", dose_str, re.IGNORECASE)
    return float(match.group(1)) if match else None


def _local_dose_check(drug_name: str, dose_str: str, frequency: str) -> dict:
    """
    Fallback local dose ceiling check.
    Used only when OpenFDA has no dosage information.
    """
    dose_mg = _parse_dose_mg(dose_str)
    if dose_mg is None:
        return {"status": "unknown", "detail": "Could not parse dose amount from prescription"}

    doses_per_day = FREQUENCY_DOSES_PER_DAY.get(frequency or "", 1)
    total_daily = dose_mg * doses_per_day
    max_daily = LOCAL_MAX_DAILY_DOSE_MG.get(drug_name.lower())

    if max_daily is None:
        return {"status": "unknown", "detail": f"No local reference ceiling for {drug_name}"}

    if total_daily > max_daily:
        return {
            "status": "error",
            "detail": f"{total_daily}mg/day exceeds max safe dose of {max_daily}mg/day (local reference)",
        }

    if total_daily > max_daily * 0.9:
        return {
            "status": "warning",
            "detail": f"{total_daily}mg/day is close to the max safe dose of {max_daily}mg/day (local reference)",
        }

    return {"status": "ok", "detail": f"{total_daily}mg/day is within safe range (local reference)"}


# ---------------------------------------------------------
# Core validator for one drug entry
# ---------------------------------------------------------

def _validate_single_drug(name: str, dose: str, frequency: str, route: str) -> dict:
    """
    Run RxNorm + OpenFDA validation for a single generic drug name.
    Returns structured clinical data for LLM consumption.
    """
    issues = []

    # ---- RxNorm ----
    rx = validate_drug(name)
    log.info("drug.rxnorm", drug=name, found=rx["found"], rxcui=rx.get("rxcui"))

    if not rx["found"]:
        issues.append(f"'{name}' not found in RxNorm — may be misspelled, brand name, or non-standard")

    # ---- OpenFDA ----
    fda = validate_drug_fda(name)
    log.info("drug.openfda", drug=name, found=fda["found"])

    if not fda["found"]:
        issues.append(f"'{name}' not found in OpenFDA drug labels")

    # ---- Dose safety ----
    # Use local ceiling check as a SIGNAL only — full dose reasoning goes to LLM
    dose_check = _local_dose_check(name, dose, frequency)
    if dose_check["status"] == "error":
        issues.append(f"Dose concern for {name}: {dose_check['detail']}")
    elif dose_check["status"] == "warning":
        issues.append(f"Dose note for {name}: {dose_check['detail']}")

    # ---- Route safety ----
    if route and "insulin" in name.lower() and route.upper() == "PO":
        issues.append(f"Insulin cannot be administered orally (PO) — must be parenteral or inhaled")

    return {
        "name": name,
        "rxnorm": rx,
        "fda": fda,
        "dose_check": dose_check,
        "issues": issues,
    }


# ---------------------------------------------------------
# Main validation entry point
# ---------------------------------------------------------

def validate_prescription_drugs(extracted_fields: dict) -> dict:
    """
    Validate all drugs in a prescription.

    For each drug:
    - Normalize brand → generic (handles combinations)
    - Validate each generic component via RxNorm + OpenFDA
    - Collect FDA dosage, warnings, contraindications, drug_interactions text

    Returns a structured dict suitable for LLM clinical reasoning.
    """
    drugs = (extracted_fields or {}).get("drugs", [])
    per_drug_results = []

    for drug_entry in drugs:
        raw_name = drug_entry.get("drug_name", "")
        dose = drug_entry.get("dose")
        frequency = drug_entry.get("frequency")
        route = drug_entry.get("route")

        # --------------------------------------------------
        # Step 1: Normalize brand → generic component list
        # --------------------------------------------------
        norm = normalize_drug_name(raw_name)

        if norm["found"]:
            # Use properly split generic names (handles combinations)
            generic_components = norm["generic"]
            log.info(
                "drug.normalized_to_generics",
                raw=raw_name,
                generics=generic_components,
                is_combination=norm.get("is_combination", False),
                source=norm["source"],
            )
        else:
            # Fall back to the cleaned raw name as-is
            generic_components = [raw_name.lower().strip()]
            log.warning(
                "drug.no_csv_match_using_raw",
                raw=raw_name,
                best_guess=norm.get("best_guess"),
                confidence=norm.get("confidence"),
            )

        # --------------------------------------------------
        # Step 2: Validate each generic component
        # --------------------------------------------------
        component_results = []
        all_issues = []

        for component in generic_components:
            result = _validate_single_drug(component, dose, frequency, route)
            component_results.append(result)
            all_issues.extend(result["issues"])

        # --------------------------------------------------
        # Step 3: Build consolidated FDA clinical context
        # for this drug (used by LLM)
        # --------------------------------------------------
        fda_clinical = _merge_fda_data(component_results)

        per_drug_results.append({
            "raw_name":            raw_name,
            "clean_names":         generic_components,
            "is_combination":      norm.get("is_combination", len(generic_components) > 1),
            "brand_matched":       norm.get("normalized_brand"),
            "category":            norm.get("category", ""),
            "components":          component_results,
            "fda_clinical":        fda_clinical,
            "issues":              all_issues,
            # Legacy keys (kept for backwards compat with rules/aggregator)
            "rxnorm": [r["rxnorm"] for r in component_results],
            "fda":    [r["fda"]    for r in component_results],
        })

    # --------------------------------------------------
    # Cross-drug interaction text (from OpenFDA labels)
    # The LLM uses this to reason about interactions
    # --------------------------------------------------
    cross_interaction_context = _build_cross_interaction_context(per_drug_results)

    return {
        "per_drug":            per_drug_results,
        "interactions":        cross_interaction_context,
        "overall_issues": [ctx["summary"] for ctx in cross_interaction_context],
    }


# ---------------------------------------------------------
# Helpers
# ---------------------------------------------------------

def _merge_fda_data(component_results: list[dict]) -> dict:
    """
    Merge FDA label data from multiple components of a combination drug.
    Concatenates text fields; keeps non-empty values.
    """
    merged = {
        "dosage_and_administration": "",
        "warnings":                  "",
        "contraindications":         "",
        "drug_interactions":         "",
        "indications_and_usage":     "",
        "adverse_reactions":         "",
        "use_in_specific_populations": "",
        "overdosage":                "",
    }

    for r in component_results:
        fda = r.get("fda", {})
        for key in merged:
            existing = merged[key]
            new_val = fda.get(key, "")
            if new_val and not existing:
                merged[key] = new_val
            elif new_val and existing and new_val[:100] not in existing:
                merged[key] = existing + "\n\n---\n\n" + new_val

    return merged


def _build_cross_interaction_context(per_drug_results: list[dict]) -> list[dict]:
    """
    Build cross-drug interaction context from each drug's FDA label
    `drug_interactions` field.

    The FDA label for Drug A will mention Drug B by name if they interact.
    We surface this text to the LLM for expert reasoning.
    """
    context = []

    all_drug_names = []
    for dr in per_drug_results:
        all_drug_names.extend(dr["clean_names"])

    for dr in per_drug_results:
        fda = dr.get("fda_clinical", {})
        interaction_text = fda.get("drug_interactions", "")

        if not interaction_text:
            continue

        # Check if any OTHER drug in the prescription is mentioned in this label's interaction text
        other_drugs = [n for n in all_drug_names if n not in dr["clean_names"]]
        mentioned = [n for n in other_drugs if n.lower() in interaction_text.lower()]

        if mentioned:
            context.append({
                "source_drug": dr["clean_names"],
                "mentions_drugs": mentioned,
                "interaction_text": interaction_text[:1000],
                "summary": (
                    f"{', '.join(dr['clean_names'])} FDA label mentions interaction with "
                    f"{', '.join(mentioned)}: {interaction_text[:300]}..."
                ),
            })
        else:
            # Still include the interaction text for LLM to reason about
            # even if we didn't detect a direct co-prescribing match
            if len(all_drug_names) > 1:
                context.append({
                    "source_drug": dr["clean_names"],
                    "mentions_drugs": [],
                    "interaction_text": interaction_text[:1000],
                    "summary": (
                        f"{', '.join(dr['clean_names'])} FDA label interaction section: "
                        f"{interaction_text[:300]}..."
                    ),
                })

    return context
