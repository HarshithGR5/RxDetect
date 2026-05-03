"""
vector_store.py
FAISS-backed vector store for clinical knowledge chunks.
Robust against metadata inconsistencies.
"""

import json
import structlog
import numpy as np
from pathlib import Path

from app.config import settings
from app.services.rag.embedder import embed_text, EMBEDDING_DIM

log = structlog.get_logger(__name__)

INDEX_PATH = Path(settings.faiss_index_path)
META_PATH = INDEX_PATH.parent / "faiss_metadata.json"


# ---------------------------------------------------------
# Helpers
# ---------------------------------------------------------

def _load_faiss():
    try:
        import faiss
        return faiss
    except ImportError:
        log.error("vector_store.faiss_not_installed")
        raise


def _ensure_dirs():
    INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------
# Vector Store
# ---------------------------------------------------------

class VectorStore:
    """
    FAISS flat-L2 index with metadata.
    Each entry: { "text": str, "source": str }
    """

    def __init__(self):
        self.faiss = _load_faiss()
        self.index = None
        self.metadata: list[dict] = []
        self._load_or_create()

    # -----------------------------
    # Load / Create
    # -----------------------------

    def _load_or_create(self):
        _ensure_dirs()
        idx_file = INDEX_PATH.with_suffix(".faiss")

        if idx_file.exists() and META_PATH.exists():
            log.info("vector_store.loading", path=str(idx_file))

            self.index = self.faiss.read_index(str(idx_file))

            with open(META_PATH, "r") as f:
                raw_meta = json.load(f)

            # 🔥 FIX: normalize metadata keys
            self.metadata = []
            for item in raw_meta:
                text = item.get("text") or item.get("chunk") or ""
                source = item.get("source", "unknown")

                if text:  # skip broken entries
                    self.metadata.append({
                        "text": text,
                        "source": source,
                    })

            log.info(
                "vector_store.loaded",
                total_vectors=self.index.ntotal,
                metadata_entries=len(self.metadata),
            )

        else:
            log.info("vector_store.creating_new")
            self.index = self.faiss.IndexFlatL2(EMBEDDING_DIM)
            self.metadata = []

    # -----------------------------
    # Save
    # -----------------------------

    def _save(self):
        idx_file = INDEX_PATH.with_suffix(".faiss")
        self.faiss.write_index(self.index, str(idx_file))

        with open(META_PATH, "w") as f:
            json.dump(self.metadata, f)

    # -----------------------------
    # Reset (IMPORTANT)
    # -----------------------------

    def reset(self):
        """Clear index + metadata completely."""
        self.index = self.faiss.IndexFlatL2(EMBEDDING_DIM)
        self.metadata = []
        self._save()
        log.warning("vector_store.reset")

    # -----------------------------
    # Add Data
    # -----------------------------

    def add_texts(self, texts: list[str], sources: list[str]):
        """Embed and add texts."""
        from app.services.rag.embedder import embed_batch

        if not texts:
            return

        embeddings = embed_batch(texts)
        vectors = np.array(embeddings, dtype=np.float32)

        self.index.add(vectors)

        for text, source in zip(texts, sources):
            if text:
                self.metadata.append({
                    "text": text,
                    "source": source,
                })

        self._save()

        log.info(
            "vector_store.added",
            added=len(texts),
            total=self.index.ntotal,
        )

    # -----------------------------
    # Search
    # -----------------------------

    def search(self, query: str, top_k: int = 5) -> list[dict]:
        """Return top-k similar chunks."""

        if self.index.ntotal == 0:
            log.warning("vector_store.empty_index")
            return []

        q_vec = np.array([embed_text(query)], dtype=np.float32)

        distances, indices = self.index.search(
            q_vec,
            min(top_k, self.index.ntotal)
        )

        results = []

        for dist, idx in zip(distances[0], indices[0]):
            if idx < 0 or idx >= len(self.metadata):
                continue

            meta = self.metadata[idx]

            text = meta.get("text") or meta.get("chunk") or ""
            source = meta.get("source", "unknown")

            if not text:
                continue

            similarity = float(1 / (1 + dist))

            results.append({
                "text": text,
                "source": source,
                "score": round(similarity, 4),
            })

        return results

    # -----------------------------
    # Count
    # -----------------------------

    def total_vectors(self) -> int:
        return self.index.ntotal if self.index else 0


# ---------------------------------------------------------
# Singleton
# ---------------------------------------------------------

_store: VectorStore | None = None


def get_vector_store() -> VectorStore:
    global _store
    if _store is None:
        _store = VectorStore()
    return _store