# -*- coding: utf-8 -*-
"""
System monitoring tools for GGUF Runner.
CPU, RAM, disk, network, processes, uptime — Windows-first, Linux-friendly.
No external deps required (stdlib + optional psutil if installed).
"""
from __future__ import annotations

import os
import platform
import shutil
import socket
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from config_loader import ROOT, workspace_dir

try:
    import psutil  # type: ignore
    _HAS_PSUTIL = True
except Exception:
    psutil = None  # type: ignore
    _HAS_PSUTIL = False


def _run(cmd: list[str] | str, timeout: int = 30, shell: bool = False) -> tuple[int, str, str]:
    try:
        r = subprocess.run(
            cmd,
            shell=shell,
            capture_output=True,
            text=True,
            timeout=timeout,
            encoding="utf-8",
            errors="replace",
        )
        return r.returncode, r.stdout or "", r.stderr or ""
    except Exception as e:
        return 1, "", str(e)


def _human_bytes(n: float) -> str:
    n = float(n or 0)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if abs(n) < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} PB"


# ---------- overview ----------

def monitor_system() -> dict[str, Any]:
    """Snapshot: OS, CPU, RAM, disk root, boot time."""
    info: dict[str, Any] = {
        "ok": True,
        "time": datetime.now().isoformat(timespec="seconds"),
        "platform": platform.platform(),
        "system": platform.system(),
        "release": platform.release(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "python": sys.version.split()[0],
        "hostname": socket.gethostname(),
        "user": os.environ.get("USERNAME") or os.environ.get("USER"),
        "cwd": os.getcwd(),
        "app_root": str(ROOT),
        "psutil": _HAS_PSUTIL,
    }
    if _HAS_PSUTIL:
        info["cpu_count_logical"] = psutil.cpu_count(logical=True)
        info["cpu_count_physical"] = psutil.cpu_count(logical=False)
        info["cpu_percent"] = psutil.cpu_percent(interval=0.3)
        vm = psutil.virtual_memory()
        info["ram"] = {
            "total": vm.total,
            "available": vm.available,
            "used": vm.used,
            "percent": vm.percent,
            "total_h": _human_bytes(vm.total),
            "used_h": _human_bytes(vm.used),
            "available_h": _human_bytes(vm.available),
        }
        try:
            bt = datetime.fromtimestamp(psutil.boot_time())
            info["boot_time"] = bt.isoformat(timespec="seconds")
            info["uptime_sec"] = int(time.time() - psutil.boot_time())
        except Exception:
            pass
        try:
            du = shutil.disk_usage(str(Path.home().anchor or "/"))
            info["disk_root"] = {
                "total": du.total,
                "used": du.used,
                "free": du.free,
                "percent": round(du.used / du.total * 100, 1) if du.total else 0,
                "total_h": _human_bytes(du.total),
                "free_h": _human_bytes(du.free),
            }
        except Exception:
            pass
    else:
        info["cpu_count"] = os.cpu_count()
        try:
            du = shutil.disk_usage(str(Path.home().anchor if os.name == "nt" else "/"))
            info["disk_root"] = {
                "total_h": _human_bytes(du.total),
                "free_h": _human_bytes(du.free),
                "used_h": _human_bytes(du.used),
                "percent": round(du.used / du.total * 100, 1) if du.total else 0,
            }
        except Exception:
            pass
        if os.name == "nt":
            code, out, _ = _run("wmic os get FreePhysicalMemory,TotalVisibleMemorySize /value", shell=True)
            info["wmic_mem_raw"] = out.strip()[:500]
    return info


def monitor_cpu(interval: float = 0.5) -> dict[str, Any]:
    if _HAS_PSUTIL:
        interval = max(0.1, min(float(interval or 0.5), 5.0))
        per = psutil.cpu_percent(interval=interval, percpu=True)
        return {
            "ok": True,
            "cpu_percent": sum(per) / len(per) if per else psutil.cpu_percent(interval=0),
            "per_cpu": per,
            "count_logical": psutil.cpu_count(logical=True),
            "count_physical": psutil.cpu_count(logical=False),
            "freq": getattr(psutil.cpu_freq(), "current", None) if psutil.cpu_freq() else None,
        }
    if os.name == "nt":
        code, out, err = _run(
            'powershell -NoProfile -Command "(Get-Counter \'\\Processor(_Total)\\% Processor Time\').CounterSamples.CookedValue"',
            timeout=20,
        )
        return {"ok": code == 0, "raw": (out or err).strip()[:1000], "note": "install psutil for richer CPU stats"}
    code, out, err = _run(["top", "-bn1"], timeout=10)
    return {"ok": True, "raw": (out or err)[:2000], "note": "install psutil for richer CPU stats"}


def monitor_memory() -> dict[str, Any]:
    if _HAS_PSUTIL:
        vm = psutil.virtual_memory()
        sm = psutil.swap_memory()
        return {
            "ok": True,
            "ram": {
                "total": vm.total,
                "available": vm.available,
                "used": vm.used,
                "percent": vm.percent,
                "total_h": _human_bytes(vm.total),
                "used_h": _human_bytes(vm.used),
                "available_h": _human_bytes(vm.available),
            },
            "swap": {
                "total": sm.total,
                "used": sm.used,
                "percent": sm.percent,
                "total_h": _human_bytes(sm.total),
                "used_h": _human_bytes(sm.used),
            },
        }
    if os.name == "nt":
        code, out, _ = _run(
            "wmic OS get FreePhysicalMemory,TotalVisibleMemorySize /value",
            shell=True,
        )
        return {"ok": code == 0, "raw": out.strip()[:800], "note": "pip install psutil recommended"}
    code, out, _ = _run(["free", "-h"], timeout=10)
    return {"ok": code == 0, "raw": out}


def monitor_disk(path: str = "") -> dict[str, Any]:
    """Disk usage for path (default: all partitions if psutil, else system drive)."""
    if _HAS_PSUTIL and not path:
        parts = []
        for p in psutil.disk_partitions(all=False):
            try:
                u = psutil.disk_usage(p.mountpoint)
                parts.append({
                    "device": p.device,
                    "mount": p.mountpoint,
                    "fstype": p.fstype,
                    "total_h": _human_bytes(u.total),
                    "used_h": _human_bytes(u.used),
                    "free_h": _human_bytes(u.free),
                    "percent": u.percent,
                })
            except Exception as e:
                parts.append({"device": p.device, "mount": p.mountpoint, "error": str(e)})
        io = None
        try:
            c = psutil.disk_io_counters()
            if c:
                io = {"read_h": _human_bytes(c.read_bytes), "write_h": _human_bytes(c.write_bytes)}
        except Exception:
            pass
        return {"ok": True, "partitions": parts, "io": io}

    target = path or (str(Path.home().anchor) if os.name == "nt" else "/")
    try:
        u = shutil.disk_usage(target)
        return {
            "ok": True,
            "path": target,
            "total_h": _human_bytes(u.total),
            "used_h": _human_bytes(u.used),
            "free_h": _human_bytes(u.free),
            "percent": round(u.used / u.total * 100, 1) if u.total else 0,
        }
    except Exception as e:
        return {"ok": False, "error": str(e), "path": target}


def monitor_network() -> dict[str, Any]:
    if _HAS_PSUTIL:
        io = psutil.net_io_counters()
        addrs = {}
        for name, lst in psutil.net_if_addrs().items():
            addrs[name] = [
                {"family": str(a.family), "address": a.address, "netmask": a.netmask}
                for a in lst
            ]
        stats = {}
        try:
            for name, st in psutil.net_if_stats().items():
                stats[name] = {"isup": st.isup, "speed": st.speed, "mtu": st.mtu}
        except Exception:
            pass
        return {
            "ok": True,
            "io": {
                "bytes_sent_h": _human_bytes(io.bytes_sent),
                "bytes_recv_h": _human_bytes(io.bytes_recv),
                "packets_sent": io.packets_sent,
                "packets_recv": io.packets_recv,
                "errin": io.errin,
                "errout": io.errout,
            },
            "interfaces": addrs,
            "stats": stats,
        }
    if os.name == "nt":
        code, out, _ = _run("ipconfig /all", shell=True, timeout=20)
        return {"ok": code == 0, "raw": out[:4000], "note": "pip install psutil recommended"}
    code, out, _ = _run(["ip", "-br", "addr"], timeout=10)
    if code != 0:
        code, out, _ = _run(["ifconfig"], timeout=10)
    return {"ok": True, "raw": out[:4000]}


def monitor_processes(limit: int = 25, sort: str = "cpu") -> dict[str, Any]:
    """Top processes by cpu or memory."""
    limit = max(1, min(int(limit or 25), 100))
    sort = (sort or "cpu").lower()
    if _HAS_PSUTIL:
        rows = []
        for p in psutil.process_iter(["pid", "name", "username", "cpu_percent", "memory_percent", "memory_info"]):
            try:
                info = p.info
                rss = 0
                mi = info.get("memory_info")
                if mi is not None:
                    rss = getattr(mi, "rss", 0) or 0
                rows.append({
                    "pid": info.get("pid"),
                    "name": info.get("name"),
                    "user": info.get("username"),
                    "cpu": info.get("cpu_percent") or 0,
                    "mem_percent": round(float(info.get("memory_percent") or 0), 2),
                    "rss_h": _human_bytes(rss),
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        key = "cpu" if sort.startswith("cpu") else "mem_percent"
        rows.sort(key=lambda x: float(x.get(key) or 0), reverse=True)
        return {"ok": True, "sort": sort, "processes": rows[:limit], "count": len(rows)}
    if os.name == "nt":
        code, out, _ = _run("tasklist /fo csv /nh", shell=True, timeout=30)
        lines = [ln for ln in out.splitlines() if ln.strip()][:limit]
        return {"ok": code == 0, "processes": lines, "count": len(lines)}
    code, out, _ = _run(["ps", "aux", "--sort=-%cpu"], timeout=15)
    lines = out.splitlines()[: limit + 1]
    return {"ok": True, "processes": lines, "count": max(0, len(lines) - 1)}


def monitor_process(pid: int = 0, name: str = "") -> dict[str, Any]:
    """Details for one process by pid or name substring."""
    if _HAS_PSUTIL:
        if pid:
            try:
                p = psutil.Process(int(pid))
                with p.oneshot():
                    mi = p.memory_info()
                    return {
                        "ok": True,
                        "pid": p.pid,
                        "name": p.name(),
                        "status": p.status(),
                        "cpu_percent": p.cpu_percent(interval=0.2),
                        "mem_percent": p.memory_percent(),
                        "rss_h": _human_bytes(mi.rss),
                        "cmdline": p.cmdline()[:20],
                        "create_time": datetime.fromtimestamp(p.create_time()).isoformat(timespec="seconds"),
                        "username": p.username(),
                    }
            except Exception as e:
                return {"ok": False, "error": str(e)}
        name = (name or "").lower().strip()
        if not name:
            return {"ok": False, "error": "provide pid or name"}
        found = []
        for p in psutil.process_iter(["pid", "name"]):
            try:
                if name in (p.info.get("name") or "").lower():
                    found.append({"pid": p.info["pid"], "name": p.info["name"]})
            except Exception:
                continue
        return {"ok": True, "matches": found[:40], "count": len(found)}
    return {"ok": False, "error": "psutil required for process detail (pip install psutil)"}


def monitor_uptime() -> dict[str, Any]:
    if _HAS_PSUTIL:
        bt = psutil.boot_time()
        up = int(time.time() - bt)
        h, rem = divmod(up, 3600)
        m, s = divmod(rem, 60)
        d, h = divmod(h, 24)
        return {
            "ok": True,
            "boot_time": datetime.fromtimestamp(bt).isoformat(timespec="seconds"),
            "uptime_sec": up,
            "uptime_human": f"{d}d {h}h {m}m {s}s",
        }
    if os.name == "nt":
        code, out, _ = _run(
            'powershell -NoProfile -Command "(get-date) - (gcim Win32_OperatingSystem).LastBootUpTime"',
            timeout=15,
        )
        return {"ok": code == 0, "raw": out.strip()[:500]}
    code, out, _ = _run(["uptime"], timeout=5)
    return {"ok": True, "raw": out.strip()}


def monitor_sensors() -> dict[str, Any]:
    """Temperatures / fans if psutil supports them."""
    if not _HAS_PSUTIL:
        return {"ok": False, "error": "psutil not installed"}
    out: dict[str, Any] = {"ok": True}
    try:
        temps = psutil.sensors_temperatures() if hasattr(psutil, "sensors_temperatures") else {}
        out["temperatures"] = {
            k: [{"label": t.label, "current": t.current, "high": t.high} for t in v]
            for k, v in (temps or {}).items()
        }
    except Exception as e:
        out["temperatures_error"] = str(e)
    try:
        fans = psutil.sensors_fans() if hasattr(psutil, "sensors_fans") else {}
        out["fans"] = {k: [{"label": f.label, "current": f.current} for f in v] for k, v in (fans or {}).items()}
    except Exception as e:
        out["fans_error"] = str(e)
    try:
        bat = psutil.sensors_battery() if hasattr(psutil, "sensors_battery") else None
        if bat:
            out["battery"] = {
                "percent": bat.percent,
                "plugged": bat.power_plugged,
                "secs_left": bat.secsleft,
            }
    except Exception:
        pass
    return out


def monitor_app() -> dict[str, Any]:
    """GGUF Runner app / workspace footprint."""
    def _dir_size(path: Path, limit_files: int = 5000) -> tuple[int, int]:
        total = 0
        n = 0
        try:
            for f in path.rglob("*"):
                if f.is_file():
                    try:
                        total += f.stat().st_size
                        n += 1
                    except OSError:
                        pass
                    if n >= limit_files:
                        break
        except Exception:
            pass
        return total, n

    models = ROOT / "models"
    ws = workspace_dir()
    m_size, m_n = _dir_size(models) if models.exists() else (0, 0)
    w_size, w_n = _dir_size(ws) if ws.exists() else (0, 0)
    gguf = list(models.glob("*.gguf")) if models.exists() else []
    return {
        "ok": True,
        "root": str(ROOT),
        "models_dir": str(models),
        "models_count": len(gguf),
        "models_size_h": _human_bytes(m_size),
        "workspace_size_h": _human_bytes(w_size),
        "workspace_files_scanned": w_n,
        "gguf_files": [p.name for p in gguf[:30]],
    }


def monitor_ports(limit: int = 40) -> dict[str, Any]:
    """Listening connections / ports."""
    limit = max(1, min(int(limit or 40), 200))
    if _HAS_PSUTIL:
        rows = []
        for c in psutil.net_connections(kind="inet"):
            if c.status != "LISTEN" and not (c.status == "NONE" and c.laddr):
                # include LISTEN primarily
                if c.status != "LISTEN":
                    continue
            la = c.laddr
            rows.append({
                "pid": c.pid,
                "status": c.status,
                "laddr": f"{getattr(la, 'ip', la[0] if la else '')}:{getattr(la, 'port', la[1] if la and len(la)>1 else '')}",
            })
            if len(rows) >= limit:
                break
        return {"ok": True, "listening": rows, "count": len(rows)}
    if os.name == "nt":
        code, out, _ = _run("netstat -ano | findstr LISTENING", shell=True, timeout=20)
        lines = [ln for ln in out.splitlines() if ln.strip()][:limit]
        return {"ok": True, "raw_lines": lines, "count": len(lines)}
    code, out, _ = _run(["ss", "-tlnp"], timeout=10)
    return {"ok": code == 0, "raw": out[:3000]}


MONITOR_TOOLS: dict[str, Any] = {
    "monitor_system": monitor_system,
    "monitor_cpu": monitor_cpu,
    "monitor_memory": monitor_memory,
    "monitor_disk": monitor_disk,
    "monitor_network": monitor_network,
    "monitor_processes": monitor_processes,
    "monitor_process": monitor_process,
    "monitor_uptime": monitor_uptime,
    "monitor_sensors": monitor_sensors,
    "monitor_app": monitor_app,
    "monitor_ports": monitor_ports,
    # short aliases
    "sys_monitor": monitor_system,
    "cpu": monitor_cpu,
    "mem": monitor_memory,
    "disk": monitor_disk,
}
