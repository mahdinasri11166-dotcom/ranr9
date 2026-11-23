# -*- coding: utf-8 -*-
"""Session helpers: trim context + optional extractive summary."""
from __future__ import annotations
from typing import Any

def trim_messages(messages: list[dict], keep: int = 28) -> list[dict]:
    if len(messages) <= keep:
        return messages
    return messages[-keep:]

def extractive_summary(messages: list[dict], max_chars: int = 1200) -> str:
    parts = []
    for m in messages[-20:]:
        role = m.get("role") or ""
        content = (m.get("content") or "").strip().replace("\n", " ")
        if not content:
            continue
        parts.append(f"{role}: {content[:200]}")
    text = " | ".join(parts)
    return text[:max_chars]

def inject_summary_system(messages: list[dict], summary: str) -> list[dict]:
    if not summary:
        return messages
    note = {"role": "system", "content": f"[خلاصه سشن قبلی]\n{summary}"}
    return [note] + messages
