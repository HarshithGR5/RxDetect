"""
vector_store.py
FAISS-backed vector store for clinical knowledge chunks.

Supports arbitrarily large indexes (tested to 50k+ vectors).
Metadata schema per entry:
  { "text": str, "source": str, "hash": str, "page": int, "file": str }
"""

import json
import structlog
import numpy as np
from pathlib import Path

from app.config import settings
from app.services.rag.embedder import embed_text, EMBEDDING_DIM

log = structlog.get_logger(__name__)

INDEX_PATH = Path(settings.faiss_index_path)
META_PATH  = INDEX_PATH.parent / "faiss_metadata.json"


def _load_faiss():
    try:
        import faiss
        return faiss
    except ImportError:
        log.error("vector_store.faiss_not_installed")
        raise


def _ensure_dirs():
    INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)


class VectorStore:
    """
    FAISS IndexFlatL2 with persisted JSON metadata.

    Scales comfortably to ~100k vectors on CPU.
    For larger corpora switch to IndexIVFFlat with nlist ≈ sqrt(N).
    """

    def __init__(self):
        self.faiss = _load_faiss()
        self.index = None
        self.metadata: list[dict] = []
        self._load_or_create()

    # ── Load / Create ─────────────────────────────────────────────────────────

    def _load_or_create(self):
        _ensure_dirs()
        idx_file = INDEX_PATH.with_suffix(".faiss")

        if idx_file.exists() and META_PATH.exists():
            log.info("vector_store.loading", path=str(idx_file))
            self.index = self.faiss.read_index(str(idx_file))

            with open(META_PATH, "r") as f:
                raw = json.load(f)

            # Normalise legacy entries that may have different key names
            self.metadata = []
            for item in raw:
                text   = item.get("text") or item.get("chunk") or ""
                source = item.get("source", "unknown")
                if text:
                    self.metadata.append({
                        "text":   text,
                        "source": source,
                        "hash":   item.get("hash", ""),
                        "page":   item.get("page", 0),
                        "file":   item.get("file", source),
                    })

            log.info(
                "vector_store.loaded",
                total_vectors=self.index.ntotal,
                metadata_entries=len(self.metadata),
            )
        else:
            log.info("vector_store.creating_new")
            self.index    = self.faiss.IndexFlatL2(EMBEDDING_DIM)
            self.metadata = []

    # ── Save ──────────────────────────────────────────────────────────────────

    def _save(self):
        idx_file = INDEX_PATH.with_suffix(".faiss")
        self.faiss.write_index(self.index, str(idx_file))
        with open(META_PATH, "w") as f:
            json.dump(self.metadata, f)

    # ── Reset ─────────────────────────────────────────────────────────────────

    def reset(self):
        """Wipe the index and all metadata (irreversible)."""
        self.index    = self.faiss.IndexFlatL2(EMBEDDING_DIM)
        self.metadata = []
        self._save()
        log.warning("vector_store.reset_complete")

    # ── Add ───────────────────────────────────────────────────────────────────

    def add_texts(
        self,
        texts:   list[str],
        sources: list[str],
        metas:   list[dict] | None = None,
    ):
        """
        Embed and add texts to the index.

        Args:
            texts:   Raw text chunks.
            sources: Human-readable source strings (filename + page).
            metas:   Optional per-chunk metadata dicts.
                     Merged with {"text", "source"} before storage.
        """
        from app.services.rag.embedder import embed_batch

        if not texts:
            return

        metas = metas or [{}] * len(texts)

        embeddings = embed_batch(texts)
        vectors    = np.array(embeddings, dtype=np.float32)
        self.index.add(vectors)

        for text, source, meta in zip(texts, sources, metas):
            if text:
                self.metadata.append({
                    "text":   text,
                    "source": source,
                    "hash":   meta.get("hash", ""),
                    "page":   meta.get("page",  0),
                    "file":   meta.get("file",  source),
                })

        self._save()

        log.info(
            "vector_store.added",
            added=len(texts),
            total=self.index.ntotal,
        )

    # ── Search ────────────────────────────────────────────────────────────────

    def search(self, query: str, top_k: int = 5) -> list[dict]:
        """Return top-k most similar chunks with similarity scores."""
        if self.index.ntotal == 0:
            log.warning("vector_store.empty_index")
            return []

        q_vec = np.array([embed_text(query)], dtype=np.float32)
        distances, indices = self.index.search(
            q_vec, min(top_k, self.index.ntotal)
        )

        results = []
        for dist, idx in zip(distances[0], indices[0]):
            if idx < 0 or idx >= len(self.metadata):
                continue
            meta = self.metadata[idx]
            text = meta.get("text") or meta.get("chunk") or ""
            if not text:
                continue
            results.append({
                "text":   text,
                "source": meta.get("source", "unknown"),
                "page":   meta.get("page",   0),
                "file":   meta.get("file",   ""),
                "score":  round(float(1 / (1 + dist)), 4),
            })

        return results

    # ── Stats ─────────────────────────────────────────────────────────────────

    def total_vectors(self) -> int:
        return self.index.ntotal if self.index else 0

    def stats(self) -> dict:
        files: dict[str, int] = {}
        for m in self.metadata:
            f = m.get("file", "unknown")
            files[f] = files.get(f, 0) + 1
        return {
            "total_vectors": self.total_vectors(),
            "total_metadata": len(self.metadata),
            "chunks_per_file": files,
        }


# ── Singleton ─────────────────────────────────────────────────────────────────

_store: VectorStore | None = None


def get_vector_store() -> VectorStore:
    global _store
    if _store is None:
        _store = VectorStore()
    return _store
