# -*- coding: utf-8 -*-
"""Rotating HTTP/HTTPS proxy pool for GGUF Runner.

Config file (first found wins):
  workspace/proxies.json
  profiles/proxies.json

Format:
{
  "enabled": true,
  "rotate": "per_request",
  "proxies": [
    "http://user:pass@host:port",
    "http://1.2.3.4:8080",
    "socks5://127.0.0.1:9050"
  ]
}

Also supports plain text workspace/proxies.txt (one proxy URL per line).
"""
from __future__ import annotations

import json
import random
import threading
import time
from pathlib import Path
from typing import Any
from urllib.error import URLError, HTTPError
from urllib.request import Request, build_opener, ProxyHandler, urlopen

from config_loader import ROOT, workspace_dir

_lock = threading.Lock()
_state = {"index": 0, "failures": {}}


def _paths() -> list[Path]:
    return [
        workspace_dir() / "proxies.json",
        ROOT / "profiles" / "proxies.json",
        workspace_dir() / "proxies.txt",
        ROOT / "profiles" / "proxies.txt",
    ]


def load_config() -> dict[str, Any]:
    for p in _paths():
        if not p.exists():
            continue
        try:
            if p.suffix.lower() == ".txt":
                lines = [
                    ln.strip()
                    for ln in p.read_text(encoding="utf-8", errors="replace").splitlines()
                    if ln.strip() and not ln.strip().startswith("#")
                ]
                return {"enabled": bool(lines), "rotate": "per_request", "proxies": lines, "source": str(p)}
            data = json.loads(p.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                continue
            data.setdefault("enabled", True)
            data.setdefault("rotate", "per_request")
            data.setdefault("proxies", [])
            data["source"] = str(p)
            return data
        except Exception:
            continue
    return {"enabled": False, "rotate": "per_request", "proxies": [], "source": None}


def save_config(cfg: dict[str, Any]) -> Path:
    path = workspace_dir() / "proxies.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    out = {
        "enabled": bool(cfg.get("enabled", True)),
        "rotate": cfg.get("rotate") or "per_request",
        "proxies": list(cfg.get("proxies") or []),
    }
    path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def list_proxies() -> dict[str, Any]:
    cfg = load_config()
    return {
        "ok": True,
        "enabled": bool(cfg.get("enabled")),
        "rotate": cfg.get("rotate"),
        "count": len(cfg.get("proxies") or []),
        "proxies": cfg.get("proxies") or [],
        "source": cfg.get("source"),
    }


def add_proxy(proxy: str) -> dict[str, Any]:
    proxy = (proxy or "").strip()
    if not proxy:
        return {"ok": False, "error": "proxy URL required (e.g. http://host:port)"}
    if "://" not in proxy:
        proxy = "http://" + proxy
    cfg = load_config()
    proxies = list(cfg.get("proxies") or [])
    if proxy not in proxies:
        proxies.append(proxy)
    cfg["proxies"] = proxies
    cfg["enabled"] = True
    path = save_config(cfg)
    return {"ok": True, "added": proxy, "count": len(proxies), "path": str(path)}


def remove_proxy(proxy: str = "", index: int = -1) -> dict[str, Any]:
    cfg = load_config()
    proxies = list(cfg.get("proxies") or [])
    removed = None
    if 0 <= index < len(proxies):
        removed = proxies.pop(index)
    elif proxy:
        proxy = proxy.strip()
        if proxy in proxies:
            proxies.remove(proxy)
            removed = proxy
    else:
        return {"ok": False, "error": "provide proxy or index"}
    cfg["proxies"] = proxies
    save_config(cfg)
    return {"ok": True, "removed": removed, "count": len(proxies)}


def set_enabled(enabled: bool = True) -> dict[str, Any]:
    cfg = load_config()
    cfg["enabled"] = bool(enabled)
    path = save_config(cfg)
    return {"ok": True, "enabled": cfg["enabled"], "path": str(path)}


def next_proxy() -> str | None:
    cfg = load_config()
    if not cfg.get("enabled"):
        return None
    proxies = [p for p in (cfg.get("proxies") or []) if p]
    if not proxies:
        return None
    with _lock:
        mode = (cfg.get("rotate") or "per_request").lower()
        if mode == "random":
            return random.choice(proxies)
        idx = int(_state["index"]) % len(proxies)
        _state["index"] = idx + 1
        return proxies[idx]


def opener_for(proxy: str | None = None):
    """Return urllib opener; if proxy is None, try pool."""
    px = proxy if proxy is not None else next_proxy()
    if not px:
        return None, None
    # urllib built-in supports http/https proxies; socks needs PySocks
    handlers = []
    if px.lower().startswith("socks"):
        try:
            import socks  # type: ignore
            from sockshandler import SocksiPyHandler  # type: ignore
            # parse socks5://host:port
            from urllib.parse import urlparse
            u = urlparse(px)
            host = u.hostname or "127.0.0.1"
            port = u.port or 1080
            handlers.append(SocksiPyHandler(socks.SOCKS5, host, port))
            return build_opener(*handlers), px
        except Exception:
            # fall through — may fail later
            pass
    handlers.append(ProxyHandler({"http": px, "https": px}))
    return build_opener(*handlers), px


def http_get(url: str, headers: dict | None = None, timeout: int = 20, retries: int = 3) -> tuple[int, str, dict, str | None]:
    """GET with optional rotating proxy. Returns status, body, headers, proxy_used."""
    h = {"User-Agent": "GGUF-Runner/4.0", "Accept": "*/*"}
    if headers:
        h.update(headers)
    last_err = ""
    used = None
    for attempt in range(max(1, retries)):
        opener, used = opener_for()
        req = Request(url, headers=h, method="GET")
        try:
            if opener:
                with opener.open(req, timeout=timeout) as r:
                    body = r.read(1_500_000).decode("utf-8", errors="replace")
                    return r.status, body, dict(r.headers), used
            with urlopen(req, timeout=timeout) as r:
                body = r.read(1_500_000).decode("utf-8", errors="replace")
                return r.status, body, dict(r.headers), used
        except HTTPError as e:
            body = e.read(80_000).decode("utf-8", errors="replace") if e.fp else ""
            return e.code, body, dict(e.headers or {}), used
        except Exception as e:
            last_err = str(e)
            time.sleep(0.4 * (attempt + 1))
            continue
    return 0, last_err or "request failed", {}, used


def test_proxy(proxy: str = "", test_url: str = "https://httpbin.org/ip") -> dict[str, Any]:
    proxy = (proxy or "").strip() or (next_proxy() or "")
    if not proxy:
        return {"ok": False, "error": "no proxy to test"}
    try:
        opener, used = opener_for(proxy)
        req = Request(test_url, headers={"User-Agent": "GGUF-Runner-ProxyTest/1"})
        if opener:
            with opener.open(req, timeout=15) as r:
                body = r.read(5000).decode("utf-8", errors="replace")
                return {"ok": True, "proxy": used, "status": r.status, "body": body[:500]}
        return {"ok": False, "error": "could not build opener", "proxy": proxy}
    except Exception as e:
        return {"ok": False, "error": str(e), "proxy": proxy}


# Tool registry helpers
PROXY_TOOLS = {
    "proxy_list": lambda **kw: list_proxies(),
    "proxy_add": lambda proxy="", **kw: add_proxy(proxy),
    "proxy_remove": lambda proxy="", index=-1, **kw: remove_proxy(proxy, int(index) if index is not None else -1),
    "proxy_enable": lambda enabled=True, **kw: set_enabled(bool(enabled)),
    "proxy_test": lambda proxy="", url="https://httpbin.org/ip", **kw: test_proxy(proxy, url or "https://httpbin.org/ip"),
    "proxy_next": lambda **kw: {"ok": True, "proxy": next_proxy()},
}
