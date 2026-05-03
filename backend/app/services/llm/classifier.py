"""
classifier.py
Calls GPT-4o with the full prompt and returns a structured LLMClassification result.
"""
import json
import re
import structlog
from openai import OpenAI
from app.config import settings
from app.services.llm.prompts import SYSTEM_PROMPT, build_analysis_prompt

log = structlog.get_logger(__name__)
client = OpenAI(api_key=settings.openai_api_key)

VALID_LABELS = {"No Discrepancy", "Omission", "Commission", "Inconsistency", "Illegibility"}


def classify_prescription(
    extracted_fields: dict,
    validation_result: dict,
    rule_findings: list[dict],
    retrieved_context: str,
    completeness_score: float | None = None,
) -> dict:
    """
    Run GPT-4o classification on the prescription.

    Returns:
        {
          "label": str,
          "confidence": float,
          "reason": str,
          "flagged_fields": list[str],
          "evidence_used": list[str],
          "recommendations": list[str],
          "raw_response": str,
          "error": str | None,
        }
    """
    user_prompt = build_analysis_prompt(
        extracted_fields=extracted_fields,
        validation_result=validation_result,
        rule_findings=rule_findings,
        retrieved_context=retrieved_context,
        completeness_score=completeness_score,
    )

    log.info("llm_classifier.start", fields_keys=list((extracted_fields or {}).keys()))

    try:
        response = client.chat.completions.create(
            model=settings.openai_reasoning_model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=1000,
            temperature=0.0,
        )
    except Exception as e:
        log.error("llm_classifier.api_error", error=str(e))
        return _error_response(str(e))

    raw = response.choices[0].message.content.strip()
    clean = re.sub(r"^```(?:json)?|```$", "", raw, flags=re.MULTILINE).strip()

    try:
        parsed = json.loads(clean)
    except json.JSONDecodeError as e:
        log.warning("llm_classifier.json_error", raw=raw[:200])
        return _error_response(f"JSON parse error: {e}", raw_response=raw)

    # Validate label
    label = parsed.get("label", "No Discrepancy")
    if label not in VALID_LABELS:
        label = "No Discrepancy"

    confidence = float(parsed.get("confidence", 0.5))
    confidence = max(0.0, min(1.0, confidence))

    log.info("llm_classifier.done", label=label, confidence=confidence)

    return {
        "label": label,
        "confidence": confidence,
        "reason": parsed.get("reason", ""),
        "flagged_fields": parsed.get("flagged_fields", []),
        "evidence_used": parsed.get("evidence_used", []),
        "recommendations": parsed.get("recommendations", []),
        "raw_response": raw,
        "error": None,
    }


def _error_response(error: str, raw_response: str = "") -> dict:
    return {
        "label": "No Discrepancy",
        "confidence": 0.0,
        "reason": "",
        "flagged_fields": [],
        "evidence_used": [],
        "recommendations": [],
        "raw_response": raw_response,
        "error": error,
    }