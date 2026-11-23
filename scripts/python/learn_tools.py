# -*- coding: utf-8 -*-
"""
Learn / research tools:
- web search + page read
- YouTube transcript/description learn
- save knowledge to workspace/knowledge + optional RAG
- OCR (image text) best-effort
- translate (public APIs, no paid key required)

Note: Instagram/Facebook heavily restrict scraping; we only attempt public HTML
when reachable. Prefer official export or user-provided URLs/text.
"""
from __future__ import annotations

import json
import re
import time
import html as html_lib
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import quote_plus, urlparse, urljoin
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

from config_loader import ROOT, workspace_dir

try:
    from proxy_pool import opener_for, load_config as load_proxy_cfg
except Exception:
    def opener_for(proxy=None):
        return None, None
    def load_proxy_cfg():
        return {"enabled": False}


UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) GGUF-Runner-Learn/1.0"


def _knowledge_dir() -> Path:
    d = workspace_dir() / "knowledge"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _http_get(url: str, timeout: int = 25, use_proxy: bool = True) -> dict[str, Any]:
    url = (url or "").strip()
    if not url.startswith(("http://", "https://")):
        return {"ok": False, "error": "bad url"}
    headers = {"User-Agent": UA, "Accept": "text/html,application/json,*/*"}
    try:
        req = Request(url, headers=headers, method="GET")
        opener = None
        proxy = None
        if use_proxy and (load_proxy_cfg() or {}).get("enabled"):
            opener, proxy = opener_for()
        if opener:
            resp = opener.open(req, timeout=timeout)
        else:
            resp = urlopen(req, timeout=timeout)
        with resp:
            raw = resp.read(2_000_000)
            status = getattr(resp, "status", None) or resp.getcode()
            ctype = (resp.headers.get("Content-Type") or "").lower()
        text = raw.decode("utf-8", errors="replace")
        return {"ok": 200 <= int(status) < 400, "status": int(status), "body": text, "content_type": ctype, "proxy": proxy, "url": url}
    except Exception as e:
        return {"ok": False, "error": str(e), "url": url}


def _strip_html(html: str, limit: int = 12000) -> str:
    if not html:
        return ""
    # remove scripts/styles
    s = re.sub(r"(?is)<script[^>]*>.*?</script>", " ", html)
    s = re.sub(r"(?is)<style[^>]*>.*?</style>", " ", s)
    s = re.sub(r"(?is)<noscript[^>]*>.*?</noscript>", " ", s)
    s = re.sub(r"(?is)<!--.*?-->", " ", s)
    s = re.sub(r"(?is)<br\s*/?>", "\n", s)
    s = re.sub(r"(?is)</p>", "\n", s)
    s = re.sub(r"(?is)<[^>]+>", " ", s)
    s = html_lib.unescape(s)
    s = re.sub(r"[ \t]+", " ", s)
    s = re.sub(r"\n{3,}", "\n\n", s)
    return s.strip()[:limit]


def web_search(query: str, max_results: int = 5) -> dict[str, Any]:
    """DuckDuckGo HTML lite search (no API key)."""
    query = (query or "").strip()
    if not query:
        return {"ok": False, "error": "query empty"}
    max_results = max(1, min(int(max_results or 5), 10))
    url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"
    r = _http_get(url, timeout=20)
    if not r.get("ok"):
        # fallback bing
        url2 = f"https://www.bing.com/search?q={quote_plus(query)}"
        r = _http_get(url2, timeout=20)
        if not r.get("ok"):
            return {"ok": False, "error": r.get("error"), "query": query}
    body = r.get("body") or ""
    results = []
    # DDG result links
    for m in re.finditer(r'uddg=([^&"]+)|href="(https?://[^"]+)"[^>]*class="[^"]*result', body):
        pass
    for m in re.finditer(r'class="result__a"[^>]*href="([^"]+)"[^>]*>(.*?)</a>', body, re.I | re.S):
        href = html_lib.unescape(m.group(1))
        title = _strip_html(m.group(2), 200)
        if "duckduckgo.com" in href:
            continue
        results.append({"title": title, "url": href})
        if len(results) >= max_results:
            break
    if not results:
        for m in re.finditer(r'href="(https?://[^"]+)"[^>]*>([^<]{8,120})</a>', body):
            href, title = m.group(1), m.group(2).strip()
            if any(x in href for x in ("microsoft.com", "bing.com", "duckduckgo", "javascript:")):
                continue
            results.append({"title": title[:200], "url": href})
            if len(results) >= max_results:
                break
    return {"ok": True, "query": query, "results": results, "count": len(results)}


def web_read(url: str, max_chars: int = 10000) -> dict[str, Any]:
    """Fetch a page and extract readable text."""
    r = _http_get(url, timeout=25)
    if not r.get("ok"):
        return r
    text = _strip_html(r.get("body") or "", int(max_chars or 10000))
    title = ""
    m = re.search(r"(?is)<title[^>]*>(.*?)</title>", r.get("body") or "")
    if m:
        title = _strip_html(m.group(1), 300)
    return {"ok": True, "url": url, "title": title, "text": text, "chars": len(text)}


def _yt_id(url_or_id: str) -> str | None:
    s = (url_or_id or "").strip()
    if re.fullmatch(r"[\w-]{11}", s):
        return s
    m = re.search(r"(?:v=|/shorts/|youtu\.be/)([\w-]{11})", s)
    return m.group(1) if m else None


def youtube_transcript(url_or_id: str, lang: str = "en") -> dict[str, Any]:
    """Best-effort YouTube transcript via timedtext / watch page."""
    vid = _yt_id(url_or_id)
    if not vid:
        return {"ok": False, "error": "invalid youtube id/url"}
    # try timedtext list
    list_url = f"https://www.youtube.com/api/timedtext?type=list&v={vid}"
    lr = _http_get(list_url, timeout=15)
    langs = []
    if lr.get("ok") and lr.get("body"):
        langs = re.findall(r'lang_code="([^"]+)"', lr["body"])
    prefer = [lang, "en", "en-US", "fa", "ar"] + langs
    transcript = ""
    used_lang = None
    for L in prefer:
        if not L:
            continue
        tu = f"https://www.youtube.com/api/timedtext?lang={L}&v={vid}"
        tr = _http_get(tu, timeout=15)
        if not tr.get("ok") or not tr.get("body") or "<text" not in (tr.get("body") or ""):
            continue
        parts = re.findall(r"<text[^>]*>(.*?)</text>", tr["body"], re.S)
        transcript = _strip_html(" ".join(parts), 30000)
        if transcript.strip():
            used_lang = L
            break
    # metadata
    watch = _http_get(f"https://www.youtube.com/watch?v={vid}", timeout=20)
    title = description = ""
    if watch.get("ok"):
        body = watch.get("body") or ""
        mt = re.search(r'"title":"(.*?)"', body)
        if mt:
            title = mt.group(1).encode().decode("unicode_escape", errors="ignore")[:300]
        md = re.search(r'"shortDescription":"(.*?)"', body)
        if md:
            description = md.group(1).encode().decode("unicode_escape", errors="ignore")[:4000]
        if not title:
            m = re.search(r"(?is)<title[^>]*>(.*?)</title>", body)
            if m:
                title = _strip_html(m.group(1), 300)
    if not transcript and not description:
        return {"ok": False, "error": "no transcript/description available", "video_id": vid, "title": title}
    return {
        "ok": True,
        "video_id": vid,
        "url": f"https://www.youtube.com/watch?v={vid}",
        "title": title,
        "lang": used_lang,
        "transcript": transcript[:20000],
        "description": description,
        "has_transcript": bool(transcript.strip()),
    }


def youtube_search_learn(query: str, max_videos: int = 2) -> dict[str, Any]:
    """Search YouTube via web and pull transcripts for top results."""
    query = (query or "").strip()
    if not query:
        return {"ok": False, "error": "query empty"}
    max_videos = max(1, min(int(max_videos or 2), 3))
    url = f"https://www.youtube.com/results?search_query={quote_plus(query)}"
    r = _http_get(url, timeout=20)
    ids = []
    if r.get("ok"):
        ids = list(dict.fromkeys(re.findall(r'"videoId":"([\w-]{11})"', r.get("body") or "")))[:max_videos]
    if not ids:
        # DDG restricted to site
        sr = web_search(f"site:youtube.com {query}", max_results=max_videos)
        for item in sr.get("results") or []:
            vid = _yt_id(item.get("url") or "")
            if vid:
                ids.append(vid)
        ids = list(dict.fromkeys(ids))[:max_videos]
    learned = []
    for vid in ids:
        tr = youtube_transcript(vid)
        learned.append(tr)
    return {"ok": True, "query": query, "videos": learned, "count": len(learned)}


def save_knowledge(topic: str, content: str, source: str = "", tags: list | None = None) -> dict[str, Any]:
    """Save learned text under workspace/knowledge/."""
    topic = (topic or "note").strip() or "note"
    safe = re.sub(r"[^\w\u0600-\u06FF\-]+", "_", topic)[:80] or "note"
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = _knowledge_dir() / f"{safe}_{ts}.md"
    body = f"# {topic}\n\n"
    if source:
        body += f"Source: {source}\n\n"
    if tags:
        body += f"Tags: {', '.join(tags)}\n\n"
    body += content or ""
    path.write_text(body, encoding="utf-8")
    # also append index
    idx = _knowledge_dir() / "index.jsonl"
    with idx.open("a", encoding="utf-8") as f:
        f.write(json.dumps({"topic": topic, "path": str(path), "source": source, "ts": ts}, ensure_ascii=False) + "\n")
    return {"ok": True, "path": str(path), "chars": len(body)}


def learn_topic(topic: str, max_pages: int = 3, include_youtube: bool = True) -> dict[str, Any]:
    """Search web (+ optional YouTube), read pages, merge notes, save knowledge."""
    topic = (topic or "").strip()
    if not topic:
        return {"ok": False, "error": "topic empty"}
    max_pages = max(1, min(int(max_pages or 3), 5))
    search = web_search(topic, max_results=max_pages)
    notes = [f"# Learn: {topic}", f"Time: {datetime.now().isoformat(timespec='seconds')}", ""]
    sources = []
    for item in (search.get("results") or [])[:max_pages]:
        url = item.get("url") or ""
        page = web_read(url, max_chars=6000)
        if page.get("ok") and page.get("text"):
            notes.append(f"## {page.get('title') or item.get('title') or url}")
            notes.append(f"URL: {url}")
            notes.append(page["text"][:5000])
            notes.append("")
            sources.append(url)
    yt = None
    if include_youtube:
        yt = youtube_search_learn(topic, max_videos=2)
        for v in yt.get("videos") or []:
            if not v.get("ok"):
                continue
            notes.append(f"## YouTube: {v.get('title') or v.get('video_id')}")
            notes.append(f"URL: {v.get('url')}")
            if v.get("transcript"):
                notes.append(v["transcript"][:8000])
            elif v.get("description"):
                notes.append(v["description"][:4000])
            notes.append("")
            sources.append(v.get("url") or "")
    content = "\n".join(notes)
    saved = save_knowledge(topic, content, source="; ".join(sources[:8]), tags=["auto-learn"])
    # try RAG rebuild lightly if available
    rag = None
    try:
        from rag_local import build_index
        rag = build_index(max_docs=200)
    except Exception as e:
        rag = {"ok": False, "error": str(e)}
    return {
        "ok": True,
        "topic": topic,
        "sources": sources,
        "search_count": search.get("count"),
        "youtube": {"count": (yt or {}).get("count")} if yt else None,
        "saved": saved,
        "preview": content[:1500],
        "rag": rag,
    }


def ocr_image(path: str = "", url: str = "") -> dict[str, Any]:
    """OCR text from local image path or image URL.

    Tries: pytesseract → easyocr → Pillow metadata only message.
    """
    img_bytes = None
    src = path or url
    if url and url.startswith("http"):
        r = _http_get(url, timeout=30)
        if not r.get("ok"):
            return r
        # body may be binary mis-decoded; re-fetch raw
        try:
            req = Request(url, headers={"User-Agent": UA})
            with urlopen(req, timeout=30) as resp:
                img_bytes = resp.read(8_000_000)
        except Exception as e:
            return {"ok": False, "error": str(e)}
        # save temp
        tmp = workspace_dir() / "tmp_ocr.bin"
        tmp.write_bytes(img_bytes)
        path = str(tmp)
    path = (path or "").strip()
    if not path or not Path(path).exists():
        return {"ok": False, "error": "image path/url required"}
    # pytesseract
    try:
        from PIL import Image  # type: ignore
        import pytesseract  # type: ignore
        img = Image.open(path)
        text = pytesseract.image_to_string(img) or ""
        return {"ok": True, "engine": "pytesseract", "text": text.strip()[:15000], "path": path}
    except Exception as e1:
        err1 = str(e1)
    try:
        import easyocr  # type: ignore
        reader = easyocr.Reader(["en", "fa", "ar"], gpu=False)
        result = reader.readtext(path, detail=0)
        text = "\n".join(result) if isinstance(result, list) else str(result)
        return {"ok": True, "engine": "easyocr", "text": text[:15000], "path": path}
    except Exception as e2:
        return {
            "ok": False,
            "error": "OCR engine not available",
            "hint": "pip install pytesseract pillow  (and install Tesseract-OCR app)  OR  pip install easyocr",
            "detail": f"{err1} | {e2}",
            "path": path,
        }


def translate_text(text: str, target: str = "fa", source: str = "auto", allow_online: bool = True) -> dict[str, Any]:
    """Offline-first translation (Argos packs) with optional online fallback."""
    try:
        from offline_translate import translate_offline_first
        return translate_offline_first(text, target=target, source=source, allow_online=allow_online)
    except Exception as e:
        # legacy online path if module missing
        text = (text or "").strip()
        if not text:
            return {"ok": False, "error": "text empty"}
        return {"ok": False, "error": f"translate backend: {e}"}



def social_read(url: str) -> dict[str, Any]:
    """Best-effort public page read (Instagram/Twitter/etc often block bots)."""
    url = (url or "").strip()
    if not url.startswith("http"):
        return {"ok": False, "error": "url required"}
    host = (urlparse(url).hostname or "").lower()
    r = web_read(url, max_chars=8000)
    if not r.get("ok"):
        return {
            "ok": False,
            "error": r.get("error") or "fetch failed",
            "hint": "Many social sites block scrapers. Paste text/caption or use export.",
            "host": host,
        }
    if len((r.get("text") or "").strip()) < 40:
        return {
            "ok": False,
            "error": "little/no public text extracted",
            "host": host,
            "title": r.get("title"),
            "hint": "Login walls / JS apps — provide screenshot for OCR or copy text.",
        }
    return {**r, "host": host}


LEARN_TOOLS: dict[str, Any] = {
    "web_search": web_search,
    "web_read": web_read,
    "learn_topic": learn_topic,
    "youtube_transcript": youtube_transcript,
    "youtube_search_learn": youtube_search_learn,
    "save_knowledge": save_knowledge,
    "ocr_image": ocr_image,
    "translate": translate_text,
    "translate_text": translate_text,
    "social_read": social_read,
}
