# -*- coding: utf-8 -*-
"""Policy hooks — unrestricted mode: no hard blocks (user-controlled product)."""
from __future__ import annotations

from typing import Any


def refuse_bruteforce(**kwargs) -> dict[str, Any]:
    """Legacy name kept for compatibility; no longer hard-blocks."""
    return {
        "ok": False,
        "blocked": False,
        "error": (
            "ابزار bruteforce داخلی پیاده‌سازی نشده است. "
            "می‌توانید ابزار سفارشی خود را در workspace/user_tools/ اضافه کنید."
        ),
        "policy": "unrestricted_v2",
        "hint": "see docs/ADD_TOOLS.md or workspace/user_tools/README.txt",
    }


def refuse_aggressive_vuln_scan(**kwargs) -> dict[str, Any]:
    """Legacy name kept for compatibility; no longer hard-blocks."""
    return {
        "ok": False,
        "blocked": False,
        "error": (
            "ابزار اسکن تهاجمی داخلی پیاده‌سازی نشده است. "
            "ابزار سفارشی را از workspace/user_tools/ ثبت کنید."
        ),
        "policy": "unrestricted_v2",
        "hint": "see docs/ADD_TOOLS.md",
    }
