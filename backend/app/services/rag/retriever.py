"""
retriever.py
Queries the FAISS vector store and formats retrieved context
for the LLM reasoning chain.
"""
import structlog
from app.services.rag.vector_store import get_vector_store

log = structlog.get_logger(__name__)

MIN_SCORE     = 0.55    # Only include genuinely relevant chunks.
MIN_CHUNK_LEN = 80
DEFAULT_TOP_K = 8

# Suppress off-topic evidence entirely when best score is below this
RELEVANCE_THRESHOLD = 0.50


def retrieve_context(query: str, top_k: int = DEFAULT_TOP_K) -> tuple[str, list[dict]]:
    """
    Retrieve the most relevant clinical guideline chunks for a query.

    Returns:
        (formatted_context_str, raw_results_list)
    """
    store = get_vector_store()

    if store.total_vectors() == 0:
        log.warning("retriever.empty_store")
        return "No clinical knowledge base available.", []

    results = store.search(query, top_k=top_k)

    # Suppress entirely if the best match is still off-topic
    if results and results[0]["score"] < RELEVANCE_THRESHOLD:
        log.info(
            "retriever.low_relevance_suppressed",
            top_score=results[0]["score"],
            threshold=RELEVANCE_THRESHOLD,
            query_snippet=query[:80],
        )
        return (
            "No sufficiently relevant clinical guidelines found for this prescription. "
            "Clinical reasoning relies on FDA drug data and rule engine findings.",
            [],
        )

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
            f"[Source {i}: {r['source']}{page_info} | relevance: {r['score']:.0%}]\n"
            f"{r['text'][:600]}"
        )

    log.info(
        "retriever.done",
        query_snippet=query[:60],
        results=len(filtered),
        top_score=filtered[0]["score"] if filtered else 0,
    )
    return "\n\n".join(lines), filtered



# Words that appear in drug name tokens but are NOT drug names themselves.
# These come from brand-name decomposition and form abbreviations.
_NON_DRUG_TOKENS: frozenset = frozenset({
    "saline", "drop", "drops", "syp", "syrup", "tab", "tabs", "tablet",
    "tablets", "cap", "caps", "capsule", "capsules", "susp", "suspension",
    "inj", "injection", "soln", "solution", "ml", "mg", "mcg", "iu", "g",
    "ds", "sf", "forte", "plus", "extra", "plain", "pediatric", "paediatric",
    "adult", "junior", "sr", "xr", "er", "cr", "lp", "od",
})

# Maximum number of distinct drugs to include in a single RAG query.
# More than ~4 makes the query too broad for dense-passage retrieval.
_MAX_DRUGS_PER_QUERY = 4


def _filter_drug_tokens(names: list[str]) -> list[str]:
    """
    Remove non-drug words (form abbreviations, excipient names, dosage units)
    that can appear in `clean_names` after brand-name normalization.
    Also drops tokens shorter than 4 characters that aren't real drug names.
    """
    out = []
    for n in names:
        n_stripped = n.strip()
        n_lower    = n_stripped.lower()
        if not n_stripped:
            continue
        if n_lower in _NON_DRUG_TOKENS:
            continue
        # drop very short tokens that are likely abbreviations/units
        if len(n_stripped) <= 3 and not n_lower.startswith("co-"):
            continue
        out.append(n_stripped)
    return out


def build_prescription_query(extracted_fields: dict, validation_result: dict) -> str:
    """
    Build a focused natural-language clinical query for dense-passage retrieval.

    Key improvements:
    - Strips non-drug tokens (saline, drop, syp, etc.) from clean_names
    - Limits to _MAX_DRUGS_PER_QUERY drugs so the query stays semantically focused
    - Phrases as a clinical question a pharmacist would ask
    """
    generic_drugs: list[str] = []
    drug_categories: list[str] = []

    for d in (validation_result or {}).get("per_drug", []):
        clean = _filter_drug_tokens(d.get("clean_names", []))
        generic_drugs.extend(clean)
        cat = d.get("category", "")
        if cat and cat not in drug_categories:
            drug_categories.append(cat)

    # Remove duplicates preserving order
    seen: set[str] = set()
    unique_drugs: list[str] = []
    for d in generic_drugs:
        if d not in seen:
            seen.add(d)
            unique_drugs.append(d)

    # Cap to avoid diluting the embedding query
    unique_drugs = unique_drugs[:_MAX_DRUGS_PER_QUERY]

    diagnosis   = extracted_fields.get("diagnosis", "")
    age         = extracted_fields.get("patient_age")
    med_history = extracted_fields.get("previous_medical_history", "") or ""
    allergy     = extracted_fields.get("allergy_history", "") or ""

    # ── Build a focused clinical question ────────────────────────────────────
    drugs_str = " + ".join(unique_drugs) if unique_drugs else ""
    cat_str   = ", ".join(drug_categories[:3]) if drug_categories else ""

    # Drug + category phrase
    if drugs_str and cat_str:
        drug_phrase = f"{drugs_str} ({cat_str})"
    elif drugs_str:
        drug_phrase = drugs_str
    else:
        drug_phrase = "prescribed medications"

    # Condition phrase
    condition_parts = []
    if diagnosis:
        condition_parts.append(diagnosis)
    if age:
        condition_parts.append(f"age {age}")
    if med_history:
        condition_parts.append(med_history[:120])   # cap to keep query tight
    condition_phrase = ", ".join(condition_parts) if condition_parts else "general use"

    # Allergy addendum
    allergy_clause = f" Patient has known allergy: {allergy}." if allergy else ""

    # Final natural-language clinical question
    query = (
        f"Clinical guidelines for {drug_phrase} in {condition_phrase}: "
        f"recommended dosage, contraindications, drug interactions, "
        f"adverse effects, and monitoring parameters.{allergy_clause}"
    )

    log.debug("retriever.query_built", query=query)
    return query
