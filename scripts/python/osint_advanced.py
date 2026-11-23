# -*- coding: utf-8 -*-
"""
Advanced passive OSINT: email DNS, crt.sh subdomains, domain graph,
username parallel+cache+confidence, file metadata.
No brute-force, no active exploitation, no breach dumps.
"""
from __future__ import annotations

import concurrent.futures
import hashlib
import json
import re
import socket
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote
from urllib.request import Request, urlopen

from config_loader import ROOT, workspace_dir

UA = "GGUF-Runner-OSINT/2.5 (+passive-research)"
TIMEOUT = 12
CACHE_DIR = workspace_dir() / "osint" / "cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)


def _http_get(url: str, timeout: int = TIMEOUT) -> tuple[int, str]:
    req = Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
    try:
        with urlopen(req, timeout=timeout) as r:
            return r.status, r.read(1_500_000).decode("utf-8", errors="replace")
    except Exception as e:
        code = getattr(e, "code", 0) or 0
        body = ""
        try:
            if hasattr(e, "read"):
                body = e.read(80_000).decode("utf-8", errors="replace")
        except Exception:
            body = str(e)
        return code, body or str(e)


def _cache_get(key: str, max_age_sec: int = 86400) -> Any | None:
    p = CACHE_DIR / (hashlib.sha256(key.encode()).hexdigest()[:40] + ".json")
    if not p.exists():
        return None
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        if time.time() - data.get("_ts", 0) > max_age_sec:
            return None
        return data.get("value")
    except Exception:
        return None


def _cache_set(key: str, value: Any) -> None:
    p = CACHE_DIR / (hashlib.sha256(key.encode()).hexdigest()[:40] + ".json")
    p.write_text(json.dumps({"_ts": time.time(), "value": value}, ensure_ascii=False), encoding="utf-8")


# ---------- Email: MX / SPF / DMARC (no breach) ----------

def osint_email_dns(email: str) -> dict[str, Any]:
    email = (email or "").strip().lower()
    if not re.match(r"^[a-z0-9._%+\-]+@[a-z0-9.\-]+\.[a-z]{2,}$", email):
        return {"ok": False, "error": "قالب ایمیل نامعتبر است"}
    local, domain = email.split("@", 1)
    out: dict[str, Any] = {
        "ok": True,
        "email": email,
        "local": local,
        "domain": domain,
        "mx": [],
        "spf": None,
        "dmarc": None,
        "txt": [],
        "notes": [],
    }
    # MX via dnspython if available, else socket heuristics + public DNS-over-HTTPS
    try:
        import dns.resolver  # type: ignore
        for rtype, key in (("MX", "mx"), ("TXT", "txt")):
            try:
                answers = dns.resolver.resolve(domain if rtype != "TXT" or key == "txt" else domain, rtype)
                rows = []
                for a in answers:
                    rows.append(a.to_text())
                if rtype == "MX":
                    out["mx"] = sorted(rows)
                else:
                    out["txt"] = rows
            except Exception as e:
                out["notes"].append(f"{rtype}: {e}")
        try:
            dmarc_answers = dns.resolver.resolve(f"_dmarc.{domain}", "TXT")
            out["dmarc"] = [a.to_text() for a in dmarc_answers]
        except Exception as e:
            out["notes"].append(f"DMARC: {e}")
    except ImportError:
        # DoH Cloudflare
        for name, qtype in ((domain, "MX"), (domain, "TXT"), (f"_dmarc.{domain}", "TXT")):
            url = f"https://cloudflare-dns.com/dns-query?name={quote(name)}&type={qtype}"
            code, body = _http_get(url, timeout=10)
            # Accept header needed for JSON — retry
            req = Request(url, headers={"User-Agent": UA, "Accept": "application/dns-json"})
            try:
                with urlopen(req, timeout=10) as r:
                    data = json.loads(r.read().decode())
            except Exception as e:
                out["notes"].append(f"DoH {qtype} {name}: {e}")
                continue
            answers = data.get("Answer") or []
            texts = [a.get("data", "") for a in answers]
            if qtype == "MX" and name == domain:
                out["mx"] = texts
            elif name.startswith("_dmarc"):
                out["dmarc"] = texts
            else:
                out["txt"].extend(texts)

    for t in out.get("txt") or []:
        if "v=spf1" in t.lower():
            out["spf"] = t
    if out.get("dmarc"):
        out["dmarc"] = out["dmarc"] if isinstance(out["dmarc"], list) else [out["dmarc"]]
    out["summary"] = {
        "has_mx": bool(out["mx"]),
        "has_spf": bool(out["spf"]),
        "has_dmarc": bool(out["dmarc"]),
    }
    return out


# ---------- crt.sh subdomains + domain graph ----------

def osint_crtsh_subdomains(domain: str, max_rows: int = 200) -> dict[str, Any]:
    domain = (domain or "").strip().lower().removeprefix("http://").removeprefix("https://").split("/")[0]
    if not domain or "." not in domain:
        return {"ok": False, "error": "دامنه نامعتبر"}
    cache_key = f"crtsh:{domain}"
    cached = _cache_get(cache_key, max_age_sec=43200)
    if cached:
        cached["from_cache"] = True
        return cached

    url = f"https://crt.sh/?q=%25.{quote(domain)}&output=json"
    code, body = _http_get(url, timeout=30)
    if code != 200 and not body.strip().startswith("["):
        return {"ok": False, "error": f"crt.sh status={code}", "body_preview": body[:300]}
    try:
        rows = json.loads(body)
    except json.JSONDecodeError:
        return {"ok": False, "error": "پاسخ crt.sh JSON نبود", "body_preview": body[:300]}

    names: set[str] = set()
    for row in rows[: max_rows * 3]:
        nv = row.get("name_value") or ""
        for part in nv.split("\n"):
            part = part.strip().lower().lstrip("*.")
            if part.endswith(domain) or part == domain:
                if re.match(r"^[a-z0-9.-]+$", part):
                    names.add(part)
        if len(names) >= max_rows:
            break

    subs = sorted(names)
    # simple graph: apex -> each subdomain
    nodes = [{"id": domain, "type": "apex"}] + [{"id": s, "type": "subdomain"} for s in subs if s != domain]
    edges = [{"from": domain, "to": s, "rel": "certificate_san"} for s in subs if s != domain]
    result = {
        "ok": True,
        "domain": domain,
        "subdomains": subs,
        "count": len(subs),
        "graph": {"nodes": nodes, "edges": edges},
        "source": "crt.sh",
        "from_cache": False,
    }
    _cache_set(cache_key, result)
    return result


def osint_domain_graph(domain: str) -> dict[str, Any]:
    """Combine DNS + crt.sh into one relationship graph structure."""
    from osint_tools import osint_domain_info

    domain = (domain or "").strip().lower().removeprefix("http://").removeprefix("https://").split("/")[0]
    if not domain or "." not in domain:
        return {"ok": False, "error": "دامنه نامعتبر"}
    base = osint_domain_info(domain)
    crt = osint_crtsh_subdomains(domain)
    nodes = [{"id": domain, "type": "apex", "dns": base.get("dns"), "tls": base.get("tls")}]
    edges = []
    for ip in (base.get("dns") or {}).get("addresses") or []:
        nodes.append({"id": ip, "type": "ip"})
        edges.append({"from": domain, "to": ip, "rel": "resolves_to"})
    if crt.get("ok"):
        for s in crt.get("subdomains") or []:
            if s == domain:
                continue
            nodes.append({"id": s, "type": "subdomain"})
            edges.append({"from": domain, "to": s, "rel": "cert_san"})
    # dedupe nodes by id
    seen = set()
    uniq_nodes = []
    for n in nodes:
        if n["id"] not in seen:
            seen.add(n["id"])
            uniq_nodes.append(n)
    return {
        "ok": True,
        "domain": domain,
        "graph": {"nodes": uniq_nodes, "edges": edges},
        "subdomain_count": len([n for n in uniq_nodes if n["type"] == "subdomain"]),
        "sources": ["dns", "tls", "crt.sh"],
    }


# ---------- Username parallel + confidence + cache ----------

_PLATFORMS = [
    ("github", "https://github.com/{u}", ["page not found", "not found"]),
    ("gitlab", "https://gitlab.com/{u}", ["page not found"]),
    ("reddit", "https://www.reddit.com/user/{u}", ["page not found", "nobody"]),
    ("hackernews", "https://news.ycombinator.com/user?id={u}", ["no such user"]),
    ("keybase", "https://keybase.io/{u}", ["not found"]),
    ("medium", "https://medium.com/@{u}", ["404"]),
    ("aboutme", "https://about.me/{u}", ["not found", "404"]),
    ("linktree", "https://linktr.ee/{u}", ["page not found", "doesn't exist"]),
    ("steam", "https://steamcommunity.com/id/{u}", ["error", "not found"]),
]


def _check_one(platform: str, url_tpl: str, soft404: list[str], username: str) -> dict[str, Any]:
    url = url_tpl.format(u=quote(username))
    code, body = _http_get(url, timeout=8)
    low = body.lower()[:4000]
    soft = any(s in low for s in soft404)
    exists = code == 200 and not soft
    # confidence heuristic
    conf = 0.0
    if exists:
        conf = 0.75
        if platform in ("github", "gitlab") and username.lower() in low:
            conf = 0.9
        if len(body) > 5000:
            conf = min(0.95, conf + 0.1)
    elif code == 404:
        conf = 0.85  # confident not found
    elif code in (0, 429, 503):
        conf = 0.2
        exists = None  # unknown
    else:
        conf = 0.4
        exists = False
    return {
        "platform": platform,
        "url": url,
        "status": code,
        "exists": exists,
        "confidence": round(conf, 2),
    }


def osint_username_parallel(username: str, max_workers: int = 8) -> dict[str, Any]:
    u = (username or "").strip().lstrip("@")
    if not u or not re.match(r"^[\w.-]{2,39}$", u):
        return {"ok": False, "error": "نام کاربری نامعتبر (۲ تا ۳۹ کاراکتر)"}
    cache_key = f"userpar:{u}"
    cached = _cache_get(cache_key, max_age_sec=21600)
    if cached:
        cached["from_cache"] = True
        return cached

    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as ex:
        futs = [ex.submit(_check_one, p, tpl, soft, u) for p, tpl, soft in _PLATFORMS]
        for f in concurrent.futures.as_completed(futs):
            try:
                results.append(f.result())
            except Exception as e:
                results.append({"platform": "?", "error": str(e), "exists": None, "confidence": 0})

    found = [r for r in results if r.get("exists") is True]
    missing = [r for r in results if r.get("exists") is False]
    unknown = [r for r in results if r.get("exists") is None]
    out = {
        "ok": True,
        "username": u,
        "found": found,
        "not_found": missing,
        "unknown": unknown,
        "found_count": len(found),
        "avg_confidence_found": round(sum(r["confidence"] for r in found) / len(found), 2) if found else 0,
        "from_cache": False,
        "disclaimer": "فقط HTTP عمومی — مالکیت را اثبات نمی‌کند",
    }
    _cache_set(cache_key, out)
    return out


# ---------- Metadata: image EXIF + PDF ----------

def osint_file_metadata(path: str) -> dict[str, Any]:
    """Read metadata from a file under workspace (or absolute if still under workspace)."""
    ws = workspace_dir().resolve()
    p = Path(path)
    if not p.is_absolute():
        p = (ws / path).resolve()
    else:
        p = p.resolve()
    if not str(p).startswith(str(ws)):
        return {"ok": False, "error": "فقط فایل‌های داخل workspace مجازند"}
    if not p.exists() or not p.is_file():
        return {"ok": False, "error": "فایل پیدا نشد"}

    out: dict[str, Any] = {
        "ok": True,
        "path": str(p.relative_to(ws)),
        "size": p.stat().st_size,
        "suffix": p.suffix.lower(),
    }
    suf = p.suffix.lower()
    if suf in (".png", ".jpg", ".jpeg", ".webp", ".tiff", ".tif"):
        try:
            from PIL import Image
            from PIL.ExifTags import TAGS
            img = Image.open(p)
            out["image"] = {"format": img.format, "size": img.size, "mode": img.mode}
            exif_raw = getattr(img, "_getexif", lambda: None)() or {}
            if not exif_raw and hasattr(img, "getexif"):
                exif_raw = dict(img.getexif())
            exif = {}
            for k, v in (exif_raw or {}).items():
                tag = TAGS.get(k, str(k))
                try:
                    exif[tag] = v if isinstance(v, (int, float, str)) else str(v)[:200]
                except Exception:
                    exif[tag] = repr(v)[:200]
            # strip GPS into structured if present
            out["exif"] = exif
            gps_keys = [k for k in exif if "gps" in k.lower()]
            out["has_gps_tags"] = bool(gps_keys)
        except Exception as e:
            out["image_error"] = str(e)
    elif suf == ".pdf":
        try:
            from pypdf import PdfReader
            reader = PdfReader(str(p))
            meta = reader.metadata or {}
            out["pdf"] = {
                "pages": len(reader.pages),
                "title": getattr(meta, "title", None) or meta.get("/Title") if isinstance(meta, dict) else None,
                "author": getattr(meta, "author", None) or (meta.get("/Author") if isinstance(meta, dict) else None),
                "creator": getattr(meta, "creator", None) or (meta.get("/Creator") if isinstance(meta, dict) else None),
                "producer": getattr(meta, "producer", None) or (meta.get("/Producer") if isinstance(meta, dict) else None),
                "subject": getattr(meta, "subject", None) or (meta.get("/Subject") if isinstance(meta, dict) else None),
            }
        except Exception as e:
            out["pdf_error"] = str(e)
    else:
        out["note"] = "برای این پسوند فقط اطلاعات فایل پایه استخراج شد"
    return out


# Registry
ADVANCED_OSINT = {
    "osint_email_dns": osint_email_dns,
    "osint_crtsh": osint_crtsh_subdomains,
    "osint_domain_graph": osint_domain_graph,
    "osint_username_parallel": osint_username_parallel,
    "osint_file_metadata": osint_file_metadata,
}
