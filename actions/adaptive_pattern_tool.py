"""
actions/adaptive_pattern_tool.py
Action to inspect JARVIS Adaptive Pattern Memory.
Shows success rates per tool and learned error-to-fix patterns.
"""

from __future__ import annotations
from typing import Optional
from memory.adaptive_pattern import (
    get_tool_performance_summary,
    get_recommended_tool_fix,
)


def handle_adaptive_pattern(
    action: str = "summary",
    tool_name: Optional[str] = None,
    error_msg: Optional[str] = None,
    player=None,
    speak=None,
) -> str:
    act = (action or "summary").lower().strip()

    if act in ("summary", "stats", "rates", "list"):
        return get_tool_performance_summary()

    elif act in ("fix", "lookup", "recommend"):
        if not tool_name or not error_msg:
            return "Please provide both 'tool_name' and 'error_msg' to look up learned fixes."
        fix = get_recommended_tool_fix(tool_name, error_msg)
        if fix:
            return f"Learned fix for {tool_name} error:\n{fix}"
        return f"No known fix learned for '{tool_name}' with that error yet."

    return "Unknown action. Choose from 'summary' or 'fix'."


def pattern_action(parameters: dict, player=None, speak=None) -> str:
    action = parameters.get("action", "summary")
    tool_name = parameters.get("tool_name")
    error_msg = parameters.get("error_msg")
    return handle_adaptive_pattern(
        action=action,
        tool_name=tool_name,
        error_msg=error_msg,
        player=player,
        speak=speak,
    )


TOOL = {
    "name": "adaptive_pattern_memory",
    "description": (
        "Inspects JARVIS Adaptive Pattern Memory: shows tool execution success rates (%), "
        "total invocations, failure rates, and learned error-to-fix mappings across sessions."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {
                "type": "STRING",
                "description": "Action: 'summary' (view stats and success rates) or 'fix' (lookup learned fix).",
            },
            "tool_name": {
                "type": "STRING",
                "description": "Tool name to query fix for.",
            },
            "error_msg": {
                "type": "STRING",
                "description": "Error message to query fix for.",
            },
        },
        "required": ["action"],
    },
    "handler": pattern_action,
}
