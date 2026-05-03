"""
patients.py — API v1
Patient record CRUD.
"""
import uuid
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.dependencies import get_current_user, get_db
from app.models import Patient, User

router = APIRouter()


# ── Schemas ──────────────────────────────────────────────────────────────────

class PatientCreate(BaseModel):
    full_name: str
    mrn: Optional[str] = None
    date_of_birth: Optional[date] = None
    age: Optional[int] = None
    gender: Optional[str] = None
    phone: Optional[str] = None
    known_allergies: Optional[str] = None
    current_medications: Optional[str] = None


class PatientUpdate(BaseModel):
    full_name: Optional[str] = None
    date_of_birth: Optional[date] = None
    age: Optional[int] = None
    gender: Optional[str] = None
    phone: Optional[str] = None
    known_allergies: Optional[str] = None
    current_medications: Optional[str] = None


# ── Routes ───────────────────────────────────────────────────────────────────

@router.post("/", status_code=status.HTTP_201_CREATED)
def create_patient(
    payload: PatientCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if payload.mrn:
        existing = db.query(Patient).filter(Patient.mrn == payload.mrn).first()
        if existing:
            raise HTTPException(status_code=409, detail=f"Patient with MRN {payload.mrn} already exists")

    patient = Patient(**payload.model_dump())
    db.add(patient)
    db.commit()
    db.refresh(patient)
    return {"patient_id": str(patient.id), **payload.model_dump()}


@router.get("/")
def list_patients(
    search: Optional[str] = Query(None, description="Search by name or MRN"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = db.query(Patient)
    if search:
        q = q.filter(
            Patient.full_name.ilike(f"%{search}%") | Patient.mrn.ilike(f"%{search}%")
        )
    total = q.count()
    items = q.order_by(Patient.full_name).offset((page - 1) * page_size).limit(page_size).all()
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [
            {
                "id": str(p.id),
                "mrn": p.mrn,
                "full_name": p.full_name,
                "age": p.age,
                "gender": p.gender,
                "known_allergies": p.known_allergies,
            }
            for p in items
        ],
    }


@router.get("/{patient_id}")
def get_patient(
    patient_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    return {
        "id": str(patient.id),
        "mrn": patient.mrn,
        "full_name": patient.full_name,
        "date_of_birth": patient.date_of_birth.isoformat() if patient.date_of_birth else None,
        "age": patient.age,
        "gender": patient.gender,
        "phone": patient.phone,
        "known_allergies": patient.known_allergies,
        "current_medications": patient.current_medications,
        "prescriptions": [str(rx.id) for rx in patient.prescriptions],
    }


@router.patch("/{patient_id}")
def update_patient(
    patient_id: str,
    payload: PatientUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(patient, field, value)
    db.commit()
    db.refresh(patient)
    return {"message": "Patient updated", "patient_id": patient_id}


@router.delete("/{patient_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_patient(
    patient_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    db.delete(patient)
    db.commit()