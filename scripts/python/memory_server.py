# -*- coding: utf-8 -*-
"""Simple text / keyword RAG memory server on :8765"""
from __future__ import annotations

import json
import re
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parents[2]
MEMORY = ROOT / "memory"
VECTORS = MEMORY / "vectors"
BOOKS = ROOT / "books"

MEMORY.mkdir(exist_ok=True)
VECTORS.mkdir(exist_ok=True)


def load_corpus() -> list[dict]:
    docs = []
    for folder in (VECTORS, BOOKS, MEMORY):
        if not folder.exists():
            continue
        for p in folder.rglob("*"):
            if p.suffix.lower() in (".txt", ".md", ".jsonl") and p.is_file():
                try:
                    text = p.read_text(encoding="utf-8", errors="replace")
                except Exception:
                    continue
                # chunk roughly by paragraphs
                chunks = [c.strip() for c in re.split(r"\n{2,}", text) if c.strip()]
                for i, c in enumerate(chunks):
                    docs.append({"id": f"{p.name}:{i}", "source": str(p.relative_to(ROOT)), "text": c[:4000]})
    return docs


CORPUS = load_corpus()


def search(query: str, top_k: int = 5) -> list[dict]:
    q = query.lower().split()
    if not q:
        return []
    scored = []
    for doc in CORPUS:
        text = doc["text"].lower()
        score = sum(1 for w in q if w in text)
        if score:
            scored.append((score, doc))
    scored.sort(key=lambda x: -x[0])
    return [d for _, d in scored[:top_k]]


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        print(f"[memory] {args[0]}")

    def _json(self, code: int, obj):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        u = urlparse(self.path)
        if u.path in ("/", "/health"):
            return self._json(200, {"ok": True, "docs": len(CORPUS), "service": "memory"})
        if u.path == "/search":
            qs = parse_qs(u.query)
            q = (qs.get("q") or [""])[0]
            k = int((qs.get("k") or ["5"])[0])
            return self._json(200, {"results": search(q, k)})
        self._json(404, {"error": "not found"})

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length) if length else b"{}"
        try:
            data = json.loads(raw.decode("utf-8"))
        except Exception:
            return self._json(400, {"error": "bad json"})
        if self.path == "/search":
            return self._json(200, {"results": search(data.get("query", ""), int(data.get("top_k", 5)))})
        if self.path == "/reload":
            global CORPUS
            CORPUS = load_corpus()
            return self._json(200, {"ok": True, "docs": len(CORPUS)})
        self._json(404, {"error": "not found"})


def main():
    host, port = "127.0.0.1", 8765
    print(f"Memory / RAG server http://{host}:{port}  docs={len(CORPUS)}")
    HTTPServer((host, port), Handler).serve_forever()


if __name__ == "__main__":
    main()
