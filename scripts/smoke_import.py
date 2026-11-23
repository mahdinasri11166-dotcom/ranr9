# -*- coding: utf-8 -*-
"""Quick import smoke test for offline builds."""
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "python"))
errs = []
for mod in ("customtkinter", "psutil", "requests"):
    try:
        __import__(mod)
        print("OK", mod)
    except Exception as e:
        errs.append(f"{mod}: {e}")
        print("FAIL", mod, e)
for mod in (
    "agent_tools", "engine", "downloader", "proxy_pool",
    "advanced_tools", "monitor_tools", "model_editor", "rag_local", "export_tools", "offline_translate", "intent_router", "cyber_tools", "learn_tools",
):
    try:
        __import__(mod)
        print("OK", mod)
    except Exception as e:
        errs.append(f"{mod}: {e}")
        print("FAIL", mod, e)
try:
    import agent_tools
    print("TOOLS", len(getattr(agent_tools, "TOOLS", {})))
except Exception as e:
    errs.append(str(e))
sys.exit(1 if errs else 0)
