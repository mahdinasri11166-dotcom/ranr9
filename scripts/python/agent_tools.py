# -*- coding: utf-8 -*-
"""Agent tools registry: FS + OSINT + advanced + RAG + plugins + browser (read-only)."""
from __future__ import annotations

import json
import os
import subprocess
import zipfile
from pathlib import Path
from typing import Any, Callable

from config_loader import ROOT, workspace_dir, load_approval_policy

WORKSPACE = workspace_dir()

try:
    from osint_tools import OSINT_TOOLS, osint_schema_for_prompt
except ImportError:
    OSINT_TOOLS = {}
    def osint_schema_for_prompt() -> str:
        return ""

try:
    from osint_advanced import ADVANCED_OSINT
except ImportError:
    ADVANCED_OSINT = {}

try:
    from osint_plus import OSINT_PLUS_TOOLS
except ImportError:
    OSINT_PLUS_TOOLS = {}

try:
    from case_manager import CASE_TOOLS
except ImportError:
    CASE_TOOLS = {}

try:
    from elevated_tools import ELEVATED_TOOLS
except ImportError:
    ELEVATED_TOOLS = {}

try:
    from builder_tools import BUILDER_TOOLS
except ImportError:
    BUILDER_TOOLS = {}

try:
    from coding_tools import CODING_TOOLS
except ImportError:
    CODING_TOOLS = {}

try:
    from browser_tools import BROWSER_LAYER_TOOLS
except ImportError:
    BROWSER_LAYER_TOOLS = {}

try:
    from agent_memory import MEMORY_LAYER_TOOLS
except ImportError:
    MEMORY_LAYER_TOOLS = {}

try:
    from system_named_tools import SYSTEM_NAMED_TOOLS
except ImportError:
    SYSTEM_NAMED_TOOLS = {}

try:
    from downloader import DOWNLOAD_TOOLS
except ImportError:
    DOWNLOAD_TOOLS = {}

try:
    from proxy_pool import PROXY_TOOLS
except ImportError:
    PROXY_TOOLS = {}

try:
    from advanced_tools import ADVANCED_TOOLS
except ImportError:
    ADVANCED_TOOLS = {}

try:
    from monitor_tools import MONITOR_TOOLS
except ImportError:
    MONITOR_TOOLS = {}

try:
    from model_editor import MODEL_EDITOR_TOOLS
except ImportError:
    MODEL_EDITOR_TOOLS = {}

try:
    from learn_tools import LEARN_TOOLS
except ImportError:
    LEARN_TOOLS = {}

try:
    from cyber_tools import CYBER_TOOLS
except ImportError:
    CYBER_TOOLS = {}

try:
    from offline_translate import OFFLINE_TRANSLATE_TOOLS
except ImportError:
    OFFLINE_TRANSLATE_TOOLS = {}

try:
    from export_tools import EXPORT_TOOLS
except ImportError:
    EXPORT_TOOLS = {}


try:
    from session_store import session_list, session_load, session_delete, session_export_md
except ImportError:
    session_list = session_load = session_delete = session_export_md = None

try:
    from report_engine import tool_generate_osint_report, save_report
except ImportError:
    tool_generate_osint_report = None
    save_report = None

try:
    from plugin_system import plugin_list, plugin_run, ensure_sample_plugin
except ImportError:
    plugin_list = plugin_run = ensure_sample_plugin = None

try:
    from browser_readonly import browser_read
except ImportError:
    browser_read = None

try:
    from rag_local import rag_search, build_index
except ImportError:
    rag_search = build_index = None

try:
    from policy_guards import refuse_bruteforce, refuse_aggressive_vuln_scan
except ImportError:
    def refuse_bruteforce(**kw):
        return {"ok": False, "blocked": True, "error": "brute-force disabled"}
    def refuse_aggressive_vuln_scan(**kw):
        return {"ok": False, "blocked": True, "error": "aggressive scan disabled"}

try:
    from doctor import run_doctor, model_wizard
except ImportError:
    run_doctor = model_wizard = None


def _unrestricted() -> bool:
    try:
        pol = load_approval_policy() or {}
        return bool(pol.get("unrestricted_tools")) or bool(pol.get("elevated_mode"))
    except Exception:
        return True


def _safe_path(rel: str) -> Path:
    """Resolve path. In unrestricted/elevated mode allow paths outside workspace."""
    rel = (rel or "").strip()
    if not rel:
        rel = "."
    # absolute, drive letter, UNC, or home
    is_abs = (
        rel.startswith("~")
        or (len(rel) > 1 and rel[1] == ":")
        or rel.startswith("\\")
        or rel.startswith("/")
    )
    if is_abs:
        if _unrestricted():
            return Path(rel).expanduser().resolve()
        raise PermissionError(f"Path outside workspace blocked: {rel}")
    rel_norm = rel.replace(chr(92), "/").lstrip("/")
    target = (WORKSPACE / rel_norm).resolve()
    if not str(target).startswith(str(WORKSPACE.resolve())):
        if _unrestricted():
            return target
        raise PermissionError(f"Path outside workspace blocked: {rel}")
    return target


def tool_list_dir(path: str = ".") -> dict[str, Any]:
    p = _safe_path(path)
    if not p.exists():
        return {"ok": False, "error": "not found"}
    if not p.is_dir():
        return {"ok": False, "error": "not a directory"}
    items = []
    for child in sorted(p.iterdir())[:500]:
        items.append({
            "name": child.name,
            "type": "dir" if child.is_dir() else "file",
            "size": child.stat().st_size if child.is_file() else None,
        })
    return {"ok": True, "path": str(p.relative_to(WORKSPACE)), "items": items}


def tool_read_file(path: str, max_bytes: int = 200_000) -> dict[str, Any]:
    p = _safe_path(path)
    if not p.exists() or not p.is_file():
        return {"ok": False, "error": "file not found"}
    data = p.read_bytes()[:max_bytes]
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        text = data.decode("utf-8", errors="replace")
    return {"ok": True, "path": path, "content": text, "truncated": len(data) >= p.stat().st_size}


def tool_write_file(path: str, content: str) -> dict[str, Any]:
    p = _safe_path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return {"ok": True, "path": path, "bytes": len(content.encode("utf-8"))}


def tool_make_zip(paths: list[str] | None = None, out_name: str = "export.zip") -> dict[str, Any]:
    paths = paths or ["."]
    out = _safe_path(out_name)
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
        for rel in paths:
            src = _safe_path(rel)
            if src.is_file():
                zf.write(src, arcname=src.name)
            elif src.is_dir():
                for f in src.rglob("*"):
                    if f.is_file():
                        zf.write(f, arcname=str(f.relative_to(src.parent)))
    return {"ok": True, "zip": str(out.relative_to(WORKSPACE))}


def tool_run_python(code: str, timeout: int = 15) -> dict[str, Any]:
    import tempfile
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, encoding="utf-8", dir=str(WORKSPACE)) as f:
        f.write(code)
        tmp = f.name
    try:
        r = subprocess.run(
            [os.environ.get("PYTHON", "python"), tmp],
            cwd=str(WORKSPACE),
            capture_output=True,
            text=True,
            timeout=timeout,
            env={**os.environ, "PYTHONIOENCODING": "utf-8"},
        )
        return {
            "ok": r.returncode == 0,
            "stdout": (r.stdout or "")[:8000],
            "stderr": (r.stderr or "")[:4000],
            "returncode": r.returncode,
        }
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "timeout"}
    finally:
        try:
            os.unlink(tmp)
        except OSError:
            pass


def tool_app_settings(action: str = "get") -> dict[str, Any]:
    from config_loader import load_ini
    if action == "get":
        return {"ok": True, "config": load_ini()}
    return {"ok": False, "error": "only get supported from tools"}


def tool_save_osint_report(name: str, data: dict | str = None) -> dict[str, Any]:
    safe = "".join(c if c.isalnum() or c in "-_." else "_" for c in (name or "report"))[:80]
    rel = f"osint/{safe}.json"
    p = _safe_path(rel)
    p.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(data, str):
        p.write_text(data, encoding="utf-8")
    else:
        p.write_text(json.dumps(data or {}, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"ok": True, "path": rel}


def tool_memory_search(query: str, top_k: int = 5) -> dict[str, Any]:
    from urllib.request import Request, urlopen
    try:
        body = json.dumps({"query": query, "top_k": top_k}).encode()
        req = Request("http://127.0.0.1:8765/search", data=body, headers={"Content-Type": "application/json"}, method="POST")
        with urlopen(req, timeout=5) as r:
            return json.loads(r.read().decode("utf-8"))
    except Exception as e:
        if rag_search:
            return rag_search(query, top_k=top_k)
        return {"ok": False, "error": f"memory server unreachable: {e}"}


CORE_TOOLS: dict[str, Callable[..., dict[str, Any]]] = {
    "list_dir": tool_list_dir,
    "fs_list": tool_list_dir,
    "read_file": tool_read_file,
    "fs_read": tool_read_file,
    "write_file": tool_write_file,
    "fs_write": tool_write_file,
    "make_zip": tool_make_zip,
    "fs_zip": tool_make_zip,
    "run_python": tool_run_python,
    "code_run": tool_run_python,
    "app_settings": tool_app_settings,
    "app_config": tool_app_settings,
    "save_osint_report": tool_save_osint_report,
    "memory_search": tool_memory_search,
    "rag_search": tool_memory_search,
}

if tool_generate_osint_report:
    CORE_TOOLS["generate_osint_report"] = tool_generate_osint_report
if plugin_list:
    CORE_TOOLS["plugin_list"] = lambda: plugin_list()
    CORE_TOOLS["plugin_run"] = lambda plugin_id, arguments=None: plugin_run(plugin_id, arguments or {})
if browser_read:
    CORE_TOOLS["browser_read"] = browser_read
if rag_search:
    CORE_TOOLS["rag_local_search"] = rag_search
    CORE_TOOLS["rag_build_index"] = lambda max_docs=400: build_index(max_docs=max_docs)
if run_doctor:
    CORE_TOOLS["doctor"] = lambda: run_doctor()
    CORE_TOOLS["model_wizard"] = lambda: model_wizard()
if session_list:
    CORE_TOOLS["session_list"] = lambda limit=50: session_list(limit=limit)
    CORE_TOOLS["session_load"] = lambda file_name: session_load(file_name)
    CORE_TOOLS["session_delete"] = lambda file_name: session_delete(file_name)
    CORE_TOOLS["session_export_md"] = lambda file_name, out_name=None: session_export_md(file_name, out_name)

# Policy: register refusal names so agent/docs know they are blocked
CORE_TOOLS["bruteforce"] = refuse_bruteforce
CORE_TOOLS["brute_force"] = refuse_bruteforce
CORE_TOOLS["vuln_scan"] = refuse_aggressive_vuln_scan
CORE_TOOLS["aggressive_scan"] = refuse_aggressive_vuln_scan
CORE_TOOLS["port_scan"] = refuse_aggressive_vuln_scan


def _load_user_tools() -> dict[str, Callable[..., dict[str, Any]]]:
    """Auto-load custom tools from workspace/user_tools/*.py

    Each module may define:
      TOOLS = {"name": callable, ...}
    or a single function `run` registered as the module name.
    """
    import importlib.util
    found: dict[str, Callable[..., dict[str, Any]]] = {}
    roots = [
        WORKSPACE / "user_tools",
        ROOT / "user_tools",
    ]
    for base in roots:
        try:
            base.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass
        if not base.is_dir():
            continue
        for py in sorted(base.glob("*.py")):
            if py.name.startswith("_"):
                continue
            try:
                spec = importlib.util.spec_from_file_location(f"gguf_user_{py.stem}", py)
                if not spec or not spec.loader:
                    continue
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                if hasattr(mod, "TOOLS") and isinstance(mod.TOOLS, dict):
                    for k, fn in mod.TOOLS.items():
                        if callable(fn):
                            found[str(k)] = fn
                elif hasattr(mod, "run") and callable(mod.run):
                    found[py.stem] = mod.run
            except Exception as e:
                try:
                    from app_logging import get_logger
                    get_logger("tools").warning("user tool %s failed: %s", py.name, e)
                except Exception:
                    pass
    return found


USER_TOOLS = _load_user_tools()

TOOLS: dict[str, Callable[..., dict[str, Any]]] = {**CORE_TOOLS, **OSINT_TOOLS, **ADVANCED_OSINT, **OSINT_PLUS_TOOLS, **CASE_TOOLS, **ELEVATED_TOOLS, **BUILDER_TOOLS, **CODING_TOOLS, **BROWSER_LAYER_TOOLS, **MEMORY_LAYER_TOOLS, **SYSTEM_NAMED_TOOLS, **USER_TOOLS, **DOWNLOAD_TOOLS, **PROXY_TOOLS, **ADVANCED_TOOLS, **MONITOR_TOOLS, **MODEL_EDITOR_TOOLS, **LEARN_TOOLS, **CYBER_TOOLS, **OFFLINE_TRANSLATE_TOOLS, **EXPORT_TOOLS}


def needs_approval(tool_name: str) -> bool:
    """Return True only when policy explicitly requires approval.
    unrestricted_tools / default ALLOW → no gate."""
    try:
        policy = load_approval_policy() or {}
        if policy.get("require_approval_for_all"):
            return True
        # unrestricted mode: never require approval unless tool is explicitly listed
        if policy.get("unrestricted_tools") is True:
            tools = policy.get("tools") or {}
            level = str(tools.get(tool_name) or "").upper()
            return level == "REQUIRE_APPROVAL"
        blocked = policy.get("blocked_tools") or []
        if tool_name in blocked:
            # blocked list no longer forces approval dialog; still executable if registered
            return False
        tools = policy.get("tools") or {}
        level = tools.get(tool_name) or policy.get("default") or "ALLOW"
        return str(level).upper() == "REQUIRE_APPROVAL"
    except Exception:
        return False  # open by default


def execute_tool(name: str, arguments: dict[str, Any] | None = None) -> dict[str, Any]:
    if not isinstance(name, str) or not name.strip():
        return {"ok": False, "error": "tool name required"}
    if arguments is None:
        arguments = {}
    if not isinstance(arguments, dict):
        return {"ok": False, "error": "arguments must be a dict"}
    # simple rate limit
    try:
        import time
        from pathlib import Path as _P
        from config_loader import ROOT as _ROOT
        rl = _ROOT / "workspace" / "audit" / ".rate"
        now = time.time()
        last = 0.0
        if rl.exists():
            try:
                last = float(rl.read_text(encoding="utf-8").strip() or "0")
            except Exception:
                last = 0.0
        if now - last < 0.05:
            time.sleep(0.05)
        rl.parent.mkdir(parents=True, exist_ok=True)
        rl.write_text(str(now), encoding="utf-8")
    except Exception:
        pass
    try:
        from tool_budget import allow_tool
        ok_b, msg_b = allow_tool()
        if not ok_b:
            return {"ok": False, "error": msg_b}
    except Exception:
        pass
    fn = TOOLS.get(name)
    if not fn:
        return {"ok": False, "error": f"unknown tool: {name}", "available": sorted(TOOLS.keys())[:80]}
    try:
        import inspect
        try:
            sig = inspect.signature(fn)
            params = sig.parameters
            if arguments and any(p.kind == inspect.Parameter.VAR_KEYWORD for p in params.values()):
                result = fn(**arguments)
            else:
                # filter known params
                kwargs = {k: v for k, v in arguments.items() if k in params}
                result = fn(**kwargs) if kwargs or not arguments else fn()
        except (TypeError, ValueError):
            try:
                result = fn(**arguments)
            except TypeError:
                result = fn()
        if not isinstance(result, dict):
            result = {"ok": True, "result": result}
        try:
            from audit_log import audit_tool
            audit_tool(name, arguments, result, approved=None)
        except Exception:
            pass
        return result
    except Exception as e:
        err = {"ok": False, "error": str(e)}
        try:
            from audit_log import audit_tool
            audit_tool(name, arguments, err, approved=None)
        except Exception:
            pass
        return err


def tools_schema_for_prompt(include_osint: bool = True) -> str:
    base = """You can call tools automatically when the user needs real actions.
Reply with ONLY a JSON object when a tool is needed (no markdown):
{"tool": "name", "arguments": {...}}
After you receive [tool result: ...], continue with a final answer.

Tools:
FILE: list_dir, read_file, write_file, make_zip, run_python, app_settings
DOWNLOAD: download / download_start(url), download_status(job_id), download_list, download_resume, download_cancel
PROXY: proxy_add, proxy_list, proxy_enable, proxy_test, proxy_remove
SHELL: shell / shell_run / cmd (command), shell_powershell(script)
API: api_request / api_get / api_post / api_put / api_delete (url, method, headers, json_body)
MONITOR: monitor_system, monitor_cpu, monitor_memory, monitor_disk, monitor_network, monitor_processes, monitor_ports, monitor_app
MODEL: model_meta_get, model_meta_save, model_meta_list, model_rename
RAG/MEMORY: memory_search, rag_local_search, rag_build_index, todo_plan, memory_save
CODE/GIT: search_code, apply_patch, run_tests, git_status, git_diff, git_log, git_commit
BUILD: build_scaffold, build_list_templates, build_tree
BROWSER: browser_read, browser_fetch
SESSIONS: session_list, session_load, session_delete
SYS: sys_info, sys_list_dir, sys_read_file, sys_write_file, sys_run_cmd, process_list
PLUGINS: plugin_list, plugin_run
LEARN: learn_topic(topic), web_search, web_read, youtube_transcript, youtube_search_learn,
  save_knowledge, ocr_image(path|url), translate(text, target), social_read(url)
CYBER: cyber_hash_file, cyber_file_meta, cyber_net_local, cyber_process_security,
  cyber_dns_full, cyber_http_headers, cyber_tls_info, cyber_port_check,
  cyber_nmap (if installed), cyber_win_events, cyber_report, cyber_quick_audit
EXPORT: make_code_file(language, code, filename), make_document(content, fmt=docx|pdf),
  build_and_export, list_exports, write_json_file, write_csv_file
  When user asks to build a program: generate full code then call make_code_file.
  Files are saved in workspace/exports/ for the user to download.
DOCTOR: doctor
"""
    if include_osint:
        base += "\n" + osint_schema_for_prompt()
        base += """
Cases:
- case_create(name, target="", notes="")
- case_list() / case_get(case_id)
- case_add_note(case_id, text) / case_add_event(case_id, event, detail="")
- case_attach_json(case_id, artifact_name, data)
- case_export_report(case_id)

Full OSINT (passive/public):
- osint_dossier / osint_full(target) — auto domain|ip|email|username|url investigation
- osint_dns_all, osint_rdap, osint_whois, osint_ssl_cert, osint_http_probe, osint_robots
- osint_ip_geo, osint_reverse_dns, osint_asn
- osint_username_full, osint_email_full, osint_phone_basic
- osint_reddit, osint_wikipedia, osint_favicon_hash
Advanced OSINT:
- osint_email_dns(email) — MX/SPF/DMARC via DNS (no breach dump)
- osint_crtsh(domain) — subdomains from certificate transparency
- osint_domain_graph(domain) — DNS+TLS+crt.sh relationship graph
- osint_username_parallel(username) — parallel checks + cache + confidence
- osint_file_metadata(path) — EXIF / PDF producer under workspace
"""
    return base


# Ensure sample plugin exists on import (safe)
try:
    if ensure_sample_plugin:
        ensure_sample_plugin()
except Exception:
    pass

def _tool_backup_sessions():
    from backup_tools import backup_sessions
    return backup_sessions()

def _tool_backup_profiles():
    from backup_tools import backup_profiles
    return backup_profiles()

def _tool_audit_list(limit: int = 40):
    from audit_log import read_audit
    return {"ok": True, "items": read_audit(limit=int(limit or 40))}

def _tool_update_check():
    from update_check import check_github_release
    return check_github_release()

def _tool_model_inspect(path: str = ""):
    from model_meta import read_gguf_metadata, estimate_ram_gb
    from config_loader import ROOT
    from pathlib import Path
    p = Path(path) if path else None
    if not p or not p.exists():
        # try models dir first file
        models = list((ROOT / "models").glob("*.gguf"))
        if not models:
            return {"ok": False, "error": "no model path"}
        p = models[0]
    meta = read_gguf_metadata(p)
    meta["estimate"] = estimate_ram_gb(meta.get("size_bytes") or 0)
    return meta

TOOLS.update({
    "backup_sessions": _tool_backup_sessions,
    "backup_profiles": _tool_backup_profiles,
    "audit_list": _tool_audit_list,
    "update_check": _tool_update_check,
    "model_inspect": _tool_model_inspect,
})

def _session_restore_last():
    from config_loader import sessions_dir
    import json
    files = sorted(sessions_dir().glob("session_*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not files:
        return {"ok": False, "error": "no sessions"}
    data = json.loads(files[0].read_text(encoding="utf-8"))
    return {"ok": True, "path": str(files[0]), "data": data}

def _load_advise(path: str = "", prefer_gpu: bool = False):
    from load_advisor import suggest_load
    from config_loader import ROOT
    from pathlib import Path
    p = Path(path) if path else None
    if not p or not p.exists():
        ms = list((ROOT / "models").glob("*.gguf"))
        if not ms:
            return {"ok": False, "error": "no model"}
        p = ms[0]
    return suggest_load(p, prefer_gpu=bool(prefer_gpu))

def _backup_restore(path: str = ""):
    from config_loader import ROOT, sessions_dir
    import shutil, json
    from pathlib import Path
    p = Path(path)
    if not p.exists():
        # latest sessions backup
        bdir = ROOT / "workspace" / "backups"
        cands = sorted(bdir.glob("sessions_*"), key=lambda x: x.stat().st_mtime, reverse=True) if bdir.exists() else []
        if not cands:
            return {"ok": False, "error": "no backup"}
        p = cands[0]
    dest = sessions_dir()
    if p.is_dir():
        for f in p.glob("session_*.json"):
            shutil.copy2(f, dest / f.name)
        return {"ok": True, "restored_from": str(p), "to": str(dest)}
    return {"ok": False, "error": "backup must be a folder"}

TOOLS.update({
    "session_restore_last": _session_restore_last,
    "load_advise": _load_advise,
    "backup_restore": _backup_restore,
})
