# -*- coding: utf-8 -*-
"""Ingest books/ and memory/ text into local RAG index."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from config_loader import ROOT
from rag_local import build_index, INDEX_PATH


def main():
    books = ROOT / "books"
    mem = ROOT / "memory"
    books.mkdir(exist_ok=True)
    mem.mkdir(exist_ok=True)
    n_books = len(list(books.glob("*.txt")) + list(books.glob("*.md")))
    n_mem = len(list(mem.glob("*.txt")) + list(mem.glob("*.md")))
    print(f"books files: {n_books}, memory files: {n_mem}")
    result = build_index(max_docs=800, chunk_size=900)
    print(result)
    print(f"index: {INDEX_PATH}")
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
