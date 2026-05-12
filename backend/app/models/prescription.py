import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Text, Float, ForeignKey, Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from app.models.base import Base
import enum


class PrescriptionStatus(str, enum.Enum):
    uploaded   = "uploaded"
    processing = "processing"
    ocr_done   = "ocr_done"
    validated  = "validated"
    analyzed   = "analyzed"
    failed     = "failed"


class Prescription(Base):
    __tablename__ = "prescriptions"

    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    uploaded_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    patient_id  = Column(UUID(as_uuid=True), ForeignKey("patients.id"), nullable=True)

    # ── Storage ────────────────────────────────────────────────────────────────
    # local_path      : temporary path on disk used by the Celery OCR worker.
    #                   Cleared to NULL once OCR completes (file is deleted).
    # storage_key     : permanent key in the configured storage backend.
    #                   Format: "{bucket}/{filename}"  e.g. "prescriptions/abc.jpg"
    #                   NULL when no external storage is configured.
    # storage_backend : "supabase" | "local" | NULL
    local_path        = Column(String(512), nullable=True)
    storage_key       = Column(String(1024), nullable=True)
    storage_backend   = Column(String(32), nullable=True)

    input_type        = Column(String(64), nullable=True)
    original_filename = Column(String(255), nullable=True)

    # Status & job tracking
    status        = Column(SAEnum(PrescriptionStatus), default=PrescriptionStatus.uploaded)
    celery_job_id = Column(String(128), nullable=True)

    # OCR output
    raw_ocr_text     = Column(Text, nullable=True)
    extracted_fields = Column(JSONB, nullable=True)

    # Confidence signals
    ocr_confidence     = Column(Float, nullable=True)   # readability 0-1
    completeness_score = Column(Float, nullable=True)   # field completeness 0-1
    missing_fields     = Column(JSONB, nullable=True)   # list of missing field names

    # Validation output
    drug_validation_result = Column(JSONB, nullable=True)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_at = Column(DateTime, nullable=True)

    # Relationships
    uploader = relationship("User", back_populates="prescriptions", foreign_keys=[uploaded_by])
    patient  = relationship("Patient", back_populates="prescriptions")
    report   = relationship("DiscrepancyReport", back_populates="prescription", uselist=False)

    def __repr__(self):
        return f"<Prescription id={self.id} status={self.status} backend={self.storage_backend}>"
