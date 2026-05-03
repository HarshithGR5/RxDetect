import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Float, Boolean, ForeignKey, Text, Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from app.models.base import Base
import enum


class DiscrepancyLabel(str, enum.Enum):
    no_discrepancy = "No Discrepancy"
    omission = "Omission"
    commission = "Commission"
    inconsistency = "Inconsistency"
    illegibility = "Illegibility"


class DiscrepancyReport(Base):
    __tablename__ = "discrepancy_reports"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    prescription_id = Column(UUID(as_uuid=True), ForeignKey("prescriptions.id"), unique=True, nullable=False)

    # Core classification
    label = Column(SAEnum(DiscrepancyLabel), nullable=False)
    confidence = Column(Float, nullable=False)               # 0.0-1.0 aggregated

    # Rule engine
    rules_triggered = Column(JSONB, nullable=True)           # list of {rule_id, description, severity}
    rule_label = Column(String(64), nullable=True)           # label from rule engine alone

    # LLM reasoning
    llm_label = Column(String(64), nullable=True)
    llm_confidence = Column(Float, nullable=True)
    llm_reason = Column(Text, nullable=True)
    evidence_sources = Column(JSONB, nullable=True)          # list of {source, excerpt, score}

    # ML classifier (optional)
    ml_label = Column(String(64), nullable=True)
    ml_confidence = Column(Float, nullable=True)
    ml_features = Column(JSONB, nullable=True)               # top SHAP features
    consensus = Column(String(8), nullable=True)             # "HIGH" | "LOW"

    # PDF report
    pdf_local_path = Column(String(512), nullable=True)
    pdf_generated_at = Column(DateTime, nullable=True)

    # Pharmacist feedback
    pharmacist_label = Column(String(64), nullable=True)     # correction from pharmacist
    feedback_note = Column(Text, nullable=True)
    feedback_at = Column(DateTime, nullable=True)
    is_correct = Column(Boolean, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    prescription = relationship("Prescription", back_populates="report")

    def __repr__(self):
        return f"<DiscrepancyReport id={self.id} label={self.label} confidence={self.confidence}>"