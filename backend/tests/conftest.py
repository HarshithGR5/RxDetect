"""
conftest.py
Shared pytest fixtures.
"""
import pytest


@pytest.fixture
def sample_prescription():
    """A complete, valid extracted prescription dict for reuse across tests."""
    return {
        "patient_name": "Ravi Kumar",
        "patient_age": 45,
        "patient_gender": "Male",
        "date": "2025-01-01",
        "doctor_name": "Dr. S. Mehta",
        "doctor_registration_no": "MCI-12345",
        "hospital_clinic": "Apollo Clinic",
        "signature_present": True,
        "diagnosis": "Upper Respiratory Tract Infection",
        "drugs": [
            {
                "drug_name": "Azithromycin",
                "dose": "500 mg",
                "route": "PO",
                "frequency": "OD",
                "duration": "3 days",
                "special_instructions": "Take with food",
            }
        ],
        "illegible_fields": [],
        "overall_legibility_score": 0.95,
    }


@pytest.fixture
def sample_validation_result():
    """A minimal drug validation result dict."""
    return {
        "per_drug": [
            {
                "drug_name": "Azithromycin",
                "rxnorm": {"found": True, "rxcui": "18631", "name": "Azithromycin"},
                "fda": {"found": True},
                "dose_check": {"status": "ok", "detail": "Dose within range"},
                "issues": [],
            }
        ],
        "interactions": [],
        "overall_issues": [],
    }