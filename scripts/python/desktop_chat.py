# -*- coding: utf-8 -*-
"""
GGUF Runner — Desktop Chat v2.4
Team: Mehdi Tariri · Mohsen Tarifii
Features: GGUF chat, Agent + Approval Gate, OSINT tools, sessions, profiles
"""
from __future__ import annotations

import json
import sys
import threading
import time
import traceback
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

try:
    import customtkinter as ctk
    _HAS_CTK = True
except ImportError:
    ctk = None  # type: ignore
    _HAS_CTK = False

from config_loader import (
    ROOT,
    list_models,
    load_ini,
    load_profile,
    sessions_dir,
    workspace_dir,
    save_ini,
    identity_system_suffix,
)
from agent_tools import (
    execute_tool,
    needs_approval,
    tools_schema_for_prompt,
)

APP_VERSION = "2.6.0"

def _safe_int(val, default=0, lo=None, hi=None):
    try:
        n = int(float(str(val).strip()))
    except Exception:
        return default
    if lo is not None:
        n = max(lo, n)
    if hi is not None:
        n = min(hi, n)
    return n


def _safe_float(val, default=0.0, lo=None, hi=None):
    try:
        n = float(str(val).strip())
    except Exception:
        return default
    if lo is not None:
        n = max(lo, n)
    if hi is not None:
        n = min(hi, n)
    return n


if _HAS_CTK:
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("dark-blue")

HELP_TEXT = """Slash commands:
  /help              این راهنما
  /clear             پاک کردن صفحه
  /new               سشن جدید
  /save              ذخیره سشن
  /sessions          لیست سشن‌ها
  /open <file.json>  بارگذاری سشن
  /export [file]     خروجی Markdown سشن
  /agent on|off      حالت Agent
  /osint on|off|<t>  تمرکز OSINT یا گزارش سریع
  /case list|new|export
  /rag <query>       جستجوی حافظه/RAG
  /buildrag          ساخت ایندکس RAG از books/memory
  /doctor            تشخیص محیط
  /elevated on|off   حالت مدیر سیستم (نیاز تأیید هر دستور)
  /scaffold <name> [template]  ساخت پروژه در workspace/projects
  /templates         لیست قالب‌های ساخت
  /models            لیست مدل‌ها
  /load <file.gguf>  لود مدل
  /system <text>     system prompt این سشن
"""


class LlamaEngine:
    def __init__(self):
        self.llm = None
        self.model_path: Path | None = None
        self.n_ctx = 4096

    def load(self, path: Path, n_ctx: int = 4096, n_gpu_layers: int = 0, n_threads: int = 4) -> str:
        try:
            from llama_cpp import Llama
        except ImportError:
            return "llama-cpp-python is not installed. Run SETUP.bat"
        self.unload()
        try:
            self.llm = Llama(
                model_path=str(path),
                n_ctx=n_ctx,
                n_gpu_layers=n_gpu_layers,
                n_threads=n_threads,
                verbose=False,
            )
            self.model_path = path
            self.n_ctx = n_ctx
            return ""
        except Exception as e:
            self.llm = None
            return str(e)

    def unload(self):
        self.llm = None
        self.model_path = None

    def chat(self, messages, temperature=0.7, max_tokens=1024, top_p=0.9, repeat_penalty=1.1, stream=True):
        if not self.llm:
            raise RuntimeError("No model loaded")
        return self.llm.create_chat_completion(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            top_p=top_p,
            repeat_penalty=repeat_penalty,
            stream=stream,
        )


class ApprovalDialog((ctk.CTkToplevel if _HAS_CTK else object)):
    def __init__(self, master, tool_name: str, arguments: dict, require_yes: bool = True):
        super().__init__(master)
        self.title("Approval Gate")
        self.geometry("540x380")
        self.result = False
        self.require_yes = require_yes
        self.transient(master)
        self.grab_set()

        ctk.CTkLabel(self, text="Tool requires approval", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=(12, 4))
        ctk.CTkLabel(self, text=f"Tool: {tool_name}", text_color="#e94560").pack()
        box = ctk.CTkTextbox(self, height=190)
        box.pack(fill="both", expand=True, padx=12, pady=8)
        raw = json.dumps({"tool": tool_name, "arguments": arguments}, ensure_ascii=False, indent=2)
        box.insert("1.0", raw)
        box.configure(state="disabled")

        self.entry = None
        if require_yes:
            ctk.CTkLabel(self, text="Type YES to confirm high-risk tool:").pack()
            self.entry = ctk.CTkEntry(self, width=120)
            self.entry.pack(pady=4)

        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(pady=10)
        ctk.CTkButton(row, text="Allow", width=100, command=self._ok, fg_color="#22c55e").pack(side="left", padx=6)
        ctk.CTkButton(row, text="Deny", width=100, command=self._no, fg_color="#ef4444").pack(side="left", padx=6)

    def _ok(self):
        if self.require_yes and self.entry and self.entry.get().strip().upper() != "YES":
            return
        self.result = True
        self.destroy()

    def _no(self):
        self.result = False
        self.destroy()


class DesktopChat((ctk.CTk if _HAS_CTK else object)):
    def __init__(self):
        super().__init__()
        self.title(f"GGUF Runner Desktop Chat v{APP_VERSION}")
        self.geometry("1180x740")
        self.minsize(860, 580)

        self.cfg = load_ini()
        self.engine = LlamaEngine()
        self.messages: list[dict] = []
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.agent_mode = False
        self.osint_mode = False
        self.busy = False
        self._asst_started = False
        self.system_prompt = self.cfg.get("system_prompt") or "You are a helpful assistant."
        self.profile_name = "default"

        self._build_ui()
        self._refresh_models()
        self._log_system(f"GGUF Runner v{APP_VERSION} | workspace: {workspace_dir()}")
        self._log_system("Commands: /help  |  Put .gguf in models\\ then Load")

    def _build_ui(self):
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        side = ctk.CTkFrame(self, width=270, corner_radius=0)
        side.grid(row=0, column=0, sticky="nsew")
        side.grid_propagate(False)

        ctk.CTkLabel(side, text="GGUF Runner", font=ctk.CTkFont(size=18, weight="bold")).pack(pady=(14, 2))
        ctk.CTkLabel(side, text=f"v{APP_VERSION} · OSINT + Agent", text_color="gray").pack(pady=(0, 10))

        ctk.CTkLabel(side, text="Model").pack(anchor="w", padx=12)
        self.model_var = ctk.StringVar(value="")
        self.model_menu = ctk.CTkOptionMenu(side, variable=self.model_var, values=["(no models)"], width=230)
        self.model_menu.pack(padx=12, pady=4)

        row_m = ctk.CTkFrame(side, fg_color="transparent")
        row_m.pack(fill="x", padx=12, pady=4)
        ctk.CTkButton(row_m, text="Refresh", width=95, command=self._refresh_models).pack(side="left", padx=2)
        ctk.CTkButton(row_m, text="Load", width=95, command=self._load_model, fg_color="#e94560").pack(side="left", padx=2)

        ctk.CTkLabel(side, text="Profile").pack(anchor="w", padx=12, pady=(10, 0))
        self.profile_var = ctk.StringVar(value="default")
        profiles = ["default", "coder", "trader", "osint"]
        for p in (ROOT / "profiles").glob("*.json"):
            if p.stem not in profiles and p.stem not in ("approval_policy", "models_map", "router_config"):
                profiles.append(p.stem)
        ctk.CTkOptionMenu(side, variable=self.profile_var, values=profiles, width=230, command=self._on_profile).pack(padx=12, pady=4)

        self.agent_switch = ctk.CTkSwitch(side, text="Agent mode", command=self._toggle_agent)
        self.agent_switch.pack(anchor="w", padx=12, pady=(10, 4))
        self.osint_switch = ctk.CTkSwitch(side, text="OSINT focus", command=self._toggle_osint)
        self.osint_switch.pack(anchor="w", padx=12, pady=4)

        ctk.CTkLabel(side, text="Parameters").pack(anchor="w", padx=12, pady=(10, 0))
        self.temp_var = ctk.DoubleVar(value=float(self.cfg.get("temperature", 0.7)))
        self.ctx_var = ctk.IntVar(value=int(self.cfg.get("ctx_size", 4096)))
        self.max_tok_var = ctk.IntVar(value=int(self.cfg.get("max_tokens", 2048)))
        self.ngl_var = ctk.IntVar(value=int(self.cfg.get("n_gpu_layers", 0)))

        for label, var in [
            ("Temperature", self.temp_var),
            ("Context", self.ctx_var),
            ("Max tokens", self.max_tok_var),
            ("GPU layers", self.ngl_var),
        ]:
            f = ctk.CTkFrame(side, fg_color="transparent")
            f.pack(fill="x", padx=12, pady=2)
            ctk.CTkLabel(f, text=label, width=95, anchor="w").pack(side="left")
            ctk.CTkEntry(f, textvariable=var, width=90).pack(side="right")

        ctk.CTkButton(side, text="New session", command=self._new_session).pack(padx=12, pady=(14, 4), fill="x")
        ctk.CTkButton(side, text="Save session", command=self._save_session).pack(padx=12, pady=4, fill="x")
        ctk.CTkButton(side, text="Open workspace", command=lambda: self._open_path(workspace_dir())).pack(padx=12, pady=4, fill="x")
        ctk.CTkButton(side, text="Open models", command=lambda: self._open_path(ROOT / "models")).pack(padx=12, pady=4, fill="x")
        ctk.CTkButton(side, text="Help / commands", command=lambda: self._log_system(HELP_TEXT)).pack(padx=12, pady=4, fill="x")

        self.status = ctk.CTkLabel(side, text="No model loaded", text_color="gray", wraplength=240)
        self.status.pack(side="bottom", pady=12, padx=8)

        main = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        main.grid(row=0, column=1, sticky="nsew")
        main.grid_rowconfigure(0, weight=1)
        main.grid_columnconfigure(0, weight=1)

        self.chat_box = ctk.CTkTextbox(main, wrap="word", font=ctk.CTkFont(size=14), state="disabled")
        self.chat_box.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)

        bottom = ctk.CTkFrame(main, fg_color="transparent")
        bottom.grid(row=1, column=0, sticky="ew", padx=8, pady=(0, 10))
        bottom.grid_columnconfigure(0, weight=1)

        self.input = ctk.CTkTextbox(bottom, height=88, font=ctk.CTkFont(size=14))
        self.input.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        self.input.bind("<Control-Return>", lambda e: self._on_send())

        btn_col = ctk.CTkFrame(bottom, fg_color="transparent")
        btn_col.grid(row=0, column=1)
        self.send_btn = ctk.CTkButton(btn_col, text="Send", width=96, height=36, command=self._on_send, fg_color="#e94560")
        self.send_btn.pack(pady=2)
        ctk.CTkButton(btn_col, text="Stop", width=96, height=28, command=self._on_stop, fg_color="#555").pack(pady=2)

    def _log(self, role: str, text: str):
        self.chat_box.configure(state="normal")
        prefix = {"user": "You", "assistant": "Assistant", "system": "System", "tool": "Tool"}.get(role, role)
        self.chat_box.insert("end", f"\n[{prefix}]\n{text}\n")
        self.chat_box.see("end")
        self.chat_box.configure(state="disabled")

    def _log_system(self, text: str):
        self._log("system", text)

    def _refresh_models(self):
        models = list_models()
        names = [m.name for m in models] or ["(no models)"]
        self.model_menu.configure(values=names)
        self.model_var.set(names[0])

    def _load_model(self, name: str | None = None):
        name = name or self.model_var.get()
        if not name or name.startswith("("):
            self._log_system("No GGUF model found. Copy .gguf files into models\\")
            return
        path = ROOT / "models" / name
        if not path.exists():
            self._log_system(f"Not found: {name}")
            return
        self.status.configure(text="Loading…")
        self.update_idletasks()

        def work():
            err = self.engine.load(
                path,
                n_ctx=_safe_int(self.ctx_var.get(), 4096, 512, 131072),
                n_gpu_layers=_safe_int(self.ngl_var.get(), 0, 0, 999),
                n_threads=_safe_int(self.cfg.get("threads", 4), 4, 1, 64),
            )
            self.after(0, lambda: self._after_load(path, err))

        threading.Thread(target=work, daemon=True).start()

    def _after_load(self, path: Path, err: str):
        if err:
            self.status.configure(text="Load failed")
            self._log_system(f"Load error: {err}")
        else:
            self.status.configure(text=f"Loaded: {path.name}")
            self._log_system(f"Model loaded: {path.name}")
            self.cfg["model"] = path.name
            try:
                save_ini(self.cfg)
            except Exception:
                pass

    def _on_profile(self, name: str):
        prof = load_profile(name)
        self.profile_name = name
        self.system_prompt = prof.get("system") or self.system_prompt
        if "temperature" in prof:
            self.temp_var.set(float(prof["temperature"]))
        if "max_tokens" in prof:
            self.max_tok_var.set(int(prof["max_tokens"]))
        if "ctx_size" in prof:
            self.ctx_var.set(int(prof["ctx_size"]))
        if name == "osint":
            self.osint_mode = True
            self.osint_switch.select()
            self.agent_mode = True
            self.agent_switch.select()
        self._log_system(f"Profile: {name}")

    def _toggle_agent(self):
        self.agent_mode = bool(self.agent_switch.get())
        self._log_system("Agent ON" if self.agent_mode else "Agent OFF")

    def _toggle_osint(self):
        self.osint_mode = bool(self.osint_switch.get())
        if self.osint_mode and not self.agent_mode:
            self.agent_mode = True
            self.agent_switch.select()
        self._log_system("OSINT focus ON — public-source tools only" if self.osint_mode else "OSINT focus OFF")

    def _new_session(self):
        self.messages.clear()
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.chat_box.configure(state="normal")
        self.chat_box.delete("1.0", "end")
        self.chat_box.configure(state="disabled")
        self._asst_started = False
        self._log_system("New session")

    def _save_session(self):
        path = sessions_dir() / f"session_{self.session_id}.json"
        data = {
            "id": self.session_id,
            "profile": self.profile_name,
            "model": self.engine.model_path.name if self.engine.model_path else None,
            "agent": self.agent_mode,
            "osint": self.osint_mode,
            "messages": self.messages,
            "saved_at": datetime.now().isoformat(),
        }
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        self._log_system(f"Saved: {path.name}")

    def _open_path(self, p: Path):
        import os
        import subprocess
        try:
            p.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            self._log_system(f"ساختن پوشه ممکن نشد: {e}")
            return
        try:
            if hasattr(os, "startfile"):
                os.startfile(str(p))
            elif sys.platform == "darwin":
                subprocess.Popen(["open", str(p)])
            else:
                subprocess.Popen(["xdg-open", str(p)])
        except Exception as e:
            self._log_system(f"باز کردن پوشه ممکن نشد: {e}")

    def _on_stop(self):
        self.busy = False

    def _handle_slash(self, text: str) -> bool:
        low = text.lower().strip()
        if low in ("/help", "/?"):
            self._log_system(HELP_TEXT)
            return True
        if low == "/clear":
            self.chat_box.configure(state="normal")
            self.chat_box.delete("1.0", "end")
            self.chat_box.configure(state="disabled")
            return True
        if low == "/new":
            self._new_session()
            return True
        if low == "/save":
            self._save_session()
            return True
        if low.startswith("/agent"):
            parts = text.split(maxsplit=1)
            on = parts[1].strip().lower() in ("on", "1", "true") if len(parts) > 1 else not self.agent_mode
            self.agent_mode = on
            if on:
                self.agent_switch.select()
            else:
                self.agent_switch.deselect()
            self._log_system(f"Agent {'ON' if on else 'OFF'}")
            return True
        if low.startswith("/osint"):
            parts = text.split(maxsplit=1)
            if len(parts) == 1 or parts[1].strip().lower() in ("on", "off"):
                on = parts[1].strip().lower() == "on" if len(parts) > 1 else not self.osint_mode
                self.osint_mode = on
                if on:
                    self.osint_switch.select()
                    self.agent_mode = True
                    self.agent_switch.select()
                else:
                    self.osint_switch.deselect()
                self._log_system(f"OSINT {'ON' if on else 'OFF'}")
                return True
            target = parts[1].strip()
            self._log_system(f"OSINT report for: {target}")
            self.busy = True
            self.send_btn.configure(state="disabled")

            def work():
                res = execute_tool("osint_report", {"target": target})
                self.after(0, lambda: self._finish_direct_tool("osint_report", res))

            threading.Thread(target=work, daemon=True).start()
            return True
        if low == "/models":
            models = list_models()
            self._log_system("Models:\n" + ("\n".join(m.name for m in models) or "(none)"))
            return True
        if low.startswith("/load "):
            self._load_model(text.split(maxsplit=1)[1].strip())
            return True
        if low.startswith("/system "):
            self.system_prompt = text.split(maxsplit=1)[1]
            self._log_system("System prompt updated for this session")
            return True
        if low.startswith("/rag "):
            q = text.split(maxsplit=1)[1]
            res = execute_tool("memory_search", {"query": q})
            self._log("tool", json.dumps(res, ensure_ascii=False, indent=2)[:4000])
            return True
        if low in ("/sessions", "/session"):
            res = execute_tool("session_list", {})
            lines = []
            for s in (res.get("sessions") or []):
                lines.append(f"{s.get('file')} | msgs={s.get('messages')} | {s.get('saved_at')}")
            self._log_system("Sessions:\n" + ("\n".join(lines) or "(empty)"))
            return True
        if low.startswith("/open "):
            fname = text.split(maxsplit=1)[1].strip()
            res = execute_tool("session_load", {"file_name": fname})
            if not res.get("ok"):
                self._log_system(str(res.get("error") or res))
                return True
            sess = res.get("session") or {}
            self.messages = list(sess.get("messages") or [])
            self.session_id = sess.get("id") or self.session_id
            self.chat_box.configure(state="normal")
            self.chat_box.delete("1.0", "end")
            self.chat_box.configure(state="disabled")
            for m in self.messages[-40:]:
                self._log(m.get("role") or "system", str(m.get("content") or "")[:4000])
            self._log_system(f"Loaded {res.get('file')}")
            return True
        if low.startswith("/case"):
            parts = text.split(maxsplit=2)
            sub = parts[1].lower() if len(parts) > 1 else "list"
            if sub == "list":
                self._log("tool", json.dumps(execute_tool("case_list", {}), ensure_ascii=False, indent=2)[:4000])
            elif sub in ("new", "create") and len(parts) > 2:
                self._log("tool", json.dumps(execute_tool("case_create", {"name": parts[2], "target": parts[2]}), ensure_ascii=False, indent=2)[:4000])
            elif sub == "export" and len(parts) > 2:
                self._log("tool", json.dumps(execute_tool("case_export_report", {"case_id": parts[2]}), ensure_ascii=False, indent=2)[:4000])
            else:
                self._log_system("Usage: /case list | /case new <name> | /case export <id>")
            return True
        if low == "/export" or low.startswith("/export "):
            parts = text.split(maxsplit=1)
            fname = parts[1].strip() if len(parts) > 1 else f"session_{self.session_id}.json"
            try:
                self._save_session()
            except Exception:
                pass
            if not fname.startswith("session_"):
                fname = "session_" + fname
            if not fname.endswith(".json"):
                fname += ".json"
            res = execute_tool("session_export_md", {"file_name": fname})
            self._log_system(json.dumps(res, ensure_ascii=False, indent=2)[:2000])
            return True
        if low in ("/buildrag", "/ragbuild"):
            res = execute_tool("rag_build_index", {"max_docs": 800})
            self._log_system(json.dumps(res, ensure_ascii=False, indent=2)[:2000])
            return True
        if low in ("/templates", "/scaffold-list"):
            self._log("tool", json.dumps(execute_tool("build_list_templates", {}), ensure_ascii=False, indent=2))
            return True
        if low.startswith("/scaffold"):
            parts = text.split()
            name = parts[1] if len(parts) > 1 else "demo"
            tmpl = parts[2] if len(parts) > 2 else "python-cli"
            self._log("tool", json.dumps(execute_tool("build_scaffold", {"name": name, "template": tmpl}), ensure_ascii=False, indent=2)[:4000])
            return True
        if low.startswith("/elevated"):
            parts = text.split()
            from config_loader import load_approval_policy, ROOT
            import json
            pol_path = ROOT / "profiles" / "approval_policy.json"
            try:
                pol = load_approval_policy() or {}
            except Exception:
                pol = {}
            if len(parts) > 1 and parts[1].lower() in ("on", "1", "true", "yes"):
                pol["elevated_mode"] = True
                pol_path.parent.mkdir(parents=True, exist_ok=True)
                pol_path.write_text(json.dumps(pol, ensure_ascii=False, indent=2), encoding="utf-8")
                self._log_system("elevated_mode=ON — هر دستور sys_* نیاز به تأیید شما دارد.")
            elif len(parts) > 1 and parts[1].lower() in ("off", "0", "false", "no"):
                pol["elevated_mode"] = False
                pol_path.write_text(json.dumps(pol, ensure_ascii=False, indent=2), encoding="utf-8")
                self._log_system("elevated_mode=OFF")
            else:
                self._log_system(f"elevated_mode={bool(pol.get('elevated_mode'))} — استفاده: /elevated on|off")
            return True
        if low == "/doctor":
            res = execute_tool("doctor", {})
            lines = [str(res.get("summary_fa") or "")]
            for f in (res.get("findings") or [])[:25]:
                lines.append(f"[{f.get('level')}] {f.get('msg')}")
            self._log_system("\n".join(lines))
            return True
        return False

    def _finish_direct_tool(self, name: str, result: dict):
        self._log("tool", json.dumps(result, ensure_ascii=False, indent=2)[:6000])
        try:
            execute_tool("save_osint_report", {"name": f"quick_{int(time.time())}", "data": result})
        except Exception:
            pass
        self.busy = False
        self.send_btn.configure(state="normal")

    def _on_send(self):
        if self.busy:
            return
        text = self.input.get("1.0", "end").strip()
        if not text:
            return
        self.input.delete("1.0", "end")
        if text.startswith("/"):
            if self._handle_slash(text):
                return
        if not self.engine.llm:
            self._log_system("Load a model first (or use /osint <target> without model for direct tools).")
            return
        self._log("user", text)
        self.messages.append({"role": "user", "content": text})
        self.busy = True
        self._asst_started = False
        self.send_btn.configure(state="disabled")
        threading.Thread(target=self._generate, daemon=True).start()

    def _build_messages(self) -> list[dict]:
        sys_content = (self.system_prompt or "You are a helpful assistant.") + identity_system_suffix()
        if self.agent_mode or self.osint_mode:
            sys_content += "\n\n" + tools_schema_for_prompt(include_osint=True)
        if self.osint_mode:
            sys_content += (
                "\nYou are assisting with OSINT / open-source research. "
                "Prefer structured tool calls (osint_report, osint_domain, osint_username, ...). "
                "Cite public sources. Never invent private data. Refuse illegal requests."
            )
        out = [{"role": "system", "content": sys_content}]
        out.extend(self.messages[-28:])
        return out

    def _generate(self):
        try:
            msgs = self._build_messages()
            stream = self.engine.chat(
                msgs,
                temperature=_safe_float(self.temp_var.get(), 0.7, 0.0, 2.0),
                max_tokens=_safe_int(self.max_tok_var.get(), 1024, 16, 8192),
                top_p=float(self.cfg.get("top_p", 0.9)),
                repeat_penalty=float(self.cfg.get("repeat_penalty", 1.1)),
                stream=True,
            )
            full = []
            for chunk in stream:
                if not self.busy:
                    break
                try:
                    choices = chunk.get("choices") or [{}]
                    delta = (choices[0] or {}).get("delta") or {}
                    token = delta.get("content") or ""
                except Exception:
                    token = ""
                if token:
                    full.append(token)
                    self.after(0, lambda t=token: self._append_assistant_token(t))
            reply = "".join(full).strip()
            self._asst_started = False
            if reply:
                self.messages.append({"role": "assistant", "content": reply})
                if len(self.messages) % 4 == 0:
                    try:
                        self.after(0, self._save_session)
                    except Exception:
                        pass
                if self.agent_mode or self.osint_mode:
                    self.after(0, lambda r=reply: self._maybe_run_tool(r))
        except Exception as e:
            err_txt = f"Error: {e}\n{traceback.format_exc()[:500]}"
            self.after(0, lambda t=err_txt: self._log_system(t))
        finally:
            self.busy = False
            self.after(0, lambda: self.send_btn.configure(state="normal"))

    def _append_assistant_token(self, token: str):
        self.chat_box.configure(state="normal")
        if not self._asst_started:
            self.chat_box.insert("end", "\n[Assistant]\n")
            self._asst_started = True
        self.chat_box.insert("end", token)
        self.chat_box.see("end")
        self.chat_box.configure(state="disabled")

    def _maybe_run_tool(self, reply: str):
        text = reply.strip()
        if not (text.startswith("{") and "tool" in text):
            start = text.find("{")
            end = text.rfind("}")
            if start >= 0 and end > start:
                text = text[start : end + 1]
            else:
                return
        try:
            obj = json.loads(text)
        except json.JSONDecodeError:
            return
        name = obj.get("tool") or obj.get("name")
        args = obj.get("arguments") or obj.get("args") or {}
        if not name:
            return
        self._log("tool", f"Requested: {name} {json.dumps(args, ensure_ascii=False)}")

        high_risk = name in (
            "run_python", "write_file", "fs_write", "code_run",
            "osint_fetch", "osint_search", "osint_username", "osint_username_parallel",
            "osint_report", "osint_crtsh", "osint_domain_graph", "browser_read",
            "plugin_run", "build_scaffold", "build_write_files", "apply_patch", "run_tests", "shell_allowlisted",
            "git_commit", "browser_fetch", "browser_playwright", "fetch_json",
            "process_list", "env_get", "open_app", "clipboard_get", "clipboard_set", "notify",
            "sys_run_cmd", "sys_write_file", "sys_read_file", "sys_list_dir",
            "sys_open_path", "sys_open_url", "sys_info",
        )
        if needs_approval(name):
            try:
                dlg = ApprovalDialog(self, name, args, require_yes=high_risk)
                self.wait_window(dlg)
                approved = bool(getattr(dlg, "result", False))
            except Exception as ex:
                self._log_system(f"پنجره تأیید خطا داد: {ex}")
                approved = False
            if not approved:
                self._log("tool", "Denied by user")
                self._append_tool_result(name, {"ok": False, "error": "user denied"})
                return
            try:
                log = ROOT / "memory" / "approval_log.jsonl"
                log.parent.mkdir(exist_ok=True)
                with log.open("a", encoding="utf-8") as f:
                    f.write(json.dumps({"ts": time.time(), "tool": name, "args": args, "approved": True}, ensure_ascii=False) + "\n")
            except Exception:
                pass

        try:
            result = execute_tool(name, args if isinstance(args, dict) else {})
        except Exception as ex:
            result = {"ok": False, "error": f"tool crash: {ex}"}
        try:
            self._log("tool", json.dumps(result, ensure_ascii=False, indent=2)[:5000])
        except Exception:
            self._log("tool", str(result)[:5000])
        self._append_tool_result(name, result)

    def _append_tool_result(self, name: str, result: dict):
        try:
            content = f"[tool result: {name}]\n{json.dumps(result, ensure_ascii=False, default=str)}"
        except Exception:
            content = f"[tool result: {name}]\n{result!r}"
        self.messages.append({"role": "user", "content": content})
        if self.engine.llm and not self.busy:
            self.busy = True
            self._asst_started = False
            try:
                self.send_btn.configure(state="disabled")
            except Exception:
                pass
            threading.Thread(target=self._generate, daemon=True).start()


def main():
    if not _HAS_CTK:
        print("[ERROR] customtkinter not installed. Run SETUP.bat first.")
        raise SystemExit(1)
    try:
        for d in ("models", "sessions", "workspace", "memory", "books", "dataset"):
            (ROOT / d).mkdir(parents=True, exist_ok=True)
        (workspace_dir() / "osint").mkdir(parents=True, exist_ok=True)
        (workspace_dir() / "plugins").mkdir(parents=True, exist_ok=True)
    except Exception as e:
        print("folder init warning:", e)
    try:
        app = DesktopChat()
        app.protocol("WM_DELETE_WINDOW", app.destroy)
        app.mainloop()
    except Exception as e:
        print("[FATAL] Desktop chat failed:", e)
        traceback.print_exc()
        try:
            input("Enter to exit...")
        except Exception:
            pass
        raise SystemExit(1)


if __name__ == "__main__":
    main()
