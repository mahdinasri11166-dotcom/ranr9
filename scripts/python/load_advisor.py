# -*- coding: utf-8 -*-
"""Suggest ctx / n_gpu_layers / threads / batch from GGUF size and system RAM."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from model_meta import read_gguf_metadata, estimate_ram_gb


def _system_ram_gb() -> float | None:
    try:
        import os

        if hasattr(os, "sysconf"):
            pages = os.sysconf("SC_PHYS_PAGES")
            page = os.sysconf("SC_PAGE_SIZE")
            return round(pages * page / (1024**3), 1)
    except Exception:
        pass
    try:
        import ctypes

        class MEMORYSTATUSEX(ctypes.Structure):
            _fields_ = [
                ("dwLength", ctypes.c_ulong),
                ("dwMemoryLoad", ctypes.c_ulong),
                ("ullTotalPhys", ctypes.c_ulonglong),
                ("ullAvailPhys", ctypes.c_ulonglong),
                ("ullTotalPageFile", ctypes.c_ulonglong),
                ("ullAvailPageFile", ctypes.c_ulonglong),
                ("ullTotalVirtual", ctypes.c_ulonglong),
                ("ullAvailVirtual", ctypes.c_ulonglong),
                ("sullAvailExtendedVirtual", ctypes.c_ulonglong),
            ]

        stat = MEMORYSTATUSEX()
        stat.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
        ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat))
        return round(stat.ullTotalPhys / (1024**3), 1)
    except Exception:
        return None


def _cpu_threads() -> int:
    import os

    n = os.cpu_count() or 4
    return max(2, min(16, n - 1 if n > 2 else n))


def suggest_load(path: Path | str, prefer_gpu: bool = False, preset: str = "balanced") -> dict[str, Any]:
    """
    preset: fast | balanced | quality
      fast     — smaller ctx, more batch, aggressive threads
      balanced — default
      quality  — larger ctx when RAM allows
    """
    path = Path(path)
    meta = read_gguf_metadata(path)
    size_gb = float(meta.get("size_gb") or 0)
    ram = _system_ram_gb()
    threads = _cpu_threads()

    # base ctx
    ctx = 4096
    if size_gb >= 5:
        ctx = 3072
    if size_gb >= 7:
        ctx = 2048
    if size_gb >= 12:
        ctx = 2048
    if ram is not None and ram < 8:
        ctx = min(ctx, 2048)
    if ram is not None and ram < 6:
        ctx = 1024
    if ram is not None and ram >= 16 and size_gb < 5 and preset == "quality":
        ctx = 8192
    if preset == "fast":
        ctx = min(ctx, 2048)
        threads = min(16, threads + 1)
    if preset == "quality" and ram is not None and ram >= 12:
        ctx = max(ctx, 4096)

    ngl = 0
    gpu_note = "CPU (امن و پایدار)"
    if prefer_gpu:
        if ram is not None and ram >= 12 and size_gb < 8:
            ngl = 33
            gpu_note = "GPU جزئی (ngl=33) — نیاز به llama-cpp با CUDA/Metal"
        elif ram is not None and ram >= 16 and size_gb < 12:
            ngl = 20
            gpu_note = "GPU سبک (ngl=20)"
        else:
            gpu_note = "رم/حجم مدل برای GPU خودکار کافی نیست → CPU"

    # batch scales with ctx
    if ctx <= 2048:
        batch = 512 if preset == "fast" else 256
    elif ctx <= 4096:
        batch = 512
    else:
        batch = 1024 if preset != "fast" else 512

    est = estimate_ram_gb(meta.get("size_bytes") or 0, ctx, ngl)
    return {
        "ok": True,
        "path": str(path),
        "meta": meta,
        "suggested_ctx": ctx,
        "suggested_ngl": ngl,
        "suggested_threads": threads,
        "suggested_batch": batch,
        "system_ram_gb": ram,
        "estimate": est,
        "preset": preset,
        "note_fa": gpu_note,
        "tips_fa": [
            "mmap فعال است تا لود سریع‌تر و RAM کمتر باشد",
            "برای سرعت بیشتر: preset=fast یا GPU layers",
            "برای متن بلند: preset=quality و RAM کافی",
            "اگر OOM شد: ctx را نصف کنید یا ngl=0",
        ],
    }
