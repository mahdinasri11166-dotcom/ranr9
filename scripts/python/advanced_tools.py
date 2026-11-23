# -*- coding: utf-8 -*-
"""
Advanced tools: unrestricted shell, HTTP API client, file helpers.

Works best with profiles/approval_policy.json:
  unrestricted_tools: true
  elevated_mode: true
"""
from __future__ import annotations

import json
import os
import subprocess
import time
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen

from config_loader import ROOT, workspace_dir, load_approval_policy

try:
    from proxy_pool import opener_for, next_proxy, load_config as load_proxy_cfg
except Exception:
    def opener_for(proxy=None):
        return None, None
    def next_proxy():
        return None
    def load_proxy_cfg():
        return {"enabled": False}

try:
    from downloader import download_start, download_status, download_list
except Exception:
    download_start = download_status = download_list = None


def _unrestricted() -> bool:
    try:
        pol = load_approval_policy() or {}
        return bool(pol.get("unrestricted_tools")) or bool(pol.get("elevated_mode"))
    except Exception:
        return True


# ---------------------------------------------------------------------------
# Free shell
# ---------------------------------------------------------------------------

def shell_run(
    command: str,
    cwd: str = "",
    timeout: int = 120,
    env_extra: dict | None = None,
    shell: bool = True,
) -> dict[str, Any]:
    """Run any shell/cmd command (unrestricted mode).

    Windows uses cmd.exe; output captured (stdout+stderr).
    """
    command = (command or "").strip()
    if not command:
        return {"ok": False, "error": "command is empty"}

    work = Path(cwd).expanduser() if cwd else workspace_dir()
    if not work.is_absolute():
        work = (workspace_dir() / work).resolve()
    if not work.exists():
        try:
            work.mkdir(parents=True, exist_ok=True)
        except Exception:
            work = workspace_dir()

    env = os.environ.copy()
    if isinstance(env_extra, dict):
        env.update({str(k): str(v) for k, v in env_extra.items()})

    # Soft refuse only the most catastrophic patterns
    low = command.lower()
    hard_refuse = [
        "format c:",
        "format d:",
        "rm -rf / ",
        "rm -rf /*",
        "del /f /s /q c:\\windows",
        ":(){:|:&};:",
    ]
    for bad in hard_refuse:
        if bad in low:
            return {"ok": False, "blocked": True, "error": f"refused dangerous pattern: {bad}"}

    t0 = time.time()
    try:
        if os.name == "nt":
            # Prefer cmd /c for classic Windows shell behavior
            r = subprocess.run(
                command,
                shell=True,
                cwd=str(work),
                capture_output=True,
                text=True,
                timeout=max(1, int(timeout)),
                env=env,
                encoding="utf-8",
                errors="replace",
            )
        else:
            r = subprocess.run(
                command,
                shell=bool(shell),
                cwd=str(work),
                capture_output=True,
                text=True,
                timeout=max(1, int(timeout)),
                env=env,
            )
        out = (r.stdout or "")[-100_000:]
        err = (r.stderr or "")[-50_000:]
        return {
            "ok": r.returncode == 0,
            "returncode": r.returncode,
            "stdout": out,
            "stderr": err,
            "cwd": str(work),
            "seconds": round(time.time() - t0, 3),
            "command": command,
        }
    except subprocess.TimeoutExpired as e:
        return {
            "ok": False,
            "error": "timeout",
            "timeout": timeout,
            "stdout": (e.stdout or "")[-20_000:] if isinstance(e.stdout, str) else "",
            "stderr": (e.stderr or "")[-10_000:] if isinstance(e.stderr, str) else "",
            "command": command,
        }
    except Exception as e:
        return {"ok": False, "error": str(e), "command": command}


def shell_free(command: str, cwd: str = "", timeout: int = 180, **kw) -> dict[str, Any]:
    """Alias: unrestricted shell."""
    return shell_run(command, cwd=cwd, timeout=timeout, env_extra=kw.get("env_extra"))


def shell_powershell(script: str, timeout: int = 180) -> dict[str, Any]:
    """Run a PowerShell snippet (Windows)."""
    script = (script or "").strip()
    if not script:
        return {"ok": False, "error": "script empty"}
    if os.name != "nt":
        return shell_run(script, timeout=timeout)
    # Encoded-less simple -Command
    cmd = f'powershell -NoProfile -ExecutionPolicy Bypass -Command "{script.replace(chr(34), chr(39))}"'
    return shell_run(cmd, timeout=timeout)


# ---------------------------------------------------------------------------
# Advanced HTTP / API client
# ---------------------------------------------------------------------------

def api_request(
    url: str,
    method: str = "GET",
    headers: dict | None = None,
    body: str | dict | None = None,
    json_body: dict | None = None,
    params: dict | None = None,
    timeout: int = 60,
    use_proxy: bool = True,
    max_bytes: int = 2_000_000,
) -> dict[str, Any]:
    """Full HTTP client for any API.

    - method: GET POST PUT PATCH DELETE HEAD OPTIONS
    - headers: dict
    - body: raw string or dict (form-ish json dump)
    - json_body: dict → Content-Type application/json
    - params: query string dict
    - use_proxy: honor rotating proxy pool when enabled
    """
    url = (url or "").strip()
    if not url.startswith(("http://", "https://")):
        return {"ok": False, "error": "url must start with http:// or https://"}
    method = (method or "GET").upper().strip()
    if params and isinstance(params, dict):
        q = urlencode({str(k): str(v) for k, v in params.items()})
        url = url + ("&" if "?" in url else "?") + q

    h = {
        "User-Agent": "GGUF-Runner-API/1.0",
        "Accept": "application/json, text/plain, */*",
    }
    if isinstance(headers, dict):
        h.update({str(k): str(v) for k, v in headers.items()})

    data_bytes = None
    if json_body is not None:
        data_bytes = json.dumps(json_body, ensure_ascii=False).encode("utf-8")
        h.setdefault("Content-Type", "application/json; charset=utf-8")
    elif body is not None:
        if isinstance(body, dict):
            data_bytes = json.dumps(body, ensure_ascii=False).encode("utf-8")
            h.setdefault("Content-Type", "application/json; charset=utf-8")
        else:
            data_bytes = str(body).encode("utf-8")

    proxy_used = None
    t0 = time.time()
    try:
        req = Request(url, data=data_bytes, headers=h, method=method)
        opener = None
        if use_proxy and (load_proxy_cfg() or {}).get("enabled"):
            opener, proxy_used = opener_for()
        if opener:
            resp = opener.open(req, timeout=max(1, int(timeout)))
        else:
            resp = urlopen(req, timeout=max(1, int(timeout)))
        with resp:
            status = getattr(resp, "status", None) or resp.getcode()
            raw = resp.read(max(1, int(max_bytes)))
            resp_headers = dict(resp.headers)
        text = raw.decode("utf-8", errors="replace")
        parsed = None
        try:
            if text.strip().startswith(("{", "[")):
                parsed = json.loads(text)
        except Exception:
            parsed = None
        return {
            "ok": 200 <= int(status) < 400,
            "status": int(status),
            "url": url,
            "method": method,
            "headers": {k: v for k, v in list(resp_headers.items())[:40]},
            "body": text if len(text) < 200_000 else text[:200_000],
            "json": parsed,
            "bytes": len(raw),
            "proxy": proxy_used,
            "seconds": round(time.time() - t0, 3),
        }
    except HTTPError as e:
        body_err = ""
        try:
            body_err = e.read(100_000).decode("utf-8", errors="replace")
        except Exception:
            pass
        return {
            "ok": False,
            "status": e.code,
            "error": str(e),
            "body": body_err,
            "url": url,
            "method": method,
            "proxy": proxy_used,
        }
    except Exception as e:
        return {"ok": False, "error": str(e), "url": url, "method": method, "proxy": proxy_used}


def api_get(url: str, **kw) -> dict[str, Any]:
    return api_request(url, method="GET", **kw)


def api_post(url: str, json_body: dict | None = None, body: str | dict | None = None, **kw) -> dict[str, Any]:
    return api_request(url, method="POST", json_body=json_body, body=body, **kw)


def api_put(url: str, json_body: dict | None = None, body: str | dict | None = None, **kw) -> dict[str, Any]:
    return api_request(url, method="PUT", json_body=json_body, body=body, **kw)


def api_delete(url: str, **kw) -> dict[str, Any]:
    return api_request(url, method="DELETE", **kw)


# ---------------------------------------------------------------------------
# File download aliases (delegates to downloader)
# ---------------------------------------------------------------------------

def http_download(url: str, filename: str = "", dest_dir: str = "", **kw) -> dict[str, Any]:
    if not download_start:
        return {"ok": False, "error": "downloader module not available"}
    return download_start(url, filename=filename, dest_dir=dest_dir, use_proxy=kw.get("use_proxy", True))


def http_download_status(job_id: str = "", **kw) -> dict[str, Any]:
    if not download_status:
        return {"ok": False, "error": "downloader module not available"}
    return download_status(job_id or "")


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

ADVANCED_TOOLS: dict[str, Any] = {
    # Shell
    "shell_run": shell_run,
    "shell_free": shell_free,
    "shell": shell_free,
    "shell_powershell": shell_powershell,
    "cmd": shell_free,
    # API
    "api_request": api_request,
    "api_get": api_get,
    "api_post": api_post,
    "api_put": api_put,
    "api_delete": api_delete,
    "http_request": api_request,
    # Download
    "http_download": http_download,
    "http_download_status": http_download_status,
}
