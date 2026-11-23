# -*- coding: utf-8 -*-
"""Layer 3: todo plan, persistent memory, session reflect, workspace RAG trigger."""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from config_loader import workspace_dir

MEM_DIR = workspace_dir() / "agent_memory"
TODO_PATH = MEM_DIR / "todo.json"
KV_PATH = MEM_DIR / "kv.json"
REFLECT_PATH = MEM_DIR / "reflections.jsonl"


def _load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def _save_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def todo_list() -> dict[str, Any]:
    items = _load_json(TODO_PATH, [])
    return {"ok": True, "items": items, "count": len(items)}


def todo_plan(tasks: list | str) -> dict[str, Any]:
    """Replace or set todo list. tasks: list of strings or JSON array string."""
    if isinstance(tasks, str):
        try:
            tasks = json.loads(tasks)
        except json.JSONDecodeError:
            tasks = [t.strip() for t in tasks.split("\n") if t.strip()]
    if not isinstance(tasks, list):
        return {"ok": False, "error": "tasks must be list"}
    items = []
    for i, t in enumerate(tasks[:50]):
        if isinstance(t, dict):
            items.append({"id": t.get("id", i + 1), "text": str(t.get("text", t)), "done": bool(t.get("done"))})
        else:
            items.append({"id": i + 1, "text": str(t), "done": False})
    _save_json(TODO_PATH, items)
    return {"ok": True, "items": items, "count": len(items)}


def todo_tick(id: int, done: bool = True) -> dict[str, Any]:
    items = _load_json(TODO_PATH, [])
    found = False
    for it in items:
        if int(it.get("id", -1)) == int(id):
            it["done"] = bool(done)
            found = True
            break
    if not found:
        return {"ok": False, "error": f"id not found: {id}"}
    _save_json(TODO_PATH, items)
    return {"ok": True, "items": items}


def memory_save(key: str, value: str) -> dict[str, Any]:
    key = (key or "").strip()
    if not key:
        return {"ok": False, "error": "key required"}
    data = _load_json(KV_PATH, {})
    data[key] = {"value": value, "ts": time.time()}
    _save_json(KV_PATH, data)
    return {"ok": True, "key": key}


def memory_get(key: str = "") -> dict[str, Any]:
    data = _load_json(KV_PATH, {})
    if key:
        if key not in data:
            return {"ok": False, "error": "not found"}
        return {"ok": True, "key": key, "entry": data[key]}
    return {"ok": True, "keys": list(data.keys()), "count": len(data)}


def session_reflect(summary: str, next_steps: str = "") -> dict[str, Any]:
    MEM_DIR.mkdir(parents=True, exist_ok=True)
    row = {"ts": time.time(), "summary": summary, "next_steps": next_steps}
    with REFLECT_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
    return {"ok": True, "saved": True}


def workspace_rag_rebuild(max_docs: int = 500) -> dict[str, Any]:
    try:
        from rag_local import build_index
        return build_index(max_docs=max_docs)
    except Exception as e:
        return {"ok": False, "error": str(e)}


def workspace_rag_search(query: str, top_k: int = 5) -> dict[str, Any]:
    try:
        from rag_local import rag_search
        return rag_search(query, top_k=top_k)
    except Exception as e:
        return {"ok": False, "error": str(e)}


MEMORY_LAYER_TOOLS = {
    "todo_list": todo_list,
    "todo_plan": todo_plan,
    "todo_tick": todo_tick,
    "memory_save": memory_save,
    "memory_get": memory_get,
    "session_reflect": session_reflect,
    "workspace_rag_rebuild": workspace_rag_rebuild,
    "workspace_rag_search": workspace_rag_search,
}
