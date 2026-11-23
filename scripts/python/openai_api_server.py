# -*- coding: utf-8 -*-
"""
OpenAI-compatible HTTP API on localhost for GGUF Runner.
Endpoints: GET /v1/models, POST /v1/chat/completions, GET /health
Uses llama-cpp-python when a .gguf is loaded; can also proxy llama-server.
"""
from __future__ import annotations

import json
import threading
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen

from config_loader import ROOT, list_models, load_ini, identity_system_suffix

HOST = "127.0.0.1"
PORT = 8787
LLAMA_SERVER = "http://127.0.0.1:8080"

_lock = threading.Lock()
_llm = None
_model_name: str | None = None
_n_ctx = 4096


def _load_model(path: Path, n_ctx: int = 4096, n_gpu_layers: int = 0) -> str:
    global _llm, _model_name, _n_ctx
    try:
        from llama_cpp import Llama
    except ImportError:
        return "llama-cpp-python not installed"
    with _lock:
        try:
            _llm = Llama(
                model_path=str(path),
                n_ctx=n_ctx,
                n_gpu_layers=n_gpu_layers,
                verbose=False,
            )
            _model_name = path.name
            _n_ctx = n_ctx
            return ""
        except Exception as e:
            _llm = None
            _model_name = None
            return str(e)


def _ensure_default_model() -> str | None:
    """Load first available model if none loaded. Returns error or None."""
    global _llm
    if _llm is not None:
        return None
    models = list_models()
    if not models:
        return "no .gguf in models/"
    cfg = load_ini()
    err = _load_model(
        models[0],
        n_ctx=int(cfg.get("ctx_size") or 4096),
        n_gpu_layers=int(cfg.get("n_gpu_layers") or 0),
    )
    return err or None


def _proxy_llama_server(body: bytes) -> tuple[int, bytes]:
    try:
        req = Request(
            LLAMA_SERVER + "/v1/chat/completions",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(req, timeout=300) as r:
            return r.status, r.read()
    except Exception as e:
        return 502, json.dumps({"error": {"message": str(e), "type": "proxy_error"}}).encode()


def _chat_local(payload: dict[str, Any]) -> dict[str, Any]:
    err = _ensure_default_model()
    if err:
        return {"error": {"message": err, "type": "model_error"}}
    messages = list(payload.get("messages") or [])
    # inject fixed identity into first system message or prepend one
    suffix = identity_system_suffix()
    if messages and messages[0].get("role") == "system":
        messages[0] = dict(messages[0])
        messages[0]["content"] = (messages[0].get("content") or "") + suffix
    else:
        messages = [{"role": "system", "content": "You are a helpful assistant." + suffix}] + messages
    temperature = float(payload.get("temperature", 0.7))
    max_tokens = int(payload.get("max_tokens", 1024))
    top_p = float(payload.get("top_p", 0.9))
    stream = bool(payload.get("stream", False))
    if stream:
        # simple non-stream fallback for compatibility
        pass
    with _lock:
        assert _llm is not None
        out = _llm.create_chat_completion(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            top_p=top_p,
            stream=False,
        )
    # normalize id
    if isinstance(out, dict):
        out.setdefault("id", f"chatcmpl-{uuid.uuid4().hex[:24]}")
        out.setdefault("object", "chat.completion")
        out.setdefault("created", int(time.time()))
        out.setdefault("model", _model_name or "gguf-local")
    return out


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        print(f"[api] {args[0]}")

    def _send(self, code: int, obj: Any, content_type: str = "application/json"):
        if isinstance(obj, (dict, list)):
            body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        elif isinstance(obj, bytes):
            body = obj
        else:
            body = str(obj).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", f"{content_type}; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self._send(204, b"")

    def do_GET(self):
        path = self.path.split("?")[0]
        if path in ("/", "/health"):
            return self._send(200, {
                "ok": True,
                "service": "gguf-openai-api",
                "model_loaded": _model_name,
                "port": PORT,
            })
        if path == "/v1/models":
            models = [{"id": p.name, "object": "model", "owned_by": "local"} for p in list_models()]
            if _model_name and not any(m["id"] == _model_name for m in models):
                models.insert(0, {"id": _model_name, "object": "model", "owned_by": "local"})
            return self._send(200, {"object": "list", "data": models})
        self._send(404, {"error": {"message": "not found", "type": "not_found"}})

    def do_POST(self):
        path = self.path.split("?")[0]
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length) if length else b"{}"
        try:
            payload = json.loads(raw.decode("utf-8") or "{}")
        except json.JSONDecodeError:
            return self._send(400, {"error": {"message": "invalid json", "type": "invalid_request_error"}})

        if path == "/v1/models/load":
            name = (payload.get("model") or "").strip()
            models = {p.name: p for p in list_models()}
            if name not in models:
                return self._send(404, {"error": {"message": f"model not found: {name}"}})
            err = _load_model(
                models[name],
                n_ctx=int(payload.get("n_ctx") or load_ini().get("ctx_size") or 4096),
                n_gpu_layers=int(payload.get("n_gpu_layers") or load_ini().get("n_gpu_layers") or 0),
            )
            if err:
                return self._send(500, {"error": {"message": err}})
            return self._send(200, {"ok": True, "model": name})

        if path in ("/v1/chat/completions", "/chat/completions"):
            # Prefer local llama-cpp; optional proxy if use_server true
            if payload.get("use_llama_server"):
                code, body = _proxy_llama_server(raw)
                self.send_response(code)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
            result = _chat_local(payload)
            if "error" in result and "choices" not in result:
                return self._send(500, result)
            return self._send(200, result)

        self._send(404, {"error": {"message": "not found", "type": "not_found"}})


def main():
    cfg = load_ini()
    host = str(cfg.get("api_host") or HOST)
    port = int(cfg.get("api_port") or PORT)
    # try preload first model
    err = _ensure_default_model()
    if err:
        print(f"[api] no model preloaded: {err}")
    else:
        print(f"[api] loaded: {_model_name}")
    print(f"OpenAI-compatible API http://{host}:{port}")
    print("  GET  /health")
    print("  GET  /v1/models")
    print("  POST /v1/chat/completions")
    print("  POST /v1/models/load  {\"model\": \"file.gguf\"}")
    httpd = ThreadingHTTPServer((host, port), Handler)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nbye")


if __name__ == "__main__":
    main()
