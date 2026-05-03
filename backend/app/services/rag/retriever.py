"""
retriever.py
Queries the FAISS vector store and formats retrieved context
for the LLM reasoning chain.
"""
import structlog
from app.services.rag.vector_store import get_vector_store

log = structlog.get_logger(__name__)

MIN_SCORE = 0.30   # threshold tuned for L2-based similarity scoring (1/1+dist)
MIN_CHUNK_LEN = 80


def retrieve_context(query: str, top_k: int = 5) -> tuple[str, list[dict]]:
    """
    Retrieve the most relevant clinical guideline chunks for a query.

    Args:
        query: Natural-language query (drug name + clinical question)
        top_k: Number of chunks to retrieve

    Returns:
        (formatted_context_str, raw_results_list)
    """
    store = get_vector_store()

    if store.total_vectors() == 0:
        log.warning("retriever.empty_store")
        return "No clinical knowledge base available.", []

    results = store.search(query, top_k=top_k)

    # Filter by minimum relevance score and minimum chunk length only
    # DO NOT filter by content keywords — all guideline text is relevant
    filtered = [
        r for r in results
        if r["score"] >= MIN_SCORE
        and len(r.get("text", "")) >= MIN_CHUNK_LEN
    ]

    if not filtered:
        log.info("retriever.no_results_above_threshold", threshold=MIN_SCORE, total=len(results))
        return "No relevant clinical guidelines found for this query.", []

    # Format for LLM consumption
    lines = []
    for i, r in enumerate(filtered, 1):
        lines.append(
            f"[Source {i}: {r['source']} | relevance: {r['score']:.2f}]\n{r['text'][:500]}"
        )

    log.info("retriever.done", query_snippet=query[:60], results=len(filtered))
    return "\n\n".join(lines), filtered


def build_prescription_query(extracted_fields: dict, validation_result: dict) -> str:
    """
    Build a clinically meaningful query using normalized generic drug names + diagnosis.
    Pulls generic names from the validation layer (not raw OCR text).
    """
    generic_drugs = []

    for d in (validation_result or {}).get("per_drug", []):
        generic_drugs.extend(d.get("clean_names", []))

    diagnosis = extracted_fields.get("diagnosis", "")
    age = extracted_fields.get("patient_age")

    parts = []

    if generic_drugs:
        parts.append(f"Drugs: {', '.join(set(generic_drugs))}")

    if diagnosis:
        parts.append(f"Condition: {diagnosis}")

    if age:
        parts.append(f"Patient age: {age}")

    parts.append("dosage safety contraindications drug interactions clinical guidelines")

    return ". ".join(parts)
