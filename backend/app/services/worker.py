"""
worker.py
Celery application and main async pipeline — with checklist support.

Storage behaviour
-----------------
On upload, the file is always saved to local disk first (so the Celery
worker can read it for OCR).  If Supabase Storage is configured, the file
is also uploaded there for durable persistence.

After OCR is complete the local copy is deleted. If the local copy is
missing at the time the worker runs (e.g. on a retry after a server restart)
and a Supabase storage_key is present, the file is automatically downloaded
from Supabase to a temp path before OCR proceeds.

Upstash / Redis optimization
-----------------------------
- result_expires=1800        : task results are auto-deleted after 30 min.
                               Without this, every completed task stores a
                               result key in Redis forever, accumulating
                               thousands of keys that cost commands to manage.
- visibility_timeout=43200   : 12-hour visibility window prevents phantom
                               re-queuing of long-running tasks.
- worker_max_tasks_per_child : recycles worker processes to prevent memory
                               growth over time.
- broker_heartbeat=None      : disables Celery broker heartbeats — the
                               default fires every 2 s and sends ~30 Redis
                               commands/minute even when completely idle.
                               Tasks still succeed; the heartbeat only affects
                               event monitoring (flower, etc.).
"""

import os
import ssl
import tempfile

from celery import Celery
import structlog

from app.config import settings

log = structlog.get_logger(__name__)

celery_app = Celery(
    "rx_worker",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

_ssl_conf = {"ssl_cert_reqs": ssl.CERT_NONE}
_is_rediss = settings.celery_broker_url.startswith("rediss://")

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    broker_connection_retry_on_startup=True,

    # ── Upstash / Redis idle-optimization ─────────────────────────────────
    # Auto-expire task results after 30 minutes.  Without this, every
    # completed task leaves a key in Redis indefinitely, and Upstash charges
    # a command each time Celery manages those keys.
    result_expires=1800,

    # Prevents phantom re-queuing: if a worker crashes while processing a
    # task, Upstash won't re-enqueue it until 12 h have passed.
    broker_transport_options={"visibility_timeout": 43200},

    # Disable broker heartbeats — they send Redis commands every 2 s even
    # when no tasks are running.  Set to None to turn them off entirely.
    broker_heartbeat=None,

    # Recycle worker processes every 50 tasks to prevent memory growth.
    worker_max_tasks_per_child=50,

    # redis-py 4.2+ requires ssl.CERT_NONE (enum) not the string "CERT_NONE".
    # Only set SSL options when the URL actually uses rediss://.
    **({"broker_use_ssl": _ssl_conf, "redis_backend_use_ssl": _ssl_conf} if _is_rediss else {}),
)


def _discard_input_file(local_path: str | None) -> None:
    """
    Delete the uploaded prescription image/PDF after OCR is complete.
    Silently ignores missing files or permission errors — analysis must
    not fail due to cleanup failures.
    """
    if not local_path:
        return
    try:
        if os.path.exists(local_path):
            os.remove(local_path)
            log.info("worker.input_file_discarded", path=local_path)
    except Exception as e:
        log.warning("worker.input_file_discard_failed", path=local_path, error=str(e))


def _ensure_local_file(local_path: str | None, storage_key: str | None, storage_backend: str | None) -> str | None:
    """
    Ensure the input file exists on local disk before OCR.

    Priority:
      1. local_path exists on disk → return it as-is (normal path).
      2. local_path missing but storage_key set (Supabase) → download to
         a temp file and return that path.
      3. Neither → return None (OCR will fail gracefully).

    The returned path is the actual file path to pass to the OCR extractor.
    If we downloaded from Supabase the caller is responsible for deleting
    the temp file after use.
    """
    if local_path and os.path.exists(local_path):
        return local_path

    if storage_key and storage_backend == "supabase":
        log.info(
            "worker.local_file_missing_fetching_from_supabase",
            local_path=local_path,
            storage_key=storage_key,
        )
        try:
            from app.utils.storage import storage
            signed_url = storage.get_url(storage_key, expires_in=300)
            if not signed_url:
                log.error("worker.supabase_signed_url_empty", storage_key=storage_key)
                return None

            import requests as req_lib
            resp = req_lib.get(signed_url, timeout=60)
            resp.raise_for_status()

            ext = os.path.splitext(storage_key)[-1] or ".jpg"
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=ext)
            tmp.write(resp.content)
            tmp.close()

            log.info(
                "worker.supabase_file_downloaded",
                storage_key=storage_key,
                tmp_path=tmp.name,
                size=len(resp.content),
            )
            return tmp.name

        except Exception as exc:
            log.error(
                "worker.supabase_download_failed",
                storage_key=storage_key,
                error=str(exc),
            )
            return None

    log.warning(
        "worker.no_input_file_available",
        local_path=local_path,
        storage_key=storage_key,
    )
    return None


@celery_app.task(bind=True, name="tasks.run_analysis", max_retries=2)
def run_analysis_task(self, prescription_id: str):

    from app.dependencies import SessionLocal
    from app.models import Prescription, DiscrepancyReport, PrescriptionStatus
    from sqlalchemy.exc import IntegrityError

    db = SessionLocal()
    tmp_file_to_cleanup: str | None = None

    try:
        # -------------------------------------------------
        # 1. LOAD
        # -------------------------------------------------
        rx = db.query(Prescription).filter(Prescription.id == prescription_id).first()

        if not rx:
            log.error("worker.prescription_not_found", id=prescription_id)
            return {"status": "failed"}

        if rx.status == PrescriptionStatus.analyzed:
            log.warning("worker.skipped_already_processed", id=prescription_id)
            return {"status": "already_processed"}

        _safe_update_status(db, rx, PrescriptionStatus.processing)

        # -------------------------------------------------
        # 2. RESOLVE INPUT FILE
        # -------------------------------------------------
        resolved_path = _ensure_local_file(rx.local_path, rx.storage_key, rx.storage_backend)

        if not resolved_path:
            log.error(
                "worker.no_input_file",
                prescription_id=prescription_id,
                local_path=rx.local_path,
                storage_key=rx.storage_key,
            )
            _safe_update_status(db, rx, PrescriptionStatus.failed)
            return {"status": "failed", "error": "Input file not found locally or in remote storage"}

        if resolved_path != rx.local_path:
            tmp_file_to_cleanup = resolved_path

        # -------------------------------------------------
        # 3. OCR
        # -------------------------------------------------
        from app.services.ocr.vision_extractor import extract_prescription_fields

        ocr = extract_prescription_fields(resolved_path)

        if ocr.get("error") or not ocr.get("extracted_fields"):
            _safe_update_status(db, rx, PrescriptionStatus.failed)
            return {"status": "failed", "error": ocr.get("error")}

        raw_fields      = ocr["extracted_fields"]
        raw_text        = ocr["raw_text"]
        raw_conf        = ocr["ocr_confidence"]
        checklist_items = ocr.get("checklist_items", [])

        # -------------------------------------------------
        # 4. DISCARD INPUT FILE
        # -------------------------------------------------
        _discard_input_file(rx.local_path)
        rx.local_path = None

        if tmp_file_to_cleanup:
            _discard_input_file(tmp_file_to_cleanup)
            tmp_file_to_cleanup = None

        # -------------------------------------------------
        # 5. CLEAN
        # -------------------------------------------------
        from app.services.ocr.text_cleaner import clean_extracted_fields

        cleaned_fields = clean_extracted_fields(raw_fields)

        # -------------------------------------------------
        # 6. CONFIDENCE
        # -------------------------------------------------
        from app.services.ocr.confidence import (
            compute_ocr_confidence,
            compute_completeness_score,
        )

        ocr_conf    = compute_ocr_confidence(cleaned_fields, raw_conf)
        completeness = compute_completeness_score(cleaned_fields)

        rx.raw_ocr_text       = raw_text
        rx.extracted_fields   = cleaned_fields
        rx.ocr_confidence     = ocr_conf
        rx.completeness_score = completeness["completeness_score"]
        rx.missing_fields     = completeness["missing_fields"]

        _safe_update_status(db, rx, PrescriptionStatus.ocr_done)

        # -------------------------------------------------
        # 7. VALIDATION
        # -------------------------------------------------
        from app.services.validation.drug_validator import validate_prescription_drugs

        validation_result = validate_prescription_drugs(cleaned_fields)
        rx.drug_validation_result = validation_result

        log.info("worker.validation_done", drugs=len(validation_result.get("per_drug", [])))

        _safe_update_status(db, rx, PrescriptionStatus.validated)

        # -------------------------------------------------
        # 8. RULE ENGINE
        # -------------------------------------------------
        from app.services.rules.engine import run_all_rules

        rule_result = run_all_rules(cleaned_fields, ocr_conf, validation_result)

        # -------------------------------------------------
        # 9. RAG
        # -------------------------------------------------
        from app.services.rag.retriever import retrieve_context, build_prescription_query

        query = build_prescription_query(cleaned_fields, validation_result)
        log.info("worker.rag_query", query=query)

        retrieved_context, retrieved_chunks = retrieve_context(query, top_k=5)

        # -------------------------------------------------
        # 10. LLM
        # -------------------------------------------------
        from app.services.llm.reasoning_chain import run_reasoning_chain

        llm_result = run_reasoning_chain(
            extracted_fields  = cleaned_fields,
            validation_result = validation_result,
            rule_findings     = rule_result.findings,
            retrieved_context = retrieved_context,
            retrieved_chunks  = retrieved_chunks,
        )

        # -------------------------------------------------
        # 11. ML
        # -------------------------------------------------
        from app.services.ml.predictor import predict

        ml_result = predict(cleaned_fields, validation_result, ocr_conf)

        # -------------------------------------------------
        # 12. AGGREGATE
        # -------------------------------------------------
        from app.services.aggregator import aggregate_results

        final = aggregate_results(
            rule_result       = rule_result,
            llm_result        = llm_result,
            ml_result         = ml_result,
            retrieved_chunks  = retrieved_chunks,
            validation_result = validation_result,
        )

        log.info(
            "worker.final_result",
            label      = final.label,
            confidence = final.confidence,
            flags      = len(final.flagged_fields),
            checklist_items = len(checklist_items),
        )

        # -------------------------------------------------
        # 13. UPSERT REPORT
        # -------------------------------------------------
        from app.models.discrepancy_report import DiscrepancyLabel

        raw_label  = final.label.strip()
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
            existing.label           = label_enum.value
            existing.confidence      = final.confidence
            existing.rules_triggered = final.rules_triggered
            existing.rule_label      = final.rule_label
            existing.llm_label       = final.llm_label
            existing.llm_confidence  = final.llm_confidence
            existing.llm_reason      = final.llm_reason
            existing.evidence_sources = final.evidence_sources
            existing.ml_label        = final.ml_label
            existing.ml_confidence   = final.ml_confidence
            existing.ml_features     = final.ml_features
            existing.consensus       = final.consensus
            existing.checklist_items = checklist_items

        else:
            log.info("worker.creating_new_report", prescription_id=rx.id)
            report = DiscrepancyReport(
                prescription_id  = rx.id,
                label            = label_enum.value,
                confidence       = final.confidence,
                rules_triggered  = final.rules_triggered,
                rule_label       = final.rule_label,
                llm_label        = final.llm_label,
                llm_confidence   = final.llm_confidence,
                llm_reason       = final.llm_reason,
                evidence_sources = final.evidence_sources,
                ml_label         = final.ml_label,
                ml_confidence    = final.ml_confidence,
                ml_features      = final.ml_features,
                consensus        = final.consensus,
                checklist_items  = checklist_items,
            )
            db.add(report)

        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            log.warning("worker.duplicate_handled", prescription_id=rx.id)

        _safe_update_status(db, rx, PrescriptionStatus.analyzed)

        return {
            "status":     "done",
            "label":      final.label,
            "confidence": final.confidence,
            "checklist":  len(checklist_items),
        }

    except Exception as e:
        db.rollback()
        log.error("worker.error", error=str(e))
        _safe_update_status(db, rx, PrescriptionStatus.failed)
        raise self.retry(exc=e, countdown=10)

    finally:
        if tmp_file_to_cleanup:
            _discard_input_file(tmp_file_to_cleanup)
        db.close()


def _safe_update_status(db, rx, status):
    try:
        rx.status = status
        db.commit()
    except Exception:
        db.rollback()
