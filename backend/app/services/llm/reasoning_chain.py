"""
reasoning_chain.py

Lightweight reasoning layer:
- Receives precomputed RAG context from worker
- Builds prompt
- Calls LLM classifier
- Returns structured result

NO retrieval happens here (worker owns RAG)
"""

import structlog
from typing import Optional

from app.services.llm.classifier import classify_prescription

log = structlog.get_logger(__name__)


class PrescriptionReasoningChain:
    """
    Clean reasoning chain:
    Worker handles:
      - OCR
      - Validation
      - Rules
      - RAG

    This layer ONLY does:
      → LLM reasoning
    """

    def run(
        self,
        extracted_fields: dict,
        validation_result: dict,
        rule_findings: list[dict],
        retrieved_context: str,
        retrieved_chunks: list[dict] | None = None,
        completeness_score: float | None = None,
    ) -> dict:

        log.info("reasoning_chain.start")

        # Optional: attach top evidence to rules
        enriched_findings = self._enrich_rule_findings(
            rule_findings,
            retrieved_chunks or []
        )

        # 🔥 CORE LLM CALL
        try:
            llm_result = classify_prescription(
                extracted_fields=extracted_fields,
                validation_result=validation_result,
                rule_findings=enriched_findings,
                retrieved_context=retrieved_context,
                completeness_score=completeness_score,
            )
        except Exception as e:
            log.error("reasoning_chain.llm_failed", error=str(e))
            llm_result = {
                "label": "No Discrepancy",
                "confidence": 0.0,
                "reason": "",
                "flagged_fields": [],
                "evidence_used": [],
                "recommendations": [],
                "error": str(e),
            }

        # Attach chunks for traceability
        llm_result["retrieved_chunks"] = retrieved_chunks or []
        if "error" not in llm_result:
            llm_result["error"] = None

        log.info(
            "reasoning_chain.complete",
            label=llm_result.get("label"),
            confidence=llm_result.get("confidence"),
            chunks_used=len(retrieved_chunks or []),
        )

        return llm_result

    # -------------------------------------------------
    # Optional helper
    # -------------------------------------------------

    def _enrich_rule_findings(
        self,
        rule_findings: list[dict],
        retrieved_chunks: list[dict],
    ) -> list[dict]:
        """
        Attach top supporting evidence to rule findings.
        """
        if not retrieved_chunks or not rule_findings:
            return rule_findings

        top_chunk = retrieved_chunks[0]

        enriched = []
        for finding in rule_findings:
            f = dict(finding)

            if top_chunk.get("score", 0) >= 0.3:
                f["supporting_evidence"] = top_chunk.get("source", "")

            enriched.append(f)

        return enriched


# -------------------------------------------------
# Singleton
# -------------------------------------------------

_chain: Optional[PrescriptionReasoningChain] = None


def get_reasoning_chain() -> PrescriptionReasoningChain:
    global _chain
    if _chain is None:
        _chain = PrescriptionReasoningChain()
    return _chain


# -------------------------------------------------
# Public entrypoint (USED BY WORKER)
# -------------------------------------------------

def run_reasoning_chain(
    extracted_fields: dict,
    validation_result: dict,
    rule_findings: list[dict],
    retrieved_context: str,
    retrieved_chunks: list[dict] | None = None,
    completeness_score: float | None = None,
) -> dict:
    """
    Worker should call this.

    IMPORTANT:
    - retrieved_context MUST come from worker RAG
    - retrieved_chunks optional but recommended
    """
    return get_reasoning_chain().run(
        extracted_fields=extracted_fields,
        validation_result=validation_result,
        rule_findings=rule_findings,
        retrieved_context=retrieved_context,
        retrieved_chunks=retrieved_chunks,
        completeness_score=completeness_score,
    )