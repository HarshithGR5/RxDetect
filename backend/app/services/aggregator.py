"""
aggregator.py

Combines:
- Rule Engine (deterministic)
- LLM reasoning (GPT + RAG)
- ML classifier (optional)

into final DiscrepancyResult.
"""

from dataclasses import dataclass, field
from typing import Optional
import structlog

log = structlog.get_logger(__name__)


# ---------------------------------------------------
# LABEL PRIORITY
# ---------------------------------------------------

LABEL_WEIGHTS = {
    "Illegibility": 5,
    "Commission": 4,
    "Omission": 3,
    "Inconsistency": 2,
    "No Discrepancy": 1,
}


# ---------------------------------------------------
# RESULT MODEL
# ---------------------------------------------------

@dataclass
class DiscrepancyResult:
    label: str
    confidence: float

    rule_label: str
    llm_label: str
    llm_confidence: float
    llm_reason: str

    evidence_sources: list[dict]
    rules_triggered: list[dict]

    ml_label: Optional[str] = None
    ml_confidence: Optional[float] = None
    ml_features: Optional[list] = None

    consensus: str = "LOW"

    flagged_fields: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)

    # 🔥 NEW: pass drug-level context forward
    clinical_summary: list[dict] = field(default_factory=list)


# ---------------------------------------------------
# CONSENSUS
# ---------------------------------------------------

def _consensus(label_a: str, label_b: Optional[str]) -> str:
    if label_b is None:
        return "N/A"
    return "HIGH" if label_a == label_b else "LOW"


# ---------------------------------------------------
# MAIN AGGREGATOR
# ---------------------------------------------------

def aggregate_results(
    rule_result,
    llm_result: dict,
    ml_result: Optional[dict] = None,
    retrieved_chunks: Optional[list[dict]] = None,
    validation_result: Optional[dict] = None,   # 🔥 NEW
) -> DiscrepancyResult:

    rule_label = rule_result.label
    rule_severity = rule_result.highest_severity
    rule_findings = rule_result.findings

    llm_label = llm_result.get("label", "No Discrepancy")
    llm_confidence = llm_result.get("confidence", 0.5)
    llm_reason = llm_result.get("reason", "")

    ml_label = (ml_result or {}).get("label")
    ml_confidence = (ml_result or {}).get("confidence")
    ml_features = (ml_result or {}).get("top_features")

    # 🔥 Interaction awareness
    interactions = (validation_result or {}).get("interactions", [])

    # ---------------------------------------------------
    # DECISION LOGIC
    # ---------------------------------------------------

    if rule_severity == "CRITICAL":

        # 🔥 Allow override for illegibility if LLM found real issue
        if rule_label == "Illegibility" and llm_confidence > 0.6:
            final_label = llm_label
            final_confidence = llm_confidence * 0.9
            log.info("aggregator.override_illegibility", llm=llm_label)

        else:
            final_label = rule_label
            final_confidence = 0.95
            log.info("aggregator.rule_critical_wins", label=final_label)

    elif rule_severity == "HIGH":

        if llm_label != rule_label and llm_confidence >= 0.85:
            final_label = llm_label
            final_confidence = llm_confidence * 0.95
            log.info("aggregator.llm_overrides_high_rule")

        else:
            final_label = rule_label
            agreement_bonus = 0.05 if llm_label == rule_label else 0.0
            final_confidence = min(0.95, 0.82 + agreement_bonus)
            log.info("aggregator.rule_high_wins", label=final_label)

    else:
        # 🔥 LLM drives
        final_label = llm_label
        final_confidence = llm_confidence

        # 🔥 Interaction boost
        if interactions:
            final_confidence = min(0.98, final_confidence + 0.05)

            if final_label == "No Discrepancy":
                final_label = "Inconsistency"

        # ML adjustment
        if ml_label:
            if ml_label == llm_label:
                final_confidence = min(0.98, final_confidence + 0.04)
            else:
                final_confidence = max(0.10, final_confidence - 0.03)

        log.info("aggregator.llm_drives", label=final_label, confidence=final_confidence)

    # ---------------------------------------------------
    # CONSENSUS
    # ---------------------------------------------------

    consensus = _consensus(final_label, ml_label)

    # ---------------------------------------------------
    # MERGE FLAGGED FIELDS
    # ---------------------------------------------------

    flagged_fields = set(llm_result.get("flagged_fields", []))

    for r in rule_findings:
        desc = r.get("description", "")
        if "drug" in desc.lower():
            flagged_fields.add(desc)

    flagged_fields = list(flagged_fields)

    # ---------------------------------------------------
    # FORMAT EVIDENCE
    # ---------------------------------------------------

    evidence_sources = []

    if retrieved_chunks:
        for chunk in retrieved_chunks:
            evidence_sources.append({
                "source": chunk.get("source", "Unknown"),
                "excerpt": chunk.get("text", "")[:400],   # 🔥 increased
                "score": chunk.get("score", 0.0),
                "source_type": chunk.get("source", "").split(":")[0],
            })

    # ---------------------------------------------------
    # CLINICAL SUMMARY
    # ---------------------------------------------------

    clinical_summary = (validation_result or {}).get("per_drug", [])

    # ---------------------------------------------------
    # RETURN FINAL
    # ---------------------------------------------------

    return DiscrepancyResult(
        label=final_label,
        confidence=round(final_confidence, 4),

        rule_label=rule_label,
        llm_label=llm_label,
        llm_confidence=llm_confidence,
        llm_reason=llm_reason,

        evidence_sources=evidence_sources,
        rules_triggered=rule_findings,

        ml_label=ml_label,
        ml_confidence=ml_confidence,
        ml_features=ml_features,

        consensus=consensus,

        flagged_fields=flagged_fields,
        recommendations=llm_result.get("recommendations", []),

        clinical_summary=clinical_summary,   # 🔥 NEW
    )