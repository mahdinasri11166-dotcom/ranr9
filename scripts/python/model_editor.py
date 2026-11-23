# -*- coding: utf-8 -*-
"""Per-model editable profiles (sidecar JSON next to .gguf).

Does NOT modify binary GGUF weights. Stores display name, prompts, load params, notes.
File: models/<name>.gguf.meta.json  (or profiles/model_meta/<name>.json fallback)
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from config_loader import ROOT, list_models

try:
    from model_meta import read_gguf_metadata, estimate_ram_gb
except Exception:
    def read_gguf_metadata(path, max_kv=40):
        p = Path(path)
        return {"ok": p.is_file(), "name": p.name, "size_bytes": p.stat().st_size if p.is_file() else 0}

    def estimate_ram_gb(*a, **k):
        return {}


def models_dir() -> Path:
    d = ROOT / "models"
    d.mkdir(parents=True, exist_ok=True)
    return d


def meta_path_for(gguf: Path | str) -> Path:
    p = Path(gguf)
    if not p.is_absolute():
        p = models_dir() / p
    return p.with_suffix(p.suffix + ".meta.json")  # file.gguf.meta.json


def default_meta(gguf: Path | str) -> dict[str, Any]:
    p = Path(gguf)
    return {
        "file": p.name,
        "display_name": p.stem,
        "notes": "",
        "system_prompt": "",
        "n_ctx": 4096,
        "n_gpu_layers": 0,
        "n_threads": 0,
        "temperature": 0.7,
        "max_tokens": 2048,
        "top_p": 0.9,
        "repeat_penalty": 1.1,
        "tags": [],
        "favorite": False,
    }


def load_meta(gguf: Path | str) -> dict[str, Any]:
    p = Path(gguf)
    if not p.is_absolute():
        p = models_dir() / p
    meta = default_meta(p)
    mp = meta_path_for(p)
    if mp.exists():
        try:
            data = json.loads(mp.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                meta.update(data)
        except Exception:
            pass
    meta["file"] = p.name
    meta["path"] = str(p)
    meta["meta_path"] = str(mp)
    # attach read-only GGUF header info
    try:
        hdr = read_gguf_metadata(p)
        meta["gguf"] = {
            "architecture": hdr.get("architecture"),
            "name_meta": hdr.get("name_meta"),
            "context_length": hdr.get("context_length"),
            "size_gb": hdr.get("size_gb"),
            "size_bytes": hdr.get("size_bytes"),
            "tensor_count": hdr.get("tensor_count"),
            "gguf_version": hdr.get("gguf_version"),
            "keys": hdr.get("keys") or {},
        }
        if hdr.get("context_length") and not mp.exists():
            try:
                meta["n_ctx"] = min(int(hdr["context_length"]), 32768)
            except Exception:
                pass
    except Exception as e:
        meta["gguf_error"] = str(e)
    return meta


def save_meta(gguf: Path | str, data: dict[str, Any]) -> dict[str, Any]:
    p = Path(gguf)
    if not p.is_absolute():
        p = models_dir() / p
    if not p.exists():
        return {"ok": False, "error": f"model not found: {p}"}
    allowed = {
        "display_name", "notes", "system_prompt", "n_ctx", "n_gpu_layers", "n_threads",
        "temperature", "max_tokens", "top_p", "repeat_penalty", "tags", "favorite", "file",
    }
    out = default_meta(p)
    for k, v in (data or {}).items():
        if k in allowed:
            out[k] = v
    out["file"] = p.name
    # types
    try:
        out["n_ctx"] = int(out.get("n_ctx") or 4096)
        out["n_gpu_layers"] = int(out.get("n_gpu_layers") or 0)
        out["n_threads"] = int(out.get("n_threads") or 0)
        out["max_tokens"] = int(out.get("max_tokens") or 2048)
        out["temperature"] = float(out.get("temperature") or 0.7)
        out["top_p"] = float(out.get("top_p") or 0.9)
        out["repeat_penalty"] = float(out.get("repeat_penalty") or 1.1)
    except Exception as e:
        return {"ok": False, "error": f"invalid number: {e}"}
    mp = meta_path_for(p)
    mp.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"ok": True, "path": str(mp), "meta": out}


def list_model_metas() -> dict[str, Any]:
    items = []
    for p in list_models():
        m = load_meta(p)
        items.append({
            "file": p.name,
            "path": str(p),
            "display_name": m.get("display_name") or p.stem,
            "size_gb": (m.get("gguf") or {}).get("size_gb"),
            "favorite": bool(m.get("favorite")),
            "has_sidecar": meta_path_for(p).exists(),
            "n_ctx": m.get("n_ctx"),
            "n_gpu_layers": m.get("n_gpu_layers"),
        })
    return {"ok": True, "models": items, "count": len(items)}


def rename_model(gguf: Path | str, new_name: str) -> dict[str, Any]:
    p = Path(gguf)
    if not p.is_absolute():
        p = models_dir() / p
    new_name = (new_name or "").strip()
    if not new_name:
        return {"ok": False, "error": "new_name required"}
    if not new_name.lower().endswith(".gguf"):
        new_name += ".gguf"
    dest = p.with_name(new_name)
    if dest.exists():
        return {"ok": False, "error": f"already exists: {dest.name}"}
    try:
        p.rename(dest)
        old_meta = meta_path_for(p)
        new_meta = meta_path_for(dest)
        if old_meta.exists():
            old_meta.rename(new_meta)
            try:
                data = json.loads(new_meta.read_text(encoding="utf-8"))
                data["file"] = dest.name
                new_meta.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            except Exception:
                pass
        return {"ok": True, "old": p.name, "new": dest.name, "path": str(dest)}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def duplicate_model(gguf: Path | str, new_name: str = "") -> dict[str, Any]:
    p = Path(gguf)
    if not p.is_absolute():
        p = models_dir() / p
    if not p.exists():
        return {"ok": False, "error": "not found"}
    new_name = (new_name or "").strip() or f"{p.stem}_copy.gguf"
    if not new_name.lower().endswith(".gguf"):
        new_name += ".gguf"
    dest = p.with_name(new_name)
    if dest.exists():
        return {"ok": False, "error": f"already exists: {dest.name}"}
    try:
        shutil.copy2(p, dest)
        meta = load_meta(p)
        meta["file"] = dest.name
        meta["display_name"] = Path(new_name).stem
        save_meta(dest, meta)
        return {"ok": True, "path": str(dest)}
    except Exception as e:
        return {"ok": False, "error": str(e)}


MODEL_EDITOR_TOOLS = {
    "model_meta_get": lambda path="", **kw: load_meta(path),
    "model_meta_save": lambda path="", meta=None, **kw: save_meta(path, meta or kw),
    "model_meta_list": lambda **kw: list_model_metas(),
    "model_rename": lambda path="", new_name="", **kw: rename_model(path, new_name),
    "model_duplicate": lambda path="", new_name="", **kw: duplicate_model(path, new_name),
}
