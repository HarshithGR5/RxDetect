"""
embedder.py
Generates text embeddings using OpenAI text-embedding-3-small.
Used by the vector store to index and query clinical knowledge.
"""
import structlog
from openai import OpenAI
from app.config import settings

log = structlog.get_logger(__name__)
client = OpenAI(api_key=settings.openai_api_key)

EMBEDDING_DIM = 1536   # text-embedding-3-small output dimension


def embed_text(text: str) -> list[float]:
    """Return the embedding vector for a single text string."""
    text = text.replace("\n", " ").strip()
    if not text:
        return [0.0] * EMBEDDING_DIM
    try:
        resp = client.embeddings.create(
            model=settings.openai_embedding_model,
            input=text,
        )
        return resp.data[0].embedding
    except Exception as e:
        log.error("embedder.error", error=str(e))
        return [0.0] * EMBEDDING_DIM


def embed_batch(texts: list[str]) -> list[list[float]]:
    """Embed a list of texts in a single API call (max 2048 items)."""
    cleaned = [t.replace("\n", " ").strip() for t in texts]
    try:
        resp = client.embeddings.create(
            model=settings.openai_embedding_model,
            input=cleaned,
        )
        # Results are returned in the same order as input
        return [item.embedding for item in sorted(resp.data, key=lambda x: x.index)]
    except Exception as e:
        log.error("embedder.batch_error", error=str(e))
        return [[0.0] * EMBEDDING_DIM] * len(texts)