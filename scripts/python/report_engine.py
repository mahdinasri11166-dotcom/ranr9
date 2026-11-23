# -*- coding: utf-8 -*-
"""Persian HTML/PDF-ish OSINT report engine with timeline and sources."""
from __future__ import annotations

import html
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from config_loader import workspace_dir


def _esc(s: Any) -> str:
    return html.escape("" if s is None else str(s))


def render_graph_svg(graph: dict[str, Any], width: int = 720, height: int = 420) -> str:
    """Simple SVG force-free layout for domain graph nodes/edges."""
    nodes = list((graph or {}).get("nodes") or [])
    edges = list((graph or {}).get("edges") or [])
    if not nodes:
        return "<p class='meta'>گراف خالی است</p>"
    # layout: apex center, others on circle
    import math
    cx, cy = width // 2, height // 2
    pos = {}
    others = [n for n in nodes if n.get("type") != "apex"]
    apex = [n for n in nodes if n.get("type") == "apex"]
    for a in apex:
        pos[a["id"]] = (cx, cy)
    n = max(len(others), 1)
    radius = min(width, height) * 0.36
    for i, node in enumerate(others):
        ang = 2 * math.pi * i / n
        pos[node["id"]] = (cx + int(radius * math.cos(ang)), cy + int(radius * math.sin(ang)))
    # leftover nodes without pos
    for node in nodes:
        pos.setdefault(node["id"], (cx + 40, cy + 40))
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" style="background:#0c0e14;border-radius:10px">']
    for e in edges:
        a, b = e.get("from"), e.get("to")
        if a in pos and b in pos:
            x1, y1 = pos[a]
            x2, y2 = pos[b]
            parts.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="#445" stroke-width="2"/>')
            mid_x, mid_y = (x1 + x2) // 2, (y1 + y2) // 2
            rel = _esc(e.get("rel") or "")
            if rel:
                parts.append(f'<text x="{mid_x}" y="{mid_y}" fill="#667" font-size="10" text-anchor="middle">{rel}</text>')
    colors = {"apex": "#e94560", "subdomain": "#38bdf8", "ip": "#a3e635", "default": "#94a3b8"}
    for node in nodes:
        nid = node["id"]
        x, y = pos[nid]
        color = colors.get(node.get("type") or "", colors["default"])
        label = _esc((nid[:28] + "…") if len(nid) > 28 else nid)
        parts.append(f'<circle cx="{x}" cy="{y}" r="16" fill="{color}" opacity="0.9"/>')
        parts.append(f'<text x="{x}" y="{y + 32}" fill="#dde" font-size="11" text-anchor="middle">{label}</text>')
    parts.append("</svg>")
    return "\n".join(parts)




def build_html_report(
    title: str,
    target: str,
    sections: list[dict[str, Any]],
    timeline: list[dict[str, Any]] | None = None,
    sources: list[str] | None = None,
) -> str:
    timeline = timeline or []
    sources = sources or []
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    parts = [
        "<!DOCTYPE html><html lang='fa' dir='rtl'><head><meta charset='utf-8'>",
        f"<title>{_esc(title)}</title>",
        "<style>",
        "body{font-family:Tahoma,Segoe UI,sans-serif;background:#0f1115;color:#e8e8ef;margin:0;padding:24px;line-height:1.6}",
        "h1{color:#e94560;margin:0 0 8px} h2{color:#7dd3fc;border-bottom:1px solid #333;padding-bottom:6px}",
        ".meta{color:#9aa;font-size:13px;margin-bottom:24px}",
        ".card{background:#1a1d27;border:1px solid #2a2f3a;border-radius:10px;padding:14px 16px;margin:12px 0}",
        "pre{white-space:pre-wrap;word-break:break-word;background:#0c0e14;padding:10px;border-radius:8px;font-size:12px}",
        ".tl{border-right:3px solid #e94560;padding-right:12px;margin:8px 0}",
        ".src{display:inline-block;background:#243;padding:2px 8px;border-radius:6px;margin:2px;font-size:12px}",
        "a{color:#7dd3fc}",
        "</style></head><body>",
        f"<h1>{_esc(title)}</h1>",
        f"<div class='meta'>هدف: <b>{_esc(target)}</b> · تولید: {_esc(now)} · GGUF Runner OSINT</div>",
    ]
    if timeline:
        parts.append("<h2>خط زمان</h2><div class='card'>")
        for ev in timeline:
            parts.append(
                f"<div class='tl'><b>{_esc(ev.get('time',''))}</b> — {_esc(ev.get('event',''))}"
                f"<div style='color:#9aa;font-size:12px'>{_esc(ev.get('detail',''))}</div></div>"
            )
        parts.append("</div>")
    for sec in sections:
        parts.append(f"<h2>{_esc(sec.get('title','بخش'))}</h2><div class='card'>")
        if sec.get("html"):
            parts.append(str(sec["html"]))
        else:
            body = sec.get("data", sec.get("text", ""))
            if isinstance(body, (dict, list)):
                body = json.dumps(body, ensure_ascii=False, indent=2)
            parts.append(f"<pre>{_esc(body)}</pre>")
        parts.append("</div>")
    if sources:
        parts.append("<h2>منابع</h2><div class='card'>")
        for s in sources:
            parts.append(f"<span class='src'>{_esc(s)}</span> ")
        parts.append("</div>")
    parts.append(
        "<p class='meta'>این گزارش فقط از منابع عمومی/غیرفعال ساخته شده. "
        "مالکیت هویت را اثبات نمی‌کند. استفاده تهاجمی یا غیرقانونی مجاز نیست.</p>"
        "</body></html>"
    )
    return "\n".join(parts)


def save_report(
    name: str,
    target: str,
    modules_data: dict[str, Any],
    title: str | None = None,
) -> dict[str, Any]:
    """Save HTML report under workspace/osint/reports/."""
    ws = workspace_dir()
    out_dir = ws / "osint" / "reports"
    out_dir.mkdir(parents=True, exist_ok=True)
    safe = "".join(c if c.isalnum() or c in "-_." else "_" for c in (name or "report"))[:80]
    path = out_dir / f"{safe}.html"
    json_path = out_dir / f"{safe}.json"

    timeline = [{"time": datetime.now(timezone.utc).isoformat(), "event": "شروع گزارش", "detail": target}]
    sections = []
    sources: list[str] = []
    for mod_name, data in (modules_data or {}).items():
        if isinstance(data, dict) and isinstance(data.get("graph"), dict):
            sections.append({
                "title": f"{mod_name} — گراف",
                "html": render_graph_svg(data["graph"]),
            })
        sections.append({"title": mod_name, "data": data})
        timeline.append({"time": datetime.now(timezone.utc).isoformat(), "event": f"ماژول {mod_name}", "detail": "ok" if (isinstance(data, dict) and data.get("ok", True)) else "partial"})
        if isinstance(data, dict):
            if data.get("source"):
                sources.append(str(data["source"]))
            for s in data.get("sources") or []:
                sources.append(str(s))
    sources = sorted(set(sources)) or ["user_supplied", "public_dns", "public_http"]

    html_doc = build_html_report(
        title or f"گزارش OSINT — {target}",
        target,
        sections,
        timeline=timeline,
        sources=sources,
    )
    path.write_text(html_doc, encoding="utf-8")
    json_path.write_text(json.dumps({"target": target, "modules": modules_data, "sources": sources}, ensure_ascii=False, indent=2), encoding="utf-8")

    # Lightweight "PDF companion": same content as printable note (true PDF needs extra deps)
    txt_path = out_dir / f"{safe}.txt"
    lines = [f"گزارش OSINT: {target}", f"فایل HTML: {path.name}", ""]
    for sec in sections:
        lines.append(f"## {sec['title']}")
        lines.append(json.dumps(sec.get("data"), ensure_ascii=False, indent=2)[:5000])
        lines.append("")
    txt_path.write_text("\n".join(lines), encoding="utf-8")

    return {
        "ok": True,
        "html": str(path.relative_to(ws)),
        "json": str(json_path.relative_to(ws)),
        "text": str(txt_path.relative_to(ws)),
        "note": "برای چاپ PDF از مرورگر: باز کردن HTML → Print → Save as PDF",
    }


def tool_generate_osint_report(name: str, target: str, data_json: str | dict | None = "{}") -> dict[str, Any]:
    try:
        if isinstance(data_json, dict):
            data = data_json
        elif isinstance(data_json, str):
            data = json.loads(data_json) if data_json.strip() else {}
        else:
            data = {"value": data_json}
    except json.JSONDecodeError:
        data = {"raw": data_json}
    if not isinstance(data, dict):
        data = {"result": data}
    if not (name or "").strip():
        name = "report"
    if not (target or "").strip():
        target = "unknown"
    return save_report(name, target, data)
