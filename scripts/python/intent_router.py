# -*- coding: utf-8 -*-
"""
Advanced Persian/English natural-language → tool routing.

Handles colloquial Persian (رو، کن، بده، میخوام، ببین)، English mixes,
and multi-signal scoring when several rules could match.
"""
from __future__ import annotations

import re
from typing import Any, Callable
from urllib.parse import urlparse

# ---------- extractors ----------

def first_url(text: str) -> str | None:
    m = re.search(r"https?://[^\s<>\"'،]+", text)
    return m.group(0).rstrip(").,،؛") if m else None


def first_domain(text: str) -> str | None:
    m = re.search(
        r"(?<![@\w])((?:[a-z0-9-]+\.)+(?:com|ir|org|net|io|dev|info|co|ai|app|edu|gov|me|tv|xyz|site|online)(?:\.[a-z]{2})?)",
        text,
        re.I,
    )
    return m.group(1).lower() if m else None


def path_like(text: str) -> str | None:
    m = re.search(
        r"([A-Za-z]:\\[^\s\"']+|/(?:home|Users|tmp|var|opt|mnt)[^\s\"']+)",
        text,
    )
    return m.group(1) if m else None


def strip_leading_polite(text: str) -> str:
    return re.sub(
        r"^(لطفاً|لطفا|خواهشا|خواهشمندم|میشه|میتونی|می‌تونی|please)\s+",
        "",
        text.strip(),
        flags=re.I,
    )


def after_keyword(text: str, patterns: str) -> str:
    m = re.search(patterns, text, flags=re.I)
    if not m:
        return text.strip()
    return text[m.end() :].lstrip(" :：-–").strip()


# ---------- language target for translate ----------

_LANG_MAP = {
    "فارسی": "fa", "persian": "fa", "farsi": "fa",
    "انگلیسی": "en", "english": "en",
    "عربی": "ar", "arabic": "ar",
    "آلمانی": "de", "german": "de",
    "فرانسوی": "fr", "french": "fr",
    "ترکی": "tr", "turkish": "tr",
    "اسپانیایی": "es", "spanish": "es",
    "روسی": "ru", "russian": "ru",
    "چینی": "zh", "chinese": "zh",
    "ژاپنی": "ja", "japanese": "ja",
    "هندی": "hi", "hindi": "hi",
}


def detect_target_lang(text: str, default: str = "fa") -> str:
    low = text.lower()
    for name, code in _LANG_MAP.items():
        if name in low or re.search(rf"\b{code}\b", low):
            return code
    if re.search(r"به\s+([آا-یA-Za-z]+)", text):
        m = re.search(r"به\s+([آا-یA-Za-z]+)", text)
        if m and m.group(1) in _LANG_MAP:
            return _LANG_MAP[m.group(1)]
    return default


# ---------- rule table with scores ----------

def route_intent(text: str) -> dict[str, Any] | None:
    """Return best {tool, arguments, reason, score} or None."""
    raw = (text or "").strip()
    if not raw or raw.startswith("/"):
        return None
    t = strip_leading_polite(raw)
    low = t.lower()
    url = first_url(t)
    domain = first_domain(t)
    path = path_like(t)

    candidates: list[dict[str, Any]] = []

    def add(tool: str, arguments: dict, reason: str, score: float):
        candidates.append({"tool": tool, "arguments": arguments, "reason": reason, "score": score})

    # ===== LEARN (high priority if explicit) =====
    if re.search(r"(یاد\s*بگیر|یادگیری|میخوام\s*یاد|می‌خوام\s*یاد|learn about|teach me)", t, re.I):
        topic = after_keyword(t, r"(?:یاد\s*بگیر|یادگیری|learn about|teach me)\s*(?:کن|کنید)?\s*[:：]?")
        topic = re.sub(r"^(این\s*موضوع|موضوع|درباره|در\s*مورد|about)\s*", "", topic, flags=re.I).strip() or t
        # if youtube mentioned, prefer youtube learn
        if re.search(r"(یوتیوب|youtube)", t, re.I):
            add("youtube_search_learn", {"query": topic, "max_videos": 2}, "learn youtube", 0.92)
        else:
            add("learn_topic", {"topic": topic, "max_pages": 3, "include_youtube": True}, "learn", 0.95)

    if re.search(r"(تحقیق\s*کن|پژوهش|بررسی\s*کن\s*درباره)", t) and not domain:
        topic = after_keyword(t, r"(?:تحقیق\s*کن|پژوهش|بررسی\s*کن\s*درباره)\s*[:：]?")
        topic = re.sub(r"^(درباره|در\s*مورد|about)\s*", "", topic, flags=re.I).strip() or t
        add("learn_topic", {"topic": topic, "max_pages": 3, "include_youtube": True}, "research", 0.88)

    # ===== SECURITY / AUDIT =====
    sec_words = r"(امنیت|امنیتی|آدیت|audit|tls|ssl|هدر\s*امن|گواهی|https?\s*header|security\s*check|امن\s*ه|مأمون)"
    site_words = r"(سایت|دامنه|وبسایت|وب\s*سایت|domain|site|url|آدرس)"
    if re.search(sec_words, t, re.I) or (
        re.search(r"(بررسی|چک|آنالیز|تحلیل|ببین)\s*(کن|کنید|کنی)?", t)
        and re.search(site_words, t, re.I)
        and (url or domain)
    ):
        target = url or domain
        if target:
            add("cyber_quick_audit", {"url_or_domain": target}, "security audit", 0.93)

    if re.search(r"security\s*check|check\s*security|ssl\s*check", t, re.I) and (url or domain):
        add("cyber_quick_audit", {"url_or_domain": url or domain}, "security check en", 0.9)

    # soft: «ببین این سایت امنه؟ example.org»
    if re.search(r"(امن\s*ه|امن\s*است|امن\s*نیست)", t) and (url or domain):
        add("cyber_quick_audit", {"url_or_domain": url or domain}, "is site safe", 0.85)

    if re.search(r"(dns|دی\s*ان\s*اس|دی‌ان‌اس|رکورد\s*dns|nameserver)", t, re.I) and (domain or url):
        d = domain or (urlparse(url).hostname if url else None)
        if d:
            add("cyber_dns_full", {"domain": d}, "dns", 0.9)

    if re.search(r"(tls|گواهی\s*ssl|certificate)", t, re.I) and (domain or url):
        h = domain or (urlparse(url).hostname if url else None)
        if h:
            add("cyber_tls_info", {"host": h}, "tls", 0.87)

    # ===== DOWNLOAD =====
    if re.search(r"(دانلود|download)\s*(کن|کنید|کنی|ش\s*کن)?", t, re.I) and url:
        add("download_start", {"url": url}, "download", 0.96)

    if re.search(r"(دانلودش|دانلودش\s*کن)", t) and url:
        add("download_start", {"url": url}, "download colloquial", 0.95)

    # ===== MONITOR =====
    if re.search(r"(وضعیت\s*سیستم|مانیتور|منابع\s*سیستم|system\s*status|health\s*check)", t, re.I):
        add("monitor_system", {}, "monitor", 0.9)
    if re.search(r"(رم|حافظه|\bmemory\b|\bram\b)\s*(آزاد|چقدر|مصرف|وضعیت)?", t, re.I) and not re.search(r"instagram|اینستا", t, re.I):
        add("monitor_memory", {}, "memory", 0.88)
    if re.search(r"(سی\s*پی\s*یو|\bcpu\b|پردازنده)\s*(چقدر|مصرف|وضعیت)?", t, re.I):
        add("monitor_cpu", {}, "cpu", 0.9)
    if re.search(r"(دیسک|فضای\s*دیسک|disk\s*space)", t, re.I):
        add("monitor_disk", {}, "disk", 0.88)
    if re.search(r"(پروسس|process|برنامه\s*هایی\s*باز|tasklist)", t, re.I):
        add("monitor_processes", {}, "processes", 0.88)
    if re.search(r"(پورت\s*های\s*باز|listening|netlocal|کارت\s*شبکه|شبکه\s*محلی)", t, re.I):
        add("cyber_net_local", {}, "local net", 0.9)

    # ===== TRANSLATE =====
    if re.search(r"(ترجمه\s*کن|translate)", t, re.I):
        target = detect_target_lang(t, default="fa")
        body = after_keyword(t, r"(?:ترجمه\s*کن|translate)(?:\s+به\s+\S+)?\s*[:：]?")
        body = re.sub(r"^(به\s*)?(" + "|".join(map(re.escape, _LANG_MAP.keys())) + r")\s*[:：]?\s*", "", body, flags=re.I)
        body = body.strip() or t
        add("translate", {"text": body, "target": target}, "translate", 0.94)

    # ===== YOUTUBE =====
    if re.search(r"(یوتیوب|youtube)", t, re.I):
        if url and re.search(r"youtu", url, re.I):
            if re.search(r"(زیرنویس|transcript|caption)", t, re.I):
                add("youtube_transcript", {"url_or_id": url}, "yt transcript", 0.95)
            else:
                add("youtube_transcript", {"url_or_id": url}, "yt url", 0.9)
        else:
            q = after_keyword(t, r"(?:یوتیوب|youtube)\s*")
            q = re.sub(r"^(درباره|در\s*مورد|about)\s*", "", q, flags=re.I).strip() or t
            add("youtube_search_learn", {"query": q, "max_videos": 2}, "yt search", 0.86)

    if re.search(r"(زیرنویس|transcript)\s*(اینو|این)?\s*(بکش|بگیر|استخراج)?", t, re.I) and url and "youtu" in (url or ""):
        add("youtube_transcript", {"url_or_id": url}, "transcript", 0.96)

    # ===== OCR =====
    if re.search(r"(متن\s*عکس|ocr|بخوان\s*از\s*عکس|عکس\s*را\s*بخوان|استخراج\s*کن.*عکس)", t, re.I):
        if url:
            add("ocr_image", {"url": url}, "ocr url", 0.92)
        elif path:
            add("ocr_image", {"path": path}, "ocr path", 0.92)

    # ===== SOCIAL =====
    if re.search(r"(اینستا|اینستاگرام|instagram|توییتر|twitter|x\.com|تلگرام\s*کانال)", t, re.I) and url:
        add("social_read", {"url": url}, "social", 0.93)

    # ===== SHELL =====
    if re.search(r"(اجرا\s*کن\s*دستور|دستور\s*شل|shell\s*:|cmd\s*:|powershell\s*:)", t, re.I):
        cmd = after_keyword(t, r"(?:اجرا\s*کن\s*دستور|دستور\s*(?:شل)?\s*:|shell\s*:|cmd\s*:|powershell\s*:)")
        if cmd:
            add("shell_run", {"command": cmd, "timeout": 120}, "shell", 0.93)

    # ===== WEB SEARCH =====
    if re.search(r"(جستجو\s*کن|سرچ\s*کن|تو\s*(?:اینترنت|نت|وب)\s*سرچ|search\s*for|google\s*کن)", t, re.I):
        q = after_keyword(t, r"(?:جستجو\s*کن|سرچ\s*کن|search\s*for|google\s*کن)\s*[:：]?")
        q = re.sub(r"^(در\s*)?(اینترنت|نت|وب|google)?\s*", "", q, flags=re.I).strip() or t
        add("web_search", {"query": q, "max_results": 5}, "search", 0.9)

    # ===== HASH / FILE =====
    if re.search(r"(هش|hash|sha256|md5)\s*(کن|بگیر|بده|file)?", t, re.I) and path:
        add("cyber_hash_file", {"path": path}, "hash", 0.94)
    if re.search(r"(بخوان|نشون\s*بده|محتوای)\s*(فایل)?", t) and path and not re.search(r"عکس", t):
        add("read_file", {"path": path}, "read file", 0.85)

    # ===== API =====
    if re.search(r"(درخواست\s*api|api\s*call|http\s*get|http\s*post)", t, re.I) and url:
        method = "GET"
        if re.search(r"post", t, re.I):
            method = "POST"
        add("api_request", {"url": url, "method": method}, "api", 0.88)

    # ===== PROXY =====
    if re.search(r"(پروکسی|proxy)\s*(اضافه|add)", t, re.I) and (url or re.search(r"\d+\.\d+\.\d+\.\d+:\d+", t)):
        px = url or re.search(r"(\d+\.\d+\.\d+\.\d+:\d+)", t).group(1)
        if px and not px.startswith("http"):
            px = "http://" + px
        add("proxy_add", {"proxy": px}, "proxy add", 0.9)

    
    # ===== DOCUMENT EXPORT (code files left to LLM tool-call with full source) =====

    if re.search(r"(فایل\s*)?(ورد|word|docx)\s*(بساز|بده|تولید)?", t, re.I) or re.search(r"(بساز|بده).*?(ورد|docx)", t, re.I):
        add("make_document", {"content": t, "fmt": "docx", "title": "Document"}, "docx", 0.8)
    if re.search(r"(فایل\s*)?(پی\s*دی\s*اف|pdf)\s*(بساز|بده|تولید)?", t, re.I):
        add("make_document", {"content": t, "fmt": "pdf", "title": "Document"}, "pdf", 0.8)



    # ===== OSINT =====
    if re.search(r"(osint|اوسینت|اطلاعات\s*باز|تحقیق\s*روی|بررسی\s*دامنه|whois|ساب\s*دامنه)", t, re.I):
        target = first_url(t) or first_domain(t) or ""
        if not target:
            m = re.search(r"(?:برای|روی|about)\s+(\S+)", t, re.I)
            if m:
                target = m.group(1)
        if target:
            add("osint_dossier", {"target": target}, "osint dossier", 0.91)

    # pick best
    if not candidates:
        return None
    candidates.sort(key=lambda x: x["score"], reverse=True)
    best = candidates[0]
    if best["score"] < 0.72:
        return None
    return {
        "tool": best["tool"],
        "arguments": best["arguments"],
        "reason": best["reason"],
        "score": best["score"],
        "alternatives": [{"tool": c["tool"], "score": c["score"]} for c in candidates[1:3]],
    }


def persian_tool_examples() -> str:
    return (
        "- «یک برنامه پایتون بساز که ...» → کد را بنویس سپس make_code_file\n"
        "- «خروجی ورد/PDF بده» → make_document\n"
        "دستورات فارسی/انگلیسی کاربر را به ابزار وصل کن. مثال:\n"
        "- «سایت X را بررسی کن / امنه؟» → cyber_quick_audit\n"
        "- «درباره X تحقیق کن / یاد بگیر» → learn_topic\n"
        "- «دانلود کن + لینک» → download_start\n"
        "- «وضعیت سیستم / رم / سی‌پی‌یو» → monitor_*\n"
        "- «ترجمه کن به انگلیسی/آلمانی: ...» → translate\n"
        "- «تو نت سرچ کن ...» → web_search\n"
        "- «زیرنویس یوتیوب» → youtube_transcript\n"
        "اگر ابزار لازم است فقط JSON: {\"tool\":\"name\",\"arguments\":{...}}\n"
    )


def list_intent_patterns() -> list[dict[str, str]]:
    """Documentation helper for UI/docs."""
    return [
        {"intent": "یادگیری/تحقیق", "examples": "یاد بگیر، تحقیق کن، میخوام یاد بگیرم", "tool": "learn_topic"},
        {"intent": "آدیت امنیتی", "examples": "بررسی کن، امنه؟، TLS، security check", "tool": "cyber_quick_audit"},
        {"intent": "دانلود", "examples": "دانلود کن، دانلودش کن + URL", "tool": "download_start"},
        {"intent": "مانیتور", "examples": "وضعیت سیستم، رم، سی‌پی‌یو، پروسس", "tool": "monitor_*"},
        {"intent": "ترجمه", "examples": "ترجمه کن به انگلیسی/آلمانی/...", "tool": "translate"},
        {"intent": "جستجوی وب", "examples": "جستجو کن، سرچ کن، تو نت", "tool": "web_search"},
        {"intent": "یوتیوب", "examples": "یوتیوب، زیرنویس", "tool": "youtube_*"},
        {"intent": "OCR", "examples": "متن عکس، OCR", "tool": "ocr_image"},
        {"intent": "شل", "examples": "دستور شل، cmd:", "tool": "shell_run"},
        {"intent": "هش فایل", "examples": "هش، sha256 + مسیر", "tool": "cyber_hash_file"},
        {"intent": "شبکه محلی", "examples": "پورت‌های باز، کارت شبکه", "tool": "cyber_net_local"},
        {"intent": "سوشال", "examples": "اینستا + لینک", "tool": "social_read"},
    ]
