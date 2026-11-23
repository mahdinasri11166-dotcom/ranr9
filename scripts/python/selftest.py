# -*- coding: utf-8 -*-
"""GGUF Runner selftest — aligned with v4.2 unrestricted defaults."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
ok = fail = 0


def check(name, cond, detail=""):
    global ok, fail
    if cond:
        ok += 1
        print(f"  [OK]  {name}")
    else:
        fail += 1
        print(f"  [FAIL] {name}  {detail}")


def main():
    print("=== GGUF selftest v4.2 ===")
    mods = [
        "desktop_chat", "app_hub", "engine", "model_meta", "model_editor",
        "audit_log", "session_memory", "backup_tools", "update_check",
        "model_router", "load_advisor", "tool_budget", "app_logging",
        "agent_tools", "osint_tools", "osint_advanced", "report_engine",
        "plugin_system", "browser_readonly", "rag_local", "doctor",
        "policy_guards", "case_manager", "session_store", "ingest_books",
        "openai_api_server", "first_run_wizard", "elevated_tools",
        "builder_tools", "system_named_tools", "agent_memory", "browser_tools",
        "coding_tools", "downloader", "proxy_pool", "advanced_tools",
        "monitor_tools",
    ]
    for m in mods:
        check(f"file:{m}", (ROOT / "scripts/python" / f"{m}.py").exists())

    from agent_tools import TOOLS, execute_tool

    check("tools>=40", len(TOOLS) >= 40, str(len(TOOLS)))
    for name in (
        "session_list", "session_export_md", "case_create",
        "download_start", "proxy_list", "shell_run", "api_request",
        "monitor_system", "model_meta_get",
    ):
        check(f"tool:{name}", name in TOOLS)

    r = execute_tool("session_list", {})
    check("session_list runs", r.get("ok") is True, str(r)[:120])

    r2 = execute_tool("case_list", {})
    check("case_list runs", r2.get("ok") is True, str(r2)[:120])

    # bruteforce is not implemented (not a hard security block anymore)
    r3 = execute_tool("bruteforce", {})
    check("bruteforce responds", isinstance(r3, dict) and "ok" in r3)

    # path: in unrestricted mode outside workspace may be allowed
    r4 = execute_tool("list_dir", {"path": "."})
    check("list_dir workspace", r4.get("ok") is True, str(r4)[:120])

    try:
        from report_engine import render_graph_svg
        svg = render_graph_svg({"nodes": [{"id": "a", "type": "apex"}], "edges": []})
        check("graph svg", "<svg" in svg)
    except Exception as e:
        check("graph svg", False, str(e))

    try:
        import openai_api_server
        check("openai api port", getattr(openai_api_server, "PORT", None) == 8787)
    except Exception as e:
        check("openai api port", False, str(e))

    check("sys_run_cmd registered", "sys_run_cmd" in TOOLS)
    check("build_scaffold registered", "build_scaffold" in TOOLS)
    r6 = execute_tool("build_list_templates", {})
    check("templates list", r6.get("ok") is True, str(r6)[:120])
    check("search_code registered", "search_code" in TOOLS)

    r7 = execute_tool("proxy_list", {})
    check("proxy_list runs", r7.get("ok") is True, str(r7)[:120])

    r8 = execute_tool("monitor_system", {})
    check("monitor_system runs", r8.get("ok") is True, str(r8)[:120])

    r9 = execute_tool("model_meta_list", {})
    check("model_meta_list runs", r9.get("ok") is True, str(r9)[:120])

    # policy file
    pol = ROOT / "profiles" / "approval_policy.json"
    check("approval_policy exists", pol.exists())
    check("tool:make_code_file", "make_code_file" in TOOLS)
    check("tool:make_document", "make_document" in TOOLS)
    check("tool:osint_google", "osint_google" in TOOLS)
    check("tool:osint_dossier", "osint_dossier" in TOOLS)
    r_ex = execute_tool("make_code_file", {"language": "python", "code": "print(42)\n", "filename": "selftest_snippet.py"})
    check("make_code_file runs", r_ex.get("ok") is True, str(r_ex)[:120])
    r_dx = execute_tool("make_document", {"content": "hello selftest", "fmt": "docx", "filename": "selftest.docx"})
    check("make_document docx", r_dx.get("ok") is True, str(r_dx)[:120])


    print(f"\nResult: {ok} ok, {fail} fail")
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
