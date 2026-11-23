# -*- coding: utf-8 -*-
from __future__ import annotations
import json
from pathlib import Path
from config_loader import ROOT

def local_version() -> str:
    p = ROOT / "version.json"
    try:
        return str(json.loads(p.read_text(encoding="utf-8")).get("version") or "?")
    except Exception:
        return "?"

def check_github_release(repo: str = "mahditariri/GGUF-Runner") -> dict:
    """Optional network check — never blocks offline use."""
    local = local_version()
    try:
        import urllib.request
        url = f"https://api.github.com/repos/{repo}/releases/latest"
        req = urllib.request.Request(url, headers={"User-Agent": "GGUF-Runner"})
        with urllib.request.urlopen(req, timeout=8) as r:
            data = json.loads(r.read().decode("utf-8"))
        tag = (data.get("tag_name") or "").lstrip("v")
        return {
            "ok": True,
            "local": local,
            "latest": tag,
            "html_url": data.get("html_url"),
            "update_available": bool(tag and tag != local),
        }
    except Exception as e:
        return {"ok": False, "local": local, "error": str(e), "note_fa": "آفلاین یا شبکه در دسترس نیست"}


def download_latest_asset(dest_dir: str | None = None, repo: str = "mahditariri/GGUF-Runner") -> dict:
    """Download first .exe asset from latest release into workspace/updates (user must confirm in UI)."""
    import urllib.request
    from pathlib import Path
    from config_loader import ROOT
    dest = Path(dest_dir) if dest_dir else (ROOT / "workspace" / "updates")
    dest.mkdir(parents=True, exist_ok=True)
    try:
        url = f"https://api.github.com/repos/{repo}/releases/latest"
        req = urllib.request.Request(url, headers={"User-Agent": "GGUF-Runner"})
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.loads(r.read().decode("utf-8"))
        assets = data.get("assets") or []
        asset = None
        for a in assets:
            n = (a.get("name") or "").lower()
            if n.endswith(".exe") or n.endswith(".zip"):
                asset = a
                break
        if not asset:
            return {"ok": False, "error": "no exe/zip asset on latest release", "tag": data.get("tag_name")}
        out = dest / asset["name"]
        urllib.request.urlretrieve(asset["browser_download_url"], out)
        return {"ok": True, "path": str(out), "tag": data.get("tag_name"), "name": asset["name"]}
    except Exception as e:
        return {"ok": False, "error": str(e)}
