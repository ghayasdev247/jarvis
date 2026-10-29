"""
actions/pc_optimizer.py — Advanced PC Health & Performance Optimizer for J.A.R.V.I.S.
Inspired by Stonic AI's autonomous system optimization and diagnostic engine.
Performs memory trimming, junk/cache cleaning, and full hardware diagnostics.
"""
from __future__ import annotations

import os
import shutil
import platform
import ctypes
from pathlib import Path
import psutil

from core import sfx

_OS = platform.system()


def _trim_ram() -> tuple[int, int]:
    """Trim memory working sets on Windows across active processes."""
    freed_processes = 0
    if _OS != "Windows":
        return 0, 0

    try:
        mem_before = psutil.virtual_memory().used
        kernel32 = ctypes.windll.kernel32
        psapi = ctypes.windll.psapi
        
        for proc in psutil.process_iter(['pid', 'name']):
            try:
                pid = proc.info['pid']
                if pid <= 4:
                    continue
                # PROCESS_QUERY_INFORMATION | PROCESS_SET_QUOTA
                handle = kernel32.OpenProcess(0x0400 | 0x0100, False, pid)
                if handle:
                    if psapi.EmptyWorkingSet(handle):
                        freed_processes += 1
                    kernel32.CloseHandle(handle)
            except Exception:
                continue

        mem_after = psutil.virtual_memory().used
        reclaimed_mb = max(0, int((mem_before - mem_after) / (1024 * 1024)))
        return freed_processes, reclaimed_mb
    except Exception:
        return 0, 0


def _clean_temp_files() -> tuple[int, float]:
    """Clean safe temporary files, user temp directory, and crash dumps."""
    cleaned_count = 0
    bytes_freed = 0

    temp_dirs = []
    if _OS == "Windows":
        u_temp = os.environ.get("TEMP", "")
        if u_temp and os.path.isdir(u_temp):
            temp_dirs.append(Path(u_temp))
        w_temp = os.environ.get("SYSTEMROOT", r"C:\Windows") + r"\Temp"
        if os.path.isdir(w_temp):
            temp_dirs.append(Path(w_temp))
    else:
        temp_dirs.append(Path("/tmp"))

    for t_dir in temp_dirs:
        try:
            for item in t_dir.iterdir():
                try:
                    if item.is_file():
                        sz = item.stat().st_size
                        item.unlink(missing_ok=True)
                        cleaned_count += 1
                        bytes_freed += sz
                    elif item.is_dir() and item.name.startswith(("_", "tmp", "pip")):
                        sz = sum(f.stat().st_size for f in item.rglob('*') if f.is_file())
                        shutil.rmtree(item, ignore_errors=True)
                        cleaned_count += 1
                        bytes_freed += sz
                except Exception:
                    continue
        except Exception:
            continue

    mb_freed = round(bytes_freed / (1024 * 1024), 1)
    return cleaned_count, mb_freed


def _get_top_processes(count: int = 5) -> list[str]:
    """Get the heaviest processes by RAM usage."""
    procs = []
    for p in psutil.process_iter(['pid', 'name', 'memory_info']):
        try:
            m = p.info['memory_info'].rss / (1024 * 1024)
            procs.append((p.info['name'], m))
        except Exception:
            continue
    procs.sort(key=lambda x: x[1], reverse=True)
    return [f"{name} ({mem:.0f} MB)" for name, mem in procs[:count]]


def pc_optimizer(parameters: dict, player=None, speak=None) -> str:
    params = parameters or {}
    action = params.get("action", "optimize_ram").lower().strip()

    if player:
        player.write_log(f"[Optimizer] Running: {action}")

    try:
        if action in ("optimize_ram", "clean_ram", "boost_ram", "trim_memory"):
            procs, reclaimed_mb = _trim_ram()
            vm = psutil.virtual_memory()
            sfx.play_optimized()
            msg = (
                f"RAM optimized, sir. Trimmed working sets across {procs} processes, "
                f"reclaiming ~{reclaimed_mb} MB. System memory is now at {vm.percent}% utilization "
                f"({vm.available // (1024 * 1024):,} MB available)."
            )
            return msg

        elif action in ("clean_junk", "clean_temp", "clear_cache", "cleanup"):
            files, mb = _clean_temp_files()
            sfx.play_optimized()
            msg = f"Cleaned {files} temporary items, recovering {mb} MB of disk storage, sir."
            return msg

        elif action in ("full_optimize", "tune_up", "boost"):
            procs, reclaimed_mb = _trim_ram()
            files, mb = _clean_temp_files()
            sfx.play_optimized()
            vm = psutil.virtual_memory()
            msg = (
                f"Full PC optimization complete, sir. Freed ~{reclaimed_mb} MB of RAM across {procs} processes "
                f"and deleted {files} junk files ({mb} MB). Memory load is at {vm.percent}%."
            )
            return msg

        elif action in ("health", "diagnostics", "status"):
            cpu = psutil.cpu_percent(interval=0.2)
            vm = psutil.virtual_memory()
            disk = psutil.disk_usage('C:\\' if _OS == 'Windows' else '/')
            battery = psutil.sensors_battery()
            bat_str = f"{battery.percent}% ({'Charging' if battery.power_plugged else 'Discharging'})" if battery else "AC Power"
            top_p = ", ".join(_get_top_processes(3))

            msg = (
                f"System Health Diagnostics:\n"
                f"• CPU Load: {cpu}%\n"
                f"• RAM: {vm.percent}% ({vm.used // (1024 * 1024):,} MB used / {vm.total // (1024 * 1024):,} MB total)\n"
                f"• Disk Space: {disk.free // (1024 * 1024 * 1024)} GB free ({disk.percent}% used)\n"
                f"• Battery: {bat_str}\n"
                f"• Top Processes: {top_p}"
            )
            return msg

        else:
            return f"Unknown optimizer action: '{action}'. Available: optimize_ram, clean_junk, full_optimize, health."

    except Exception as e:
        return f"Optimizer encountered an error: {e}"


# ── Tool declaration (auto-discovered by core/action_loader.py) ──────────────
TOOL = {
    "name": "pc_optimizer",
    "description": "System performance optimizer and diagnostics (inspired by Stonic AI). Actions include: 'optimize_ram' (trims working sets and reclaims RAM), 'clean_junk' (cleans temporary cache files and frees disk space), 'full_optimize' (both RAM and storage cleanup), and 'health' (reports CPU, RAM, battery, disk, and top memory-consuming processes).",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {
                "type": "STRING",
                "description": "optimize_ram | clean_junk | full_optimize | health (default: optimize_ram)"
            }
        },
        "required": []
    },
    "handler": pc_optimizer,
}
