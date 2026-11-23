# -*- coding: utf-8 -*-
"""Minimal web fetch proxy on :8766 (for agent net_fetch)."""
from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        print(f"[proxy] {args[0]}")

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
            return self._json(200, {"ok": True, "service": "web_proxy"})
        self._json(404, {"error": "use POST /fetch"})

    def do_POST(self):
        if self.path not in ("/fetch", "/v1/fetch"):
            return self._json(404, {"error": "not found"})
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length)
        try:
            data = json.loads(raw.decode("utf-8"))
        except Exception:
            return self._json(400, {"error": "bad json"})
        url = data.get("url") or ""
        if not url.startswith(("http://", "https://")):
            return self._json(400, {"error": "invalid url"})
        try:
            req = Request(url, headers={"User-Agent": "GGUF-Runner-Proxy/2.3"})
            with urlopen(req, timeout=20) as r:
                content = r.read(500_000).decode("utf-8", errors="replace")
            return self._json(200, {"ok": True, "url": url, "content": content[:100_000]})
        except (URLError, HTTPError, TimeoutError) as e:
            return self._json(502, {"ok": False, "error": str(e)})


def main():
    print("Web proxy http://127.0.0.1:8766")
    HTTPServer(("127.0.0.1", 8766), Handler).serve_forever()


if __name__ == "__main__":
    main()
