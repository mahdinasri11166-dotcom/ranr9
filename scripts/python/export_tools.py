# -*- coding: utf-8 -*-
"""
Generate downloadable project files:
- source code with correct extensions
- Word (.docx) minimal OOXML
- PDF minimal writer
- Markdown / TXT / JSON / CSV

Saves under workspace/exports/ for the user to open/copy.
"""
from __future__ import annotations

import csv
import io
import json
import re
import zipfile
from datetime import datetime
from pathlib import Path
import sys
from typing import Any
from xml.sax.saxutils import escape

from config_loader import workspace_dir

LANG_EXT = {
    "python": ".py", "py": ".py", "پایتون": ".py",
    "javascript": ".js", "js": ".js", "node": ".js", "جاوااسکریپت": ".js",
    "typescript": ".ts", "ts": ".ts",
    "html": ".html", "css": ".css",
    "java": ".java", "جاوا": ".java",
    "c": ".c", "cpp": ".cpp", "c++": ".cpp", "cplusplus": ".cpp",
    "csharp": ".cs", "cs": ".cs", "c#": ".cs",
    "go": ".go", "golang": ".go",
    "rust": ".rs", "rs": ".rs",
    "php": ".php",
    "ruby": ".rb", "rb": ".rb",
    "swift": ".swift",
    "kotlin": ".kt", "kt": ".kt",
    "sql": ".sql",
    "bash": ".sh", "shell": ".sh", "powershell": ".ps1", "ps1": ".ps1",
    "r": ".r",
    "lua": ".lua",
    "dart": ".dart",
    "json": ".json", "yaml": ".yml", "yml": ".yml", "xml": ".xml",
    "markdown": ".md", "md": ".md", "txt": ".txt", "text": ".txt",
    "docx": ".docx", "word": ".docx", "ورد": ".docx",
    "pdf": ".pdf",
    "csv": ".csv",
}


def _exports_dir() -> Path:
    d = workspace_dir() / "exports"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _safe_name(name: str, ext: str) -> str:
    name = (name or "output").strip()
    stem = Path(name).stem if name else "output"
    suffix = Path(name).suffix if (name and "." in Path(name).name) else ""
    stem = re.sub(r"[^\w\u0600-\u06FF\-]+", "_", stem)[:80] or "output"
    if suffix and ext and suffix.lower() == ext.lower():
        return stem + suffix
    if ext:
        return stem + ext
    if suffix:
        return stem + suffix
    return stem + ".txt"

def resolve_extension(language: str = "", filename: str = "") -> str:
    if filename and "." in Path(filename).name:
        return Path(filename).suffix
    key = (language or "").strip().lower()
    return LANG_EXT.get(key, ".txt")


def write_text_file(content: str, filename: str = "", language: str = "", encoding: str = "utf-8") -> dict[str, Any]:
    ext = resolve_extension(language, filename)
    fname = _safe_name(filename or f"code_{datetime.now().strftime('%H%M%S')}", ext)
    path = _exports_dir() / fname
    path.write_text(content or "", encoding=encoding)
    return {
        "ok": True,
        "path": str(path),
        "filename": fname,
        "extension": ext,
        "bytes": path.stat().st_size,
        "language": language,
    }


def write_json_file(data: Any, filename: str = "data.json") -> dict[str, Any]:
    text = json.dumps(data, ensure_ascii=False, indent=2)
    return write_text_file(text, filename=filename, language="json")


def write_csv_file(rows: list, filename: str = "data.csv", headers: list | None = None) -> dict[str, Any]:
    path = _exports_dir() / _safe_name(filename, ".csv")
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        if headers:
            w.writerow(headers)
        for row in rows or []:
            if isinstance(row, dict):
                if headers:
                    w.writerow([row.get(h, "") for h in headers])
                else:
                    w.writerow(list(row.values()))
            else:
                w.writerow(list(row) if not isinstance(row, str) else [row])
    return {"ok": True, "path": str(path), "filename": path.name, "bytes": path.stat().st_size}


def _docx_bytes(title: str, body: str) -> bytes:
    """Minimal docx (OOXML) without python-docx."""
    title = title or "Document"
    paragraphs = (body or "").replace("\r\n", "\n").split("\n")
    p_xml = []
    p_xml.append(
        f'<w:p><w:r><w:rPr><w:b/></w:rPr><w:t>{escape(title)}</w:t></w:r></w:p>'
    )
    for line in paragraphs:
        p_xml.append(f'<w:p><w:r><w:t>{escape(line)}</w:t></w:r></w:p>')
    document_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        "<w:body>"
        + "".join(p_xml)
        + "</w:body></w:document>"
    )
    content_types = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
</Types>'''
    rels = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>'''
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", content_types)
        z.writestr("_rels/.rels", rels)
        z.writestr("word/document.xml", document_xml)
    return buf.getvalue()


def write_docx(content: str, filename: str = "document.docx", title: str = "Document") -> dict[str, Any]:
    fname = _safe_name(filename, ".docx")
    path = _exports_dir() / fname
    path.write_bytes(_docx_bytes(title, content or ""))
    return {"ok": True, "path": str(path), "filename": fname, "bytes": path.stat().st_size, "format": "docx"}


def _pdf_bytes(title: str, body: str) -> bytes:
    """Very small single-page PDF (Latin + escaped content; UTF-8 as hex for non-ascii best-effort)."""
    def pdf_escape(s: str) -> str:
        # Prefer ASCII; replace non-ascii with ?
        s2 = "".join(ch if 32 <= ord(ch) < 127 else "?" for ch in s)
        return s2.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")

    lines = (body or "").replace("\r\n", "\n").split("\n")[:60]
    content_lines = [f"BT /F1 16 Tf 50 780 Td ({pdf_escape(title or 'Document')}) Tj"]
    y = 750
    content_lines.append("/F1 11 Tf")
    for line in lines:
        y -= 14
        if y < 50:
            break
        content_lines.append(f"0 -14 Td ({pdf_escape(line[:110])}) Tj")
    content_lines.append("ET")
    stream = "\n".join(content_lines).encode("latin-1", errors="replace")

    objs = []
    objs.append(b"1 0 obj<< /Type /Catalog /Pages 2 0 R >>endobj\n")
    objs.append(b"2 0 obj<< /Type /Pages /Kids [3 0 R] /Count 1 >>endobj\n")
    objs.append(
        b"3 0 obj<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Contents 4 0 R /Resources<< /Font<< /F1 5 0 R >> >> >>endobj\n"
    )
    objs.append(f"4 0 obj<< /Length {len(stream)} >>stream\n".encode("latin-1") + stream + b"\nendstream\nendobj\n")
    objs.append(b"5 0 obj<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>endobj\n")

    out = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for obj in objs:
        offsets.append(len(out))
        out.extend(obj)
    xref_pos = len(out)
    out.extend(f"xref\n0 {len(offsets)}\n".encode("latin-1"))
    out.extend(b"0000000000 65535 f \n")
    for off in offsets[1:]:
        out.extend(f"{off:010d} 00000 n \n".encode("latin-1"))
    out.extend(
        f"trailer<< /Size {len(offsets)} /Root 1 0 R >>\nstartxref\n{xref_pos}\n%%EOF\n".encode("latin-1")
    )
    return bytes(out)


def write_pdf(content: str, filename: str = "document.pdf", title: str = "Document") -> dict[str, Any]:
    fname = _safe_name(filename, ".pdf")
    path = _exports_dir() / fname
    # Prefer reportlab if available for better Unicode
    try:
        from reportlab.lib.pagesizes import A4  # type: ignore
        from reportlab.pdfgen import canvas  # type: ignore
        from reportlab.pdfbase import pdfmetrics  # type: ignore
        from reportlab.pdfbase.ttfonts import TTFont  # type: ignore
        c = canvas.Canvas(str(path), pagesize=A4)
        width, height = A4
        c.setFont("Helvetica-Bold", 14)
        c.drawString(40, height - 40, (title or "Document")[:120])
        c.setFont("Helvetica", 10)
        y = height - 70
        for line in (content or "").splitlines()[:80]:
            # reportlab default fonts are limited for Persian; still write ascii-safe
            safe = line.encode("latin-1", errors="replace").decode("latin-1")
            c.drawString(40, y, safe[:100])
            y -= 12
            if y < 40:
                c.showPage()
                y = height - 40
                c.setFont("Helvetica", 10)
        c.save()
        return {"ok": True, "path": str(path), "filename": fname, "bytes": path.stat().st_size, "format": "pdf", "engine": "reportlab"}
    except Exception:
        path.write_bytes(_pdf_bytes(title, content or ""))
        return {
            "ok": True,
            "path": str(path),
            "filename": fname,
            "bytes": path.stat().st_size,
            "format": "pdf",
            "engine": "minimal",
            "note": "Persian may show as ? in minimal PDF; prefer DOCX for Persian text",
        }


def make_code_file(
    language: str,
    code: str,
    filename: str = "",
    description: str = "",
) -> dict[str, Any]:
    """Write a programming language source file ready for download."""
    if not (code or "").strip():
        return {"ok": False, "error": "code is empty"}
    header = ""
    ext = resolve_extension(language, filename)
    if description:
        if ext in (".py", ".sh", ".rb", ".r", ".ps1"):
            header = f"# {description}\n"
        elif ext in (".js", ".ts", ".java", ".c", ".cpp", ".cs", ".go", ".rs", ".php", ".kt", ".swift"):
            header = f"// {description}\n"
        elif ext in (".html", ".xml"):
            header = f"<!-- {description} -->\n"
    body = header + (code or "")
    if not filename:
        filename = f"snippet_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    return write_text_file(body, filename=filename, language=language)


def make_document(
    content: str,
    fmt: str = "docx",
    filename: str = "",
    title: str = "Document",
) -> dict[str, Any]:
    fmt = (fmt or "docx").lower().strip()
    content = (content or "").strip()
    # strip common Persian/English command shells so the file body is useful
    content = re.sub(
        r"^(?:لطفاً|لطفا|please)?\s*(?:یک\s*)?(?:فایل\s*)?(?:ورد|word|docx|پی\s*دی\s*اف|pdf)?\s*(?:بساز|بده|تولید\s*کن|create|generate)?\s*[:：\-]?\s*",
        "",
        content,
        flags=re.I,
    ).strip() or content
    if fmt in ("docx", "word", "ورد"):
        return write_docx(content, filename=filename or "document.docx", title=title)
    if fmt == "pdf":
        return write_pdf(content, filename=filename or "document.pdf", title=title)
    if fmt in ("md", "markdown"):
        return write_text_file(f"# {title}\n\n{content}", filename=filename or "document.md", language="md")
    if fmt in ("txt", "text"):
        return write_text_file(f"{title}\n\n{content}", filename=filename or "document.txt", language="txt")
    return {"ok": False, "error": f"unsupported format: {fmt}", "hint": "docx|pdf|md|txt"}


def list_exports() -> dict[str, Any]:
    d = _exports_dir()
    items = []
    for p in sorted(d.glob("*"), key=lambda x: x.stat().st_mtime, reverse=True):
        if p.is_file():
            items.append({"name": p.name, "path": str(p), "bytes": p.stat().st_size})
    return {"ok": True, "dir": str(d), "files": items[:50], "count": len(items)}


def build_and_export(
    task: str,
    language: str = "python",
    code: str = "",
    filename: str = "",
    fmt: str = "",
    title: str = "",
) -> dict[str, Any]:
    """
    High-level: if code provided, write file; if fmt is docx/pdf write document.
    Agent should generate `code` content first, then call this.
    """
    task = (task or "").strip()
    language = (language or "python").strip()
    fmt = (fmt or "").strip().lower()

    if fmt in ("docx", "pdf", "word", "ورد", "md", "txt"):
        return make_document(code or task, fmt=fmt, filename=filename, title=title or task[:80] or "Document")

    if language.lower() in ("docx", "word", "ورد", "pdf"):
        return make_document(code or task, fmt=language, filename=filename, title=title or task[:80] or "Document")

    if not code:
        return {
            "ok": False,
            "error": "code empty — model must generate source first, then call make_code_file/build_and_export",
            "task": task,
            "language": language,
            "exports_dir": str(_exports_dir()),
        }
    return make_code_file(language, code, filename=filename, description=task[:200])


def open_exports() -> dict[str, Any]:
    d = _exports_dir()
    try:
        import os, subprocess
        if hasattr(os, "startfile"):
            os.startfile(str(d))
        elif sys.platform == "darwin":
            subprocess.Popen(["open", str(d)])
        else:
            subprocess.Popen(["xdg-open", str(d)])
        return {"ok": True, "path": str(d), "opened": True}
    except Exception as e:
        return {"ok": True, "path": str(d), "opened": False, "error": str(e)}


EXPORT_TOOLS: dict[str, Any] = {

    "make_code_file": make_code_file,
    "make_document": make_document,
    "write_text_file": write_text_file,
    "write_docx": write_docx,
    "write_pdf": write_pdf,
    "write_json_file": write_json_file,
    "write_csv_file": write_csv_file,
    "list_exports": list_exports,
    "open_exports": open_exports,
    "build_and_export": build_and_export,
    "export_code": make_code_file,
    "export_docx": write_docx,
    "export_pdf": write_pdf,
}
