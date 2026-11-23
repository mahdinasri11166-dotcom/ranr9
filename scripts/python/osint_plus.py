# -*- coding: utf-8 -*-
"""
Expanded passive OSINT toolkit (public sources only).
Research / defensive / authorized asset checks — no breach dumps, no credential stuffing.
"""
from __future__ import annotations

import hashlib
import json
import re
import socket
import ssl
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from typing import Any
from urllib.parse import quote, urlparse
from urllib.request import Request, urlopen

UA = "GGUF-Runner-OSINT/4.9 (+passive-research)"


def _get(url: str, timeout: int = 20, max_bytes: int = 1_500_000) -> dict[str, Any]:
    try:
        req = Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
        with urlopen(req, timeout=timeout) as resp:
            raw = resp.read(max_bytes)
            status = getattr(resp, "status", None) or resp.getcode()
            ctype = (resp.headers.get("Content-Type") or "").lower()
            text = raw.decode("utf-8", errors="replace")
            return {"ok": 200 <= int(status) < 400, "status": int(status), "body": text, "bytes": len(raw), "content_type": ctype, "url": url}
    except Exception as e:
        return {"ok": False, "error": str(e), "url": url}


def _json_get(url: str, timeout: int = 20) -> dict[str, Any]:
    r = _get(url, timeout=timeout)
    if not r.get("ok"):
        return r
    try:
        return {"ok": True, "data": json.loads(r.get("body") or "{}"), "url": url}
    except Exception as e:
        return {"ok": False, "error": f"json: {e}", "preview": (r.get("body") or "")[:400]}


# ---------- DNS / network ----------

def osint_dns_all(domain: str) -> dict[str, Any]:
    domain = (domain or "").strip().lower().rstrip(".")
    if not domain:
        return {"ok": False, "error": "domain required"}
    out: dict[str, Any] = {"ok": True, "domain": domain, "records": {}}
    try:
        out["records"]["A"] = sorted({ai[4][0] for ai in socket.getaddrinfo(domain, None, socket.AF_INET)})
    except Exception as e:
        out["records"]["A_error"] = str(e)
    try:
        out["records"]["AAAA"] = sorted({ai[4][0] for ai in socket.getaddrinfo(domain, None, socket.AF_INET6)})
    except Exception:
        out["records"]["AAAA"] = []
    # TXT / MX via dnspython if available, else system
    try:
        import dns.resolver  # type: ignore
        for rtype in ("MX", "NS", "TXT", "CNAME", "SOA"):
            try:
                ans = dns.resolver.resolve(domain, rtype)
                out["records"][rtype] = [str(r).strip() for r in ans]
            except Exception as e:
                out["records"][rtype] = f"({e.__class__.__name__})"
    except Exception:
        out["records"]["note"] = "dnspython not installed — A/AAAA only via socket"
    return out


def osint_reverse_dns(ip: str) -> dict[str, Any]:
    ip = (ip or "").strip()
    if not ip:
        return {"ok": False, "error": "ip required"}
    try:
        host, aliases, ips = socket.gethostbyaddr(ip)
        return {"ok": True, "ip": ip, "hostname": host, "aliases": list(aliases), "addrs": list(ips)}
    except Exception as e:
        return {"ok": False, "ip": ip, "error": str(e)}


def osint_rdap(domain_or_ip: str) -> dict[str, Any]:
    """RDAP lookup (registration data) via rdap.org bootstrap."""
    t = (domain_or_ip or "").strip().lower()
    if not t:
        return {"ok": False, "error": "domain_or_ip required"}
    if re.match(r"^\d{1,3}(\.\d{1,3}){3}$", t):
        url = f"https://rdap.org/ip/{t}"
    else:
        url = f"https://rdap.org/domain/{t}"
    r = _json_get(url, timeout=25)
    if not r.get("ok"):
        # fallback rdap.verisign for domains
        if "." in t and not re.match(r"^\d", t):
            r2 = _json_get(f"https://rdap.verisign.com/com/v1/domain/{t}", timeout=20)
            if r2.get("ok"):
                return {"ok": True, "source": "verisign-rdap", "target": t, "data": r2.get("data")}
        return r
    data = r.get("data") or {}
    slim = {
        "handle": data.get("handle"),
        "ldhName": data.get("ldhName") or data.get("name"),
        "status": data.get("status"),
        "nameservers": [n.get("ldhName") for n in (data.get("nameservers") or []) if isinstance(n, dict)],
        "events": data.get("events"),
        "entities_count": len(data.get("entities") or []),
    }
    return {"ok": True, "source": "rdap.org", "target": t, "summary": slim, "raw_keys": list(data.keys())[:30]}


def osint_whois_text(domain: str) -> dict[str, Any]:
    """Best-effort WHOIS via public web APIs (no local whois binary required)."""
    domain = (domain or "").strip().lower().rstrip(".")
    if not domain:
        return {"ok": False, "error": "domain required"}
    # prefer RDAP structured
    rdap = osint_rdap(domain)
    # also try who.is HTML strip (lightweight)
    html = _get(f"https://www.whois.com/whois/{quote(domain)}", timeout=20)
    text = ""
    if html.get("ok"):
        body = html.get("body") or ""
        m = re.search(r'(?is)<pre[^>]*>(.*?)</pre>', body)
        if m:
            text = re.sub(r"<[^>]+>", "", m.group(1))
            text = re.sub(r"\s+\n", "\n", text).strip()[:8000]
    return {"ok": True, "domain": domain, "rdap": rdap, "whois_text": text[:5000] if text else None}


def osint_ip_geo(ip: str) -> dict[str, Any]:
    """IP geolocation via ip-api.com (non-commercial free tier)."""
    ip = (ip or "").strip()
    if not ip:
        return {"ok": False, "error": "ip required"}
    r = _json_get(f"http://ip-api.com/json/{quote(ip)}?fields=status,message,country,regionName,city,zip,lat,lon,isp,org,as,query,timezone,reverse,mobile,proxy,hosting", timeout=15)
    if not r.get("ok"):
        return r
    data = r.get("data") or {}
    if data.get("status") != "success":
        return {"ok": False, "error": data.get("message") or "lookup failed", "data": data}
    return {"ok": True, "ip": ip, "geo": data}


def osint_asn(ip_or_asn: str) -> dict[str, Any]:
    t = (ip_or_asn or "").strip()
    if not t:
        return {"ok": False, "error": "ip_or_asn required"}
    if t.upper().startswith("AS"):
        # cymru-style via dns - optional
        return {"ok": True, "query": t, "note": "Use IP for full geo/ASN via osint_ip_geo"}
    geo = osint_ip_geo(t)
    if geo.get("ok"):
        g = geo.get("geo") or {}
        return {"ok": True, "ip": t, "asn": g.get("as"), "org": g.get("org"), "isp": g.get("isp"), "country": g.get("country")}
    return geo


# ---------- HTTP / site ----------

def osint_http_probe(url: str) -> dict[str, Any]:
    url = (url or "").strip()
    if not url.startswith("http"):
        url = "https://" + url
    r = _get(url, timeout=20, max_bytes=64_000)
    if not r.get("ok") and url.startswith("https://"):
        r = _get("http://" + urlparse(url).netloc + (urlparse(url).path or "/"), timeout=15, max_bytes=64_000)
    headers_interesting = {}
    # re-fetch headers only via another get - body already limited
    try:
        req = Request(url, headers={"User-Agent": UA}, method="GET")
        with urlopen(req, timeout=15) as resp:
            headers_interesting = {k: v for k, v in list(resp.headers.items())[:40]}
            status = getattr(resp, "status", None) or resp.getcode()
    except Exception as e:
        return {"ok": False, "error": str(e), "url": url, "fallback": r}
    sec = {k: headers_interesting.get(k) for k in (
        "Server", "X-Powered-By", "Strict-Transport-Security", "Content-Security-Policy",
        "X-Frame-Options", "X-Content-Type-Options", "Set-Cookie", "Via", "CF-Ray",
    ) if headers_interesting.get(k)}
    title = ""
    body = r.get("body") or ""
    m = re.search(r"(?is)<title[^>]*>(.*?)</title>", body)
    if m:
        title = re.sub(r"\s+", " ", m.group(1)).strip()[:200]
    techs = []
    blob = (str(headers_interesting) + body[:5000]).lower()
    for name, pat in (
        ("WordPress", r"wp-content|wordpress"),
        ("nginx", r"nginx"),
        ("Apache", r"apache"),
        ("Cloudflare", r"cloudflare|cf-ray"),
        ("React", r"react"),
        ("Next.js", r"__next"),
        ("Django", r"csrfmiddlewaretoken"),
        ("Laravel", r"laravel"),
    ):
        if re.search(pat, blob):
            techs.append(name)
    return {
        "ok": True,
        "url": url,
        "status": int(status),
        "title": title,
        "security_headers": sec,
        "tech_guess": techs,
        "headers": headers_interesting,
    }


def osint_robots(domain: str) -> dict[str, Any]:
    domain = (domain or "").strip().lower()
    if domain.startswith("http"):
        base = f"{urlparse(domain).scheme}://{urlparse(domain).hostname}"
    else:
        base = f"https://{domain}"
    robots = _get(f"{base}/robots.txt", timeout=12)
    security = _get(f"{base}/.well-known/security.txt", timeout=12)
    return {
        "ok": True,
        "base": base,
        "robots": {"ok": robots.get("ok"), "body": (robots.get("body") or "")[:4000], "error": robots.get("error")},
        "security_txt": {"ok": security.get("ok"), "body": (security.get("body") or "")[:2000], "error": security.get("error")},
    }


def osint_favicon_hash(url: str) -> dict[str, Any]:
    """Download favicon and compute mmh3-like / sha256 (sha256 always; mmh3 if available)."""
    url = (url or "").strip()
    if not url.startswith("http"):
        url = "https://" + url
    parsed = urlparse(url)
    fav = f"{parsed.scheme}://{parsed.hostname}/favicon.ico"
    r = _get(fav, timeout=15, max_bytes=500_000)
    if not r.get("ok"):
        return {"ok": False, "error": r.get("error"), "url": fav}
    raw = (r.get("body") or "").encode("utf-8", errors="replace")
    # body was decoded as text — re-fetch binary
    try:
        req = Request(fav, headers={"User-Agent": UA})
        with urlopen(req, timeout=15) as resp:
            raw = resp.read(500_000)
    except Exception as e:
        return {"ok": False, "error": str(e)}
    sha = hashlib.sha256(raw).hexdigest()
    out = {"ok": True, "favicon": fav, "size": len(raw), "sha256": sha}
    try:
        import mmh3  # type: ignore
        import base64
        b64 = base64.encodebytes(raw)
        out["mmh3"] = mmh3.hash(b64)
    except Exception:
        out["mmh3"] = None
        out["note"] = "mmh3 optional; sha256 provided"
    return out


def osint_ssl_cert(host: str, port: int = 443) -> dict[str, Any]:
    host = (host or "").strip()
    if host.startswith("http"):
        host = urlparse(host).hostname or host
    port = int(port or 443)
    try:
        ctx = ssl.create_default_context()
        with socket.create_connection((host, port), timeout=12) as sock:
            with ctx.wrap_socket(sock, server_hostname=host) as ssock:
                cert = ssock.getpeercert()
                cipher = ssock.cipher()
                ver = ssock.version()
        subject = dict(x[0] for x in (cert.get("subject") or ()))
        issuer = dict(x[0] for x in (cert.get("issuer") or ()))
        sans = [f"{a}:{b}" for a, b in (cert.get("subjectAltName") or [])][:40]
        return {
            "ok": True,
            "host": host,
            "port": port,
            "tls": ver,
            "cipher": cipher,
            "subject": subject,
            "issuer": issuer,
            "notBefore": cert.get("notBefore"),
            "notAfter": cert.get("notAfter"),
            "san": sans,
        }
    except Exception as e:
        return {"ok": False, "error": str(e), "host": host}


# ---------- people / accounts (public only) ----------

def osint_email_full(email: str) -> dict[str, Any]:
    email = (email or "").strip().lower()
    if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
        return {"ok": False, "error": "invalid email"}
    local, domain = email.split("@", 1)
    dns = osint_dns_all(domain)
    # Gravatar hash
    ghash = hashlib.md5(email.encode("utf-8")).hexdigest()
    gravatar = f"https://www.gravatar.com/avatar/{ghash}?d=404"
    g = _get(gravatar, timeout=10, max_bytes=1000)
    return {
        "ok": True,
        "email": email,
        "local": local,
        "domain": domain,
        "dns": dns,
        "gravatar": {"url": gravatar, "exists": g.get("status") == 200},
        "note": "No breach-database queries (policy).",
    }


_SOCIAL = {
    "github": "https://github.com/{u}",
    "twitter": "https://twitter.com/{u}",
    "x": "https://x.com/{u}",
    "instagram": "https://www.instagram.com/{u}/",
    "reddit": "https://www.reddit.com/user/{u}",
    "linkedin": "https://www.linkedin.com/in/{u}",
    "youtube": "https://www.youtube.com/@{u}",
    "tiktok": "https://www.tiktok.com/@{u}",
    "telegram": "https://t.me/{u}",
    "medium": "https://medium.com/@{u}",
    "pinterest": "https://www.pinterest.com/{u}/",
    "twitch": "https://www.twitch.tv/{u}",
    "keybase": "https://keybase.io/{u}",
    "hackernews": "https://news.ycombinator.com/user?id={u}",
}


def osint_username_full(username: str, timeout: float = 6.0) -> dict[str, Any]:
    u = (username or "").strip().lstrip("@")
    if not u or len(u) > 40:
        return {"ok": False, "error": "username required"}
    results = []

    def check(platform: str, url: str) -> dict[str, Any]:
        try:
            req = Request(url, headers={"User-Agent": UA})
            with urlopen(req, timeout=timeout) as resp:
                code = getattr(resp, "status", None) or resp.getcode()
                return {"platform": platform, "url": url, "status": int(code), "exists": 200 <= int(code) < 400}
        except Exception as e:
            err = str(e)
            # 404 often in error string
            exists = False
            code = None
            if "404" in err:
                code = 404
            elif "403" in err:
                code = 403
            return {"platform": platform, "url": url, "status": code, "exists": exists, "error": err[:120]}

    with ThreadPoolExecutor(max_workers=10) as ex:
        futs = {ex.submit(check, p, tmpl.format(u=u)): p for p, tmpl in _SOCIAL.items()}
        for fut in as_completed(futs):
            results.append(fut.result())
    found = [r for r in results if r.get("exists")]
    return {
        "ok": True,
        "username": u,
        "checked": len(results),
        "found_count": len(found),
        "found": found,
        "all": sorted(results, key=lambda x: x.get("platform") or ""),
    }


def osint_phone_basic(number: str) -> dict[str, Any]:
    """Basic E.164-ish parse without carrier lookup APIs."""
    n = re.sub(r"[^\d+]", "", (number or "").strip())
    if len(re.sub(r"\D", "", n)) < 8:
        return {"ok": False, "error": "number too short"}
    digits = re.sub(r"\D", "", n)
    return {
        "ok": True,
        "input": number,
        "digits": digits,
        "length": len(digits),
        "possible_e164": n if n.startswith("+") else f"+{digits}",
        "note": "No live carrier/HLR lookup — format only.",
    }


# ---------- search / archive ----------

def osint_reddit_search(query: str, limit: int = 8) -> dict[str, Any]:
    query = (query or "").strip()
    if not query:
        return {"ok": False, "error": "query required"}
    limit = max(1, min(int(limit or 8), 15))
    url = f"https://www.reddit.com/search.json?q={quote(query)}&limit={limit}"
    r = _json_get(url, timeout=20)
    if not r.get("ok"):
        return r
    children = ((r.get("data") or {}).get("data") or {}).get("children") or []
    # reddit structure data.data.children
    if not children:
        children = ((r.get("data") or {}).get("children") or [])
    items = []
    for ch in children[:limit]:
        d = ch.get("data") if isinstance(ch, dict) else {}
        items.append({
            "title": d.get("title"),
            "subreddit": d.get("subreddit"),
            "url": f"https://reddit.com{d.get('permalink')}" if d.get("permalink") else d.get("url"),
            "score": d.get("score"),
            "created": d.get("created_utc"),
        })
    return {"ok": True, "query": query, "count": len(items), "results": items}


def osint_wikipedia(query: str, lang: str = "en") -> dict[str, Any]:
    query = (query or "").strip()
    lang = (lang or "en").strip()[:5]
    if not query:
        return {"ok": False, "error": "query required"}
    url = f"https://{lang}.wikipedia.org/w/api.php?action=opensearch&search={quote(query)}&limit=5&format=json"
    r = _get(url, timeout=15)
    if not r.get("ok"):
        return r
    try:
        data = json.loads(r.get("body") or "[]")
        titles = data[1] if len(data) > 1 else []
        descs = data[2] if len(data) > 2 else []
        links = data[3] if len(data) > 3 else []
        items = [{"title": titles[i], "description": descs[i] if i < len(descs) else "", "url": links[i] if i < len(links) else ""} for i in range(len(titles))]
        return {"ok": True, "query": query, "lang": lang, "results": items}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ---------- dossier / report ----------

def osint_dossier(target: str) -> dict[str, Any]:
    """Full passive dossier — auto-detects type and runs relevant modules."""
    t = (target or "").strip()
    if not t:
        return {"ok": False, "error": "target required"}
    dossier: dict[str, Any] = {
        "ok": True,
        "target": t,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "modules": {},
    }

    # URL
    if t.startswith("http://") or t.startswith("https://"):
        dossier["type"] = "url"
        host = urlparse(t).hostname or ""
        dossier["modules"]["http"] = osint_http_probe(t)
        dossier["modules"]["robots"] = osint_robots(host or t)
        dossier["modules"]["ssl"] = osint_ssl_cert(host) if host else {}
        dossier["modules"]["dns"] = osint_dns_all(host) if host else {}
        dossier["modules"]["rdap"] = osint_rdap(host) if host else {}
        return dossier

    # email
    if "@" in t and re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", t):
        dossier["type"] = "email"
        dossier["modules"]["email"] = osint_email_full(t)
        return dossier

    # phone
    if re.search(r"\d{8,}", re.sub(r"\D", "", t)) and not re.search(r"[a-zA-Z]", t):
        dossier["type"] = "phone"
        dossier["modules"]["phone"] = osint_phone_basic(t)
        return dossier

    # IP
    if re.match(r"^\d{1,3}(\.\d{1,3}){3}$", t):
        dossier["type"] = "ip"
        dossier["modules"]["geo"] = osint_ip_geo(t)
        dossier["modules"]["reverse_dns"] = osint_reverse_dns(t)
        dossier["modules"]["rdap"] = osint_rdap(t)
        dossier["modules"]["asn"] = osint_asn(t)
        return dossier

    # domain
    if "." in t and " " not in t and not t.startswith("@"):
        dossier["type"] = "domain"
        dossier["modules"]["dns"] = osint_dns_all(t)
        dossier["modules"]["rdap"] = osint_rdap(t)
        dossier["modules"]["whois"] = osint_whois_text(t)
        dossier["modules"]["ssl"] = osint_ssl_cert(t)
        dossier["modules"]["http"] = osint_http_probe(t)
        dossier["modules"]["robots"] = osint_robots(t)
        # crt.sh if advanced available
        try:
            from osint_advanced import osint_crtsh_subdomains
            dossier["modules"]["crtsh"] = osint_crtsh_subdomains(t, max_rows=80)
        except Exception as e:
            dossier["modules"]["crtsh"] = {"ok": False, "error": str(e)}
        return dossier

    # free text → web search dossier
    if " " in t.strip():
        dossier["type"] = "search"
        dossier["modules"]["web"] = osint_google(t, max_results=10)
        try:
            dossier["modules"]["wikipedia"] = osint_wikipedia(t)
        except Exception:
            pass
        return dossier

    # username
    dossier["type"] = "username"
    dossier["modules"]["profiles"] = osint_username_full(t.lstrip("@"))
    try:
        from osint_tools import osint_github_user
        dossier["modules"]["github"] = osint_github_user(t.lstrip("@"))
    except Exception:
        pass
    return dossier




def osint_google(query: str, max_results: int = 8) -> dict[str, Any]:
    """Web search optimized for OSINT (works without local model).

    Uses DuckDuckGo HTML + Bing HTML mirrors (Google SERP often blocks bots).
    Returns title/url/snippet list suitable for reports.
    """
    query = (query or "").strip()
    if not query:
        return {"ok": False, "error": "query required"}
    max_results = max(1, min(int(max_results or 8), 15))
    results = []
    # 1) DuckDuckGo
    ddg = _get(f"https://html.duckduckgo.com/html/?q={quote(query)}", timeout=20)
    if ddg.get("ok"):
        body = ddg.get("body") or ""
        for m in re.finditer(
            r'class="result__a"[^>]*href="([^"]+)"[^>]*>(.*?)</a>.*?class="result__snippet"[^>]*>(.*?)</',
            body,
            re.I | re.S,
        ):
            href, title, snip = m.group(1), re.sub(r"<[^>]+>", "", m.group(2)), re.sub(r"<[^>]+>", "", m.group(3))
            href = href.replace("&amp;", "&")
            if "duckduckgo.com" in href:
                continue
            results.append({"title": title.strip()[:200], "url": href, "snippet": snip.strip()[:400], "source": "ddg"})
            if len(results) >= max_results:
                break
        if not results:
            for m in re.finditer(r'href="(https?://[^"]+)"[^>]*>([^<]{10,160})</a>', body):
                href, title = m.group(1), m.group(2).strip()
                if any(x in href for x in ("duckduckgo", "javascript:", "microsoft.com")):
                    continue
                results.append({"title": title[:200], "url": href, "snippet": "", "source": "ddg"})
                if len(results) >= max_results:
                    break
    # 2) Bing fallback
    if len(results) < 3:
        bing = _get(f"https://www.bing.com/search?q={quote(query)}", timeout=20)
        if bing.get("ok"):
            body = bing.get("body") or ""
            for m in re.finditer(r'<li class="b_algo".*?<a href="(https?://[^"]+)"[^>]*>(.*?)</a>.*?<p>(.*?)</p>', body, re.I | re.S):
                href = m.group(1)
                title = re.sub(r"<[^>]+>", "", m.group(2)).strip()
                snip = re.sub(r"<[^>]+>", "", m.group(3)).strip()
                if href not in [r["url"] for r in results]:
                    results.append({"title": title[:200], "url": href, "snippet": snip[:400], "source": "bing"})
                if len(results) >= max_results:
                    break
    return {
        "ok": bool(results),
        "query": query,
        "engine": "ddg+bing",
        "count": len(results),
        "results": results[:max_results],
        "note": "Direct Google SERP is often blocked for bots; DDG/Bing public HTML used.",
    }


def osint_web_search(query: str, max_results: int = 8) -> dict[str, Any]:
    return osint_google(query, max_results=max_results)

OSINT_PLUS_TOOLS: dict[str, Any] = {
    "osint_dns_all": osint_dns_all,
    "osint_reverse_dns": osint_reverse_dns,
    "osint_rdap": osint_rdap,
    "osint_whois": osint_whois_text,
    "osint_ip_geo": osint_ip_geo,
    "osint_asn": osint_asn,
    "osint_http_probe": osint_http_probe,
    "osint_robots": osint_robots,
    "osint_favicon_hash": osint_favicon_hash,
    "osint_ssl_cert": osint_ssl_cert,
    "osint_email_full": osint_email_full,
    "osint_username_full": osint_username_full,
    "osint_phone_basic": osint_phone_basic,
    "osint_reddit": osint_reddit_search,
    "osint_wikipedia": osint_wikipedia,
    "osint_dossier": osint_dossier,
    # aliases used by UI / natural language
    "osint_full": osint_dossier,
    "osint_investigate": osint_dossier,
    "osint_google": osint_google,
    "osint_web_search": osint_web_search,
    "google_search": osint_google,
    "web_search": osint_web_search,
}

