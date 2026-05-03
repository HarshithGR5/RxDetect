#!/usr/bin/env python3
"""
scripts/ingest_pdfs.py
======================
One-time (or on-demand) offline ingestion script.
Run this BEFORE starting the server when you add new PDFs.

Usage
-----
# Index everything in data/guidelines/
python scripts/ingest_pdfs.py

# Index a single file
python scripts/ingest_pdfs.py --file /path/to/clinical_pharmacy.pdf

# Re-index everything from scratch (wipe + rebuild)
python scripts/ingest_pdfs.py --reset

# Add a single file without touching existing index
python scripts/ingest_pdfs.py --file /path/to/new.pdf

# Point at a custom guidelines directory
python scripts/ingest_pdfs.py --dir /custom/path

Environment
-----------
Requires a valid .env file in the project root with:
  OPENAI_API_KEY=sk-...
  POSTGRES_* (only needed if the app models are imported — not required here)
"""

import sys
import time
import argparse
from pathlib import Path

# ── Make project root importable ──────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

import structlog
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="%H:%M:%S"),
        structlog.dev.ConsoleRenderer(),
    ]
)

log = structlog.get_logger()

# ── Imports after path/env setup ──────────────────────────────────────────────
from app.services.rag.vector_store    import get_vector_store
from app.services.rag.knowledge_loader import (
    load_file,
    load_from_directory,
    GUIDELINES_DIR,
)


def print_stats():
    stats = get_vector_store().stats()
    print("\n" + "=" * 60)
    print(f"  FAISS index — {stats['total_vectors']} total vectors")
    print("  Chunks per file:")
    for fname, count in sorted(stats["chunks_per_file"].items()):
        print(f"    {fname:<50} {count:>5} chunks")
    print("=" * 60 + "\n")


def main():
    parser = argparse.ArgumentParser(
        description="Ingest clinical PDFs into the RxDetect FAISS knowledge base"
    )
    parser.add_argument(
        "--dir",
        default=str(GUIDELINES_DIR),
        help="Directory containing PDF/TXT guideline files (default: data/guidelines/)",
    )
    parser.add_argument(
        "--file",
        help="Path to a single PDF or TXT file to add to the index",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Wipe the existing index and rebuild from scratch",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-embed chunks even if they already exist in the index",
    )
    args = parser.parse_args()

    store = get_vector_store()

    # ── Optional reset ────────────────────────────────────────────────────────
    if args.reset:
        confirm = input(
            f"This will DELETE all {store.total_vectors()} existing vectors. "
            "Type 'yes' to confirm: "
        ).strip()
        if confirm.lower() != "yes":
            print("Aborted.")
            return
        store.reset()
        print("Index wiped.\n")

    print_stats()
    t0 = time.time()

    # ── Ingest ────────────────────────────────────────────────────────────────
    if args.file:
        path = Path(args.file)
        if not path.exists():
            print(f"ERROR: file not found: {path}")
            sys.exit(1)
        added = load_file(path, force=args.force)
        print(f"\nAdded {added} new chunks from {path.name}")
    else:
        added = load_from_directory(Path(args.dir), force=args.force)
        print(f"\nAdded {added} new chunks total")

    elapsed = time.time() - t0
    print(f"Elapsed: {elapsed:.1f}s")
    print_stats()


if __name__ == "__main__":
    main()
