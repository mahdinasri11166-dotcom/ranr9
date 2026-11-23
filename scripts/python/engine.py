# -*- coding: utf-8 -*-
"""Headless model engine — load/unload/chat with Win7-safe defaults."""
from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

from model_meta import read_gguf_metadata, estimate_ram_gb
from app_logging import get_logger

log = get_logger("engine")


def is_legacy_windows() -> bool:
    """True on Windows 7 / Server 2008 R2 and older (major < 6.2 or ver 6.1)."""
    if not sys.platform.startswith("win"):
        return False
    # env from our launcher
    if (os.environ.get("GGUF_OS_CLASS") or "").lower() == "legacy":
        return True
    try:
        v = sys.getwindowsversion()
        # Win7 = 6.1 ; Win8 = 6.2
        return (v.major, v.minor) <= (6, 1)
    except Exception:
        return False
    return False


def default_threads() -> int:
    n = os.cpu_count() or 4
    if is_legacy_windows():
        return max(1, min(4, n - 1 if n > 2 else n))
    return max(2, min(16, n - 1 if n > 2 else n))


def default_batch(n_ctx: int) -> int:
    if is_legacy_windows():
        return 128 if n_ctx <= 2048 else 256
    if n_ctx <= 2048:
        return 256
    if n_ctx <= 4096:
        return 512
    return min(1024, max(256, n_ctx // 8))


def safe_ctx_for_system(requested: int, model_size_bytes: int = 0) -> int:
    req = max(512, int(requested or 2048))
    if is_legacy_windows():
        # Win7 + small RAM: keep context modest
        req = min(req, 2048)
    # very small models still fine with 2048–4096
    if model_size_bytes and model_size_bytes < 800_000_000:
        req = min(req, 4096)
    return req


class LocalEngine:
    def __init__(self):
        self.llm = None
        self.model_path: Path | None = None
        self.n_gpu_layers = 0
        self.n_ctx = 2048 if is_legacy_windows() else 4096
        self.n_threads = default_threads()
        self.n_batch = 256
        self.meta: dict[str, Any] = {}
        self.load_opts: dict[str, Any] = {}

    def inspect(self, path: Path | str) -> dict[str, Any]:
        meta = read_gguf_metadata(path)
        est = estimate_ram_gb(meta.get("size_bytes") or 0, self.n_ctx, self.n_gpu_layers)
        meta["estimate"] = est
        meta["legacy_windows"] = is_legacy_windows()
        return meta

    def load(
        self,
        path: Path,
        n_ctx: int = 4096,
        n_gpu_layers: int = 0,
        n_threads: int | None = None,
        n_batch: int | None = None,
        use_mmap: bool = True,
        use_mlock: bool = False,
        flash_attn: bool | None = None,
    ) -> str:
        path = Path(path)
        if not path.is_file():
            return f"فایل مدل پیدا نشد:\n{path}"

        try:
            from llama_cpp import Llama
        except ImportError:
            return (
                "llama-cpp-python نصب نیست.\n"
                "Setup کامل از GitHub Actions را نصب کنید یا:\n"
                "python -m pip install llama-cpp-python"
            )
        except Exception as e:
            return self._friendly_dll_error(e)

        legacy = is_legacy_windows()
        try:
            self.unload()
            self.meta = read_gguf_metadata(path)
            size_b = int(self.meta.get("size_bytes") or path.stat().st_size)

            # Win7: force CPU, modest ctx (avoids GPU stacks & heavy paths)
            if legacy:
                n_gpu_layers = 0
                n_ctx = safe_ctx_for_system(min(int(n_ctx or 2048), 2048), size_b)
                use_mlock = False
                flash_attn = False
            else:
                n_ctx = safe_ctx_for_system(int(n_ctx or 4096), size_b)

            self.n_ctx = int(n_ctx)
            self.n_gpu_layers = int(n_gpu_layers or 0)
            self.n_threads = max(1, int(n_threads if n_threads is not None else default_threads()))
            self.n_batch = int(n_batch if n_batch is not None else default_batch(self.n_ctx))

            base: dict[str, Any] = dict(
                model_path=str(path.resolve()),
                n_ctx=self.n_ctx,
                n_gpu_layers=self.n_gpu_layers,
                n_threads=self.n_threads,
                verbose=False,
            )
            # mmap helps low-RAM; keep on for Win7
            if use_mmap:
                base["use_mmap"] = True

            optional_keys = []
            if not legacy:
                optional_keys.extend(
                    [
                        ("n_batch", self.n_batch),
                        ("use_mlock", bool(use_mlock)),
                        ("logits_all", False),
                        ("embedding", False),
                    ]
                )
                if self.n_gpu_layers != 0:
                    optional_keys.append(("offload_kqv", True))
                if flash_attn is True:
                    optional_keys.append(("flash_attn", True))
            else:
                # minimal kwargs for older llama-cpp on Win7
                optional_keys.append(("n_batch", self.n_batch))

            last_err: Exception | None = None
            # progressive: full optional → drop from end
            attempts = [dict(base)]
            acc = dict(base)
            for k, val in optional_keys:
                acc[k] = val
            attempts.insert(0, dict(acc))
            # also try without n_batch
            attempts.append({k: v for k, v in base.items()})

            for attempt in attempts:
                try:
                    log.info("Llama try keys=%s", sorted(attempt.keys()))
                    self.llm = Llama(**attempt)
                    self.load_opts = dict(attempt)
                    last_err = None
                    break
                except TypeError as e:
                    last_err = e
                    continue
                except OSError as e:
                    last_err = e
                    break
                except Exception as e:
                    last_err = e
                    # DLL entry-point errors often surface as generic Exception on Win
                    if self._is_win_entry_error(e):
                        break
                    continue

            if self.llm is None:
                raise last_err or RuntimeError("load failed")

            self.model_path = path
            log.info(
                "loaded %s ngl=%s ctx=%s threads=%s batch=%s legacy=%s",
                path.name,
                self.n_gpu_layers,
                self.n_ctx,
                self.n_threads,
                self.n_batch,
                legacy,
            )
            return ""
        except Exception as e:
            self.llm = None
            self.model_path = None
            return self._friendly_dll_error(e)

    def _is_win_entry_error(self, e: Exception) -> bool:
        msg = str(e).lower()
        return any(
            x in msg
            for x in (
                "setthreadinformation",
                "entry point",
                "kernel32",
                "procedure entry point",
                "0xc000001d",
                "c000001d",
                "-1073741795",
                "illegal instruction",
                "dll",
                "winerror",
            )
        )

    def _friendly_dll_error(self, e: Exception) -> str:
        msg = str(e)
        low = msg.lower()
        log.error("load failed: %s", msg)
        if self._is_win_entry_error(e) or "setthreadinformation" in low:
            return (
                "ناسازگاری با ویندوز ۷ (KERNEL32 / SetThreadInformation).\n"
                "کتابخانهٔ llama-cpp-python یا DLL همراه آن برای ویندوز ۸+ ساخته شده است.\n\n"
                "راه‌حل‌ها:\n"
                "۱) روی همین Win7: نسخهٔ قدیمی‌تر wheel:\n"
                "   python38\\python.exe -m pip install \"llama-cpp-python==0.2.20\" --force-reinstall\n"
                "۲) یا برنامه را روی ویندوز ۱۰/۱۱ اجرا کنید.\n"
                "۳) ctx را ۲۰۰۰ و GPU layers را ۰ بگذارید و دوباره لود کنید.\n\n"
                f"جزئیات: {msg}"
            )
        if "out of memory" in low or "oom" in low or "failed to allocate" in low:
            return (
                "حافظه کافی نیست.\n"
                "ctx را روی ۲۰۴۸ یا ۱۰۲۴ بگذارید، GPU layers = 0، مدل کوچک‌تر استفاده کنید.\n"
                f"{msg}"
            )
        if "cuda" in low:
            return "مشکل GPU — n_gpu_layers=0 تنظیم کنید.\n" + msg
        if "not a directory" in low or "no such file" in low or "cannot open" in low:
            return f"باز کردن فایل مدل ناموفق بود:\n{msg}"
        return msg

    def unload(self) -> None:
        if self.llm is not None:
            log.info("unload %s", self.model_path)
        self.llm = None
        self.model_path = None
        self.meta = {}
        self.load_opts = {}

    def chat(
        self,
        messages,
        temperature=0.7,
        max_tokens=1024,
        top_p=0.9,
        top_k: int = 40,
        repeat_penalty: float = 1.08,
        stream=True,
    ):
        if not self.llm:
            raise RuntimeError("مدلی لود نشده")
        # smaller max_tokens on legacy to reduce crash risk
        if is_legacy_windows():
            max_tokens = min(int(max_tokens or 512), 512)
        kwargs = dict(
            messages=messages,
            temperature=float(temperature),
            max_tokens=int(max_tokens),
            top_p=float(top_p),
            stream=stream,
        )
        for key, val in (("top_k", int(top_k)), ("repeat_penalty", float(repeat_penalty))):
            kwargs[key] = val
        try:
            return self.llm.create_chat_completion(**kwargs)
        except TypeError:
            kwargs.pop("top_k", None)
            try:
                return self.llm.create_chat_completion(**kwargs)
            except TypeError:
                kwargs.pop("repeat_penalty", None)
                return self.llm.create_chat_completion(**kwargs)

    def performance_summary(self) -> str:
        if not self.model_path:
            return "مدلی لود نشده"
        leg = " | Win7-safe" if is_legacy_windows() else ""
        return (
            f"{self.model_path.name} | ctx={self.n_ctx} | "
            f"threads={self.n_threads} | batch={self.n_batch} | "
            f"ngl={self.n_gpu_layers}{leg}"
        )
