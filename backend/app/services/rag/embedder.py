"""
embedder.py
Generates text embeddings using OpenAI text-embedding-3-small.

Two hard limits per OpenAI embeddings call:
  - Max 2,048 items
  - Max 300,000 tokens  (≈ chars // 4)

Both limits are enforced by build_safe_batches() before any API call is made.
"""
import time
import structlog
from openai import OpenAI, RateLimitError, APIError
from app.config import settings

log = structlog.get_logger(__name__)

client = OpenAI(api_key=settings.openai_api_key)

EMBEDDING_DIM     = 1536    # text-embedding-3-small output dimension
MAX_ITEMS         = 2048    # OpenAI hard limit: items per request
MAX_TOKENS        = 250_000 # Stay under 300k with a safe buffer
CHARS_PER_TOKEN   = 4       # Rough approximation for token estimation
MAX_RETRIES       = 3
RETRY_DELAY_S     = 5


# ── Token estimation ──────────────────────────────────────────────────────────

def estimate_tokens(text: str) -> int:
    return max(1, len(text) // CHARS_PER_TOKEN)


# ── Batch builder — respects BOTH item count and token count limits ────────────

def build_safe_batches(texts: list[str]) -> list[list[str]]:
    """
    Split texts into sub-lists where each sub-list satisfies:
      len(sub) <= MAX_ITEMS  AND  sum(estimate_tokens(t) for t in sub) <= MAX_TOKENS

    A single chunk that exceeds MAX_TOKENS by itself is truncated so the API
    call doesn't fail (extreme edge case for very long clinical paragraphs).
    """
    batches: list[list[str]] = []
    current_batch: list[str] = []
    current_tokens = 0

    for text in texts:
        t_tokens = estimate_tokens(text)

        # If a single chunk is too large, truncate it
        if t_tokens > MAX_TOKENS:
            max_chars = MAX_TOKENS * CHARS_PER_TOKEN
            text = text[:max_chars]
            t_tokens = MAX_TOKENS
            log.warning("embedder.chunk_truncated", original_chars=len(text))

        # Start a new batch if adding this text would exceed either limit
        if current_batch and (
            len(current_batch) >= MAX_ITEMS or
            current_tokens + t_tokens > MAX_TOKENS
        ):
            batches.append(current_batch)
            current_batch = []
            current_tokens = 0

        current_batch.append(text)
        current_tokens += t_tokens

    if current_batch:
        batches.append(current_batch)

    return batches


# ── Single safe batch → OpenAI ────────────────────────────────────────────────

def _embed_single_batch(texts: list[str]) -> list[list[float]]:
    """Embed one pre-validated batch with retry logic."""
    cleaned = [t.replace("\n", " ").strip() or " " for t in texts]
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = client.embeddings.create(
                model=settings.openai_embedding_model,
                input=cleaned,
            )
            return [item.embedding for item in sorted(resp.data, key=lambda x: x.index)]
        except RateLimitError:
            wait = RETRY_DELAY_S * attempt
            log.warning("embedder.rate_limited", attempt=attempt, wait_s=wait)
            time.sleep(wait)
        except APIError as e:
            log.error("embedder.api_error", attempt=attempt, error=str(e))
            if attempt == MAX_RETRIES:
                break
            time.sleep(RETRY_DELAY_S)
        except Exception as e:
            log.error("embedder.unexpected_error", error=str(e))
            break
    # Fallback: return zero vectors (chunks still stored, just won't be retrieved)
    log.error("embedder.batch_failed_using_zeros", size=len(texts))
    return [[0.0] * EMBEDDING_DIM] * len(texts)


# ── Public API ────────────────────────────────────────────────────────────────

def embed_text(text: str) -> list[float]:
    """Embed a single text string."""
    result = embed_batch([text])
    return result[0] if result else [0.0] * EMBEDDING_DIM


def embed_batch(texts: list[str]) -> list[list[float]]:
    """
    Embed an arbitrarily large list of texts.

    Automatically splits into safe sub-batches respecting both the item count
    limit (2,048) and the token limit (300k) before making any API call.
    Returns embeddings in the same order as the input list.
    """
    if not texts:
        return []

    batches = build_safe_batches(texts)
    all_embeddings: list[list[float]] = []
    processed = 0

    for i, batch in enumerate(batches):
        est_tokens = sum(estimate_tokens(t) for t in batch)
        log.info(
            "embedder.batch_progress",
            batch=f"{i+1}/{len(batches)}",
            items=len(batch),
            est_tokens=est_tokens,
            processed_so_far=processed,
            total=len(texts),
        )
        embeddings = _embed_single_batch(batch)
        all_embeddings.extend(embeddings)
        processed += len(batch)

    return all_embeddings
