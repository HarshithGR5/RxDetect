"""
engine.py
Orchestrates all rule modules and returns a consolidated RuleEngineResult.
The rule engine is a deterministic hard floor — its HIGH/CRITICAL findings
cannot be overridden by the LLM.
"""
from dataclasses import dataclass, field
from app.services.rules.omission_rules import run_omission_rules
from app.services.rules.commission_rules import run_commission_rules
from app.services.rules.consistency_rules import run_consistency_rules
from app.services.rules.illegibility_rules import run_illegibility_rules

import structlog

log = structlog.get_logger(__name__)

SEVERITY_ORDER = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
TYPE_PRIORITY = ["Illegibility", "Commission", "Omission", "Inconsistency"]


@dataclass
class RuleEngineResult:
    findings: list[dict] = field(default_factory=list)
    label: str = "No Discrepancy"
    highest_severity: str = "NONE"
    triggered_rule_ids: list[str] = field(default_factory=list)


def run_all_rules(
    extracted_fields: dict,
    ocr_confidence: float,
    validation_result: dict | None = None,
) -> RuleEngineResult:
    """
    Run all rule sets against the prescription fields.
    Returns a RuleEngineResult with all findings sorted by severity.
    """
    findings: list[dict] = []

    findings.extend(run_illegibility_rules(extracted_fields, ocr_confidence))
    completeness = extracted_fields.get("_completeness", {})

    findings.extend(
        run_omission_rules(
            extracted_fields,
            completeness_score=completeness.get("completeness_score"),
            missing_fields=completeness.get("missing_fields", [])
        )
    )
    findings.extend(run_commission_rules(extracted_fields))
    findings.extend(run_consistency_rules(extracted_fields, validation_result))

    # Sort by severity
    findings.sort(key=lambda f: SEVERITY_ORDER.get(f.get("severity", "LOW"), 3))

    log.info("rule_engine.done", total_findings=len(findings))

    if not findings:
        return RuleEngineResult(findings=[], label="No Discrepancy", highest_severity="NONE")

    # Determine overall label based on most severe finding type
    highest = findings[0]
    label = highest.get("type", "No Discrepancy")

    return RuleEngineResult(
        findings=findings,
        label=label,
        highest_severity=highest.get("severity", "LOW"),
        triggered_rule_ids=[f["rule_id"] for f in findings],
    )