"""
memory/adaptive_pattern.py
Adaptive Pattern Memory for JARVIS.

Inspired by Jarvis Institute feature specifications:
- Tracks tool execution outcomes: success rate per tool.
- Error -> fix mapping: records errors encountered and successful resolutions.
- Preference weights and pattern learning: persists in memory/adaptive_patterns.json.
- Recommends best tools and flags known failure pitfalls.
"""

from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from threading import RLock
from typing import Any, Dict, List, Optional


def get_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent


BASE_DIR = get_base_dir()
PATTERNS_FILE = BASE_DIR / "memory" / "adaptive_patterns.json"
_lock = RLock()


def _load_patterns() -> Dict[str, Any]:
    if not PATTERNS_FILE.exists():
        return {
            "tool_stats": {},
            "error_fix_maps": {},
            "preference_weights": {},
        }
    try:
        data = json.loads(PATTERNS_FILE.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return {"tool_stats": {}, "error_fix_maps": {}, "preference_weights": {}}
        return data
    except Exception:
        return {"tool_stats": {}, "error_fix_maps": {}, "preference_weights": {}}


def _save_patterns(data: Dict[str, Any]) -> None:
    PATTERNS_FILE.parent.mkdir(parents=True, exist_ok=True)
    try:
        PATTERNS_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")
    except Exception as e:
        print(f"[AdaptivePattern] Save error: {e}")


def record_tool_execution(tool_name: str, success: bool, error_msg: Optional[str] = None, fix_applied: Optional[str] = None) -> None:
    """Records an execution of a tool, updating success rate and error->fix mappings."""
    if not tool_name:
        return

    with _lock:
        patterns = _load_patterns()
        stats = patterns.setdefault("tool_stats", {})
        tool_data = stats.setdefault(tool_name, {
            "invocations": 0,
            "successes": 0,
            "failures": 0,
            "last_used": None,
            "success_rate": 1.0,
        })

        tool_data["invocations"] += 1
        tool_data["last_used"] = datetime.now().isoformat()
        if success:
            tool_data["successes"] += 1
        else:
            tool_data["failures"] += 1

        total = tool_data["invocations"]
        tool_data["success_rate"] = round(tool_data["successes"] / max(1, total), 3)

        # Record error-to-fix mapping if provided
        if error_msg:
            err_maps = patterns.setdefault("error_fix_maps", {})
            err_key = f"{tool_name}:{error_msg[:80].strip()}"
            existing = err_maps.setdefault(err_key, {
                "tool": tool_name,
                "error": error_msg[:120],
                "occurrences": 0,
                "fixes": [],
            })
            existing["occurrences"] += 1
            if fix_applied and fix_applied not in existing["fixes"]:
                existing["fixes"].append(fix_applied)

        _save_patterns(patterns)


def get_tool_performance_summary() -> str:
    """Returns a formatted summary of tool success rates and learned patterns."""
    with _lock:
        patterns = _load_patterns()

    stats = patterns.get("tool_stats", {})
    if not stats:
        return "Adaptive Pattern Memory has no recorded tool runs yet."

    lines = ["=== Adaptive Pattern Memory: Tool Success Rates ==="]
    # Sort by invocations desc
    sorted_tools = sorted(stats.items(), key=lambda x: x[1].get("invocations", 0), reverse=True)
    for name, data in sorted_tools:
        rate = data.get("success_rate", 1.0) * 100
        invocations = data.get("invocations", 0)
        successes = data.get("successes", 0)
        failures = data.get("failures", 0)
        lines.append(f"• {name:20} -> {rate:5.1f}% success ({successes}/{invocations}) [Fails: {failures}]")

    err_maps = patterns.get("error_fix_maps", {})
    if err_maps:
        lines.append("\n=== Learned Error-to-Fix Mappings ===")
        for key, err_data in list(err_maps.items())[:5]:
            fixes = ", ".join(err_data.get("fixes", [])) or "None recorded"
            lines.append(f"• [{err_data.get('tool')}] Err: {err_data.get('error', '')[:60]} -> Fix: {fixes}")

    return "\n".join(lines)


def get_recommended_tool_fix(tool_name: str, error_msg: str) -> Optional[str]:
    """Retrieves a known fix for a tool error if previously learned."""
    with _lock:
        patterns = _load_patterns()
    err_maps = patterns.get("error_fix_maps", {})
    err_key = f"{tool_name}:{error_msg[:80].strip()}"
    if err_key in err_maps:
        fixes = err_maps[err_key].get("fixes", [])
        if fixes:
            return fixes[-1]
    return None
