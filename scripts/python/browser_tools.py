# -*- coding: utf-8 -*-
"""Layer 2: browser + HTTP API with domain allowlist."""
from __future__ import annotations

import json
import re
from typing import Any
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from config_loader import load_approval_policy

UA = "GGUF-Runner-Browser/2.9"

# default allowlist suffixes; policy can extend browser_allow_suffixes
DEFAULT_ALLOW = [
    "example.com", "github.com", "githubusercontent.com", "wikipedia.org",
    "python.org", "pypi.org", "docs.python.org", "stackoverflow.com",
    "cloudflare.com", "crt.sh", "duckduckgo.com",
]


def _allow_suffixes() -> list[str]:
    try:
        pol = load_approval_policy() or {}
        extra = pol.get("browser_allow_suffixes") or []
        return list(dict.fromkeys([*(DEFAULT_ALLOW), *[str(x).lower() for x in extra]]))
    except Exception:
        return list(DEFAULT_ALLOW)


def _host_allowed(host: str) -> bool:
    host = (host or "").lower()
    if not host:
        return False
    for s in _allow_suffixes():
        if host == s or host.endswith("." + s):
            return True
    return False


def browser_fetch(url: str, max_chars: int = 30000) -> dict[str, Any]:
    url = (url or "").strip()
    if not url.startswith(("http://", "https://")):
        return {"ok": False, "error": "only http/https"}
    host = urlparse(url).hostname or ""
    if not _host_allowed(host):
        return {"ok": False, "blocked": True, "error": f"host not in allowlist: {host}", "allow": _allow_suffixes()[:20]}
    req = Request(url, headers={"User-Agent": UA, "Accept": "text/html,application/json,*/*"})
    try:
        with urlopen(req, timeout=25) as r:
            raw = r.read(900_000)
            ctype = r.headers.get("Content-Type", "")
            final = r.geturl()
            code = r.status
    except Exception as e:
        return {"ok": False, "error": str(e)}
    text = raw.decode("utf-8", errors="replace")
    title = ""
    m = re.search(r"<title[^>]*>([^<]+)</title>", text, re.I)
    if m:
        title = re.sub(r"\s+", " ", m.group(1)).strip()[:300]
    clean = re.sub(r"(?is)<script[^>]*>.*?</script>", " ", text)
    clean = re.sub(r"(?is)<style[^>]*>.*?</style>", " ", clean)
    clean = re.sub(r"(?is)<[^>]+>", " ", clean)
    clean = re.sub(r"\s+", " ", clean).strip()
    return {
        "ok": 200 <= code < 400,
        "status": code,
        "url": url,
        "final_url": final,
        "title": title,
        "content_type": ctype,
        "text": clean[:max_chars],
        "engine": "urllib-readonly",
    }


def browser_playwright(url: str, max_chars: int = 30000, click_selector: str | None = None) -> dict[str, Any]:
    """Optional Playwright; falls back if not installed. click only if host allowed."""
    url = (url or "").strip()
    if not url.startswith(("http://", "https://")):
        return {"ok": False, "error": "only http/https"}
    host = urlparse(url).hostname or ""
    if not _host_allowed(host):
        return {"ok": False, "blocked": True, "error": f"host not in allowlist: {host}"}
    try:
        from playwright.sync_api import sync_playwright  # type: ignore
    except ImportError:
        # fallback
        base = browser_fetch(url, max_chars=max_chars)
        base["note"] = "playwright not installed; used readonly fetch"
        return base
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
            if click_selector:
                page.click(click_selector, timeout=5000)
            title = page.title()
            text = page.inner_text("body")[:max_chars]
            browser.close()
        return {"ok": True, "url": url, "title": title, "text": text, "engine": "playwright"}
    except Exception as e:
        return {"ok": False, "error": str(e), "engine": "playwright"}


def fetch_json(url: str, method: str = "GET", body: str | None = None, max_bytes: int = 500_000) -> dict[str, Any]:
    url = (url or "").strip()
    if not url.startswith(("http://", "https://")):
        return {"ok": False, "error": "only http/https"}
    host = urlparse(url).hostname or ""
    if not _host_allowed(host) and host not in ("127.0.0.1", "localhost"):
        return {"ok": False, "blocked": True, "error": f"host not allowed: {host}"}
    method = (method or "GET").upper()
    data = body.encode("utf-8") if body and method in ("POST", "PUT", "PATCH") else None
    req = Request(url, data=data, method=method, headers={"User-Agent": UA, "Accept": "application/json", "Content-Type": "application/json"})
    try:
        with urlopen(req, timeout=30) as r:
            raw = r.read(max_bytes)
            code = r.status
    except Exception as e:
        return {"ok": False, "error": str(e)}
    try:
        parsed = json.loads(raw.decode("utf-8", errors="replace"))
    except Exception:
        parsed = raw.decode("utf-8", errors="replace")[:20000]
    return {"ok": 200 <= code < 400, "status": code, "url": url, "data": parsed}


def browser_screenshot_info(url: str = "") -> dict[str, Any]:
    return {
        "ok": False,
        "error": "screenshot needs multimodal model + playwright; not bundled by default",
        "hint": "install playwright chromium and use a vision-capable GGUF if available",
        "url": url,
    }


BROWSER_LAYER_TOOLS = {
    "browser_fetch": browser_fetch,
    "browser_playwright": browser_playwright,
    "fetch_json": fetch_json,
    "browser_screenshot_info": browser_screenshot_info,
}
