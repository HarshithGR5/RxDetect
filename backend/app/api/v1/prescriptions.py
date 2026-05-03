"""
prescriptions.py — API v1
Handles upload, retrieval, analysis triggering, status polling,
result fetching, and pharmacist feedback.
"""
import shutil
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.config import settings
from app.dependencies import get_current_user, get_db
from app.models import (
    DiscrepancyReport,
    Patient,
    Prescription,
    PrescriptionStatus,
    User,
)

router = APIRouter()

ALLOWED_CONTENT_TYPES = {
    "image/jpeg", "image/png", "image/gif", "image/webp", "application/pdf"
}

# ── Schemas ──────────────────────────────────────────────────────────────────

class FeedbackPayload(BaseModel):
    pharmacist_label: str
    feedback_note: Optional[str] = None
    is_correct: Optional[bool] = None


# ── Helpers ──────────────────────────────────────────────────────────────────

def _get_prescription_or_404(db: Session, prescription_id: str, user: User) -> Prescription:
    rx = (
        db.query(Prescription)
        .filter(
            Prescription.id == prescription_id,
            Prescription.deleted_at.is_(None),
        )
        .first()
    )
    if not rx:
        raise HTTPException(status_code=404, detail="Prescription not found")
    return rx


# ── Routes ───────────────────────────────────────────────────────────────────

@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_prescription(
    file: UploadFile = File(...),
    patient_id: Optional[str] = Query(None, description="Optional patient UUID to link"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Upload a prescription image or PDF. Returns prescription_id for further API calls."""
    # Validate content type
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {file.content_type}. Allowed: {ALLOWED_CONTENT_TYPES}",
        )

    # Validate patient if provided
    if patient_id:
        patient = db.query(Patient).filter(Patient.id == patient_id).first()
        if not patient:
            raise HTTPException(status_code=404, detail="Patient not found")

    # Save file
    upload_dir = Path(settings.upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)

    ext = Path(file.filename or "upload").suffix or ".jpg"
    file_name = f"{uuid.uuid4()}{ext}"
    file_path = upload_dir / file_name

    try:
        with file_path.open("wb") as buf:
            shutil.copyfileobj(file.file, buf)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"File save failed: {e}")
    finally:
        file.file.close()

    # Persist to DB
    rx = Prescription(
        uploaded_by=current_user.id,
        patient_id=patient_id,
        local_path=str(file_path),
        input_type=file.content_type,
        original_filename=file.filename,
        status=PrescriptionStatus.uploaded,
    )
    db.add(rx)
    db.commit()
    db.refresh(rx)

    # Trigger the analysis task
    from app.services.worker import run_analysis_task
    task = run_analysis_task.delay(str(rx.id))
    rx.celery_job_id = task.id
    db.commit()

    return {
        "prescription_id": str(rx.id),
        "status": rx.status,
        "celery_job_id": task.id,
        "message": "Upload successful. Analysis has been started.",
    }


@router.get("/")
def list_prescriptions(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status_filter: Optional[str] = Query(None, alias="status"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List prescriptions (paginated). Admins see all; pharmacists see their own."""
    q = db.query(Prescription).filter(Prescription.deleted_at.is_(None))

    if current_user.role != "admin":
        q = q.filter(Prescription.uploaded_by == current_user.id)

    if status_filter:
        q = q.filter(Prescription.status == status_filter)

    total = q.count()
    items = q.order_by(Prescription.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [
            {
                "id": str(rx.id),
                "status": rx.status,
                "input_type": rx.input_type,
                "original_filename": rx.original_filename,
                "ocr_confidence": rx.ocr_confidence,
                "created_at": rx.created_at.isoformat(),
            }
            for rx in items
        ],
    }


@router.get("/{prescription_id}")
def get_prescription(
    prescription_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Full prescription details including extracted fields."""
    rx = _get_prescription_or_404(db, prescription_id, current_user)
    return {
        "id": str(rx.id),
        "status": rx.status,
        "input_type": rx.input_type,
        "original_filename": rx.original_filename,
        "ocr_confidence": rx.ocr_confidence,
        "extracted_fields": rx.extracted_fields,
        "drug_validation_result": rx.drug_validation_result,
        "celery_job_id": rx.celery_job_id,
        "created_at": rx.created_at.isoformat(),
        "updated_at": rx.updated_at.isoformat(),
    }


@router.get("/{prescription_id}/status")
def get_analysis_status(
    prescription_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get the current analysis status of a prescription."""
    rx = _get_prescription_or_404(db, prescription_id, current_user)
    return {
        "prescription_id": str(rx.id),
        "status": rx.status,
        "celery_job_id": rx.celery_job_id,
        "updated_at": rx.updated_at.isoformat(),
    }


@router.get("/{prescription_id}/results")
def get_analysis_results(
    prescription_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get the full analysis results for a completed prescription."""
    rx = _get_prescription_or_404(db, prescription_id, current_user)

    if rx.status != PrescriptionStatus.analyzed:
        raise HTTPException(
            status_code=202,
            detail=f"Analysis not complete. Current status: {rx.status}",
            headers={"Retry-After": "10"},
        )

    report = rx.report
    if not report:
        raise HTTPException(
            status_code=404,
            detail="Analysis is complete but the report was not found.",
        )

    return {
        "prescription_id": str(rx.id),
        "status": rx.status,
        "report": {
            "id": str(report.id),
            "label": report.label,
            "confidence": report.confidence,
            "rule_label": report.rule_label,
            "llm_label": report.llm_label,
            "ml_label": report.ml_label,
            "consensus": report.consensus,
            "rules_triggered": report.rules_triggered,
            "llm_reason": report.llm_reason,
            "evidence_sources": report.evidence_sources,
            "pdf_local_path": report.pdf_local_path,
            "generated_at": report.pdf_generated_at.isoformat() if report.pdf_generated_at else None,
        },
        "extracted_fields": rx.extracted_fields,
    }


@router.delete("/{prescription_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_prescription(
    prescription_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Soft-delete a prescription."""
    rx = _get_prescription_or_404(db, prescription_id, current_user)
    rx.deleted_at = datetime.utcnow()
    db.commit()


# ── Analysis sub-routes (mounted here for simplicity, also in analysis.py) ──

@router.post("/run/{prescription_id}")
def trigger_analysis(
    prescription_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Enqueue the full analysis pipeline via Celery."""
    rx = _get_prescription_or_404(db, prescription_id, current_user)

    if rx.status == PrescriptionStatus.analyzed:
        return {"message": "Already analyzed", "prescription_id": prescription_id}

    from app.worker import run_analysis_task
    task = run_analysis_task.apply_async(args=[str(rx.id)], queue="analysis")

    rx.celery_job_id = task.id
    rx.status = PrescriptionStatus.processing
    db.commit()

    return {
        "prescription_id": prescription_id,
        "job_id": task.id,
        "status": "queued",
    }


@router.get("/status/{job_id}")
def get_job_status(job_id: str, current_user: User = Depends(get_current_user)):
    """Poll Celery job status."""
    from app.worker import celery_app
    result = celery_app.AsyncResult(job_id)
    return {
        "job_id": job_id,
        "status": result.status.lower(),   # pending/started/success/failure
        "result": result.result if result.ready() else None,
    }


@router.get("/result/{prescription_id}")
def get_analysis_result(
    prescription_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Full analysis result once pipeline is complete."""
    rx = _get_prescription_or_404(db, prescription_id, current_user)

    if rx.status != PrescriptionStatus.analyzed:
        raise HTTPException(
            status_code=202,
            detail=f"Analysis not yet complete. Current status: {rx.status}",
        )

    report: DiscrepancyReport = rx.report
    if not report:
        raise HTTPException(status_code=404, detail="No report found for this prescription")

    return {
        "prescription_id": prescription_id,
        "status": "complete",
        "extracted_fields": rx.extracted_fields,
        "discrepancy": {
            "label": report.label,
            "confidence": report.confidence,
            "rule_triggered": report.rule_label,
            "rules": report.rules_triggered,
            "llm_reason": report.llm_reason,
            "evidence_sources": report.evidence_sources,
            "ml_prediction": {
                "label": report.ml_label,
                "confidence": report.ml_confidence,
                "top_features": report.ml_features,
            } if report.ml_label else None,
            "consensus": report.consensus,
        },
        "pharmacist_feedback": {
            "label": report.pharmacist_label,
            "note": report.feedback_note,
            "is_correct": report.is_correct,
            "submitted_at": report.feedback_at.isoformat() if report.feedback_at else None,
        },
    }


@router.patch("/feedback/{prescription_id}")
def submit_feedback(
    prescription_id: str,
    payload: FeedbackPayload,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Pharmacist correction for active learning."""
    rx = _get_prescription_or_404(db, prescription_id, current_user)
    report: DiscrepancyReport = rx.report
    if not report:
        raise HTTPException(status_code=404, detail="No report to submit feedback for")

    report.pharmacist_label = payload.pharmacist_label
    report.feedback_note = payload.feedback_note
    report.is_correct = payload.is_correct
    report.feedback_at = datetime.utcnow()
    db.commit()

    return {"message": "Feedback recorded. Thank you.", "prescription_id": prescription_id}