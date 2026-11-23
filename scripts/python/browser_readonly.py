# -*- coding: utf-8 -*-
"""Read-only browser fetch with optional domain allowlist. No script execution."""
from __future__ import annotations

import re
from typing import Any
from urllib.parse import urlparse
from urllib.request import Request, urlopen

UA = "GGUF-Runner-Browser/2.5 (+read-only)"


def browser_read(url: str, max_chars: int = 40000, allowed_suffixes: list[str] | None = None) -> dict[str, Any]:
    url = (url or "").strip()
    if not url.startswith(("http://", "https://")):
        return {"ok": False, "error": "فقط http/https"}
    host = urlparse(url).hostname or ""
    if allowed_suffixes:
        ok_host = any(host == s or host.endswith("." + s) for s in allowed_suffixes)
        if not ok_host:
            return {"ok": False, "error": f"دامنه مجاز نیست: {host}", "allowed": allowed_suffixes}
    req = Request(url, headers={"User-Agent": UA, "Accept": "text/html,application/xhtml+xml"})
    try:
        with urlopen(req, timeout=20) as r:
            raw = r.read(800_000)
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
        "content_type": ctype,
        "title": title,
        "text": clean[:max_chars],
        "mode": "read_only",
        "note": "بدون اجرای جاوااسکریپت؛ فقط دریافت HTML",
    }
