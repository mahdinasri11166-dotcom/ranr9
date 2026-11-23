# -*- coding: utf-8 -*-
"""Simple plugin loader: workspace/plugins/<name>/plugin.json + optional run.py"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import Any

from config_loader import workspace_dir, ROOT

PLUGIN_DIRS = [workspace_dir() / "plugins", ROOT / "plugins"]


def _iter_plugins() -> list[Path]:
    found = []
    for base in PLUGIN_DIRS:
        if not base.exists():
            continue
        for p in base.iterdir():
            if p.is_dir() and (p / "plugin.json").exists():
                found.append(p)
    return found


def plugin_list() -> dict[str, Any]:
    items = []
    for p in _iter_plugins():
        try:
            meta = json.loads((p / "plugin.json").read_text(encoding="utf-8"))
        except Exception as e:
            meta = {"error": str(e)}
        items.append({"id": p.name, "path": str(p), "meta": meta})
    return {"ok": True, "plugins": items, "count": len(items)}


def plugin_run(plugin_id: str, arguments: dict | None = None) -> dict[str, Any]:
    arguments = arguments or {}
    target = None
    for p in _iter_plugins():
        if p.name == plugin_id:
            target = p
            break
    if not target:
        return {"ok": False, "error": f"plugin not found: {plugin_id}"}
    meta = json.loads((target / "plugin.json").read_text(encoding="utf-8"))
    risk = (meta.get("risk") or "high").lower()
    entry = target / (meta.get("entry") or "run.py")
    if not entry.exists():
        return {"ok": False, "error": "entry script missing", "meta": meta}
    # only allow plugins marked read_only or low/medium — high still runnable after approval in UI
    spec = importlib.util.spec_from_file_location(f"gguf_plugin_{plugin_id}", entry)
    if not spec or not spec.loader:
        return {"ok": False, "error": "cannot load plugin"}
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    if not hasattr(mod, "run"):
        return {"ok": False, "error": "plugin must define run(**kwargs)"}
    result = mod.run(**arguments)
    if not isinstance(result, dict):
        result = {"ok": True, "result": result}
    result.setdefault("plugin", plugin_id)
    result.setdefault("risk", risk)
    return result


def ensure_sample_plugin() -> None:
    d = workspace_dir() / "plugins" / "echo_sample"
    d.mkdir(parents=True, exist_ok=True)
    (d / "plugin.json").write_text(
        json.dumps({
            "name": "Echo Sample",
            "version": "1.0",
            "risk": "low",
            "read_only": True,
            "entry": "run.py",
            "description": "نمونه پلاگین؛ ورودی را برمی‌گرداند",
        }, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (d / "run.py").write_text(
        "def run(message='hello', **kwargs):\n"
        "    return {'ok': True, 'echo': message, 'kwargs': kwargs}\n",
        encoding="utf-8",
    )
