# -*- coding: utf-8 -*-
"""
Builder tools: scaffold projects and write multi-file trees under workspace/.
All writes stay inside workspace unless elevated sys_* tools are used.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from config_loader import workspace_dir

WORKSPACE = workspace_dir()

TEMPLATES: dict[str, dict[str, str]] = {
    "python-cli": {
        "README.md": "# {name}\n\n```bash\npython main.py\n```\n",
        "main.py": (
            "#!/usr/bin/env python3\n"
            "def main():\n"
            "    print('Hello from {name}')\n\n"
            "if __name__ == '__main__':\n"
            "    main()\n"
        ),
        "requirements.txt": "# add deps here\n",
    },
    "python-web": {
        "README.md": "# {name}\n\nSimple HTTP stub.\n\n```bash\npython app.py\n```\n",
        "app.py": (
            "from http.server import BaseHTTPRequestHandler, HTTPServer\n\n"
            "class H(BaseHTTPRequestHandler):\n"
            "    def do_GET(self):\n"
            "        self.send_response(200)\n"
            "        self.send_header('Content-Type', 'text/plain; charset=utf-8')\n"
            "        self.end_headers()\n"
            "        self.wfile.write(b'Hello {name}')\n"
            "    def log_message(self, *a):\n"
            "        pass\n\n"
            "if __name__ == '__main__':\n"
            "    HTTPServer(('127.0.0.1', 8760), H).serve_forever()\n"
        ),
        "requirements.txt": "\n",
    },
    "html-page": {
        "index.html": (
            "<!DOCTYPE html><html lang='fa' dir='rtl'><head><meta charset='utf-8'>"
            "<title>{name}</title>"
            "<style>body{{font-family:Tahoma,sans-serif;margin:2rem;background:#111;color:#eee}}</style>"
            "</head><body><h1>{name}</h1><p>صفحه ساخته‌شده توسط GGUF Runner</p></body></html>\n"
        ),
        "README.md": "# {name}\n\nفایل index.html را در مرورگر باز کنید.\n",
    },
    "osint-case": {
        "README.md": "# Case: {name}\n\nTarget notes and artifacts.\n",
        "notes.md": "# {name}\n\n## هدف\n\n## یافته‌ها\n\n## منابع\n",
        "data.json": "{\n  \"name\": \"{name}\",\n  \"findings\": []\n}\n",
    },
}


def _safe_rel(rel: str) -> Path:
    rel = (rel or "").replace("\\", "/").lstrip("/")
    if ".." in rel.split("/"):
        raise PermissionError("path traversal blocked")
    target = (WORKSPACE / rel).resolve()
    if not str(target).startswith(str(WORKSPACE.resolve())):
        raise PermissionError("outside workspace")
    return target


def _slug(name: str) -> str:
    s = re.sub(r"[^\w\-]+", "-", (name or "project").strip(), flags=re.U)
    return (s[:60].strip("-") or "project")


def build_scaffold(name: str, template: str = "python-cli", subdir: str = "projects") -> dict[str, Any]:
    """Create a project skeleton from a built-in template under workspace."""
    name = (name or "project").strip()
    template = (template or "python-cli").strip().lower()
    if template not in TEMPLATES:
        return {
            "ok": False,
            "error": f"unknown template: {template}",
            "available": sorted(TEMPLATES.keys()),
        }
    root = _safe_rel(f"{subdir.rstrip('/')}/{_slug(name)}")
    if root.exists() and any(root.iterdir()):
        return {"ok": False, "error": f"folder not empty: {root.relative_to(WORKSPACE)}"}
    root.mkdir(parents=True, exist_ok=True)
    created = []
    for rel, content in TEMPLATES[template].items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        text = content.replace("{name}", name)
        path.write_text(text, encoding="utf-8")
        created.append(str(path.relative_to(WORKSPACE)))
    return {
        "ok": True,
        "project": str(root.relative_to(WORKSPACE)),
        "template": template,
        "files": created,
    }


def build_write_files(files: dict[str, str] | str, base: str = "projects") -> dict[str, Any]:
    """
    Write multiple files under workspace.
    files: dict path->content OR JSON string of that dict.
    Paths are relative to workspace/base or workspace if absolute-looking under workspace.
    """
    if isinstance(files, str):
        try:
            files = json.loads(files)
        except json.JSONDecodeError:
            return {"ok": False, "error": "files must be JSON object path->content"}
    if not isinstance(files, dict) or not files:
        return {"ok": False, "error": "files must be a non-empty object"}
    written = []
    errors = []
    for rel, content in list(files.items())[:100]:
        try:
            rel_s = str(rel).replace("\\", "/").lstrip("/")
            if base and not rel_s.startswith(base.rstrip("/") + "/") and "/" not in rel_s:
                rel_s = f"{base.rstrip('/')}/{rel_s}"
            path = _safe_rel(rel_s)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("" if content is None else str(content), encoding="utf-8")
            written.append(str(path.relative_to(WORKSPACE)))
        except Exception as e:
            errors.append({"path": rel, "error": str(e)})
    return {
        "ok": len(errors) == 0,
        "written": written,
        "count": len(written),
        "errors": errors,
    }


def build_list_templates() -> dict[str, Any]:
    return {
        "ok": True,
        "templates": sorted(TEMPLATES.keys()),
        "note": "Files are created only under workspace/",
    }


def build_tree(path: str = "projects", max_depth: int = 4) -> dict[str, Any]:
    try:
        root = _safe_rel(path)
    except Exception as e:
        return {"ok": False, "error": str(e)}
    if not root.exists():
        return {"ok": True, "path": path, "tree": [], "note": "empty or missing"}
    lines = []

    def walk(p: Path, prefix: str, depth: int):
        if depth > max_depth:
            return
        try:
            kids = sorted(p.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower()))
        except OSError:
            return
        for i, c in enumerate(kids[:200]):
            last = i == len(kids) - 1
            branch = "└── " if last else "├── "
            lines.append(f"{prefix}{branch}{c.name}{'/' if c.is_dir() else ''}")
            if c.is_dir():
                walk(c, prefix + ("    " if last else "│   "), depth + 1)

    lines.append(str(root.relative_to(WORKSPACE)) + "/")
    walk(root, "", 1)
    return {"ok": True, "path": str(root.relative_to(WORKSPACE)), "tree": lines}


BUILDER_TOOLS = {
    "build_scaffold": build_scaffold,
    "build_write_files": build_write_files,
    "build_list_templates": build_list_templates,
    "build_tree": build_tree,
}
