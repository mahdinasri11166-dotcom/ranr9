# -*- coding: utf-8 -*-
"""
Offline-first translation.

Order:
1) Argos Translate (local language packs) — no internet
2) Online MyMemory / LibreTranslate fallback (if network)

Language packs are installed under the app data / Argos default dir,
and can be pre-seeded by GitHub Actions into profiles/argos_packages/.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any
from urllib.parse import quote_plus
from urllib.request import Request, urlopen

from config_loader import ROOT

UA = "GGUF-Runner-Translate/1.0"


def _argos_package_dirs() -> list[Path]:
    dirs = [
        ROOT / "profiles" / "argos_packages",
        ROOT / "argos_packages",
        Path(os.environ.get("ARGOS_PACKAGE_DIR", "")) if os.environ.get("ARGOS_PACKAGE_DIR") else None,
    ]
    return [d for d in dirs if d and d.exists()]


def _ensure_argos_path():
    """Point Argos at bundled package directory when present."""
    for d in _argos_package_dirs():
        try:
            os.environ.setdefault("ARGOS_PACKAGE_DIR", str(d))
        except Exception:
            pass
        break


def argos_available() -> dict[str, Any]:
    _ensure_argos_path()
    try:
        import argostranslate.package  # type: ignore
        import argostranslate.translate  # type: ignore
    except Exception as e:
        return {"ok": False, "error": f"argostranslate not installed: {e}"}
    try:
        installed = argostranslate.package.get_installed_packages()
        pairs = [f"{p.from_code}->{p.to_code}" for p in installed]
        return {"ok": True, "pairs": pairs, "count": len(pairs)}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def _argos_translate(text: str, source: str, target: str) -> dict[str, Any]:
    _ensure_argos_path()
    try:
        import argostranslate.translate  # type: ignore
        import argostranslate.package  # type: ignore
    except Exception as e:
        return {"ok": False, "error": f"argos missing: {e}"}

    # install from bundled .argosmodel if not installed
    try:
        _install_bundled_packages()
    except Exception:
        pass

    source = (source or "en").lower()
    target = (target or "fa").lower()
    if source == "auto":
        source = "en" if target != "en" else "fa"

    try:
        # direct
        out = argostranslate.translate.translate(text, source, target)
        if out and out.strip() and out.strip() != text.strip():
            return {"ok": True, "provider": "argos-offline", "source": source, "target": target, "translated": out}
        # try pivot via English
        if source != "en" and target != "en":
            mid = argostranslate.translate.translate(text, source, "en")
            out = argostranslate.translate.translate(mid, "en", target)
            if out and out.strip():
                return {
                    "ok": True,
                    "provider": "argos-offline-pivot-en",
                    "source": source,
                    "target": target,
                    "translated": out,
                }
        # same language
        if source == target:
            return {"ok": True, "provider": "argos-offline", "source": source, "target": target, "translated": text}
        return {"ok": False, "error": f"no argos model for {source}->{target}", "installed": argos_available().get("pairs")}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def _install_bundled_packages() -> list[str]:
    """Install any *.argosmodel from profiles/argos_packages into Argos."""
    try:
        import argostranslate.package  # type: ignore
    except Exception:
        return []
    installed = []
    for d in _argos_package_dirs():
        for f in list(d.glob("*.argosmodel")) + list(d.glob("*.argosmodel.part")):
            if f.suffix == ".part":
                continue
            try:
                argostranslate.package.install_from_path(str(f))
                installed.append(f.name)
            except Exception:
                # already installed or incompatible
                pass
    return installed


def _online_translate(text: str, source: str, target: str) -> dict[str, Any]:
    text = (text or "").strip()
    target = (target or "fa").lower()
    source = (source or "auto").lower()
    langpair = f"{source}|{target}" if source != "auto" else f"en|{target}"
    if source == "auto" and target == "en":
        langpair = "fa|en"
    q = quote_plus(text[:450])
    url = f"https://api.mymemory.translated.net/get?q={q}&langpair={quote_plus(langpair)}"
    try:
        req = Request(url, headers={"User-Agent": UA})
        with urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read().decode("utf-8", errors="replace"))
        translated = ((data.get("responseData") or {}).get("translatedText") or "").strip()
        if translated:
            return {
                "ok": True,
                "provider": "mymemory-online",
                "source": source,
                "target": target,
                "translated": translated,
            }
    except Exception as e:
        last = str(e)
    else:
        last = "empty"
    return {"ok": False, "error": last}


def translate_offline_first(text: str, target: str = "fa", source: str = "auto", allow_online: bool = True) -> dict[str, Any]:
    text = (text or "").strip()
    if not text:
        return {"ok": False, "error": "text empty"}
    target = (target or "fa").strip().lower()
    source = (source or "auto").strip().lower()

    offline = _argos_translate(text, source if source != "auto" else "en", target)
    if offline.get("ok"):
        offline["text"] = text[:2000]
        offline["mode"] = "offline"
        return offline

    # try reverse guess: if target is en, source fa
    if source == "auto" and target == "en":
        offline2 = _argos_translate(text, "fa", "en")
        if offline2.get("ok"):
            offline2["text"] = text[:2000]
            offline2["mode"] = "offline"
            return offline2

    if not allow_online:
        return {
            "ok": False,
            "error": offline.get("error") or "offline translation unavailable",
            "hint": "Install Argos packs or rebuild from GitHub Actions with argos_packages",
            "argos": argos_available(),
            "mode": "offline-failed",
        }

    online = _online_translate(text, source, target)
    if online.get("ok"):
        online["text"] = text[:2000]
        online["mode"] = "online"
        online["offline_error"] = offline.get("error")
        return online
    return {
        "ok": False,
        "error": f"offline: {offline.get('error')}; online: {online.get('error')}",
        "argos": argos_available(),
        "mode": "failed",
    }


OFFLINE_TRANSLATE_TOOLS = {
    "translate_offline": lambda text="", target="fa", source="auto", **kw: translate_offline_first(
        text, target=target, source=source, allow_online=False
    ),
    "argos_status": lambda **kw: argos_available(),
}
