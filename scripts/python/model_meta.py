# -*- coding: utf-8 -*-
"""GGUF lightweight metadata + RAM estimate (no full model load)."""
from __future__ import annotations
from pathlib import Path
from typing import Any

def read_gguf_metadata(path: Path | str, max_kv: int = 40) -> dict[str, Any]:
    path = Path(path)
    out: dict[str, Any] = {
        "ok": False,
        "path": str(path),
        "name": path.name,
        "size_bytes": 0,
        "size_gb": 0.0,
        "architecture": None,
        "name_meta": None,
        "context_length": None,
        "keys": {},
    }
    if not path.is_file():
        out["error"] = "file not found"
        return out
    try:
        out["size_bytes"] = path.stat().st_size
        out["size_gb"] = round(out["size_bytes"] / (1024**3), 3)
    except OSError as e:
        out["error"] = str(e)
        return out
    try:
        with path.open("rb") as f:
            magic = f.read(4)
            if magic != b"GGUF":
                out["error"] = "not a GGUF file (bad magic)"
                return out
            # GGUF version u32, tensor_count u64, kv_count u64 (little-endian)
            import struct
            ver = struct.unpack("<I", f.read(4))[0]
            tensor_count = struct.unpack("<Q", f.read(8))[0]
            kv_count = struct.unpack("<Q", f.read(8))[0]
            out["gguf_version"] = ver
            out["tensor_count"] = tensor_count
            out["kv_count"] = kv_count
            # Best-effort KV parse (skip on complex types)
            keys = {}
            for _ in range(min(int(kv_count), max_kv * 3)):
                if len(keys) >= max_kv:
                    break
                try:
                    nlen = struct.unpack("<Q", f.read(8))[0]
                    if nlen <= 0 or nlen > 512:
                        break
                    name = f.read(nlen).decode("utf-8", errors="replace")
                    typ = struct.unpack("<I", f.read(4))[0]
                    val = _read_gguf_value(f, typ)
                    if val is not None and (
                        "arch" in name or "name" in name or "context" in name
                        or "block_count" in name or "embedding" in name
                    ):
                        keys[name] = val
                    elif val is None:
                        break
                except Exception:
                    break
            out["keys"] = keys
            out["architecture"] = keys.get("general.architecture") or keys.get("general.arch")
            out["name_meta"] = keys.get("general.name")
            for k, v in keys.items():
                if "context_length" in k and isinstance(v, (int, float)):
                    out["context_length"] = int(v)
                    break
            out["ok"] = True
    except Exception as e:
        out["error"] = str(e)
        out["ok"] = True  # size still valid
        out["parse_note"] = "partial metadata"
    return out


def _read_gguf_value(f, typ: int):
    import struct
    # GGUF types: 0 u8, 1 i8, 2 u16, 3 i16, 4 u32, 5 i32, 6 f32, 7 bool, 8 string, 9 array, 10 u64, 11 i64, 12 f64
    try:
        if typ == 0:
            return struct.unpack("<B", f.read(1))[0]
        if typ == 1:
            return struct.unpack("<b", f.read(1))[0]
        if typ == 2:
            return struct.unpack("<H", f.read(2))[0]
        if typ == 3:
            return struct.unpack("<h", f.read(2))[0]
        if typ == 4:
            return struct.unpack("<I", f.read(4))[0]
        if typ == 5:
            return struct.unpack("<i", f.read(4))[0]
        if typ == 6:
            return struct.unpack("<f", f.read(4))[0]
        if typ == 7:
            return bool(struct.unpack("<B", f.read(1))[0])
        if typ == 8:
            n = struct.unpack("<Q", f.read(8))[0]
            if n > 1_000_000:
                return None
            return f.read(n).decode("utf-8", errors="replace")
        if typ == 10:
            return struct.unpack("<Q", f.read(8))[0]
        if typ == 11:
            return struct.unpack("<q", f.read(8))[0]
        if typ == 12:
            return struct.unpack("<d", f.read(8))[0]
        if typ == 9:
            # array: type + count + skip elements (limited)
            at = struct.unpack("<I", f.read(4))[0]
            cnt = struct.unpack("<Q", f.read(8))[0]
            if cnt > 10000:
                return None
            for _ in range(int(cnt)):
                if _read_gguf_value(f, at) is None:
                    return None
            return f"<array {cnt}>"
    except Exception:
        return None
    return None


def estimate_ram_gb(size_bytes: int, n_ctx: int = 4096, n_gpu_layers: int = 0) -> dict[str, Any]:
    """Rough RAM/VRAM estimate for GGUF load."""
    size_gb = size_bytes / (1024**3)
    # weights + overhead + kv cache rough
    kv = max(0.2, (n_ctx / 4096) * 0.5 * max(size_gb / 4, 0.3))
    overhead = 0.4 + size_gb * 0.05
    total = size_gb + kv + overhead
    if n_gpu_layers == 0:
        return {
            "ram_gb_est": round(total, 2),
            "vram_gb_est": 0.0,
            "note_fa": "تقریبی — روی CPU تقریباً به اندازه فایل + کش KV رم لازم است",
        }
    # partial offload
    if n_gpu_layers < 0:
        frac = 0.85
    else:
        frac = min(0.9, 0.15 + n_gpu_layers * 0.02)
    return {
        "ram_gb_est": round(total * (1 - frac * 0.7), 2),
        "vram_gb_est": round(size_gb * frac + kv * 0.5, 2),
        "note_fa": "تقریبی — بسته به quant و بک‌اند CUDA/Vulkan فرق می‌کند",
    }
