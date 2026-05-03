"""
test_rag.py
Unit tests for the RAG retriever and knowledge loader.
Mocks the FAISS vector store so no OpenAI key or disk index is needed.
"""
import pytest
from unittest.mock import patch, MagicMock
from app.services.rag.retriever import build_prescription_query, retrieve_context


class TestBuildPrescriptionQuery:

    def test_builds_query_with_drugs_and_diagnosis(self):
        fields = {
            "drugs": [{"drug_name": "Azithromycin"}, {"drug_name": "Paracetamol"}],
            "diagnosis": "URTI",
            "patient_age": 35,
        }
        query = build_prescription_query(fields)
        assert "Azithromycin" in query
        assert "URTI" in query
        assert "35" in query

    def test_empty_fields_returns_default(self):
        query = build_prescription_query({})
        assert "General prescription" in query

    def test_no_drugs(self):
        fields = {"diagnosis": "Hypertension", "patient_age": 60}
        query = build_prescription_query(fields)
        assert "Hypertension" in query


class TestRetrieveContext:

    def test_empty_store_returns_fallback(self):
        mock_store = MagicMock()
        mock_store.total_vectors.return_value = 0

        with patch("app.services.rag.retriever.get_vector_store", return_value=mock_store):
            context_str, chunks = retrieve_context("Azithromycin dosage")

        assert "No clinical knowledge base" in context_str
        assert chunks == []

    def test_results_below_min_score_filtered(self):
        mock_store = MagicMock()
        mock_store.total_vectors.return_value = 5
        mock_store.search.return_value = [
            {"text": "Low quality chunk", "source": "Unknown", "score": 0.10},
            {"text": "Medium chunk", "source": "Guideline A", "score": 0.20},
        ]

        with patch("app.services.rag.retriever.get_vector_store", return_value=mock_store):
            context_str, chunks = retrieve_context("Azithromycin", top_k=5)

        # Both below MIN_SCORE=0.25 → filtered
        assert chunks == []
        assert "No relevant" in context_str

    def test_high_score_results_returned(self):
        mock_store = MagicMock()
        mock_store.total_vectors.return_value = 5
        mock_store.search.return_value = [
            {"text": "Azithromycin: OD dosing", "source": "WHO 2023", "score": 0.85},
            {"text": "Azithromycin interactions", "source": "DrugBank", "score": 0.72},
        ]

        with patch("app.services.rag.retriever.get_vector_store", return_value=mock_store):
            context_str, chunks = retrieve_context("Azithromycin", top_k=5)

        assert len(chunks) == 2
        assert "WHO 2023" in context_str
        assert "DrugBank" in context_str