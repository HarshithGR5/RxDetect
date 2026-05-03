"""
retriever.py
Queries the FAISS vector store and formats retrieved context
for the LLM reasoning chain.
"""
import structlog
from app.services.rag.vector_store import get_vector_store

log = structlog.get_logger(__name__)

MIN_SCORE     = 0.25    # L2-based similarity: 1/(1+dist). Lowered slightly
                        # for large indexes where distances spread further.
MIN_CHUNK_LEN = 80
DEFAULT_TOP_K = 6       # increased from 5 — more context from large corpora


def retrieve_context(query: str, top_k: int = DEFAULT_TOP_K) -> tuple[str, list[dict]]:
    """
    Retrieve the most relevant clinical guideline chunks for a query.

    Returns:
        (formatted_context_str, raw_results_list)

    Each result dict contains: text, source, page, file, score.
    """
    store = get_vector_store()

    if store.total_vectors() == 0:
        log.warning("retriever.empty_store")
        return "No clinical knowledge base available.", []

    results = store.search(query, top_k=top_k)

    filtered = [
        r for r in results
        if r["score"] >= MIN_SCORE and len(r.get("text", "")) >= MIN_CHUNK_LEN
    ]

    if not filtered:
        log.info(
            "retriever.no_results_above_threshold",
            threshold=MIN_SCORE,
            total_returned=len(results),
        )
        return "No relevant clinical guidelines found for this query.", []

    lines = []
    for i, r in enumerate(filtered, 1):
        page_info = f" | page {r['page']}" if r.get("page") else ""
        lines.append(
            f"[Source {i}: {r['source']}{page_info} | relevance: {r['score']:.2f}]\n"
            f"{r['text'][:600]}"
        )

    log.info(
        "retriever.done",
        query_snippet=query[:60],
        results=len(filtered),
        top_score=filtered[0]["score"] if filtered else 0,
    )
    return "\n\n".join(lines), filtered


def build_prescription_query(extracted_fields: dict, validation_result: dict) -> str:
    """
    Build a clinically meaningful query from the prescription's extracted
    fields and drug validation results.

    Uses normalised generic names from the validation layer (not raw OCR)
    so that brand-name drugs still hit the right guideline chunks.
    """
    generic_drugs: list[str] = []
    for d in (validation_result or {}).get("per_drug", []):
        generic_drugs.extend(d.get("clean_names", []))

    # Remove duplicates while preserving order
    seen: set[str] = set()
    unique_drugs = [d for d in generic_drugs if not (d in seen or seen.add(d))]

    diagnosis = extracted_fields.get("diagnosis", "")
    age       = extracted_fields.get("patient_age")
    route     = extracted_fields.get("route", "")

    parts: list[str] = []

    if unique_drugs:
        parts.append(f"Drugs: {', '.join(unique_drugs)}")
    if diagnosis:
        parts.append(f"Condition: {diagnosis}")
    if route:
        parts.append(f"Route: {route}")
    if age:
        parts.append(f"Patient age: {age}")

    parts.append(
        "dosage safety contraindications drug interactions clinical guidelines "
        "standard dose therapeutic range adverse effects"
    )

    return ". ".join(parts)
