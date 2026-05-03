"""
reports.py — API v1
PDF report generation and download.
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


# =========================================================
# GENERATE REPORT
# =========================================================

@router.post("/generate/{prescription_id}")
def generate_report(
    prescription_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Generate (or regenerate) the PDF report."""

    rx, report = _get_analyzed_prescription(db, prescription_id)

    from app.services.report_generator import generate_pdf_bytes, save_pdf_locally
    from app.services.aggregator import DiscrepancyResult

    # Reconstruct result object
    result = DiscrepancyResult(
        label=report.label,
        confidence=report.confidence,
        rule_label=report.rule_label or "N/A",
        llm_label=report.llm_label or "N/A",
        llm_confidence=report.llm_confidence or 0.0,
        llm_reason=report.llm_reason or "",
        evidence_sources=report.evidence_sources or [],
        rules_triggered=report.rules_triggered or [],
        ml_label=report.ml_label,
        ml_confidence=report.ml_confidence,
        ml_features=report.ml_features,
        consensus=report.consensus or "N/A",
        flagged_fields=[],
        recommendations=[],
    )

    # ✅ FIXED ARGUMENT NAME
    pdf_bytes = generate_pdf_bytes(
        prescription_id=str(rx.id),
        extracted_fields=rx.extracted_fields or {},
        result=result,
    )

    # Save locally
    local_path = save_pdf_locally(pdf_bytes, str(rx.id))

    report.pdf_local_path = local_path
    report.pdf_generated_at = datetime.utcnow()

    db.commit()

    return {
        "message": "Report generated",
        "prescription_id": prescription_id,
        "report_id": str(report.id),
        "pdf_path": local_path,
        "generated_at": report.pdf_generated_at.isoformat(),
    }


# =========================================================
# DOWNLOAD REPORT
# =========================================================

@router.get("/download/{prescription_id}")
def download_report(
    prescription_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Download PDF report."""

    rx, report = _get_analyzed_prescription(db, prescription_id)

    from app.services.report_generator import generate_pdf_bytes, save_pdf_locally
    from app.services.aggregator import DiscrepancyResult

    # Generate if missing
    if not report.pdf_local_path:
        result = DiscrepancyResult(
            label=report.label,
            confidence=report.confidence,
            rule_label=report.rule_label or "",
            llm_label=report.llm_label or "",
            llm_confidence=report.llm_confidence or 0.0,
            llm_reason=report.llm_reason or "",
            evidence_sources=report.evidence_sources or [],
            rules_triggered=report.rules_triggered or [],
            ml_label=report.ml_label,
            ml_confidence=report.ml_confidence,
            ml_features=report.ml_features,
            consensus=report.consensus or "N/A",
            flagged_fields=[],
            recommendations=[],
            clinical_summary=[],
        )

        pdf_bytes = generate_pdf_bytes(
            str(rx.id),
            rx.extracted_fields or {},
            result,
        )

        report.pdf_local_path = save_pdf_locally(pdf_bytes, str(rx.id))
        db.commit()

    # Read file
    from pathlib import Path
    local_path = Path(report.pdf_local_path)

    if not local_path.exists():
        raise HTTPException(status_code=404, detail="Report file not found")

    pdf_bytes = local_path.read_bytes()

    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="report_{prescription_id[:8]}.pdf"',
            "Content-Length": str(len(pdf_bytes)),
        },
    )


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
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [
            {
                "report_id": str(r.id),
                "prescription_id": str(r.prescription_id),
                "label": r.label,
                "confidence": r.confidence,
                "consensus": r.consensus,
                "pdf_ready": bool(r.pdf_local_path),  # ✅ FIXED
                "created_at": r.created_at.isoformat(),
            }
            for r in items  # ✅ FIXED
        ],
    }