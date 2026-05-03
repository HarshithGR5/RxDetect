import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, Text, Date
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.models.base import Base


class Patient(Base):
    __tablename__ = "patients"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    mrn = Column(String(64), unique=True, nullable=True, index=True)   # medical record number
    full_name = Column(String(255), nullable=False)
    date_of_birth = Column(Date, nullable=True)
    age = Column(Integer, nullable=True)
    gender = Column(String(16), nullable=True)
    phone = Column(String(32), nullable=True)
    known_allergies = Column(Text, nullable=True)        # comma-separated or JSON string
    current_medications = Column(Text, nullable=True)    # JSON string list
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    prescriptions = relationship("Prescription", back_populates="patient")

    def __repr__(self):
        return f"<Patient id={self.id} name={self.full_name}>"