# -*- coding: utf-8 -*-
"""OSINT case workspace: notes, timeline, linked reports."""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from config_loader import workspace_dir

CASES_ROOT = workspace_dir() / "osint" / "cases"


def _slug(name: str) -> str:
    s = re.sub(r"[^\w\-]+", "_", (name or "case").strip(), flags=re.U)
    return (s[:60] or "case").strip("_") or "case"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def case_create(name: str, target: str = "", notes: str = "") -> dict[str, Any]:
    slug = _slug(name)
    path = CASES_ROOT / slug
    path.mkdir(parents=True, exist_ok=True)
    meta = {
        "id": slug,
        "name": name or slug,
        "target": target,
        "created_at": _now(),
        "updated_at": _now(),
        "notes": notes or "",
        "timeline": [{"time": _now(), "event": "case_created", "detail": target or name}],
        "artifacts": [],
    }
    (path / "case.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    (path / "notes.md").write_text(f"# {meta['name']}\n\nTarget: {target}\n\n{notes}\n", encoding="utf-8")
    return {"ok": True, "case": meta, "path": str(path.relative_to(workspace_dir()))}


def case_list() -> dict[str, Any]:
    CASES_ROOT.mkdir(parents=True, exist_ok=True)
    items = []
    for p in sorted(CASES_ROOT.iterdir()):
        if not p.is_dir():
            continue
        meta_path = p / "case.json"
        if meta_path.exists():
            try:
                meta = json.loads(meta_path.read_text(encoding="utf-8"))
            except Exception:
                meta = {"id": p.name, "error": "bad case.json"}
        else:
            meta = {"id": p.name}
        items.append(meta)
    return {"ok": True, "cases": items, "count": len(items)}


def _load(case_id: str) -> tuple[Path, dict[str, Any]] | tuple[None, dict[str, Any]]:
    path = CASES_ROOT / _slug(case_id)
    if not path.exists():
        # try exact
        path = CASES_ROOT / case_id
    if not path.exists() or not (path / "case.json").exists():
        return None, {"ok": False, "error": f"case not found: {case_id}"}
    try:
        meta = json.loads((path / "case.json").read_text(encoding="utf-8"))
    except Exception as e:
        return None, {"ok": False, "error": str(e)}
    return path, meta


def case_get(case_id: str) -> dict[str, Any]:
    path, meta = _load(case_id)
    if path is None:
        return meta
    notes = ""
    np = path / "notes.md"
    if np.exists():
        notes = np.read_text(encoding="utf-8", errors="replace")[:20000]
    return {"ok": True, "case": meta, "notes": notes, "path": str(path.relative_to(workspace_dir()))}


def case_add_event(case_id: str, event: str, detail: str = "") -> dict[str, Any]:
    path, meta = _load(case_id)
    if path is None:
        return meta
    meta.setdefault("timeline", []).append({"time": _now(), "event": event, "detail": detail})
    meta["updated_at"] = _now()
    (path / "case.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"ok": True, "case": meta}


def case_add_note(case_id: str, text: str) -> dict[str, Any]:
    path, meta = _load(case_id)
    if path is None:
        return meta
    np = path / "notes.md"
    with np.open("a", encoding="utf-8") as f:
        f.write(f"\n\n## {_now()}\n{text}\n")
    return case_add_event(case_id, "note_added", text[:200])


def case_attach_json(case_id: str, artifact_name: str, data: dict | str) -> dict[str, Any]:
    path, meta = _load(case_id)
    if path is None:
        return meta
    safe = _slug(artifact_name) + ".json"
    ap = path / safe
    if isinstance(data, str):
        ap.write_text(data, encoding="utf-8")
    else:
        ap.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    arts = meta.setdefault("artifacts", [])
    rel = str(ap.relative_to(workspace_dir()))
    if rel not in arts:
        arts.append(rel)
    meta["updated_at"] = _now()
    (path / "case.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    case_add_event(case_id, "artifact_attached", safe)
    return {"ok": True, "artifact": rel, "case_id": meta.get("id")}


def case_export_report(case_id: str) -> dict[str, Any]:
    path, meta = _load(case_id)
    if path is None:
        return meta
    modules = {"case_meta": meta}
    for ap in meta.get("artifacts") or []:
        fp = workspace_dir() / ap if not Path(ap).is_absolute() else Path(ap)
        # artifacts stored relative to workspace
        cand = path / Path(ap).name
        if cand.exists():
            fp = cand
        try:
            modules[Path(ap).stem] = json.loads(fp.read_text(encoding="utf-8"))
        except Exception:
            modules[Path(ap).stem] = {"path": ap, "error": "unreadable"}
    try:
        from report_engine import save_report
        return save_report(f"case_{meta.get('id')}", meta.get("target") or meta.get("name") or case_id, modules)
    except Exception as e:
        return {"ok": False, "error": str(e)}


CASE_TOOLS = {
    "case_create": case_create,
    "case_list": case_list,
    "case_get": case_get,
    "case_add_event": case_add_event,
    "case_add_note": case_add_note,
    "case_attach_json": case_attach_json,
    "case_export_report": case_export_report,
}
