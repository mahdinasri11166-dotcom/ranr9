# -*- coding: utf-8 -*-
"""Resumable multi-file downloader with progress and auto-retry.

- HTTP Range resume (.part + .meta.json)
- Retries forever until cancelled when network drops
- Progress percent + speed estimate
- Optional rotating proxy via proxy_pool
"""
from __future__ import annotations

import json
import re
import threading
import time
import uuid
from pathlib import Path
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.parse import unquote, urlparse
from urllib.request import Request, urlopen

from config_loader import ROOT, workspace_dir

try:
    from proxy_pool import opener_for, next_proxy, load_config as load_proxy_cfg
except Exception:
    def opener_for(proxy=None):
        return None, None
    def next_proxy():
        return None
    def load_proxy_cfg():
        return {"enabled": False}

DOWNLOAD_DIR = workspace_dir() / "downloads"
STATE_DIR = workspace_dir() / "downloads" / ".state"

_jobs: dict[str, dict[str, Any]] = {}
_lock = threading.Lock()


def _ensure_dirs():
    DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
    STATE_DIR.mkdir(parents=True, exist_ok=True)


def _filename_from_url(url: str) -> str:
    path = urlparse(url).path
    name = unquote(path.rsplit("/", 1)[-1] or "")
    name = re.sub(r"[^\w.\-\u0600-\u06ff]+", "_", name).strip("._")
    if not name or len(name) > 180:
        name = f"file_{uuid.uuid4().hex[:10]}"
    return name


def _meta_path(job_id: str) -> Path:
    return STATE_DIR / f"{job_id}.json"


def _save_meta(job: dict[str, Any]) -> None:
    _ensure_dirs()
    data = {k: v for k, v in job.items() if k not in ("_thread",)}
    _meta_path(job["id"]).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _load_all_meta() -> None:
    _ensure_dirs()
    with _lock:
        for p in STATE_DIR.glob("*.json"):
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
                jid = data.get("id") or p.stem
                if jid not in _jobs:
                    data["id"] = jid
                    if data.get("status") == "downloading":
                        data["status"] = "paused"
                        data["message"] = "interrupted — call download_resume"
                    _jobs[jid] = data
            except Exception:
                pass


def _progress_bar(pct: float, width: int = 24) -> str:
    pct = max(0.0, min(100.0, pct))
    filled = int(width * pct / 100)
    return "[" + "#" * filled + "-" * (width - filled) + f"] {pct:5.1f}%"


def job_status(job: dict[str, Any]) -> dict[str, Any]:
    total = float(job.get("total") or 0)
    done = float(job.get("downloaded") or 0)
    pct = (done / total * 100.0) if total > 0 else (100.0 if job.get("status") == "done" else 0.0)
    speed = float(job.get("speed_bps") or 0)
    eta = None
    if speed > 0 and total > done:
        eta = int((total - done) / speed)
    return {
        "ok": True,
        "id": job.get("id"),
        "url": job.get("url"),
        "path": job.get("path"),
        "status": job.get("status"),
        "downloaded": int(done),
        "total": int(total) if total else None,
        "percent": round(pct, 2),
        "progress_bar": _progress_bar(pct),
        "speed_bps": int(speed),
        "speed_human": _human_speed(speed),
        "eta_sec": eta,
        "message": job.get("message") or "",
        "attempts": job.get("attempts") or 0,
        "proxy": job.get("proxy"),
        "error": job.get("error"),
    }


def _human_speed(bps: float) -> str:
    if bps < 1024:
        return f"{bps:.0f} B/s"
    if bps < 1024 ** 2:
        return f"{bps/1024:.1f} KB/s"
    return f"{bps/1024**2:.2f} MB/s"


def _open_url(url: str, headers: dict, timeout: int = 30):
    opener, proxy = opener_for()
    req = Request(url, headers=headers)
    if opener:
        return opener.open(req, timeout=timeout), proxy
    return urlopen(req, timeout=timeout), proxy


def _download_loop(job_id: str) -> None:
    with _lock:
        job = _jobs.get(job_id)
    if not job:
        return
    url = job["url"]
    dest = Path(job["path"])
    part = dest.with_suffix(dest.suffix + ".part") if dest.suffix else Path(str(dest) + ".part")
    job["part_path"] = str(part)
    job["status"] = "downloading"
    job["message"] = "starting"
    job["cancel"] = False
    _save_meta(job)

    chunk = 256 * 1024
    while True:
        with _lock:
            if job.get("cancel"):
                job["status"] = "cancelled"
                job["message"] = "cancelled by user"
                _save_meta(job)
                return
        existing = part.stat().st_size if part.exists() else 0
        job["downloaded"] = existing
        headers = {
            "User-Agent": "GGUF-Runner-Downloader/1.0",
            "Accept": "*/*",
        }
        if existing > 0:
            headers["Range"] = f"bytes={existing}-"

        try:
            job["attempts"] = int(job.get("attempts") or 0) + 1
            job["message"] = f"connecting (try {job['attempts']})"
            _save_meta(job)
            resp, proxy = _open_url(url, headers, timeout=45)
            job["proxy"] = proxy
            with resp:
                status = getattr(resp, "status", None) or resp.getcode()
                # 200 on resume means server ignored Range → restart
                if existing > 0 and status == 200:
                    existing = 0
                    try:
                        part.unlink()
                    except Exception:
                        pass
                cl = resp.headers.get("Content-Length")
                if status == 206 and cl:
                    total = existing + int(cl)
                elif status == 200 and cl:
                    total = int(cl)
                else:
                    total = int(job.get("total") or 0) or (existing + int(cl or 0))
                if total:
                    job["total"] = total
                mode = "ab" if existing > 0 and status == 206 else "wb"
                if mode == "wb":
                    existing = 0
                    job["downloaded"] = 0
                t0 = time.time()
                got = 0
                with open(part, mode) as f:
                    while True:
                        with _lock:
                            if job.get("cancel"):
                                job["status"] = "cancelled"
                                job["message"] = "cancelled"
                                _save_meta(job)
                                return
                        data = resp.read(chunk)
                        if not data:
                            break
                        f.write(data)
                        got += len(data)
                        job["downloaded"] = existing + got
                        elapsed = max(0.001, time.time() - t0)
                        job["speed_bps"] = got / elapsed
                        pct = (job["downloaded"] / job["total"] * 100) if job.get("total") else 0
                        job["message"] = f"{_progress_bar(pct)} {_human_speed(job['speed_bps'])}"
                        if got % (chunk * 8) < chunk:
                            _save_meta(job)
                # finished stream
                final_size = part.stat().st_size
                job["downloaded"] = final_size
                expected = job.get("total")
                if expected and final_size < expected:
                    job["status"] = "retrying"
                    job["message"] = f"incomplete {final_size}/{expected} — retry in 3s"
                    job["error"] = "incomplete download"
                    _save_meta(job)
                    time.sleep(3)
                    continue
                # move part → final
                dest.parent.mkdir(parents=True, exist_ok=True)
                if dest.exists():
                    try:
                        dest.unlink()
                    except Exception:
                        pass
                part.rename(dest)
                job["status"] = "done"
                job["message"] = f"completed → {dest.name}"
                job["error"] = None
                job["path"] = str(dest)
                job["percent"] = 100
                _save_meta(job)
                return
        except (HTTPError, URLError, TimeoutError, ConnectionError, OSError) as e:
            job["status"] = "retrying"
            job["error"] = str(e)
            job["message"] = f"network error: {e} — retry in 5s (auto-resume)"
            job["speed_bps"] = 0
            _save_meta(job)
            # wait and retry forever until cancel
            for _ in range(10):
                if job.get("cancel"):
                    job["status"] = "cancelled"
                    _save_meta(job)
                    return
                time.sleep(0.5)
            continue
        except Exception as e:
            job["status"] = "error"
            job["error"] = str(e)
            job["message"] = f"fatal: {e}"
            _save_meta(job)
            return


def download_start(
    url: str,
    filename: str = "",
    dest_dir: str = "",
    use_proxy: bool = True,
) -> dict[str, Any]:
    url = (url or "").strip()
    if not url.startswith(("http://", "https://")):
        return {"ok": False, "error": "url must start with http:// or https://"}
    _ensure_dirs()
    _load_all_meta()
    name = (filename or "").strip() or _filename_from_url(url)
    out_dir = Path(dest_dir).expanduser() if dest_dir else DOWNLOAD_DIR
    if not out_dir.is_absolute():
        out_dir = (workspace_dir() / out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    dest = out_dir / name
    job_id = uuid.uuid4().hex[:12]
    job = {
        "id": job_id,
        "url": url,
        "path": str(dest),
        "status": "queued",
        "downloaded": 0,
        "total": 0,
        "speed_bps": 0,
        "attempts": 0,
        "message": "queued",
        "use_proxy": bool(use_proxy),
        "created": time.time(),
        "cancel": False,
    }
    with _lock:
        _jobs[job_id] = job
    _save_meta(job)
    t = threading.Thread(target=_download_loop, args=(job_id,), daemon=True)
    job["_thread"] = t
    t.start()
    return {
        "ok": True,
        "id": job_id,
        "path": str(dest),
        "message": "download started (auto-resume on disconnect)",
        "status": job_status(job),
    }


def download_status(job_id: str = "") -> dict[str, Any]:
    _load_all_meta()
    with _lock:
        if job_id:
            job = _jobs.get(job_id)
            if not job:
                return {"ok": False, "error": f"unknown job: {job_id}"}
            return job_status(job)
        items = [job_status(j) for j in _jobs.values()]
    return {"ok": True, "jobs": items, "count": len(items)}


def download_resume(job_id: str = "") -> dict[str, Any]:
    _load_all_meta()
    with _lock:
        job = _jobs.get(job_id)
    if not job:
        return {"ok": False, "error": "job not found"}
    if job.get("status") == "done":
        return {"ok": True, "message": "already done", "status": job_status(job)}
    if job.get("status") == "downloading":
        return {"ok": True, "message": "already running", "status": job_status(job)}
    job["cancel"] = False
    t = threading.Thread(target=_download_loop, args=(job_id,), daemon=True)
    job["_thread"] = t
    t.start()
    return {"ok": True, "message": "resumed", "status": job_status(job)}


def download_cancel(job_id: str = "") -> dict[str, Any]:
    with _lock:
        job = _jobs.get(job_id)
    if not job:
        return {"ok": False, "error": "job not found"}
    job["cancel"] = True
    job["message"] = "cancel requested"
    _save_meta(job)
    return {"ok": True, "id": job_id, "message": "cancel requested"}


def download_list() -> dict[str, Any]:
    return download_status("")


DOWNLOAD_TOOLS = {
    "download_start": lambda url="", filename="", dest_dir="", use_proxy=True, **kw: download_start(
        url, filename, dest_dir, bool(use_proxy)
    ),
    "download": lambda url="", filename="", dest_dir="", use_proxy=True, **kw: download_start(
        url, filename, dest_dir, bool(use_proxy)
    ),
    "download_status": lambda job_id="", **kw: download_status(job_id or ""),
    "download_list": lambda **kw: download_list(),
    "download_resume": lambda job_id="", **kw: download_resume(job_id or ""),
    "download_cancel": lambda job_id="", **kw: download_cancel(job_id or ""),
}
