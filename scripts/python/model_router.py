# -*- coding: utf-8 -*-
"""Optional dual-model router: small model for tool planning, main for chat."""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any
from config_loader import ROOT
from app_logging import get_logger

log = get_logger("router")


def load_router_config() -> dict[str, Any]:
    path = ROOT / "profiles" / "router_config.json"
    default = {
        "enabled": False,
        "tool_model": "",
        "chat_model": "",
        "max_tool_tokens": 512,
        "max_chat_tokens": 2048,
    }
    if not path.exists():
        return default
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            default.update(data)
    except Exception as e:
        log.warning("router config: %s", e)
    return default


def resolve_model_path(name_or_path: str) -> Path | None:
    if not name_or_path:
        return None
    p = Path(name_or_path)
    if p.is_file():
        return p
    cand = ROOT / "models" / name_or_path
    if cand.is_file():
        return cand
    # suffix .gguf
    if not name_or_path.endswith(".gguf"):
        cand = ROOT / "models" / (name_or_path + ".gguf")
        if cand.is_file():
            return cand
    # fuzzy first match
    models = list((ROOT / "models").glob("*.gguf"))
    low = name_or_path.lower()
    for m in models:
        if low in m.name.lower():
            return m
    return None


class DualModelRouter:
    """Holds optional secondary Llama for tool calls; primary is external engine."""

    def __init__(self):
        self.tool_llm = None
        self.tool_path: Path | None = None
        self.cfg = load_router_config()

    def enabled(self) -> bool:
        self.cfg = load_router_config()
        return bool(self.cfg.get("enabled")) and bool(self.cfg.get("tool_model"))

    def ensure_tool_model(self, n_ctx: int = 2048, n_gpu_layers: int = 0, n_threads: int = 4) -> str:
        if not self.enabled():
            return ""
        path = resolve_model_path(str(self.cfg.get("tool_model") or ""))
        if not path:
            return f"tool_model پیدا نشد: {self.cfg.get('tool_model')}"
        if self.tool_path and self.tool_path.resolve() == path.resolve() and self.tool_llm is not None:
            return ""
        try:
            from llama_cpp import Llama
        except ImportError:
            return "llama-cpp-python نیست"
        try:
            self.tool_llm = None
            self.tool_llm = Llama(
                model_path=str(path),
                n_ctx=min(int(n_ctx), 4096),
                n_gpu_layers=int(n_gpu_layers),
                n_threads=max(1, int(n_threads)),
                verbose=False,
            )
            self.tool_path = path
            log.info("tool model loaded %s", path.name)
            return ""
        except Exception as e:
            self.tool_llm = None
            self.tool_path = None
            return str(e)

    def unload(self):
        self.tool_llm = None
        self.tool_path = None

    def plan_tools(self, messages: list[dict], tools_hint: str = "") -> str:
        """Run a short completion on tool model; returns text (may include JSON tool call)."""
        if not self.tool_llm:
            return ""
        max_tok = int(self.cfg.get("max_tool_tokens") or 512)
        sys = (
            "You select tools. Reply with a single JSON object "
            '{"tool":"name","arguments":{...}} or plain answer if no tool needed.\n'
            + (tools_hint[:3000] if tools_hint else "")
        )
        msgs = [{"role": "system", "content": sys}] + messages[-10:]
        try:
            out = self.tool_llm.create_chat_completion(
                messages=msgs,
                temperature=0.2,
                max_tokens=max_tok,
                stream=False,
            )
            return (((out.get("choices") or [{}])[0].get("message") or {}).get("content") or "").strip()
        except Exception as e:
            log.error("plan_tools: %s", e)
            return ""


def save_router_config(cfg: dict[str, Any]) -> None:
    path = ROOT / "profiles" / "router_config.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")


def extract_tool_json(text: str) -> dict | None:
    import json
    text = (text or "").strip()
    if not text:
        return None
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end <= start:
        return None
    try:
        obj = json.loads(text[start : end + 1])
    except Exception:
        return None
    if not isinstance(obj, dict):
        return None
    name = obj.get("tool") or obj.get("name")
    if not name:
        return None
    args = obj.get("arguments") or obj.get("args") or {}
    if args is not None and not isinstance(args, dict):
        return None
    return {"tool": name, "arguments": args or {}}
