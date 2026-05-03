"""
worker.py
Celery application and main async pipeline
"""

from celery import Celery
import structlog

from app.config import settings

log = structlog.get_logger(__name__)

celery_app = Celery(
    "rx_worker",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
)


@celery_app.task(bind=True, name="tasks.run_analysis", max_retries=2)
def run_analysis_task(self, prescription_id: str):

    from app.dependencies import SessionLocal
    from app.models import Prescription, DiscrepancyReport, PrescriptionStatus
    from sqlalchemy.exc import IntegrityError

    db = SessionLocal()

    try:
        # -------------------------------------------------
        # 1. LOAD
        # -------------------------------------------------
        rx = db.query(Prescription).filter(Prescription.id == prescription_id).first()

        if not rx:
            log.error("worker.prescription_not_found", id=prescription_id)
            return {"status": "failed"}

        # 🔥 IDMPOTENCY CHECK (CRITICAL)
        if rx.status == PrescriptionStatus.analyzed:
            log.warning("worker.skipped_already_processed", id=prescription_id)
            return {"status": "already_processed"}

        _safe_update_status(db, rx, PrescriptionStatus.processing)

        # -------------------------------------------------
        # 2. OCR
        # -------------------------------------------------
        from app.services.ocr.vision_extractor import extract_prescription_fields

        ocr = extract_prescription_fields(rx.local_path)

        if ocr.get("error") or not ocr.get("extracted_fields"):
            _safe_update_status(db, rx, PrescriptionStatus.failed)
            return {"status": "failed"}

        raw_fields = ocr["extracted_fields"]
        raw_text = ocr["raw_text"]
        raw_conf = ocr["ocr_confidence"]

        # -------------------------------------------------
        # 3. CLEAN
        # -------------------------------------------------
        from app.services.ocr.text_cleaner import clean_extracted_fields

        cleaned_fields = clean_extracted_fields(raw_fields)

        # -------------------------------------------------
        # 4. CONFIDENCE
        # -------------------------------------------------
        from app.services.ocr.confidence import (
            compute_ocr_confidence,
            compute_completeness_score,
        )

        ocr_conf = compute_ocr_confidence(cleaned_fields, raw_conf)
        completeness = compute_completeness_score(cleaned_fields)

        rx.raw_ocr_text = raw_text
        rx.extracted_fields = cleaned_fields
        rx.ocr_confidence = ocr_conf
        rx.completeness_score = completeness["completeness_score"]
        rx.missing_fields = completeness["missing_fields"]

        _safe_update_status(db, rx, PrescriptionStatus.ocr_done)

        # -------------------------------------------------
        # 5. VALIDATION
        # -------------------------------------------------
        from app.services.validation.drug_validator import validate_prescription_drugs

        validation_result = validate_prescription_drugs(cleaned_fields)

        rx.drug_validation_result = validation_result

        log.info("worker.validation_done", drugs=len(validation_result.get("per_drug", [])))

        _safe_update_status(db, rx, PrescriptionStatus.validated)

        # -------------------------------------------------
        # 6. RULE ENGINE
        # -------------------------------------------------
        from app.services.rules.engine import run_all_rules

        rule_result = run_all_rules(cleaned_fields, ocr_conf, validation_result)

        # -------------------------------------------------
        # 7. RAG
        # -------------------------------------------------
        from app.services.rag.retriever import retrieve_context, build_prescription_query

        query = build_prescription_query(cleaned_fields, validation_result)

        log.info("worker.rag_query", query=query)

        retrieved_context, retrieved_chunks = retrieve_context(query, top_k=5)

        # -------------------------------------------------
        # 8. LLM
        # -------------------------------------------------
        from app.services.llm.reasoning_chain import run_reasoning_chain

        llm_result = run_reasoning_chain(
            extracted_fields=cleaned_fields,
            validation_result=validation_result,
            rule_findings=rule_result.findings,
            retrieved_context=retrieved_context,
            retrieved_chunks=retrieved_chunks,
        )

        # -------------------------------------------------
        # 9. ML
        # -------------------------------------------------
        from app.services.ml.predictor import predict

        ml_result = predict(cleaned_fields, validation_result, ocr_conf)

        # -------------------------------------------------
        # 10. AGGREGATE
        # -------------------------------------------------
        from app.services.aggregator import aggregate_results

        final = aggregate_results(
            rule_result=rule_result,
            llm_result=llm_result,
            ml_result=ml_result,
            retrieved_chunks=retrieved_chunks,
            validation_result=validation_result,
        )

        log.info(
            "worker.final_result",
            label=final.label,
            confidence=final.confidence,
            flags=len(final.flagged_fields),
        )

        # -------------------------------------------------
        # 11. UPSERT REPORT (FIXED)
        # -------------------------------------------------
        from app.models.discrepancy_report import DiscrepancyLabel

        raw_label = final.label.strip()

        label_enum = None
        for member in DiscrepancyLabel:
            if member.value.lower() == raw_label.lower():
                label_enum = member
                break

        if not label_enum:
            label_enum = DiscrepancyLabel.inconsistency

        existing = (
            db.query(DiscrepancyReport)
            .filter(DiscrepancyReport.prescription_id == rx.id)
            .first()
        )

        if existing:
            log.info("worker.updating_existing_report", prescription_id=rx.id)

            existing.label = label_enum.value
            existing.confidence = final.confidence
            existing.rules_triggered = final.rules_triggered
            existing.rule_label = final.rule_label

            existing.llm_label = final.llm_label
            existing.llm_confidence = final.llm_confidence
            existing.llm_reason = final.llm_reason

            existing.evidence_sources = final.evidence_sources

            existing.ml_label = final.ml_label
            existing.ml_confidence = final.ml_confidence
            existing.ml_features = final.ml_features

            existing.consensus = final.consensus

        else:
            log.info("worker.creating_new_report", prescription_id=rx.id)

            report = DiscrepancyReport(
                prescription_id=rx.id,
                label=label_enum.value,
                confidence=final.confidence,
                rules_triggered=final.rules_triggered,
                rule_label=final.rule_label,
                llm_label=final.llm_label,
                llm_confidence=final.llm_confidence,
                llm_reason=final.llm_reason,
                evidence_sources=final.evidence_sources,
                ml_label=final.ml_label,
                ml_confidence=final.ml_confidence,
                ml_features=final.ml_features,
                consensus=final.consensus,
            )

            db.add(report)

        # 🔥 SAFE COMMIT
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            log.warning("worker.duplicate_handled", prescription_id=rx.id)

        _safe_update_status(db, rx, PrescriptionStatus.analyzed)

        return {
            "status": "done",
            "label": final.label,
            "confidence": final.confidence,
        }

    except Exception as e:
        db.rollback()  # 🔥 CRITICAL FIX
        log.error("worker.error", error=str(e))
        _safe_update_status(db, rx, PrescriptionStatus.failed)
        raise self.retry(exc=e, countdown=10)

    finally:
        db.close()


# -------------------------------------------------
# SAFE STATUS UPDATE
# -------------------------------------------------
def _safe_update_status(db, rx, status):
    try:
        rx.status = status
        db.commit()
    except Exception:
        db.rollback()