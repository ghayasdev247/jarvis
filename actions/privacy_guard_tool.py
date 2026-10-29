"""
actions/privacy_guard_tool.py
Privacy Guard management tool for JARVIS.
Allows checking privacy status, changing modes (STRICT / GUARDED / OFF), and reading the audit ledger.
"""

from __future__ import annotations
from typing import Optional
from core.privacy_guard import privacy_guard


def handle_privacy_guard(
    action: str = "status",
    mode: Optional[str] = None,
    text_to_redact: Optional[str] = None,
    limit: int = 10,
    player=None,
    speak=None,
) -> str:
    """Handles privacy guard inspection and mode switching."""
    act = (action or "status").lower().strip()

    if act == "status":
        current_mode = privacy_guard.get_mode()
        desc = {
            "STRICT": "STRICT mode active: All data is kept strictly local. Cloud API transmission is blocked.",
            "GUARDED": "GUARDED mode active: Sensitive credentials (API keys, passwords, bearer tokens) are auto-redacted before external transmission.",
            "OFF": "Privacy Guard is OFF: Cloud transmission occurs without redaction.",
        }.get(current_mode, "Unknown mode.")
        return f"Current Privacy Guard Mode: {current_mode}\n{desc}"

    elif act == "set_mode" or act == "mode":
        if not mode:
            return "Please specify a mode: 'STRICT', 'GUARDED', or 'OFF'."
        res = privacy_guard.set_mode(mode)
        if player:
            player.write_log(f"SYS: Privacy Guard mode changed to {mode.upper()}")
        return res

    elif act == "audit" or act == "ledger" or act == "history":
        return privacy_guard.get_audit_summary(limit=limit)

    elif act == "redact" or act == "test":
        if not text_to_redact:
            return "No text provided to redact."
        cleaned, count = privacy_guard.redact_text(text_to_redact)
        return f"Redactions performed: {count}\nResult:\n{cleaned}"

    return "Unknown action. Supported actions: 'status', 'set_mode', 'audit', 'redact'."


def privacy_guard_action(parameters: dict, player=None, speak=None) -> str:
    action = parameters.get("action", "status")
    mode = parameters.get("mode")
    text = parameters.get("text")
    limit = int(parameters.get("limit", 10))
    return handle_privacy_guard(action=action, mode=mode, text_to_redact=text, limit=limit, player=player, speak=speak)


TOOL = {
    "name": "privacy_guard",
    "description": (
        "Controls JARVIS Privacy Guard Core: inspects privacy mode, switches between STRICT "
        "(local data only), GUARDED (auto-redacts secrets and credentials), or OFF, and inspects "
        "the audit ledger of external API calls."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {
                "type": "STRING",
                "description": "Action to perform: 'status', 'set_mode', 'audit', or 'redact'.",
            },
            "mode": {
                "type": "STRING",
                "description": "Target mode for set_mode: 'STRICT', 'GUARDED', or 'OFF'.",
            },
            "text": {
                "type": "STRING",
                "description": "Sample text to test redaction on when action is 'redact'.",
            },
            "limit": {
                "type": "INTEGER",
                "description": "Number of recent audit ledger entries to display (default 10).",
            },
        },
        "required": ["action"],
    },
    "handler": privacy_guard_action,
}
