# -*- coding: utf-8 -*-
"""Layer 1: coding agent tools — search, patch, tests, allowlisted shell, git (workspace)."""
from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

from config_loader import ROOT, workspace_dir

WORKSPACE = workspace_dir()

def _git_cwd() -> Path:
    """Prefer project ROOT if it is a git repo, else workspace."""
    if (ROOT / '.git').exists():
        return ROOT
    if (WORKSPACE / '.git').exists():
        return WORKSPACE
    return WORKSPACE

SHELL_ALLOW = {
    "python", "python3", "pip", "pip3", "git", "dir", "ls", "type", "cat",
    "echo", "cd", "pwd", "where", "which", "pytest", "node", "npm", "npx",
    "rg", "findstr", "wc", "head", "tail", "mkdir", "copy", "cp", "move", "mv",
}


def _ws(path: str = ".") -> Path:
    rel = (path or ".").replace("\\", "/").lstrip("/")
    if ".." in rel.split("/"):
        raise PermissionError("path traversal blocked")
    p = (WORKSPACE / rel).resolve()
    if not str(p).startswith(str(WORKSPACE.resolve())):
        raise PermissionError("outside workspace")
    return p


def search_code(query: str, path: str = ".", max_hits: int = 40) -> dict[str, Any]:
    query = (query or "").strip()
    if not query:
        return {"ok": False, "error": "query empty"}
    root = _ws(path)
    if not root.exists():
        return {"ok": False, "error": "path not found"}
    hits = []
    max_hits = max(1, min(int(max_hits or 40), 200))
    # try rg
    try:
        r = subprocess.run(
            ["rg", "-n", "--max-count", "5", "-S", query, str(root)],
            capture_output=True, text=True, timeout=30,
        )
        if r.returncode in (0, 1):
            for line in (r.stdout or "").splitlines()[:max_hits]:
                hits.append(line)
            return {"ok": True, "engine": "rg", "hits": hits, "count": len(hits)}
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    # fallback python scan
    pat = re.compile(re.escape(query), re.I)
    for f in root.rglob("*"):
        if not f.is_file():
            continue
        if f.suffix.lower() not in {".py", ".js", ".ts", ".tsx", ".jsx", ".md", ".txt", ".json", ".html", ".css", ".bat", ".ps1", ".yml", ".yaml", ".toml"}:
            continue
        try:
            if f.stat().st_size > 1_500_000:
                continue
            text = f.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for i, line in enumerate(text.splitlines(), 1):
            if pat.search(line):
                hits.append(f"{f.relative_to(WORKSPACE)}:{i}:{line.strip()[:200]}")
                if len(hits) >= max_hits:
                    return {"ok": True, "engine": "python", "hits": hits, "count": len(hits)}
    return {"ok": True, "engine": "python", "hits": hits, "count": len(hits)}


def apply_patch(path: str, old: str, new: str, replace_all: bool = False) -> dict[str, Any]:
    p = _ws(path)
    if not p.exists() or not p.is_file():
        return {"ok": False, "error": "file not found"}
    text = p.read_text(encoding="utf-8", errors="replace")
    if old not in text:
        return {"ok": False, "error": "old text not found", "path": str(p.relative_to(WORKSPACE))}
    if replace_all:
        updated = text.replace(old, new)
        count = text.count(old)
    else:
        updated = text.replace(old, new, 1)
        count = 1
    p.write_text(updated, encoding="utf-8")
    return {"ok": True, "path": str(p.relative_to(WORKSPACE)), "replacements": count}


def run_tests(command: str = "python -m pytest -q", timeout: int = 120) -> dict[str, Any]:
    """Run tests inside workspace with mild allowlist on first token."""
    command = (command or "python -m pytest -q").strip()
    first = command.split()[0].lower().replace(".exe", "")
    if first not in SHELL_ALLOW and first not in ("py",):
        return {"ok": False, "blocked": True, "error": f"command not allowlisted: {first}"}
    try:
        r = subprocess.run(
            command, shell=True, cwd=str(WORKSPACE),
            capture_output=True, text=True, timeout=max(5, min(timeout, 600)),
        )
        return {
            "ok": r.returncode == 0,
            "returncode": r.returncode,
            "stdout": (r.stdout or "")[:15000],
            "stderr": (r.stderr or "")[:8000],
            "command": command,
        }
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "timeout", "command": command}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def shell_allowlisted(command: str, timeout: int = 60) -> dict[str, Any]:
    command = (command or "").strip()
    if not command:
        return {"ok": False, "error": "empty command"}
    # extract first executable token
    token = command.strip().split()[0]
    base = Path(token).name.lower().replace(".exe", "")
    if base not in SHELL_ALLOW:
        return {
            "ok": False,
            "blocked": True,
            "error": f"not allowlisted: {base}",
            "allowed": sorted(SHELL_ALLOW),
        }
    try:
        r = subprocess.run(
            command, shell=True, cwd=str(WORKSPACE),
            capture_output=True, text=True, timeout=max(1, min(timeout, 300)),
        )
        return {
            "ok": r.returncode == 0,
            "returncode": r.returncode,
            "stdout": (r.stdout or "")[:15000],
            "stderr": (r.stderr or "")[:8000],
            "command": command,
        }
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "timeout"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def _git(args: list[str], timeout: int = 60) -> dict[str, Any]:
    try:
        r = subprocess.run(
            ["git", *args], cwd=str(_git_cwd()),
            capture_output=True, text=True, timeout=timeout,
        )
        return {
            "ok": r.returncode == 0,
            "returncode": r.returncode,
            "stdout": (r.stdout or "")[:15000],
            "stderr": (r.stderr or "")[:5000],
            "args": args,
            "cwd": str(_git_cwd()),
        }
    except FileNotFoundError:
        return {"ok": False, "error": "git not installed"}
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "timeout"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def git_status() -> dict[str, Any]:
    return _git(["status", "--short", "--branch"])


def git_diff(staged: bool = False) -> dict[str, Any]:
    return _git(["diff", "--staged"] if staged else ["diff"])


def git_log(n: int = 10) -> dict[str, Any]:
    n = max(1, min(int(n or 10), 50))
    return _git(["log", f"-{n}", "--oneline"])


def git_commit(message: str) -> dict[str, Any]:
    message = (message or "").strip()
    if not message:
        return {"ok": False, "error": "message required"}
    add = _git(["add", "-A"])
    if not add.get("ok") and add.get("returncode") not in (0, None):
        # still try commit
        pass
    return _git(["commit", "-m", message])




def git_branch_list() -> dict[str, Any]:
    return _git(["branch", "-a", "-v"])


def git_branch_create(name: str, checkout: bool = True) -> dict[str, Any]:
    name = (name or "").strip()
    if not name or not re.match(r"^[A-Za-z0-9._/\-]+$", name):
        return {"ok": False, "error": "invalid branch name"}
    r = _git(["branch", name])
    if checkout and r.get("ok"):
        r2 = _git(["checkout", name])
        return {"ok": r2.get("ok"), "create": r, "checkout": r2}
    return r


def git_checkout(name: str) -> dict[str, Any]:
    name = (name or "").strip()
    if not name:
        return {"ok": False, "error": "branch required"}
    return _git(["checkout", name])


def git_remote_list() -> dict[str, Any]:
    return _git(["remote", "-v"])


def git_stash(message: str = "") -> dict[str, Any]:
    args = ["stash", "push"]
    if message:
        args += ["-m", message]
    return _git(args)


def git_stash_list() -> dict[str, Any]:
    return _git(["stash", "list"])


def git_init() -> dict[str, Any]:
    cwd = _git_cwd()
    if (cwd / ".git").exists():
        return {"ok": True, "note": "already a git repo", "cwd": str(cwd)}
    return _git(["init"])


def git_ensure_gitignore() -> dict[str, Any]:
    """Create/update .gitignore for GGUF Runner large/local artifacts."""
    cwd = _git_cwd()
    path = cwd / ".gitignore"
    patterns = [
        "# GGUF Runner — auto",
        "models/**/*.gguf",
        "*.gguf",
        "python/",
        "bin/llama-server.exe",
        "bin/*.dll",
        "installer/payload/",
        "installer/Output/",
        "__pycache__/",
        "*.pyc",
        ".venv/",
        "venv/",
        "sessions/",
        "workspace/osint/cache/",
        "workspace/agent_memory/",
        "*.bin",
        "*.safetensors",
        "*.onnx",
        ".DS_Store",
        "Thumbs.db",
    ]
    existing = path.read_text(encoding="utf-8") if path.exists() else ""
    added = []
    lines = existing.splitlines()
    for pat in patterns:
        if pat.startswith("#"):
            continue
        if pat not in lines:
            lines.append(pat)
            added.append(pat)
    if not existing.strip().startswith("#"):
        lines = patterns[:1] + lines
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return {"ok": True, "path": str(path), "added": added, "cwd": str(cwd)}


def large_files_scan(path: str = ".", min_mb: float = 50.0, limit: int = 40) -> dict[str, Any]:
    """List large files under workspace/ROOT (default min 50MB)."""
    min_bytes = int(float(min_mb) * 1024 * 1024)
    limit = max(1, min(int(limit or 40), 200))
    roots = []
    # prefer scanning models + workspace + root common dirs
    for rel in (path, "models", "workspace", "bin", "python"):
        try:
            if rel == ".":
                roots.append(_git_cwd())
            else:
                roots.append((ROOT / rel) if (ROOT / rel).exists() else None)
        except Exception:
            pass
    seen = set()
    found = []
    for root in roots:
        if root is None or not root.exists():
            continue
        for f in root.rglob("*"):
            try:
                if not f.is_file():
                    continue
                key = str(f.resolve())
                if key in seen:
                    continue
                seen.add(key)
                sz = f.stat().st_size
                if sz >= min_bytes:
                    found.append({
                        "path": str(f.relative_to(ROOT)) if str(f).startswith(str(ROOT)) else str(f),
                        "size_mb": round(sz / (1024 * 1024), 2),
                        "size_bytes": sz,
                    })
            except OSError:
                continue
    found.sort(key=lambda x: -x["size_bytes"])
    found = found[:limit]
    return {"ok": True, "min_mb": min_mb, "count": len(found), "files": found}


def git_lfs_hint() -> dict[str, Any]:
    """Check if git-lfs is available and suggest tracking patterns."""
    try:
        r = subprocess.run(["git", "lfs", "version"], capture_output=True, text=True, timeout=10)
        has = r.returncode == 0
        ver = (r.stdout or r.stderr or "").strip()[:200]
    except Exception as e:
        has = False
        ver = str(e)
    return {
        "ok": True,
        "git_lfs_installed": has,
        "version": ver,
        "suggest": [
            "git lfs install",
            'git lfs track "*.gguf"',
            'git lfs track "*.bin"',
            "git add .gitattributes",
        ],
        "note_fa": "فایل‌های GGUF را معمولاً commit نکنید؛ در .gitignore بگذارید یا از Git LFS استفاده کنید.",
    }


def git_lfs_track(pattern: str = "*.gguf") -> dict[str, Any]:
    pattern = (pattern or "*.gguf").strip()
    try:
        r = subprocess.run(
            ["git", "lfs", "track", pattern],
            cwd=str(_git_cwd()),
            capture_output=True,
            text=True,
            timeout=30,
        )
        return {
            "ok": r.returncode == 0,
            "stdout": (r.stdout or "")[:5000],
            "stderr": (r.stderr or "")[:3000],
            "cwd": str(_git_cwd()),
        }
    except FileNotFoundError:
        return {"ok": False, "error": "git-lfs not installed"}
    except Exception as e:
        return {"ok": False, "error": str(e)}

CODING_TOOLS = {
    "search_code": search_code,
    "apply_patch": apply_patch,
    "run_tests": run_tests,
    "shell_allowlisted": shell_allowlisted,
    "git_status": git_status,
    "git_diff": git_diff,
    "git_log": git_log,
    "git_commit": git_commit,
    "git_branch_list": git_branch_list,
    "git_branch_create": git_branch_create,
    "git_checkout": git_checkout,
    "git_remote_list": git_remote_list,
    "git_stash": git_stash,
    "git_stash_list": git_stash_list,
    "git_init": git_init,
    "git_ensure_gitignore": git_ensure_gitignore,
    "large_files_scan": large_files_scan,
    "git_lfs_hint": git_lfs_hint,
    "git_lfs_track": git_lfs_track,
}
