# -*- coding: utf-8 -*-
"""
OSINT tools for GGUF Runner Agent.
Public-source intelligence only. No credential stuffing, no auth bypass.
All network calls are optional and fail soft when offline.
"""
from __future__ import annotations

import json
import re
import socket
import ssl
from datetime import datetime, timezone
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode, urlparse
from urllib.request import Request, urlopen

UA = "GGUF-Runner-OSINT/2.4 (+local-agent; research)"
TIMEOUT = 12


def _http_get(url: str, headers: dict | None = None, timeout: int = TIMEOUT) -> tuple[int, str, dict]:
    h = {"User-Agent": UA, "Accept": "application/json, text/plain, */*"}
    if headers:
        h.update(headers)
    # Prefer rotating proxy pool when enabled
    try:
        from proxy_pool import http_get as _px_get, load_config as _px_cfg
        if (_px_cfg() or {}).get("enabled"):
            code, body, hdrs, _used = _px_get(url, headers=h, timeout=timeout, retries=2)
            return code, body, hdrs
    except Exception:
        pass
    req = Request(url, headers=h, method="GET")
    try:
        with urlopen(req, timeout=timeout) as r:
            body = r.read(800_000).decode("utf-8", errors="replace")
            return r.status, body, dict(r.headers)
    except HTTPError as e:
        body = e.read(50_000).decode("utf-8", errors="replace") if e.fp else ""
        return e.code, body, dict(e.headers or {})
    except Exception as e:
        return 0, str(e), {}


def _http_json(url: str, **kw) -> dict[str, Any]:
    code, body, _ = _http_get(url, **kw)
    if code == 0:
        return {"ok": False, "error": body, "status": 0}
    try:
        data = json.loads(body) if body.strip().startswith(("{", "[")) else {"raw": body[:5000]}
    except json.JSONDecodeError:
        data = {"raw": body[:5000]}
    data["_http_status"] = code
    data["ok"] = 200 <= code < 300
    return data


# ---------- DNS / Domain / IP ----------

def osint_dns_lookup(host: str, record: str = "A") -> dict[str, Any]:
    host = (host or "").strip().lower().removeprefix("http://").removeprefix("https://").split("/")[0]
    if not host:
        return {"ok": False, "error": "host required"}
    out: dict[str, Any] = {"ok": True, "host": host, "record": record.upper()}
    try:
        if record.upper() in ("A", "AAAA", "ANY"):
            infos = socket.getaddrinfo(host, None)
            addrs = sorted({i[4][0] for i in infos})
            out["addresses"] = addrs
        out["fqdn"] = socket.getfqdn(host)
    except socket.gaierror as e:
        return {"ok": False, "error": f"DNS failed: {e}", "host": host}
    # reverse for first IP
    if out.get("addresses"):
        try:
            out["reverse"] = socket.gethostbyaddr(out["addresses"][0])[0]
        except Exception:
            out["reverse"] = None
    return out


def osint_ip_info(ip: str) -> dict[str, Any]:
    """Public IP geolocation via ip-api.com (no key, non-commercial)."""
    ip = (ip or "").strip()
    if not ip:
        return {"ok": False, "error": "ip required"}
    # basic validation
    if not re.match(r"^[\d.:a-fA-F]+$", ip):
        return {"ok": False, "error": "invalid ip format"}
    data = _http_json(f"http://ip-api.com/json/{quote(ip)}?fields=status,message,country,countryCode,region,regionName,city,zip,lat,lon,timezone,isp,org,as,asname,reverse,mobile,proxy,hosting,query")
    if data.get("status") == "success" or data.get("ok"):
        data["ok"] = True
    return data


def osint_domain_info(domain: str) -> dict[str, Any]:
    domain = (domain or "").strip().lower()
    domain = re.sub(r"^https?://", "", domain).split("/")[0].split(":")[0]
    if not domain or "." not in domain:
        return {"ok": False, "error": "valid domain required"}
    result: dict[str, Any] = {"ok": True, "domain": domain}
    # DNS
    dns = osint_dns_lookup(domain)
    result["dns"] = dns
    # TLS cert (if reachable)
    try:
        ctx = ssl.create_default_context()
        with socket.create_connection((domain, 443), timeout=8) as sock:
            with ctx.wrap_socket(sock, server_hostname=domain) as ssock:
                cert = ssock.getpeercert()
                result["tls"] = {
                    "subject": dict(x[0] for x in cert.get("subject", ())),
                    "issuer": dict(x[0] for x in cert.get("issuer", ())),
                    "notBefore": cert.get("notBefore"),
                    "notAfter": cert.get("notAfter"),
                    "serialNumber": cert.get("serialNumber"),
                    "san": [v for k, v in cert.get("subjectAltName", ()) if k == "DNS"],
                }
    except Exception as e:
        result["tls"] = {"error": str(e)}
    # HTTP headers probe
    for scheme in ("https", "http"):
        code, body, headers = _http_get(f"{scheme}://{domain}/", timeout=8)
        if code:
            result["http"] = {
                "scheme": scheme,
                "status": code,
                "server": headers.get("Server") or headers.get("server"),
                "powered_by": headers.get("X-Powered-By") or headers.get("x-powered-by"),
                "content_type": headers.get("Content-Type") or headers.get("content-type"),
                "title": (re.search(r"<title[^>]*>([^<]+)</title>", body, re.I) or [None, ""])[1][:200],
            }
            break
    return result


# ---------- Username / Social presence (public HTTP only) ----------

_USERNAME_TARGETS = [
    ("github", "https://github.com/{u}", 200),
    ("gitlab", "https://gitlab.com/{u}", 200),
    ("reddit", "https://www.reddit.com/user/{u}", 200),
    ("twitter_x", "https://x.com/{u}", 200),
    ("instagram", "https://www.instagram.com/{u}/", 200),
    ("tiktok", "https://www.tiktok.com/@{u}", 200),
    ("youtube", "https://www.youtube.com/@{u}", 200),
    ("hackernews", "https://news.ycombinator.com/user?id={u}", 200),
    ("keybase", "https://keybase.io/{u}", 200),
    ("medium", "https://medium.com/@{u}", 200),
    ("pinterest", "https://www.pinterest.com/{u}/", 200),
    ("steam", "https://steamcommunity.com/id/{u}", 200),
    ("twitch", "https://www.twitch.tv/{u}", 200),
    ("aboutme", "https://about.me/{u}", 200),
    ("linktree", "https://linktr.ee/{u}", 200),
]


def osint_username_check(username: str, platforms: list[str] | None = None) -> dict[str, Any]:
    """Check public profile URLs. 404 ≈ likely free; 200 ≈ likely exists. Heuristic only."""
    u = (username or "").strip().lstrip("@")
    if not u or not re.match(r"^[\w.-]{2,39}$", u):
        return {"ok": False, "error": "username 2-39 chars [A-Za-z0-9_.-]"}
    found = []
    missing = []
    errors = []
    targets = _USERNAME_TARGETS
    if platforms:
        pl = {p.lower() for p in platforms}
        targets = [t for t in targets if t[0] in pl]
    for name, tpl, ok_code in targets:
        url = tpl.format(u=quote(u))
        code, body, _ = _http_get(url, timeout=8)
        # soft heuristics for soft-404 pages
        soft404 = False
        low = body.lower()[:3000]
        if code == 200 and any(x in low for x in ("page not found", "user not found", "doesn't exist", "not found", "404")):
            soft404 = True
        if code == ok_code and not soft404:
            found.append({"platform": name, "url": url, "status": code})
        elif code in (0, 429, 503):
            errors.append({"platform": name, "url": url, "status": code, "note": body[:120]})
        else:
            missing.append({"platform": name, "url": url, "status": code})
    return {
        "ok": True,
        "username": u,
        "found": found,
        "not_found_or_private": missing,
        "errors": errors,
        "found_count": len(found),
        "checked": len(targets),
        "disclaimer": "Heuristic public HTTP only. Not proof of ownership.",
    }


# ---------- Email / extractors ----------

_EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")
_URL_RE = re.compile(r"https?://[^\s\"'<>]+", re.I)
_PHONE_RE = re.compile(r"(?:\+?\d{1,3}[\s\-]?)?(?:\(?\d{2,4}\)?[\s\-]?)?\d{3,4}[\s\-]?\d{3,4}")


def osint_extract_from_text(text: str) -> dict[str, Any]:
    text = text or ""
    emails = sorted(set(_EMAIL_RE.findall(text)))
    urls = sorted(set(m.rstrip(".,);]") for m in _URL_RE.findall(text)))
    phones = sorted(set(p.strip() for p in _PHONE_RE.findall(text) if len(re.sub(r"\D", "", p)) >= 8))
    domains = sorted({e.split("@", 1)[1].lower() for e in emails})
    return {
        "ok": True,
        "emails": emails,
        "urls": urls[:100],
        "phones": phones[:50],
        "email_domains": domains,
        "counts": {"emails": len(emails), "urls": len(urls), "phones": len(phones)},
    }


def osint_email_basic(email: str) -> dict[str, Any]:
    """Format + MX/DNS checks only. No breach DB, no SMTP verify spam."""
    email = (email or "").strip().lower()
    if not _EMAIL_RE.fullmatch(email):
        return {"ok": False, "error": "invalid email format"}
    local, domain = email.split("@", 1)
    result: dict[str, Any] = {
        "ok": True,
        "email": email,
        "local": local,
        "domain": domain,
        "format_valid": True,
    }
    # disposable heuristics (small list)
    disposable = {
        "mailinator.com", "guerrillamail.com", "tempmail.com", "10minutemail.com",
        "yopmail.com", "trashmail.com", "temp-mail.org",
    }
    result["possibly_disposable"] = domain in disposable
    dns = osint_dns_lookup(domain)
    result["domain_resolves"] = bool(dns.get("addresses"))
    result["dns"] = dns
    return result


# ---------- Web / search / archives ----------

def osint_web_fetch(url: str, max_chars: int = 30000) -> dict[str, Any]:
    url = (url or "").strip()
    if not url.startswith(("http://", "https://")):
        return {"ok": False, "error": "url must start with http:// or https://"}
    code, body, headers = _http_get(url, timeout=15)
    if not code:
        return {"ok": False, "error": body}
    title = ""
    m = re.search(r"<title[^>]*>([^<]+)</title>", body, re.I)
    if m:
        title = re.sub(r"\s+", " ", m.group(1)).strip()[:300]
    # strip scripts/styles roughly for text
    clean = re.sub(r"(?is)<script[^>]*>.*?</script>", " ", body)
    clean = re.sub(r"(?is)<style[^>]*>.*?</style>", " ", clean)
    clean = re.sub(r"(?is)<[^>]+>", " ", clean)
    clean = re.sub(r"\s+", " ", clean).strip()
    extracted = osint_extract_from_text(body)
    return {
        "ok": 200 <= code < 400,
        "status": code,
        "url": url,
        "title": title,
        "server": headers.get("Server") or headers.get("server"),
        "content_type": headers.get("Content-Type") or headers.get("content-type"),
        "text_preview": clean[:max_chars],
        "emails_found": extracted["emails"][:30],
        "links_sample": extracted["urls"][:20],
    }


def osint_duckduckgo(query: str, max_results: int = 8) -> dict[str, Any]:
    """Lightweight HTML scrape of DuckDuckGo HTML endpoint (no API key)."""
    q = (query or "").strip()
    if not q:
        return {"ok": False, "error": "query required"}
    url = "https://html.duckduckgo.com/html/?" + urlencode({"q": q})
    code, body, _ = _http_get(url, headers={"User-Agent": UA}, timeout=15)
    if not code:
        return {"ok": False, "error": body}
    results = []
    # result links
    for m in re.finditer(
        r'class="result__a"[^>]*href="([^"]+)"[^>]*>(.*?)</a>',
        body,
        re.I | re.S,
    ):
        href, title = m.group(1), re.sub(r"<[^>]+>", "", m.group(2))
        title = re.sub(r"\s+", " ", title).strip()
        # ddg redirect
        if "uddg=" in href:
            from urllib.parse import parse_qs, unquote
            try:
                qs = parse_qs(urlparse(href).query)
                href = unquote(qs.get("uddg", [href])[0])
            except Exception:
                pass
        results.append({"title": title[:200], "url": href})
        if len(results) >= max_results:
            break
    # snippets
    snippets = re.findall(r'class="result__snippet"[^>]*>(.*?)</(?:a|td|div)', body, re.I | re.S)
    for i, sn in enumerate(snippets[: len(results)]):
        results[i]["snippet"] = re.sub(r"<[^>]+>", "", sn)
        results[i]["snippet"] = re.sub(r"\s+", " ", results[i]["snippet"]).strip()[:400]
    return {"ok": True, "query": q, "results": results, "count": len(results)}


def osint_wayback(url: str) -> dict[str, Any]:
    """Query Wayback CDX API for snapshots."""
    url = (url or "").strip()
    if not url:
        return {"ok": False, "error": "url required"}
    api = f"https://web.archive.org/cdx/search/cdx?url={quote(url, safe='')}&output=json&limit=10&fl=timestamp,original,statuscode,mimetype"
    data = _http_json(api)
    if not data.get("ok") and data.get("_http_status") != 200:
        # body may be list
        pass
    raw = data.get("raw")
    rows = []
    try:
        if isinstance(data.get("raw"), str):
            rows = json.loads(data["raw"])
        elif isinstance(data, list):
            rows = data
        else:
            # sometimes parsed as weird
            code, body, _ = _http_get(api)
            rows = json.loads(body) if body else []
    except Exception:
        rows = []
    snaps = []
    for row in rows[1:11] if rows and isinstance(rows[0], list) else rows[:10]:
        if isinstance(row, list) and len(row) >= 2:
            ts, original = row[0], row[1]
            snaps.append({
                "timestamp": ts,
                "original": original,
                "archive_url": f"https://web.archive.org/web/{ts}/{original}",
                "status": row[2] if len(row) > 2 else None,
            })
    return {"ok": True, "url": url, "snapshots": snaps, "count": len(snaps)}


def osint_github_user(username: str) -> dict[str, Any]:
    u = (username or "").strip().lstrip("@")
    if not u:
        return {"ok": False, "error": "username required"}
    data = _http_json(f"https://api.github.com/users/{quote(u)}")
    if not data.get("ok") and data.get("_http_status") == 404:
        return {"ok": False, "error": "user not found", "username": u}
    # public fields only
    keep = [
        "login", "id", "html_url", "name", "company", "blog", "location", "email",
        "bio", "twitter_username", "public_repos", "public_gists", "followers",
        "following", "created_at", "updated_at", "type",
    ]
    profile = {k: data.get(k) for k in keep if k in data}
    profile["ok"] = data.get("ok", True)
    profile["username"] = u
    # repos sample
    repos = _http_json(f"https://api.github.com/users/{quote(u)}/repos?sort=updated&per_page=5")
    if isinstance(repos, dict) and isinstance(repos.get("raw"), str):
        try:
            repo_list = json.loads(repos["raw"])
        except Exception:
            repo_list = []
    else:
        # when list is root - our _http_json wraps poorly for lists
        code, body, _ = _http_get(f"https://api.github.com/users/{quote(u)}/repos?sort=updated&per_page=5")
        try:
            repo_list = json.loads(body)
        except Exception:
            repo_list = []
    profile["recent_repos"] = [
        {"name": r.get("name"), "url": r.get("html_url"), "lang": r.get("language"), "stars": r.get("stargazers_count")}
        for r in (repo_list if isinstance(repo_list, list) else [])[:5]
    ]
    return profile


def osint_github_repo(full_name: str) -> dict[str, Any]:
    full_name = (full_name or "").strip().removesuffix(".git")
    if "/" not in full_name:
        return {"ok": False, "error": "use owner/repo"}
    code, body, _ = _http_get(f"https://api.github.com/repos/{quote(full_name, safe='/')}")
    try:
        data = json.loads(body)
    except Exception:
        return {"ok": False, "error": body[:300]}
    if code == 404:
        return {"ok": False, "error": "repo not found"}
    keys = [
        "full_name", "html_url", "description", "language", "stargazers_count",
        "forks_count", "open_issues_count", "created_at", "updated_at", "pushed_at",
        "license", "topics", "default_branch", "homepage", "archived", "visibility",
    ]
    out = {k: data.get(k) for k in keys}
    out["ok"] = code == 200
    if isinstance(out.get("license"), dict):
        out["license"] = out["license"].get("spdx_id") or out["license"].get("name")
    return out


# ---------- Report helper ----------

def osint_quick_report(target: str) -> dict[str, Any]:
    """
    Auto-detect target type and run a small OSINT bundle.
    target: domain, IP, email, username, or URL.
    """
    t = (target or "").strip()
    if not t:
        return {"ok": False, "error": "target required"}
    report: dict[str, Any] = {
        "ok": True,
        "target": t,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "modules": {},
    }
    # URL
    if t.startswith("http://") or t.startswith("https://"):
        report["type"] = "url"
        report["modules"]["fetch"] = osint_web_fetch(t, max_chars=8000)
        report["modules"]["wayback"] = osint_wayback(t)
        host = urlparse(t).hostname
        if host:
            report["modules"]["domain"] = osint_domain_info(host)
        return report
    # email
    if "@" in t and _EMAIL_RE.fullmatch(t):
        report["type"] = "email"
        report["modules"]["email"] = osint_email_basic(t)
        report["modules"]["domain"] = osint_domain_info(t.split("@", 1)[1])
        return report
    # IP
    if re.match(r"^\d{1,3}(\.\d{1,3}){3}$", t) or ":" in t and re.match(r"^[\da-fA-F:]+$", t):
        report["type"] = "ip"
        report["modules"]["ip"] = osint_ip_info(t)
        return report
    # domain
    if "." in t and " " not in t and not t.startswith("@"):
        report["type"] = "domain"
        report["modules"]["domain"] = osint_domain_info(t)
        report["modules"]["wayback"] = osint_wayback(t)
        return report
    # username
    report["type"] = "username"
    report["modules"]["username"] = osint_username_check(t.lstrip("@"))
    report["modules"]["github"] = osint_github_user(t.lstrip("@"))
    return report


# Registry for agent
OSINT_TOOLS = {
    "osint_dns": osint_dns_lookup,
    "osint_ip": osint_ip_info,
    "osint_domain": osint_domain_info,
    "osint_username": osint_username_check,
    "osint_email": osint_email_basic,
    "osint_extract": osint_extract_from_text,
    "osint_fetch": osint_web_fetch,
    "osint_search": osint_duckduckgo,
    "osint_wayback": osint_wayback,
    "osint_github_user": osint_github_user,
    "osint_github_repo": osint_github_repo,
    "osint_report": osint_quick_report,
}


def osint_schema_for_prompt() -> str:
    return """OSINT tools (public sources only — research / defensive use):
- osint_report(target) — auto bundle for domain|ip|email|username|url
- osint_domain(domain) — DNS + TLS cert + HTTP probe
- osint_dns(host, record="A")
- osint_ip(ip) — geolocation / ASN (ip-api)
- osint_username(username, platforms=null) — public profile presence check
- osint_email(email) — format + domain DNS (no breach dump)
- osint_search(query, max_results=8) — DuckDuckGo HTML
- osint_fetch(url, max_chars=30000) — fetch page + extract emails/links
- osint_wayback(url) — Internet Archive snapshots
- osint_github_user(username)
- osint_github_repo(full_name) — owner/repo
- osint_extract(text) — emails, urls, phones from text

Call with JSON: {"tool": "osint_report", "arguments": {"target": "example.com"}}
Respect laws and platform ToS. Do not attempt login, brute force, or private data access.
"""
