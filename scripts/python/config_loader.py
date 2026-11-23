# -*- coding: utf-8 -*-
"""Load config.ini and profiles for GGUF Runner."""
from __future__ import annotations

import configparser
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]


def get_root() -> Path:
    return ROOT


def load_ini(path: Path | None = None) -> dict[str, Any]:
    path = path or (ROOT / "config.ini")
    cfg: dict[str, Any] = {
        "host": "127.0.0.1",
        "port": 8080,
        "model": "",
        "n_gpu_layers": 0,
        "ctx_size": 4096,
        "threads": 4,
        "temperature": 0.7,
        "max_tokens": 2048,
        "top_p": 0.9,
        "repeat_penalty": 1.1,
        "system_prompt": "",
        "bin_dir": "bin",
        "models_dir": "models",
        "web_dir": "web",
    }
    if not path.exists():
        return cfg
    parser = configparser.ConfigParser()
    try:
        parser.read(path, encoding="utf-8")
    except Exception:
        return cfg
    for section in parser.sections():
        for key, val in parser.items(section):
            k = key.strip().lower()
            if k in ("port", "n_gpu_layers", "ctx_size", "threads", "max_tokens"):
                try:
                    cfg[k] = int(val.strip())
                except ValueError:
                    pass
            elif k in ("temperature", "top_p", "repeat_penalty"):
                try:
                    cfg[k] = float(val.strip())
                except ValueError:
                    pass
            else:
                cfg[k] = val.strip()
    return cfg


def save_ini(cfg: dict[str, Any], path: Path | None = None) -> None:
    path = path or (ROOT / "config.ini")
    lines = [
        "[server]",
        f"host={cfg.get('host', '127.0.0.1')}",
        f"port={cfg.get('port', 8080)}",
        f"model={cfg.get('model', '')}",
        f"n_gpu_layers={cfg.get('n_gpu_layers', 0)}",
        f"ctx_size={cfg.get('ctx_size', 4096)}",
        f"threads={cfg.get('threads', 4)}",
        "",
        "[ui]",
        f"temperature={cfg.get('temperature', 0.7)}",
        f"max_tokens={cfg.get('max_tokens', 2048)}",
        f"top_p={cfg.get('top_p', 0.9)}",
        f"repeat_penalty={cfg.get('repeat_penalty', 1.1)}",
        f"system_prompt={cfg.get('system_prompt', '')}",
        "",
        "[paths]",
        f"bin_dir={cfg.get('bin_dir', 'bin')}",
        f"models_dir={cfg.get('models_dir', 'models')}",
        f"web_dir={cfg.get('web_dir', 'web')}",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def list_models() -> list[Path]:
    models_dir = ROOT / "models"
    if not models_dir.exists():
        models_dir.mkdir(parents=True, exist_ok=True)
        return []
    return sorted(models_dir.glob("*.gguf"))


def load_profile(name: str = "default") -> dict[str, Any]:
    p = ROOT / "profiles" / f"{name}.json"
    if not p.exists():
        return {
            "name": name,
            "system": "You are a helpful assistant.",
            "temperature": 0.7,
            "top_p": 0.9,
            "max_tokens": 2048,
            "ctx_size": 4096,
            "role": "general",
        }
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {"name": name, "system": "You are a helpful assistant."}


def load_approval_policy() -> dict[str, Any]:
    p = ROOT / "profiles" / "approval_policy.json"
    if not p.exists():
        return {"default": "REQUIRE_APPROVAL", "tools": {}, "blocked_tools": []}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {"default": "REQUIRE_APPROVAL", "tools": {}, "blocked_tools": []}


def sessions_dir() -> Path:
    d = ROOT / "sessions"
    d.mkdir(parents=True, exist_ok=True)
    return d



def workspace_dir() -> Path:
    d = ROOT / "workspace"
    d.mkdir(parents=True, exist_ok=True)
    return d


def load_identity() -> dict:
    """Creator/father identity applied to every model system prompt."""
    path = ROOT / "profiles" / "identity.json"
    default = {
        "creator_name_fa": "مهدی",
        "creator_full_fa": "مهدی طریری",
        "identity_block_fa": (
            "هویت ثابت: اگر پرسیدند پدرت کیه / سازنده‌ات کیست / who is your father، "
            "بگو پدر و سازنده تو مهدی (مهدی طریری) است."
        ),
    }
    if not path.exists():
        return default
    try:
        import json
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            default.update(data)
        return default
    except Exception:
        return default


def identity_system_suffix() -> str:
    ident = load_identity()
    block = (ident.get("identity_block_fa") or "").strip()
    if not block:
        name = ident.get("creator_name_fa") or "مهدی"
        block = (
            "هویت ثابت: اگر کاربر پرسید پدرت کیه / سازنده‌ات کیست / who is your father، "
            "پاسخ بده پدر و سازنده تو «" + str(name) + "» است."
        )
    return "\n\n" + block
