# -*- coding: utf-8 -*-
"""PDF / image text extract helper on :8767"""
from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def extract_pdf(path: Path) -> str:
    try:
        from pypdf import PdfReader
        reader = PdfReader(str(path))
        parts = []
        for page in reader.pages[:50]:
            t = page.extract_text() or ""
            if t.strip():
                parts.append(t)
        return "\n\n".join(parts)
    except Exception as e:
        return f"[pypdf error: {e}]"


def extract_image(path: Path) -> str:
    try:
        from PIL import Image
        img = Image.open(path)
        return f"[image {path.name} size={img.size} mode={img.mode}] (OCR not bundled offline)"
    except Exception as e:
        return f"[image error: {e}]"


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        print(f"[extract] {args[0]}")

    def _json(self, code, obj):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
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
        if self.path in ("/", "/health"):
            return self._json(200, {"ok": True, "service": "file_extract"})
        self._json(404, {"error": "not found"})

    def do_POST(self):
        if self.path not in ("/extract", "/v1/extract"):
            return self._json(404, {"error": "not found"})
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length)
        try:
            data = json.loads(raw.decode("utf-8"))
        except Exception:
            return self._json(400, {"error": "bad json"})
        path = Path(data.get("path") or "")
        if not path.is_absolute():
            path = ROOT / path
        if not path.exists():
            return self._json(404, {"error": "file not found"})
        suf = path.suffix.lower()
        if suf == ".pdf":
            text = extract_pdf(path)
        elif suf in (".png", ".jpg", ".jpeg", ".webp", ".bmp"):
            text = extract_image(path)
        elif suf in (".txt", ".md", ".csv", ".json"):
            text = path.read_text(encoding="utf-8", errors="replace")[:100_000]
        else:
            return self._json(400, {"error": f"unsupported type {suf}"})
        return self._json(200, {"ok": True, "path": str(path), "text": text[:100_000]})


def main():
    print("File extract http://127.0.0.1:8767")
    HTTPServer(("127.0.0.1", 8767), Handler).serve_forever()


if __name__ == "__main__":
    main()
