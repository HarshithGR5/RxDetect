"""
reports.py — API v1
PDF report generation and streaming download.
PDFs are generated in-memory and streamed directly — no disk storage needed.
"""
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
import io

from app.dependencies import get_current_user, get_db
from app.models import DiscrepancyReport, Prescription, PrescriptionStatus, User

router = APIRouter()


# =========================================================
# HELPERS
# =========================================================

def _get_analyzed_prescription(db: Session, prescription_id: str):
    rx = (
        db.query(Prescription)
        .filter(Prescription.id == prescription_id, Prescription.deleted_at.is_(None))
        .first()
    )

    if not rx:
        raise HTTPException(status_code=404, detail="Prescription not found")

    if rx.status != PrescriptionStatus.analyzed:
        raise HTTPException(
            status_code=202,
            detail=f"Analysis not complete yet. Status: {rx.status}",
        )

    if not rx.report:
        raise HTTPException(status_code=404, detail="No discrepancy report available")

    return rx, rx.report


def _build_result(report):
    """Reconstruct a DiscrepancyResult-compatible object from DB report."""
    from app.services.aggregator import DiscrepancyResult
    return DiscrepancyResult(
        label            = report.label,
        confidence       = report.confidence,
        rule_label       = report.rule_label or "N/A",
        llm_label        = report.llm_label or "N/A",
        llm_confidence   = report.llm_confidence or 0.0,
        llm_reason       = report.llm_reason or "",
        evidence_sources = report.evidence_sources or [],
        rules_triggered  = report.rules_triggered or [],
        ml_label         = report.ml_label,
        ml_confidence    = report.ml_confidence,
        ml_features      = report.ml_features,
        consensus        = report.consensus or "N/A",
        flagged_fields   = [],
        recommendations  = [],
        clinical_summary = [],
        checklist_items  = report.checklist_items or [],
    )


def _generate_pdf(rx, report) -> bytes:
    from app.services.report_generator import generate_pdf_bytes
    result = _build_result(report)
    return generate_pdf_bytes(
        prescription_id  = str(rx.id),
        extracted_fields = rx.extracted_fields or {},
        result           = result,
    )


def _stream_pdf(pdf_bytes: bytes, prescription_id: str) -> StreamingResponse:
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="report_{prescription_id[:8]}.pdf"',
            "Content-Length":      str(len(pdf_bytes)),
            "Cache-Control":       "no-store",
        },
    )


# =========================================================
# GENERATE + STREAM REPORT  (POST)
# Generates PDF in memory and streams it immediately.
# No file is saved to disk.
# =========================================================

@router.post("/generate/{prescription_id}")
def generate_report(
    prescription_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Generate the PDF report in memory and stream it to the client."""

    rx, report = _get_analyzed_prescription(db, prescription_id)
    pdf_bytes  = _generate_pdf(rx, report)

    # Update timestamp so the API reflects when it was last generated
    report.pdf_generated_at = datetime.utcnow()
    db.commit()

    return _stream_pdf(pdf_bytes, prescription_id)


# =========================================================
# DOWNLOAD REPORT  (GET)
# Also generates in memory — no disk file needed.
# =========================================================

@router.get("/download/{prescription_id}")
def download_report(
    prescription_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Stream the PDF report, generating it on-the-fly."""

    rx, report = _get_analyzed_prescription(db, prescription_id)
    pdf_bytes  = _generate_pdf(rx, report)
    return _stream_pdf(pdf_bytes, prescription_id)


# =========================================================
# LIST REPORTS
# =========================================================

@router.get("/")
def list_reports(
    page: int = 1,
    page_size: int = 20,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List reports."""

    q = (
        db.query(DiscrepancyReport)
        .join(Prescription, DiscrepancyReport.prescription_id == Prescription.id)
        .filter(Prescription.deleted_at.is_(None))
    )

    if current_user.role != "admin":
        q = q.filter(Prescription.uploaded_by == current_user.id)

    total = q.count()

    items = (
        q.order_by(DiscrepancyReport.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return {
        "total":     total,
        "page":      page,
        "page_size": page_size,
        "items": [
            {
                "report_id":       str(r.id),
                "prescription_id": str(r.prescription_id),
                "label":           r.label,
                "confidence":      r.confidence,
                "consensus":       r.consensus,
                "pdf_ready":       True,   # always generatable on-demand
                "created_at":      r.created_at.isoformat(),
            }
            for r in items
        ],
    }
