# -*- coding: utf-8 -*-
"""Chat session list/load/delete/export."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from config_loader import sessions_dir, workspace_dir


def session_list(limit: int = 50) -> dict[str, Any]:
    d = sessions_dir()
    files = sorted(d.glob("session_*.json"), key=lambda p: p.stat().st_mtime, reverse=True)[:limit]
    items = []
    for p in files:
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            items.append({
                "file": p.name,
                "id": data.get("id"),
                "model": data.get("model"),
                "profile": data.get("profile"),
                "messages": len(data.get("messages") or []),
                "saved_at": data.get("saved_at"),
            })
        except Exception as e:
            items.append({"file": p.name, "error": str(e)})
    return {"ok": True, "sessions": items, "count": len(items)}


def session_load(file_name: str) -> dict[str, Any]:
    name = Path(file_name).name
    if not name.startswith("session_") or not name.endswith(".json"):
        return {"ok": False, "error": "invalid session file name"}
    p = sessions_dir() / name
    if not p.exists():
        return {"ok": False, "error": "not found"}
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        return {"ok": True, "session": data, "file": name}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def session_delete(file_name: str) -> dict[str, Any]:
    name = Path(file_name).name
    p = sessions_dir() / name
    if not p.exists():
        return {"ok": False, "error": "not found"}
    p.unlink()
    return {"ok": True, "deleted": name}


def session_export_md(file_name: str, out_name: str | None = None) -> dict[str, Any]:
    loaded = session_load(file_name)
    if not loaded.get("ok"):
        return loaded
    sess = loaded["session"]
    lines = [
        f"# Session {sess.get('id', file_name)}",
        f"- model: {sess.get('model')}",
        f"- profile: {sess.get('profile')}",
        f"- saved_at: {sess.get('saved_at')}",
        "",
    ]
    for m in sess.get("messages") or []:
        role = m.get("role", "?")
        content = str(m.get("content") or "")
        lines.append(f"## {role}\n\n{content}\n")
    out_dir = workspace_dir() / "exports"
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / (out_name or Path(file_name).stem + ".md")
    out.write_text("\n".join(lines), encoding="utf-8")
    return {"ok": True, "path": str(out.relative_to(workspace_dir())), "messages": len(sess.get("messages") or [])}
