#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GGUF Runner Cloud Gateway (FastAPI)
Auth API keys · rate limit · multi-model route · approval-aware tool policy
Developer: Mehdi Tariri <mahditariri@gmail.com>
"""
from __future__ import annotations

import os
import time
from collections import defaultdict, deque
from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

APP = FastAPI(title="GGUF Runner Gateway", version="2.1.0")
ROOT = Path(os.environ.get("GGUF_ROOT", Path(__file__).resolve().parents[2]))
API_KEYS = set(filter(None, os.environ.get("GGUF_API_KEYS", "dev-key-change-me").split(",")))
RATE_PER_MIN = int(os.environ.get("GGUF_RATE_PER_MIN", "30"))
_buckets: dict[str, deque] = defaultdict(deque)

# Optional local backends
LLAMA_URL = os.environ.get("LLAMA_SERVER_URL", "http://127.0.0.1:8080")
VLLM_URL = os.environ.get("VLLM_URL", "")  # e.g. http://vllm:8000


class ChatIn(BaseModel):
    model: str = Field(default="default")
    messages: list[dict[str, Any]]
    temperature: float = 0.7
    max_tokens: int = 512


class ToolIn(BaseModel):
    name: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    approved: bool = False


def _auth(x_api_key: str | None = Header(default=None)) -> str:
    key = x_api_key or ""
    if key not in API_KEYS:
        raise HTTPException(401, "invalid API key")
    # rate limit
    now = time.time()
    q = _buckets[key]
    while q and now - q[0] > 60:
        q.popleft()
    if len(q) >= RATE_PER_MIN:
        raise HTTPException(429, "rate limit")
    q.append(now)
    return key


@APP.get("/health")
def health():
    return {"ok": True, "service": "gguf-gateway", "llama": LLAMA_URL, "vllm": bool(VLLM_URL)}


@APP.get("/v1/models")
def models(_: str = Depends(_auth)):
    models_dir = ROOT / "models"
    items = []
    if models_dir.exists():
        for p in sorted(models_dir.glob("*.gguf")):
            items.append({"id": p.name, "object": "model"})
    if VLLM_URL:
        items.append({"id": "vllm-default", "object": "model"})
    return {"object": "list", "data": items}


@APP.post("/v1/chat/completions")
def chat(body: ChatIn, _: str = Depends(_auth)):
    """Route to llama-server (GGUF) or vLLM if configured."""
    import json
    import urllib.request

    backend = LLAMA_URL
    if body.model.startswith("vllm") and VLLM_URL:
        backend = VLLM_URL.rstrip("/")
        url = backend + "/v1/chat/completions"
    else:
        url = LLAMA_URL.rstrip("/") + "/v1/chat/completions"
    payload = json.dumps(
        {
            "model": body.model,
            "messages": body.messages,
            "temperature": body.temperature,
            "max_tokens": body.max_tokens,
            "stream": False,
        }
    ).encode()
    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return json.loads(r.read().decode())
    except Exception as e:
        raise HTTPException(502, f"backend error: {e}")


@APP.post("/v1/tools/execute")
def tools_execute(body: ToolIn, _: str = Depends(_auth)):
    """
    Cloud tool execution is FAIL-CLOSED without approved=true.
    Raw tool name+args required; no model prose path.
    """
    if not body.approved:
        raise HTTPException(403, "approval required: set approved=true after human review of RAW args")
    # Import local tools if available
    try:
        import sys

        sys.path.insert(0, str(ROOT / "scripts" / "python"))
        import agent_tools
        import approval_gate

        # still classify
        dec = approval_gate.classify(body.name)
        if dec == "BLOCK":
            raise HTTPException(403, "tool blocked by policy")
        # approved flag from client acts as human gate
        result = agent_tools.dispatch(body.name, body.arguments, skip_gate=True)
        return {"ok": True, "policy": dec, "result": result}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, str(e))


@APP.get("/v1/metrics/basic")
def metrics_basic(_: str = Depends(_auth)):
    return {
        "keys_active": len(_buckets),
        "rate_per_min": RATE_PER_MIN,
    }
