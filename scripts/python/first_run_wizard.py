# -*- coding: utf-8 -*-
"""
ویزارد اولین اجرا — GGUF Runner
مراحل: خوش‌آمد → بررسی محیط → مدل‌ها → تست لود (اختیاری) → پایان
"""
from __future__ import annotations

import json
import sys
import threading
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from config_loader import ROOT, list_models, load_ini, save_ini

MARKER = ROOT / "workspace" / ".first_run_done.json"

try:
    import customtkinter as ctk
    _HAS_CTK = True
except ImportError:
    ctk = None  # type: ignore
    _HAS_CTK = False

from doctor import run_doctor, model_wizard

APP_VERSION = "2.7.0"
if _HAS_CTK:
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("dark-blue")


def mark_done(extra: dict | None = None) -> None:
    MARKER.parent.mkdir(parents=True, exist_ok=True)
    data = {"done": True, "version": APP_VERSION}
    if extra:
        data.update(extra)
    try:
        from datetime import datetime, timezone
        data["at"] = datetime.now(timezone.utc).isoformat()
    except Exception:
        pass
    MARKER.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def is_first_run() -> bool:
    return not MARKER.exists()


class FirstRunWizard((ctk.CTk if _HAS_CTK else object)):
    def __init__(self, force: bool = False):
        super().__init__()
        self.title(f"ویزارد اولین اجرا — GGUF Runner v{APP_VERSION}")
        self.geometry("780x560")
        self.minsize(700, 480)
        self.force = force
        self.step = 0
        self.doctor_result: dict = {}
        self.selected_model: str | None = None
        self.load_test_ok = False

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self.header = ctk.CTkLabel(
            self,
            text="ویزارد راه‌اندازی اولیه",
            font=ctk.CTkFont(size=20, weight="bold"),
        )
        self.header.grid(row=0, column=0, pady=(16, 4), sticky="n")

        self.progress = ctk.CTkProgressBar(self, width=520)
        self.progress.grid(row=0, column=0, pady=(48, 0), sticky="n")
        self.progress.set(0.2)

        self.body = ctk.CTkFrame(self, fg_color="transparent")
        self.body.grid(row=1, column=0, sticky="nsew", padx=20, pady=10)
        self.body.grid_columnconfigure(0, weight=1)
        self.body.grid_rowconfigure(0, weight=1)

        self.footer = ctk.CTkFrame(self, fg_color="transparent")
        self.footer.grid(row=2, column=0, sticky="ew", padx=16, pady=12)
        self.btn_back = ctk.CTkButton(self.footer, text="قبلی", width=100, command=self._back, state="disabled")
        self.btn_back.pack(side="left", padx=4)
        self.btn_skip = ctk.CTkButton(self.footer, text="رد کردن ویزارد", width=120, fg_color="#555", command=self._skip)
        self.btn_skip.pack(side="left", padx=4)
        self.btn_next = ctk.CTkButton(self.footer, text="بعدی", width=120, fg_color="#e94560", command=self._next)
        self.btn_next.pack(side="right", padx=4)

        self._show_step(0)

    def _clear_body(self):
        for w in self.body.winfo_children():
            w.destroy()

    def _show_step(self, step: int):
        self.step = step
        self._clear_body()
        self.progress.set((step + 1) / 5)
        self.btn_back.configure(state="normal" if step > 0 else "disabled")
        if step == 0:
            self._step_welcome()
            self.btn_next.configure(text="شروع بررسی")
        elif step == 1:
            self._step_environment()
            self.btn_next.configure(text="بعدی: مدل‌ها")
        elif step == 2:
            self._step_models()
            self.btn_next.configure(text="بعدی")
        elif step == 3:
            self._step_load_test()
            self.btn_next.configure(text="بعدی: پایان")
        else:
            self._step_finish()
            self.btn_next.configure(text="باز کردن چت")

    def _step_welcome(self):
        box = ctk.CTkFrame(self.body)
        box.grid(row=0, column=0, sticky="nsew")
        ctk.CTkLabel(
            box,
            text="به GGUF Runner خوش آمدید",
            font=ctk.CTkFont(size=18, weight="bold"),
        ).pack(pady=(24, 8))
        ctk.CTkLabel(
            box,
            text=(
                "این ویزارد محیط را بررسی می‌کند، پوشه مدل را آماده می‌کند\n"
                "و برای اولین چت شما را راهنمایی می‌کند.\n\n"
                "• مدل‌های .gguf را خودتان در پوشه models می‌گذارید\n"
                "• اینترنت بعد از نصب آفلاین معمولاً لازم نیست\n"
                "• ابزارهای OSINT شبکه‌ای فقط هنگام استفاده اینترنت می‌خواهند"
            ),
            justify="center",
            font=ctk.CTkFont(size=14),
        ).pack(pady=12, padx=24)
        ctk.CTkLabel(
            box,
            text="تیم: مهدی طریری · محسن طریفی",
            text_color="gray",
        ).pack(pady=(8, 16))

    def _step_environment(self):
        box = ctk.CTkFrame(self.body)
        box.grid(row=0, column=0, sticky="nsew")
        box.grid_rowconfigure(1, weight=1)
        box.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(box, text="بررسی محیط", font=ctk.CTkFont(size=16, weight="bold")).grid(
            row=0, column=0, pady=8
        )
        self.env_text = ctk.CTkTextbox(box, font=ctk.CTkFont(size=13))
        self.env_text.grid(row=1, column=0, sticky="nsew", padx=8, pady=8)
        self.env_text.insert("end", "در حال بررسی...\n")
        row = ctk.CTkFrame(box, fg_color="transparent")
        row.grid(row=2, column=0, pady=6)
        ctk.CTkButton(row, text="اجرای دوباره Doctor", command=self._run_doctor_async).pack(side="left", padx=4)

        self._run_doctor_async()

    def _run_doctor_async(self):
        self.env_text.delete("1.0", "end")
        self.env_text.insert("end", "در حال بررسی محیط، لطفاً صبر کنید...\n")

        def work():
            try:
                res = run_doctor()
            except Exception as e:
                res = {
                    "ok": False,
                    "summary_fa": f"خطا در Doctor: {e}",
                    "findings": [{"level": "error", "msg": str(e), "fix": "SETUP.bat"}],
                    "errors": 1,
                    "warnings": 0,
                }
            self.after(0, lambda: self._fill_doctor(res))

        threading.Thread(target=work, daemon=True).start()

    def _fill_doctor(self, res: dict):
        self.doctor_result = res
        self.env_text.delete("1.0", "end")
        self.env_text.insert("end", (res.get("summary_fa") or "") + "\n\n")
        for f in res.get("findings") or []:
            mark = {"ok": "✓", "warn": "!", "error": "✗"}.get(f.get("level"), "·")
            line = f"[{mark}] {f.get('msg', '')}\n"
            if f.get("fix"):
                line += f"     → {f['fix']}\n"
            self.env_text.insert("end", line)
        if res.get("errors"):
            self.env_text.insert(
                "end",
                "\nاگر وابستگی کم است: SETUP.bat را اجرا کنید و ویزارد را دوباره باز کنید.\n",
            )

    def _step_models(self):
        box = ctk.CTkFrame(self.body)
        box.grid(row=0, column=0, sticky="nsew")
        box.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(box, text="مدل‌های GGUF", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=8)

        tips = model_wizard()
        tip_frame = ctk.CTkFrame(box)
        tip_frame.pack(fill="x", padx=12, pady=4)
        ctk.CTkLabel(tip_frame, text="پیشنهاد انتخاب مدل", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=8, pady=4)
        for s in tips.get("steps_fa") or []:
            ctk.CTkLabel(tip_frame, text=s, anchor="w").pack(anchor="w", padx=12)
        for rec in tips.get("recommendations") or []:
            ctk.CTkLabel(
                tip_frame,
                text=f"• {rec.get('name')}: {rec.get('params')} / {rec.get('quant')} — {rec.get('hint')}",
                anchor="w",
                wraplength=680,
                justify="right",
            ).pack(anchor="w", padx=12, pady=2)

        models = list_models()
        names = [m.name for m in models]
        self.model_var = ctk.StringVar(value=names[0] if names else "")
        ctk.CTkLabel(box, text=f"مدل‌های پیدا شده: {len(names)}").pack(pady=(12, 4))
        if names:
            self.model_menu = ctk.CTkOptionMenu(box, variable=self.model_var, values=names, width=400)
            self.model_menu.pack(pady=4)
            self.selected_model = names[0]
        else:
            ctk.CTkLabel(
                box,
                text="هنوز فایلی نیست. دکمه زیر را بزنید و یک .gguf در models کپی کنید، سپس تازه‌سازی.",
                text_color="#e94560",
                wraplength=640,
            ).pack(pady=8)

        row = ctk.CTkFrame(box, fg_color="transparent")
        row.pack(pady=10)
        ctk.CTkButton(row, text="باز کردن پوشه models", command=self._open_models).pack(side="left", padx=4)
        ctk.CTkButton(row, text="تازه‌سازی لیست", command=lambda: self._show_step(2)).pack(side="left", padx=4)

        self.models_status = ctk.CTkLabel(box, text="", text_color="gray")
        self.models_status.pack(pady=6)

    def _open_models(self):
        import os
        import subprocess
        d = ROOT / "models"
        d.mkdir(parents=True, exist_ok=True)
        try:
            if hasattr(os, "startfile"):
                os.startfile(str(d))
            else:
                subprocess.Popen(["xdg-open", str(d)])
        except Exception as e:
            self.models_status.configure(text=str(e))

    def _step_load_test(self):
        box = ctk.CTkFrame(self.body)
        box.grid(row=0, column=0, sticky="nsew")
        ctk.CTkLabel(box, text="تست بارگذاری مدل (اختیاری)", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=8)
        ctk.CTkLabel(
            box,
            text="اگر مدل دارید می‌توانید یک بار لود آزمایشی کنید تا از صحت GGUF و RAM مطمئن شوید.\n"
            "مدل‌های خیلی بزرگ ممکن است چند دقیقه طول بکشد یا حافظه کم بیاورد.",
            wraplength=660,
            justify="center",
        ).pack(pady=8)

        models = list_models()
        names = [m.name for m in models]
        self.test_model_var = ctk.StringVar(value=names[0] if names else "")
        if names:
            ctk.CTkOptionMenu(box, variable=self.test_model_var, values=names, width=400).pack(pady=6)
            ctk.CTkButton(box, text="شروع تست لود", fg_color="#e94560", command=self._run_load_test).pack(pady=8)
        else:
            ctk.CTkLabel(box, text="مدلی برای تست نیست — می‌توانید این مرحله را رد کنید.", text_color="#e94560").pack(pady=12)

        self.test_log = ctk.CTkTextbox(box, height=180)
        self.test_log.pack(fill="both", expand=True, padx=12, pady=8)

    def _run_load_test(self):
        name = self.test_model_var.get()
        path = ROOT / "models" / name
        self.test_log.delete("1.0", "end")
        self.test_log.insert("end", f"در حال لود: {name}\nلطفاً صبر کنید...\n")

        def work():
            try:
                from llama_cpp import Llama
            except ImportError:
                self.after(0, lambda: self._test_done(False, "llama-cpp-python نصب نیست. SETUP.bat را اجرا کنید."))
                return
            cfg = load_ini()
            try:
                n_ctx = min(int(cfg.get("ctx_size") or 2048), 2048)
                llm = Llama(
                    model_path=str(path),
                    n_ctx=n_ctx,
                    n_gpu_layers=int(cfg.get("n_gpu_layers") or 0),
                    n_threads=int(cfg.get("threads") or 4),
                    verbose=False,
                )
                # tiny completion smoke test
                out = llm.create_chat_completion(
                    messages=[{"role": "user", "content": "بگو: OK"}],
                    max_tokens=8,
                    temperature=0,
                )
                text = ""
                try:
                    text = out["choices"][0]["message"]["content"]
                except Exception:
                    text = str(out)[:200]
                del llm
                self.after(0, lambda: self._test_done(True, f"موفق.\nپاسخ نمونه: {text}\nctx تست: {n_ctx}"))
            except Exception as e:
                msg = f"ناموفق: {e}\n{traceback.format_exc()[:400]}"
                self.after(0, lambda: self._test_done(False, msg))

        threading.Thread(target=work, daemon=True).start()

    def _test_done(self, ok: bool, msg: str):
        self.load_test_ok = ok
        self.test_log.insert("end", msg + "\n")
        if ok:
            self.selected_model = self.test_model_var.get()
            cfg = load_ini()
            cfg["model"] = self.selected_model
            try:
                save_ini(cfg)
            except Exception:
                pass

    def _step_finish(self):
        box = ctk.CTkFrame(self.body)
        box.grid(row=0, column=0, sticky="nsew")
        ctk.CTkLabel(box, text="آماده استفاده", font=ctk.CTkFont(size=18, weight="bold")).pack(pady=(20, 8))
        models = list_models()
        lines = [
            f"وضعیت Doctor: {self.doctor_result.get('summary_fa') or '—'}",
            f"تعداد مدل: {len(models)}",
            f"تست لود: {'موفق' if self.load_test_ok else 'انجام نشد / ناموفق (اختیاری)'}",
            "",
            "مرحله بعد:",
            "1) اگر مدل ندارید در models یک فایل .gguf بگذارید",
            "2) CHAT.bat یا دکمه زیر را بزنید",
            "3) Agent / OSINT را از سایدبار فعال کنید",
        ]
        ctk.CTkLabel(box, text="\n".join(lines), justify="right", font=ctk.CTkFont(size=14)).pack(padx=20, pady=10)
        row = ctk.CTkFrame(box, fg_color="transparent")
        row.pack(pady=12)
        ctk.CTkButton(row, text="Doctor دوباره", command=lambda: self._show_step(1)).pack(side="left", padx=4)
        ctk.CTkButton(row, text="پوشه models", command=self._open_models).pack(side="left", padx=4)

    def _next(self):
        if self.step == 2 and hasattr(self, "model_var"):
            try:
                if list_models():
                    self.selected_model = self.model_var.get()
            except Exception:
                pass
        if self.step >= 4:
            mark_done({"model": self.selected_model, "load_test_ok": self.load_test_ok})
            self._launch_chat()
            return
        self._show_step(self.step + 1)

    def _back(self):
        if self.step > 0:
            self._show_step(self.step - 1)

    def _skip(self):
        mark_done({"skipped": True})
        self.destroy()

    def _launch_chat(self):
        mark_done({"model": self.selected_model, "load_test_ok": self.load_test_ok, "launch_chat": True})
        self.destroy()
        # launch desktop chat in-process if possible
        try:
            from desktop_chat import DesktopChat
            app = DesktopChat()
            app.mainloop()
        except Exception as e:
            print("Chat launch failed:", e)
            traceback.print_exc()
            try:
                input("Enter...")
            except Exception:
                pass


def main(argv: list[str] | None = None):
    if not _HAS_CTK:
        print("[ERROR] customtkinter نصب نیست. SETUP.bat را اجرا کنید.")
        raise SystemExit(1)
    argv = argv or sys.argv[1:]
    force = "--force" in argv or "-f" in argv
    if not force and not is_first_run():
        # still allow opening wizard; only FirstRun.bat uses auto
        pass
    # ensure folders
    for d in ("models", "workspace", "sessions", "memory"):
        (ROOT / d).mkdir(parents=True, exist_ok=True)
    app = FirstRunWizard(force=force)
    app.mainloop()


if __name__ == "__main__":
    main()
