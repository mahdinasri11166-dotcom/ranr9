# -*- coding: utf-8 -*-
"""
Cyber / security specialist tools (defensive · passive OSINT · local forensics).

Intended for:
- analyzing your own systems and authorized assets
- blue-team style visibility, DNS/HTTP checks, hashing, local net inventory
- structured security notes/reports

Not included: brute-force, exploit delivery, mass aggressive scanning of third parties.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import socket
import ssl
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from config_loader import ROOT, workspace_dir

try:
    from proxy_pool import opener_for, load_config as load_proxy_cfg
except Exception:
    def opener_for(proxy=None):
        return None, None
    def load_proxy_cfg():
        return {"enabled": False}

UA = "GGUF-Runner-Cyber/1.0 (+defensive-security)"


def _reports_dir() -> Path:
    d = workspace_dir() / "security_reports"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _is_private_host(host: str) -> bool:
    host = (host or "").strip().lower()
    if host in ("localhost", "127.0.0.1", "::1"):
        return True
    try:
        ip = socket.gethostbyname(host)
    except Exception:
        return False
    parts = ip.split(".")
    if len(parts) != 4:
        return False
    a, b = int(parts[0]), int(parts[1])
    if a == 10 or a == 127:
        return True
    if a == 192 and b == 168:
        return True
    if a == 172 and 16 <= b <= 31:
        return True
    return False


# ---------- hashing / file ----------

def cyber_hash_file(path: str, algorithms: str = "sha256,md5") -> dict[str, Any]:
    p = Path(path).expanduser()
    if not p.is_file():
        return {"ok": False, "error": f"file not found: {path}"}
    algos = [a.strip().lower() for a in (algorithms or "sha256,md5").split(",") if a.strip()]
    allowed = {"md5", "sha1", "sha256", "sha512"}
    hobjs = {}
    for a in algos:
        if a not in allowed:
            continue
        hobjs[a] = hashlib.new(a)
    if not hobjs:
        return {"ok": False, "error": "no valid algorithms"}
    size = 0
    with p.open("rb") as f:
        while True:
            chunk = f.read(1024 * 1024)
            if not chunk:
                break
            size += len(chunk)
            for h in hobjs.values():
                h.update(chunk)
    return {
        "ok": True,
        "path": str(p.resolve()),
        "size": size,
        "hashes": {k: v.hexdigest() for k, v in hobjs.items()},
    }


def cyber_file_meta(path: str) -> dict[str, Any]:
    p = Path(path).expanduser()
    if not p.exists():
        return {"ok": False, "error": "not found"}
    st = p.stat()
    out: dict[str, Any] = {
        "ok": True,
        "path": str(p.resolve()),
        "is_file": p.is_file(),
        "is_dir": p.is_dir(),
        "size": st.st_size,
        "mtime": datetime.fromtimestamp(st.st_mtime).isoformat(timespec="seconds"),
        "ctime": datetime.fromtimestamp(st.st_ctime).isoformat(timespec="seconds"),
    }
    if p.is_file() and p.suffix.lower() in {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"}:
        try:
            from PIL import Image  # type: ignore
            img = Image.open(p)
            out["image"] = {"format": img.format, "size": img.size, "mode": img.mode}
        except Exception as e:
            out["image_error"] = str(e)
    return out


# ---------- local network / process visibility ----------

def cyber_net_local() -> dict[str, Any]:
    """Local interfaces + listening ports (this machine)."""
    info: dict[str, Any] = {"ok": True, "hostname": socket.gethostname(), "time": datetime.now().isoformat(timespec="seconds")}
    try:
        import psutil  # type: ignore
        addrs = {}
        for name, lst in psutil.net_if_addrs().items():
            addrs[name] = [{"family": str(a.family), "address": a.address, "netmask": a.netmask} for a in lst]
        info["interfaces"] = addrs
        listeners = []
        for c in psutil.net_connections(kind="inet"):
            if c.status == "LISTEN":
                la = c.laddr
                listeners.append({
                    "pid": c.pid,
                    "laddr": f"{getattr(la, 'ip', '')}:{getattr(la, 'port', '')}",
                })
        info["listening"] = listeners[:80]
        info["listening_count"] = len(listeners)
    except Exception as e:
        info["psutil_error"] = str(e)
        if os.name == "nt":
            r = subprocess.run("ipconfig /all", shell=True, capture_output=True, text=True, timeout=20, encoding="utf-8", errors="replace")
            info["ipconfig"] = (r.stdout or "")[:4000]
            r2 = subprocess.run("netstat -ano", shell=True, capture_output=True, text=True, timeout=20, encoding="utf-8", errors="replace")
            lines = [ln for ln in (r2.stdout or "").splitlines() if "LISTENING" in ln.upper()][:60]
            info["listening_raw"] = lines
        else:
            r = subprocess.run(["ip", "-br", "addr"], capture_output=True, text=True, timeout=10)
            info["ip"] = r.stdout[:2000]
    return info


def cyber_process_security(limit: int = 40) -> dict[str, Any]:
    """Top processes — visibility for local triage."""
    limit = max(1, min(int(limit or 40), 100))
    try:
        import psutil  # type: ignore
        rows = []
        for p in psutil.process_iter(["pid", "name", "username", "exe", "cmdline", "cpu_percent", "memory_percent"]):
            try:
                info = p.info
                rows.append({
                    "pid": info.get("pid"),
                    "name": info.get("name"),
                    "user": info.get("username"),
                    "exe": info.get("exe"),
                    "cmd": " ".join((info.get("cmdline") or [])[:12])[:200],
                    "cpu": info.get("cpu_percent") or 0,
                    "mem": round(float(info.get("memory_percent") or 0), 2),
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        rows.sort(key=lambda x: float(x.get("mem") or 0), reverse=True)
        return {"ok": True, "processes": rows[:limit], "count": len(rows)}
    except Exception as e:
        if os.name == "nt":
            r = subprocess.run("tasklist /v", shell=True, capture_output=True, text=True, timeout=30, encoding="utf-8", errors="replace")
            return {"ok": True, "raw": (r.stdout or "")[:5000], "note": str(e)}
        return {"ok": False, "error": str(e)}


# ---------- DNS / HTTP / TLS (passive) ----------

def cyber_dns_full(domain: str) -> dict[str, Any]:
    domain = (domain or "").strip().lower().rstrip(".")
    if not domain or " " in domain:
        return {"ok": False, "error": "domain required"}
    out: dict[str, Any] = {"ok": True, "domain": domain, "records": {}}
    # A via socket
    try:
        out["records"]["A"] = sorted({ai[4][0] for ai in socket.getaddrinfo(domain, None, socket.AF_INET)})
    except Exception as e:
        out["records"]["A_error"] = str(e)
    try:
        out["records"]["AAAA"] = sorted({ai[4][0] for ai in socket.getaddrinfo(domain, None, socket.AF_INET6)})
    except Exception:
        out["records"]["AAAA"] = []
    # dig/nslookup if available
    for rtype in ("MX", "NS", "TXT", "CNAME", "SOA"):
        if os.name == "nt":
            r = subprocess.run(
                f'nslookup -type={rtype} {domain}',
                shell=True, capture_output=True, text=True, timeout=15,
                encoding="utf-8", errors="replace",
            )
            out["records"][rtype] = ((r.stdout or "") + (r.stderr or ""))[:1500]
        else:
            r = subprocess.run(["dig", "+short", rtype, domain], capture_output=True, text=True, timeout=15)
            out["records"][rtype] = (r.stdout or "").strip()[:1500]
    return out


def cyber_http_headers(url: str, timeout: int = 20) -> dict[str, Any]:
    url = (url or "").strip()
    if not url.startswith("http"):
        url = "https://" + url
    try:
        req = Request(url, headers={"User-Agent": UA}, method="GET")
        opener = None
        if (load_proxy_cfg() or {}).get("enabled"):
            opener, _ = opener_for()
        if opener:
            resp = opener.open(req, timeout=timeout)
        else:
            resp = urlopen(req, timeout=timeout)
        with resp:
            status = getattr(resp, "status", None) or resp.getcode()
            headers = {k: v for k, v in list(resp.headers.items())[:60]}
            body = resp.read(2000)
        sec = {k: headers.get(k) for k in (
            "Strict-Transport-Security", "Content-Security-Policy", "X-Frame-Options",
            "X-Content-Type-Options", "Referrer-Policy", "Permissions-Policy", "Server",
        ) if headers.get(k)}
        return {
            "ok": True,
            "url": url,
            "status": int(status),
            "headers": headers,
            "security_headers": sec,
            "body_preview_len": len(body),
        }
    except Exception as e:
        return {"ok": False, "error": str(e), "url": url}


def cyber_tls_info(host: str, port: int = 443) -> dict[str, Any]:
    host = (host or "").strip()
    if host.startswith("http"):
        host = urlparse(host).hostname or host
    port = int(port or 443)
    if not host:
        return {"ok": False, "error": "host required"}
    try:
        ctx = ssl.create_default_context()
        with socket.create_connection((host, port), timeout=12) as sock:
            with ctx.wrap_socket(sock, server_hostname=host) as ssock:
                cert = ssock.getpeercert()
                cipher = ssock.cipher()
                ver = ssock.version()
        subject = dict(x[0] for x in (cert.get("subject") or ()))
        issuer = dict(x[0] for x in (cert.get("issuer") or ()))
        sans = []
        for typ, val in cert.get("subjectAltName") or []:
            sans.append(f"{typ}:{val}")
        return {
            "ok": True,
            "host": host,
            "port": port,
            "tls_version": ver,
            "cipher": cipher,
            "subject": subject,
            "issuer": issuer,
            "notBefore": cert.get("notBefore"),
            "notAfter": cert.get("notAfter"),
            "san": sans[:30],
        }
    except Exception as e:
        return {"ok": False, "error": str(e), "host": host, "port": port}


def cyber_port_check(host: str, ports: str = "22,80,443,3389,8080", timeout: float = 1.0) -> dict[str, Any]:
    """TCP connect check for a short list of ports (authorized targets only recommended)."""
    host = (host or "").strip()
    if not host:
        return {"ok": False, "error": "host required"}
    port_list = []
    for part in (ports or "").split(","):
        part = part.strip()
        if not part:
            continue
        try:
            port_list.append(int(part))
        except ValueError:
            continue
    port_list = port_list[:30]
    results = []
    for port in port_list:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(max(0.2, min(float(timeout or 1.0), 5.0)))
        try:
            code = s.connect_ex((host, port))
            results.append({"port": port, "open": code == 0})
        except Exception as e:
            results.append({"port": port, "open": False, "error": str(e)})
        finally:
            try:
                s.close()
            except Exception:
                pass
    return {
        "ok": True,
        "host": host,
        "private_or_local": _is_private_host(host),
        "results": results,
        "note": "Use only on systems you own or are authorized to test.",
    }


def cyber_nmap(target: str = "127.0.0.1", args: str = "-sT -T3 --top-ports 20") -> dict[str, Any]:
    """Run system nmap if installed. Default targets localhost-style checks."""
    target = (target or "127.0.0.1").strip()
    # soft guard: refuse obvious broadcast/mass patterns
    if any(x in target for x in ("*", "0.0.0.0/0", "1/1")):
        return {"ok": False, "blocked": True, "error": "overly broad target refused"}
    nmap = shutil_which("nmap")
    if not nmap:
        return {"ok": False, "error": "nmap not found on PATH", "hint": "Install Nmap and retry"}
    cmd = [nmap] + (args or "-sT -T3 --top-ports 20").split() + [target]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=120, encoding="utf-8", errors="replace")
        return {
            "ok": r.returncode == 0,
            "cmd": " ".join(cmd),
            "stdout": (r.stdout or "")[:8000],
            "stderr": (r.stderr or "")[:2000],
            "returncode": r.returncode,
            "note": "Authorized testing only.",
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}


def shutil_which(cmd: str) -> str | None:
    from shutil import which
    return which(cmd)


# ---------- Windows logs (defensive) ----------

def cyber_win_events(log: str = "Security", newest: int = 20) -> dict[str, Any]:
    if os.name != "nt":
        return {"ok": False, "error": "Windows only"}
    newest = max(1, min(int(newest or 20), 50))
    log = (log or "Security").strip()
    # PowerShell Get-WinEvent
    ps = (
        f"Get-WinEvent -LogName '{log}' -MaxEvents {newest} | "
        "Select-Object TimeCreated,Id,LevelDisplayName,ProviderName,Message | "
        "ConvertTo-Json -Depth 3"
    )
    try:
        r = subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps],
            capture_output=True, text=True, timeout=60, encoding="utf-8", errors="replace",
        )
        text = (r.stdout or "").strip()
        data = None
        try:
            data = json.loads(text) if text else None
        except Exception:
            data = None
        return {
            "ok": r.returncode == 0 or bool(text),
            "log": log,
            "events": data if data is not None else text[:6000],
            "stderr": (r.stderr or "")[:1000],
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ---------- report ----------

def cyber_report(title: str, findings: str | dict | list = "", severity: str = "info") -> dict[str, Any]:
    title = (title or "security-note").strip()
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe = re.sub(r"[^\w\u0600-\u06FF\-]+", "_", title)[:60] or "report"
    path = _reports_dir() / f"{safe}_{ts}.md"
    if isinstance(findings, (dict, list)):
        body_findings = json.dumps(findings, ensure_ascii=False, indent=2)
    else:
        body_findings = str(findings or "")
    md = (
        f"# {title}\n\n"
        f"- Time: {datetime.now().isoformat(timespec='seconds')}\n"
        f"- Severity: {severity}\n"
        f"- Host: {socket.gethostname()}\n\n"
        f"## Findings\n\n```\n{body_findings}\n```\n"
    )
    path.write_text(md, encoding="utf-8")
    return {"ok": True, "path": str(path), "title": title}


def cyber_quick_audit(url_or_domain: str = "") -> dict[str, Any]:
    """One-shot passive audit: DNS + headers + TLS for a domain/URL you are allowed to test."""
    target = (url_or_domain or "").strip()
    if not target:
        return {"ok": False, "error": "url_or_domain required"}
    host = target
    if target.startswith("http"):
        host = urlparse(target).hostname or target
        url = target
    else:
        url = "https://" + target
        host = target
    dns = cyber_dns_full(host)
    headers = cyber_http_headers(url)
    tls = cyber_tls_info(host)
    local = cyber_net_local()
    summary = {
        "target": target,
        "dns_ok": dns.get("ok"),
        "http_status": headers.get("status"),
        "security_headers": headers.get("security_headers"),
        "tls": {k: tls.get(k) for k in ("tls_version", "notAfter", "issuer") if tls.get("ok")},
        "local_listening_count": local.get("listening_count"),
    }
    report = cyber_report(
        f"audit-{host}",
        {"summary": summary, "dns": dns, "headers": headers, "tls": tls},
        severity="info",
    )
    return {"ok": True, "summary": summary, "report": report, "dns": dns, "headers": headers, "tls": tls}


CYBER_TOOLS: dict[str, Any] = {
    "cyber_hash_file": cyber_hash_file,
    "cyber_file_meta": cyber_file_meta,
    "cyber_net_local": cyber_net_local,
    "cyber_process_security": cyber_process_security,
    "cyber_dns_full": cyber_dns_full,
    "cyber_http_headers": cyber_http_headers,
    "cyber_tls_info": cyber_tls_info,
    "cyber_port_check": cyber_port_check,
    "cyber_nmap": cyber_nmap,
    "cyber_win_events": cyber_win_events,
    "cyber_report": cyber_report,
    "cyber_quick_audit": cyber_quick_audit,
    # aliases
    "hash_file": cyber_hash_file,
    "tls_info": cyber_tls_info,
    "dns_lookup": cyber_dns_full,
    "security_audit": cyber_quick_audit,
}
