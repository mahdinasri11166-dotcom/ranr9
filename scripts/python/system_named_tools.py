# -*- coding: utf-8 -*-
"""Layer 4: named system tools (prefer over free-form shell). Still need elevated_mode for most."""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from elevated_tools import elevated_enabled


def _need_elev() -> dict[str, Any] | None:
    if not elevated_enabled():
        return {
            "ok": False,
            "blocked": True,
            "error": "elevated_mode is OFF — use /elevated on first",
        }
    return None


def process_list(limit: int = 40) -> dict[str, Any]:
    d = _need_elev()
    if d:
        return d
    limit = max(1, min(int(limit or 40), 200))
    try:
        if sys.platform.startswith("win"):
            r = subprocess.run(
                ["tasklist", "/fo", "csv", "/nh"],
                capture_output=True, text=True, timeout=30,
            )
            lines = [ln for ln in (r.stdout or "").splitlines() if ln.strip()][:limit]
            return {"ok": r.returncode == 0, "processes": lines, "count": len(lines)}
        r = subprocess.run(["ps", "aux"], capture_output=True, text=True, timeout=30)
        lines = (r.stdout or "").splitlines()[: limit + 1]
        return {"ok": True, "processes": lines, "count": max(0, len(lines) - 1)}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def env_get(key: str = "") -> dict[str, Any]:
    d = _need_elev()
    if d:
        return d
    # redact obvious secrets
    redact = ("key", "secret", "token", "password", "pwd", "credential")
    if key:
        val = os.environ.get(key)
        if val is None:
            return {"ok": False, "error": "not set"}
        low = key.lower()
        if any(r in low for r in redact):
            val = "***REDACTED***"
        return {"ok": True, "key": key, "value": val}
    keys = []
    for k in sorted(os.environ.keys())[:100]:
        low = k.lower()
        if any(r in low for r in redact):
            keys.append({"key": k, "value": "***REDACTED***"})
        else:
            v = os.environ.get(k, "")
            keys.append({"key": k, "value": v[:200]})
    return {"ok": True, "env": keys, "count": len(keys)}


def open_app(path: str) -> dict[str, Any]:
    d = _need_elev()
    if d:
        return d
    p = Path(path).expanduser()
    if not p.exists():
        return {"ok": False, "error": "not found"}
    try:
        if hasattr(os, "startfile"):
            os.startfile(str(p))  # type: ignore
        elif sys.platform == "darwin":
            subprocess.Popen(["open", str(p)])
        else:
            subprocess.Popen(["xdg-open", str(p)])
        return {"ok": True, "opened": str(p)}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def clipboard_get() -> dict[str, Any]:
    d = _need_elev()
    if d:
        return d
    try:
        if sys.platform.startswith("win"):
            r = subprocess.run(
                ["powershell", "-NoProfile", "-Command", "Get-Clipboard"],
                capture_output=True, text=True, timeout=10,
            )
            return {"ok": r.returncode == 0, "text": (r.stdout or "")[:20000]}
        if sys.platform == "darwin":
            r = subprocess.run(["pbpaste"], capture_output=True, text=True, timeout=10)
            return {"ok": r.returncode == 0, "text": (r.stdout or "")[:20000]}
        r = subprocess.run(["xclip", "-selection", "clipboard", "-o"], capture_output=True, text=True, timeout=10)
        return {"ok": r.returncode == 0, "text": (r.stdout or "")[:20000]}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def clipboard_set(text: str) -> dict[str, Any]:
    d = _need_elev()
    if d:
        return d
    text = text or ""
    try:
        if sys.platform.startswith("win"):
            r = subprocess.run(
                ["powershell", "-NoProfile", "-Command", "Set-Clipboard -Value @'\n" + text.replace("'", "''")[:15000] + "\n'@"],
                capture_output=True, text=True, timeout=15,
            )
            return {"ok": r.returncode == 0, "bytes": len(text)}
        if sys.platform == "darwin":
            r = subprocess.run(["pbcopy"], input=text, capture_output=True, text=True, timeout=10)
            return {"ok": r.returncode == 0}
        r = subprocess.run(["xclip", "-selection", "clipboard"], input=text, capture_output=True, text=True, timeout=10)
        return {"ok": r.returncode == 0}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def notify(message: str, title: str = "GGUF Runner") -> dict[str, Any]:
    d = _need_elev()
    if d:
        return d
    message = (message or "")[:500]
    title = (title or "GGUF Runner")[:100]
    try:
        if sys.platform.startswith("win"):
            ps = (
                f"[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] > $null; "
                f"echo '{title}: {message}'"
            )
            # simple fallback: message box via powershell
            script = f'Add-Type -AssemblyName PresentationFramework; [System.Windows.MessageBox]::Show("{message[:200]}","{title}")'
            subprocess.Popen(["powershell", "-NoProfile", "-Command", script])
            return {"ok": True, "method": "MessageBox"}
        if sys.platform == "darwin":
            subprocess.run(["osascript", "-e", f'display notification "{message}" with title "{title}"'], timeout=10)
            return {"ok": True, "method": "osascript"}
        subprocess.run(["notify-send", title, message], timeout=10)
        return {"ok": True, "method": "notify-send"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


SYSTEM_NAMED_TOOLS = {
    "process_list": process_list,
    "env_get": env_get,
    "open_app": open_app,
    "clipboard_get": clipboard_get,
    "clipboard_set": clipboard_set,
    "notify": notify,
}
