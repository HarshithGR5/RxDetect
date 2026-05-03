"""
knowledge_loader.py
Loads clinical guidelines into the FAISS vector store.

Now supports:
- PDF ingestion (WHO, BNF, NIH docs)
- Smart chunking (sentence-aware)
- Text cleaning for medical docs
- Duplicate prevention
"""

import os
import re
import hashlib
import structlog
from pathlib import Path

from app.services.rag.vector_store import get_vector_store

# PDF parsing
from pypdf import PdfReader

# Optional better extraction fallback
try:
    from pdfminer.high_level import extract_text as pdfminer_extract
    PDFMINER_AVAILABLE = True
except:
    PDFMINER_AVAILABLE = False

# Optional sentence tokenization
try:
    import nltk
    nltk.download("punkt", quiet=True)
    from nltk.tokenize import sent_tokenize
    USE_NLTK = True
except:
    USE_NLTK = False


log = structlog.get_logger(__name__)

GUIDELINES_DIR = Path("data/guidelines")

CHUNK_SIZE = 500
CHUNK_OVERLAP = 100

SUPPORTED_EXTENSIONS = [".txt", ".pdf"]


# ----------------------------
# TEXT CLEANING
# ----------------------------
def clean_text(text: str) -> str:
    """Clean medical document text."""
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"\n+", "\n", text)
    text = text.strip()

    # Remove page numbers / headers (common in PDFs)
    text = re.sub(r"Page \d+ of \d+", "", text, flags=re.IGNORECASE)

    return text


# ----------------------------
# PDF READER
# ----------------------------
def read_pdf(file_path: Path) -> str:
    """Extract text from PDF using PyPDF, fallback to pdfminer."""
    try:
        reader = PdfReader(str(file_path))
        text = ""

        for page in reader.pages:
            text += page.extract_text() or ""

        if len(text.strip()) < 100 and PDFMINER_AVAILABLE:
            log.warning("pdf.low_text_using_pdfminer", file=file_path.name)
            text = pdfminer_extract(str(file_path))

        return clean_text(text)

    except Exception as e:
        log.error("pdf.read_error", file=file_path.name, error=str(e))
        return ""


# ----------------------------
# TXT READER
# ----------------------------
def read_txt(file_path: Path) -> str:
    try:
        return clean_text(file_path.read_text(encoding="utf-8"))
    except Exception as e:
        log.error("txt.read_error", file=file_path.name, error=str(e))
        return ""


# ----------------------------
# SMART CHUNKING
# ----------------------------
def chunk_text(text: str) -> list[str]:
    """Sentence-aware chunking (better for LLM retrieval)."""

    if USE_NLTK:
        sentences = sent_tokenize(text)
    else:
        sentences = text.split(". ")

    chunks = []
    current = ""

    for sentence in sentences:
        if len(current) + len(sentence) < CHUNK_SIZE:
            current += " " + sentence
        else:
            chunks.append(current.strip())
            current = sentence

    if current:
        chunks.append(current.strip())

    # Overlap
    final_chunks = []
    for i, chunk in enumerate(chunks):
        if i > 0:
            prev = chunks[i - 1][-CHUNK_OVERLAP:]
            chunk = prev + " " + chunk
        final_chunks.append(chunk.strip())

    return [c for c in final_chunks if len(c) > 80]


# ----------------------------
# DUPLICATE HANDLING
# ----------------------------
def hash_text(text: str) -> str:
    return hashlib.md5(text.encode()).hexdigest()


def is_duplicate(store, text_hash: str) -> bool:
    return any(m.get("hash") == text_hash for m in store.metadata)


# ----------------------------
# LOAD FILE
# ----------------------------
def load_file(file_path: Path):
    store = get_vector_store()

    if file_path.suffix == ".pdf":
        content = read_pdf(file_path)
    elif file_path.suffix == ".txt":
        content = read_txt(file_path)
    else:
        return

    if not content or len(content) < 100:
        log.warning("file.empty_or_small", file=file_path.name)
        return

    chunks = chunk_text(content)

    texts = []
    sources = []

    for i, chunk in enumerate(chunks):
        h = hash_text(chunk)

        if is_duplicate(store, h):
            continue

        texts.append(chunk)
        sources.append(f"{file_path.name} (chunk {i+1})")

        store.metadata.append({
            "hash": h  # store hash for deduplication
        })

    if texts:
        store.add_texts(texts, sources)
        log.info("file_loaded", file=file_path.name, chunks=len(texts))


# ----------------------------
# LOAD ALL FILES
# ----------------------------
def load_from_directory(directory: Path = GUIDELINES_DIR):
    if not directory.exists():
        log.warning("dir_not_found", path=str(directory))
        return

    files = [
        f for f in directory.glob("*")
        if f.suffix.lower() in SUPPORTED_EXTENSIONS
    ]

    if not files:
        log.warning("no_files_found")
        return

    for file in files:
        load_file(file)


# ----------------------------
# ENTRY POINT
# ----------------------------
if __name__ == "__main__":
    import structlog
    structlog.configure()

    log.info("knowledge_loader.starting")

    load_from_directory()

    total = get_vector_store().total_vectors()
    log.info("knowledge_loader.complete", total_vectors=total)