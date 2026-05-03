"""
test_rules.py
Unit tests for all rule engine modules.
"""
import pytest
from app.services.rules.omission_rules import run_omission_rules
from app.services.rules.commission_rules import run_commission_rules
from app.services.rules.consistency_rules import run_consistency_rules
from app.services.rules.illegibility_rules import run_illegibility_rules
from app.services.rules.engine import run_all_rules


VALID_PRESCRIPTION = {
    "patient_name": "Ravi Kumar",
    "patient_age": 45,
    "doctor_name": "Dr. S. Mehta",
    "signature_present": True,
    "date": "2025-01-01",
    "diagnosis": "URTI",
    "illegible_fields": [],
    "overall_legibility_score": 0.95,
    "drugs": [
        {
            "drug_name": "Amoxicillin",
            "dose": "500 mg",
            "route": "PO",
            "frequency": "TDS",
            "duration": "5 days",
            "special_instructions": None,
        }
    ],
}


class TestOmissionRules:

    def test_no_omissions_on_valid_rx(self):
        findings = run_omission_rules(VALID_PRESCRIPTION)
        assert findings == []

    def test_missing_patient_name(self):
        rx = {**VALID_PRESCRIPTION, "patient_name": ""}
        findings = run_omission_rules(rx)
        ids = [f["rule_id"] for f in findings]
        assert "OM001" in ids

    def test_missing_patient_age(self):
        rx = {**VALID_PRESCRIPTION, "patient_age": None}
        findings = run_omission_rules(rx)
        ids = [f["rule_id"] for f in findings]
        assert "OM002" in ids

    def test_missing_signature(self):
        rx = {**VALID_PRESCRIPTION, "signature_present": False}
        findings = run_omission_rules(rx)
        ids = [f["rule_id"] for f in findings]
        assert "OM004" in ids

    def test_missing_drug_dose(self):
        rx = dict(VALID_PRESCRIPTION)
        rx["drugs"] = [{"drug_name": "Amoxicillin", "dose": "", "frequency": "TDS", "duration": "5 days"}]
        findings = run_omission_rules(rx)
        ids = [f["rule_id"] for f in findings]
        assert "OM008" in ids

    def test_missing_drug_frequency(self):
        rx = dict(VALID_PRESCRIPTION)
        rx["drugs"] = [{"drug_name": "Amoxicillin", "dose": "500 mg", "frequency": "", "duration": "5 days"}]
        findings = run_omission_rules(rx)
        ids = [f["rule_id"] for f in findings]
        assert "OM009" in ids


class TestCommissionRules:

    def test_no_commission_on_valid_rx(self):
        findings = run_commission_rules(VALID_PRESCRIPTION)
        assert findings == []

    def test_drug_diagnosis_mismatch_metformin_hypertension(self):
        rx = {**VALID_PRESCRIPTION, "diagnosis": "hypertension"}
        rx["drugs"] = [{"drug_name": "Metformin", "dose": "500 mg", "frequency": "BD", "route": "PO"}]
        findings = run_commission_rules(rx)
        ids = [f["rule_id"] for f in findings]
        assert "CM001" in ids

    def test_aspirin_child_under_16(self):
        rx = {**VALID_PRESCRIPTION, "patient_age": 10}
        rx["drugs"] = [{"drug_name": "Aspirin", "dose": "300 mg", "frequency": "OD", "route": "PO"}]
        findings = run_commission_rules(rx)
        ids = [f["rule_id"] for f in findings]
        assert "CM003" in ids

    def test_duplicate_drugs_flagged(self):
        rx = dict(VALID_PRESCRIPTION)
        rx["drugs"] = [
            {"drug_name": "Amoxicillin", "dose": "500 mg", "frequency": "TDS"},
            {"drug_name": "Amoxicillin", "dose": "250 mg", "frequency": "BD"},
        ]
        findings = run_commission_rules(rx)
        ids = [f["rule_id"] for f in findings]
        assert "CM005" in ids


class TestConsistencyRules:

    def test_azithromycin_bd_flagged(self):
        rx = dict(VALID_PRESCRIPTION)
        rx["drugs"] = [{"drug_name": "Azithromycin", "dose": "500 mg", "frequency": "BD", "duration": "7 days"}]
        findings = run_consistency_rules(rx)
        ids = [f["rule_id"] for f in findings]
        assert "IC001" in ids

    def test_azithromycin_od_ok(self):
        rx = dict(VALID_PRESCRIPTION)
        rx["drugs"] = [{"drug_name": "Azithromycin", "dose": "500 mg", "frequency": "OD", "duration": "3 days"}]
        # IC001 should NOT fire
        findings = run_consistency_rules(rx)
        ids = [f["rule_id"] for f in findings]
        assert "IC001" not in ids


class TestIllegibilityRules:

    def test_low_confidence_flags_il001(self):
        findings = run_illegibility_rules(VALID_PRESCRIPTION, ocr_confidence=0.40)
        ids = [f["rule_id"] for f in findings]
        assert "IL001" in ids

    def test_illegible_fields_flag_il002(self):
        rx = {**VALID_PRESCRIPTION, "illegible_fields": ["drug_name", "dose"]}
        findings = run_illegibility_rules(rx, ocr_confidence=0.90)
        ids = [f["rule_id"] for f in findings]
        assert "IL002" in ids

    def test_garbled_drug_name_il003(self):
        rx = dict(VALID_PRESCRIPTION)
        rx["drugs"] = [{"drug_name": "Xz", "dose": "500 mg", "frequency": "OD"}]
        findings = run_illegibility_rules(rx, ocr_confidence=0.90)
        ids = [f["rule_id"] for f in findings]
        assert "IL003" in ids


class TestRuleEngine:

    def test_valid_prescription_no_discrepancy(self):
        result = run_all_rules(VALID_PRESCRIPTION, ocr_confidence=0.95)
        assert result.label == "No Discrepancy"
        assert result.findings == []

    def test_critical_illegibility_wins(self):
        rx = {**VALID_PRESCRIPTION, "illegible_fields": ["drug_name"]}
        result = run_all_rules(rx, ocr_confidence=0.30)
        assert result.label == "Illegibility"
        assert result.highest_severity in ("CRITICAL", "HIGH")