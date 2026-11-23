# -*- coding: utf-8 -*-
"""Doctor قوی + پیام خطای فارسی + ویزارد مدل."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))


def _ok(msg: str) -> dict:
    return {"level": "ok", "msg": msg}


def _warn(msg: str, fix: str = "") -> dict:
    return {"level": "warn", "msg": msg, "fix": fix}


def _err(msg: str, fix: str = "") -> dict:
    return {"level": "error", "msg": msg, "fix": fix}


def run_doctor() -> dict:
    findings = []
    # folders
    for d in ("models", "workspace", "sessions", "memory", "scripts/python", "bin"):
        p = ROOT / d
        if p.exists():
            findings.append(_ok(f"پوشه موجود است: {d}"))
        else:
            try:
                p.mkdir(parents=True, exist_ok=True)
                findings.append(_warn(f"پوشه ساخته شد: {d}", "نیازی به کار شما نیست"))
            except Exception as e:
                findings.append(_err(f"ساختن پوشه {d} ممکن نشد", str(e)))

    # python modules
    for mod in (
        "desktop_chat", "app_hub", "agent_tools", "osint_tools", "osint_advanced",
        "report_engine", "plugin_system", "browser_readonly", "rag_local", "openai_api_server", "elevated_tools", "builder_tools", "system_named_tools", "agent_memory", "browser_tools", "coding_tools",
    ):
        p = ROOT / "scripts" / "python" / f"{mod}.py"
        if p.exists():
            findings.append(_ok(f"ماژول: {mod}.py"))
        else:
            findings.append(_err(f"ماژول کم است: {mod}.py", "پروژه را دوباره از ZIP کامل استخراج کنید"))

    # deps
    try:
        import customtkinter  # noqa
        findings.append(_ok("کتابخانه customtkinter نصب است"))
    except ImportError:
        findings.append(_err("customtkinter نیست", "SETUP.bat را اجرا کنید یا: pip install customtkinter"))

    try:
        import llama_cpp  # noqa
        findings.append(_ok("کتابخانه llama-cpp-python نصب است (چت دسکتاپ)"))
    except ImportError:
        findings.append(_err(
            "llama-cpp-python نیست — مدل GGUF لود نمی‌شود",
            "SETUP.bat را با اینترنت اجرا کنید یا نصب‌کننده Offline کامل از Actions بگیرید",
        ))

    for pkg, name in (("PIL", "Pillow"), ("pypdf", "pypdf"), ("numpy", "numpy"), ("requests", "requests"), ("psutil", "psutil")):
        try:
            __import__(pkg if pkg != "PIL" else "PIL")
            findings.append(_ok(f"{name} نصب است"))
        except ImportError:
            findings.append(_warn(f"{name} نیست (اختیاری برای بعضی ابزارها)", f"pip install {name}"))

    # models
    models = list((ROOT / "models").glob("*.gguf")) if (ROOT / "models").exists() else []
    if models:
        findings.append(_ok(f"{len(models)} مدل GGUF پیدا شد"))
        for m in models[:5]:
            mb = m.stat().st_size / (1024 * 1024)
            findings.append(_ok(f"  • {m.name} ({mb:.1f} MB)"))
    else:
        findings.append(_err(
            "هیچ فایل .gguf در models\\ نیست",
            "یک مدل کوچک CPU (مثلاً 1B–3B Q4) را در models کپی کنید — ویزارد مدل را ببینید",
        ))

    server = ROOT / "bin" / "llama-server.exe"
    if server.exists():
        findings.append(_ok("llama-server.exe موجود است (حالت وب)"))
    else:
        findings.append(_warn("llama-server.exe نیست", "اختیاری؛ چت دسکتاپ بدون آن کار می‌کند"))

    offline_marker = ROOT / "python" / "gguf_runner_offline.json"
    if offline_marker.exists():
        findings.append(_ok("مارکر پشته آفلاین نصب‌کننده موجود است"))
    elif (ROOT / "python" / "python.exe").exists():
        findings.append(_warn("Python توکار هست ولی مارکر آفلاین نیست", "در صورت خطا SETUP.bat را بزنید"))

    if (ROOT / "INSTALL.bat").exists():
        findings.append(_ok("INSTALL.bat (نصب آسان) موجود است"))
    # Tcl/Tk for embeddable Python
    import os
    py_home = ROOT / "python"
    if py_home.exists():
        tcl = py_home / "tcl" / "tcl8.6"
        if not tcl.exists():
            findings.append(_warn("python/tcl/tcl8.6 نیست — UI ممکن است fail شود", "نصب‌کننده آفلاین را دوباره بسازید یا Tcl/Tk را کپی کنید"))
        elif not os.environ.get("TCL_LIBRARY"):
            findings.append({"level": "info", "msg": "TCL_LIBRARY در این پروسه ست نیست (با CHAT.bat ست می‌شود)", "fix": "از START.bat / CHAT.bat اجرا کنید"})

    errors = sum(1 for f in findings if f["level"] == "error")
    warns = sum(1 for f in findings if f["level"] == "warn")
    return {
        "ok": errors == 0,
        "errors": errors,
        "warnings": warns,
        "findings": findings,
        "summary_fa": (
            "همه‌چیز آماده است." if errors == 0 and warns == 0
            else ("آماده با هشدار." if errors == 0 else "مشکلاتی هست که باید رفع شود.")
        ),
    }


def model_wizard() -> dict:
    """پیشنهاد مدل‌های مناسب CPU و مسیر قرارگیری — بدون دانلود اجباری."""
    tips = [
        {
            "name": "مدل خیلی کوچک (CPU ضعیف)",
            "params": "1B–1.5B",
            "quant": "Q4_K_M یا Q5_K_M",
            "hint": "برای لپ‌تاپ ۸ گیگ رم؛ پاسخ سریع‌تر، کیفیت متوسط",
        },
        {
            "name": "مدل متعادل",
            "params": "3B–7B",
            "quant": "Q4_K_M",
            "hint": "تعادل سرعت/کیفیت روی CPU قوی یا GPU با n_gpu_layers",
        },
        {
            "name": "کیفیت بالاتر",
            "params": "7B–14B",
            "quant": "Q5_K_M / Q6",
            "hint": "رم و زمان بیشتری می‌خواهد",
        },
    ]
    return {
        "ok": True,
        "models_dir": str(ROOT / "models"),
        "steps_fa": [
            "۱. از Hugging Face یا مخازن GGUF یک فایل .gguf دانلود کنید",
            "۲. فایل را فقط داخل پوشه models کپی کنید (نه زیپ تودرتو)",
            "۳. CHAT.bat را باز کنید → Refresh → Load",
            "۴. اگر خطای حافظه دیدید quant سبک‌تر یا ctx_size کوچکتر انتخاب کنید",
        ],
        "recommendations": tips,
        "note_fa": "این برنامه مدل را میزبانی یا دانلود اجباری نمی‌کند؛ فقط فایل محلی را اجرا می‌کند.",
    }


def print_doctor():
    r = run_doctor()
    print("=== GGUF Doctor ===")
    print(r["summary_fa"])
    for f in r["findings"]:
        mark = {"ok": "[OK]", "warn": "[!]", "error": "[X]"}[f["level"]]
        print(f"  {mark} {f['msg']}")
        if f.get("fix"):
            print(f"       → {f['fix']}")
    print()
    w = model_wizard()
    print("=== ویزارد مدل ===")
    for s in w["steps_fa"]:
        print(" ", s)
    print(" پوشه مدل‌ها:", w["models_dir"])
    for t in w["recommendations"]:
        print(f"  - {t['name']}: {t['params']} / {t['quant']} — {t['hint']}")
    return 0 if r["ok"] else 1


if __name__ == "__main__":
    sys.exit(print_doctor())
