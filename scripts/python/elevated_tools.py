# -*- coding: utf-8 -*-
"""
Elevated system tools — only when elevated_mode is ON in approval_policy.json
AND the UI Approval Gate accepts each call.

Still NOT included (by design): credential theft, AV kill, remote exploit,
silent persistence, keylogging.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from config_loader import ROOT, load_approval_policy, workspace_dir


def elevated_enabled() -> bool:
    try:
        pol = load_approval_policy() or {}
        return bool(pol.get("elevated_mode"))
    except Exception:
        return False


def _deny_if_off() -> dict[str, Any] | None:
    if not elevated_enabled():
        return {
            "ok": False,
            "blocked": True,
            "error": (
                "حالت مدیر (elevated_mode) خاموش است. "
                "در profiles/approval_policy.json مقدار \"elevated_mode\": true بگذارید "
                "و دوباره تأیید هر دستور را در UI بپذیرید."
            ),
        }
    return None


def sys_info() -> dict[str, Any]:
    d = _deny_if_off()
    if d:
        return d
    import platform
    return {
        "ok": True,
        "platform": platform.platform(),
        "python": sys.version,
        "cwd": os.getcwd(),
        "root": str(ROOT),
        "user": os.environ.get("USERNAME") or os.environ.get("USER"),
        "home": str(Path.home()),
    }


def sys_list_dir(path: str = ".", max_items: int = 300) -> dict[str, Any]:
    d = _deny_if_off()
    if d:
        return d
    p = Path(path).expanduser()
    if not p.is_absolute():
        p = (Path.cwd() / p).resolve()
    else:
        p = p.resolve()
    if not p.exists():
        return {"ok": False, "error": f"not found: {p}"}
    if not p.is_dir():
        return {"ok": False, "error": "not a directory"}
    items = []
    try:
        for child in sorted(p.iterdir())[: max(1, min(max_items, 2000))]:
            try:
                items.append({
                    "name": child.name,
                    "type": "dir" if child.is_dir() else "file",
                    "size": child.stat().st_size if child.is_file() else None,
                })
            except OSError:
                items.append({"name": child.name, "type": "?", "error": "stat failed"})
    except PermissionError as e:
        return {"ok": False, "error": f"permission denied: {e}"}
    return {"ok": True, "path": str(p), "items": items, "count": len(items)}


def sys_read_file(path: str, max_bytes: int = 200_000) -> dict[str, Any]:
    d = _deny_if_off()
    if d:
        return d
    p = Path(path).expanduser().resolve()
    if not p.exists() or not p.is_file():
        return {"ok": False, "error": "file not found"}
    try:
        data = p.read_bytes()[: max(1, min(max_bytes, 5_000_000))]
    except PermissionError as e:
        return {"ok": False, "error": str(e)}
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        text = data.decode("utf-8", errors="replace")
    return {
        "ok": True,
        "path": str(p),
        "bytes_read": len(data),
        "content": text,
        "truncated": p.stat().st_size > len(data),
    }


def sys_write_file(path: str, content: str) -> dict[str, Any]:
    d = _deny_if_off()
    if d:
        return d
    p = Path(path).expanduser().resolve()
    # soft safety: refuse well-known critical system paths
    low = str(p).lower().replace("/", "\\")
    blocked_prefixes = [
        r"c:\windows\system32",
        r"c:\windows\syswow64",
        r"/system32",
        r"/usr/bin",
        r"/bin/",
    ]
    for b in blocked_prefixes:
        if low.startswith(b) or f"\\{b.strip(chr(92))}" in low:
            return {"ok": False, "blocked": True, "error": f"نوشتن در مسیر سیستم مسدود است: {p}"}
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
    except Exception as e:
        return {"ok": False, "error": str(e)}
    return {"ok": True, "path": str(p), "bytes": len(content.encode("utf-8"))}


def sys_run_cmd(command: str, timeout: int = 60, shell: bool = True) -> dict[str, Any]:
    """Run a shell command after approval. Windows: cmd; else default shell."""
    d = _deny_if_off()
    if d:
        return d
    command = (command or "").strip()
    if not command:
        return {"ok": False, "error": "command empty"}
    # refuse a few catastrophic patterns even with elevated_mode
    low = command.lower()
    refuse = [
        "format ",
        "format.com",
        "rm -rf /",
        "del /s /q c:\\",
        "rd /s /q c:\\",
        "shutdown /s",
        "shutdown /r",
        ":/s",
        "mkfs",
        "diskpart",
    ]
    for r in refuse:
        if r in low:
            return {
                "ok": False,
                "blocked": True,
                "error": f"دستور خطرناک سیستمی مسدود شد (حتی در حالت مدیر): الگوی «{r.strip()}»",
            }
    timeout = max(1, min(int(timeout or 60), 600))
    try:
        if sys.platform.startswith("win"):
            r = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=str(workspace_dir()),
            )
        else:
            r = subprocess.run(
                command,
                shell=shell,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=str(workspace_dir()),
            )
        return {
            "ok": r.returncode == 0,
            "returncode": r.returncode,
            "stdout": (r.stdout or "")[:20000],
            "stderr": (r.stderr or "")[:8000],
            "command": command,
        }
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "timeout", "command": command}
    except Exception as e:
        return {"ok": False, "error": str(e), "command": command}


def sys_open_path(path: str) -> dict[str, Any]:
    d = _deny_if_off()
    if d:
        return d
    p = Path(path).expanduser().resolve()
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


def sys_open_url(url: str) -> dict[str, Any]:
    d = _deny_if_off()
    if d:
        return d
    url = (url or "").strip()
    if not url.startswith(("http://", "https://")):
        return {"ok": False, "error": "فقط http/https"}
    try:
        import webbrowser
        webbrowser.open(url)
        return {"ok": True, "opened": url}
    except Exception as e:
        return {"ok": False, "error": str(e)}


ELEVATED_TOOLS = {
    "sys_info": sys_info,
    "sys_list_dir": sys_list_dir,
    "sys_read_file": sys_read_file,
    "sys_write_file": sys_write_file,
    "sys_run_cmd": sys_run_cmd,
    "sys_open_path": sys_open_path,
    "sys_open_url": sys_open_url,
}
