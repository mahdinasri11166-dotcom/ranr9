# -*- coding: utf-8 -*-
"""Agent tool audit trail."""
from __future__ import annotations
import json
import time
from pathlib import Path
from typing import Any
from config_loader import ROOT

def _path() -> Path:
    d = ROOT / "workspace" / "audit"
    d.mkdir(parents=True, exist_ok=True)
    return d / "tools_audit.jsonl"

def audit_tool(name: str, arguments: dict[str, Any] | None, result: dict[str, Any] | None, approved: bool | None = None) -> None:
    rec = {
        "ts": time.time(),
        "tool": name,
        "arguments": _clip(arguments or {}),
        "ok": (result or {}).get("ok"),
        "approved": approved,
        "error": (result or {}).get("error"),
    }
    try:
        with _path().open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    except Exception:
        pass

def _clip(obj: Any, n: int = 2000) -> Any:
    s = json.dumps(obj, ensure_ascii=False, default=str)
    if len(s) > n:
        return s[:n] + "…"
    return obj

def read_audit(limit: int = 50) -> list[dict[str, Any]]:
    p = _path()
    if not p.exists():
        return []
    lines = p.read_text(encoding="utf-8").splitlines()
    out = []
    for line in lines[-limit:]:
        try:
            out.append(json.loads(line))
        except Exception:
            continue
    return list(reversed(out))
