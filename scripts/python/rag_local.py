# -*- coding: utf-8 -*-
"""Local RAG with lightweight bag-of-words embeddings (numpy). No GPU required."""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from config_loader import ROOT, workspace_dir

try:
    import numpy as np
except ImportError:
    np = None  # type: ignore

INDEX_PATH = workspace_dir() / "osint" / "rag_index.json"
DOCS_DIRS = [ROOT / "books", ROOT / "memory", workspace_dir() / "rag_docs", workspace_dir() / "osint" / "cases", workspace_dir() / "exports"]


def _tokenize(text: str) -> list[str]:
    text = text.lower()
    return re.findall(r"[a-z0-9\u0600-\u06ff]{2,}", text)


def _embed(tokens: list[str], vocab: dict[str, int]) -> list[float]:
    v = [0.0] * len(vocab)
    if not tokens:
        return v
    for t in tokens:
        if t in vocab:
            v[vocab[t]] += 1.0
    # L2 norm
    s = sum(x * x for x in v) ** 0.5
    if s > 0:
        v = [x / s for x in v]
    return v


def build_index(max_docs: int = 400, chunk_size: int = 800) -> dict[str, Any]:
    chunks: list[dict[str, Any]] = []
    for folder in DOCS_DIRS:
        if not folder.exists():
            continue
        for p in folder.rglob("*"):
            if not p.is_file() or p.suffix.lower() not in (".txt", ".md", ".json", ".jsonl", ".csv"):
                continue
            try:
                text = p.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue
            for i in range(0, len(text), chunk_size):
                piece = text[i : i + chunk_size].strip()
                if len(piece) < 40:
                    continue
                chunks.append({"id": f"{p.name}:{i}", "source": str(p), "text": piece})
                if len(chunks) >= max_docs:
                    break
            if len(chunks) >= max_docs:
                break
    # vocab from document frequency top terms
    df: dict[str, int] = {}
    tok_list = []
    for c in chunks:
        toks = set(_tokenize(c["text"]))
        tok_list.append(toks)
        for t in toks:
            df[t] = df.get(t, 0) + 1
    # keep frequent-enough but not ultra-common
    terms = [t for t, n in sorted(df.items(), key=lambda x: -x[1]) if 1 < n < max(2, len(chunks) * 0.9)]
    terms = terms[:2000]
    vocab = {t: i for i, t in enumerate(terms)}
    vectors = []
    for c in chunks:
        vectors.append(_embed(_tokenize(c["text"]), vocab))
    payload = {"vocab": vocab, "chunks": chunks, "vectors": vectors}
    INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
    INDEX_PATH.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return {"ok": True, "chunks": len(chunks), "vocab_size": len(vocab), "path": str(INDEX_PATH)}


def _load_index() -> dict[str, Any] | None:
    if not INDEX_PATH.exists():
        return None
    try:
        return json.loads(INDEX_PATH.read_text(encoding="utf-8"))
    except Exception:
        return None


def rag_search(query: str, top_k: int = 5) -> dict[str, Any]:
    idx = _load_index()
    if not idx:
        built = build_index()
        idx = _load_index()
        if not idx:
            return {"ok": False, "error": "ایندکس ساخته نشد", "build": built}
    vocab = idx["vocab"]
    qv = _embed(_tokenize(query), vocab)
    scored = []
    for i, vec in enumerate(idx["vectors"]):
        # dot product
        score = sum(a * b for a, b in zip(qv, vec))
        if score > 0:
            scored.append((score, i))
    scored.sort(key=lambda x: -x[0])
    hits = []
    for score, i in scored[:top_k]:
        c = idx["chunks"][i]
        hits.append({"score": round(float(score), 4), "id": c["id"], "source": c["source"], "text": c["text"][:1200]})
    return {"ok": True, "query": query, "results": hits, "count": len(hits)}
