# -*- coding: utf-8 -*-
from __future__ import annotations
import json
import shutil
import time
from pathlib import Path
from config_loader import ROOT, sessions_dir

def backup_sessions() -> dict:
    src = sessions_dir()
    dest_root = ROOT / "workspace" / "backups"
    dest_root.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d_%H%M%S")
    dest = dest_root / f"sessions_{stamp}"
    if src.exists():
        shutil.copytree(src, dest, dirs_exist_ok=True)
    count = len(list(dest.glob("*.json"))) if dest.exists() else 0
    return {"ok": True, "path": str(dest), "files": count}

def backup_profiles() -> dict:
    src = ROOT / "profiles"
    dest_root = ROOT / "workspace" / "backups"
    dest_root.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d_%H%M%S")
    dest = dest_root / f"profiles_{stamp}"
    if src.exists():
        shutil.copytree(src, dest, dirs_exist_ok=True)
    return {"ok": True, "path": str(dest)}
