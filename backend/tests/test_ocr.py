"""
test_ocr.py
Unit tests for OCR text cleaning and confidence scoring.
(Vision extractor tests are integration-level and need a real OpenAI key.)
"""
import pytest
from app.services.ocr.text_cleaner import clean_drug_name, normalise_frequency, normalise_route, clean_extracted_fields
from app.services.ocr.confidence import compute_ocr_confidence, is_below_legibility_threshold


class TestTextCleaner:

    def test_exact_alias_lookup(self):
        assert clean_drug_name("pcm") == "Paracetamol"
        assert clean_drug_name("azee") == "Azithromycin"

    def test_title_case_passthrough(self):
        result = clean_drug_name("Metformin")
        assert result == "Metformin"

    def test_normalise_frequency_od(self):
        assert normalise_frequency("once daily") == "OD"
        assert normalise_frequency("od") == "OD"
        assert normalise_frequency("1-0-0") == "OD"

    def test_normalise_frequency_bd(self):
        assert normalise_frequency("twice daily") == "BD"
        assert normalise_frequency("bid") == "BD"

    def test_normalise_route(self):
        assert normalise_route("oral") == "PO"
        assert normalise_route("intravenous") == "IV"

    def test_clean_extracted_fields_normalises_drugs(self):
        fields = {
            "patient_name": "ravi kumar",
            "drugs": [
                {"drug_name": "azee", "frequency": "once daily", "route": "oral", "dose": "500 mg", "duration": "3 days"}
            ]
        }
        cleaned = clean_extracted_fields(fields)
        assert cleaned["patient_name"] == "Ravi Kumar"
        drug = cleaned["drugs"][0]
        assert drug["drug_name"] == "Azithromycin"
        assert drug["frequency"] == "OD"
        assert drug["route"] == "PO"


class TestConfidence:

    def test_full_fields_high_confidence(self):
        fields = {
            "patient_name": "John Doe",
            "patient_age": 35,
            "doctor_name": "Dr Smith",
            "date": "2025-01-01",
            "drugs": [{"drug_name": "Amoxicillin"}],
            "illegible_fields": [],
        }
        score = compute_ocr_confidence(fields, 0.95)
        assert score >= 0.85

    def test_missing_fields_reduces_score(self):
        fields = {
            "patient_name": None,
            "patient_age": None,
            "doctor_name": None,
            "date": None,
            "drugs": [],
            "illegible_fields": ["drug_name", "dose"],
        }
        score = compute_ocr_confidence(fields, 0.90)
        assert score < 0.60

    def test_below_threshold(self):
        assert is_below_legibility_threshold(0.50) is True
        assert is_below_legibility_threshold(0.90) is False