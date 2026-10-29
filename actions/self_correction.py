"""
actions/self_correction.py — Autonomous Self-Correction and Code Repair Action.

Enables JARVIS and H.O.M.E.R to inspect errors, modify source code,
verify syntax, and heal defects autonomously without requiring human intervention.
"""
from __future__ import annotations

from core.self_heal import diagnose_and_repair, get_recent_failures


def self_correct_code(
    parameters: dict = None,
    target_file: str = "",
    issue_description: str = "",
    error_traceback: str = "",
    player=None,
    **kwargs
) -> str:
    """Diagnose and autonomously patch a file in the JARVIS codebase."""
    params = parameters or {}
    t_file = params.get("target_file") or target_file or ""
    issue = params.get("issue_description") or issue_description or ""
    tb = params.get("error_traceback") or error_traceback or ""

    if not t_file:
        # Check recent failures
        failures = get_recent_failures()
        if failures:
            last_fail = failures[-1]
            t_file = last_fail.get("source", "")
            if not issue:
                issue = last_fail.get("error", "Runtime crash or exception")
            if not tb:
                tb = last_fail.get("traceback", "")
        else:
            return "Self-correction failed: No target file or recent recorded failure specified."

    if not issue:
        issue = "Fix runtime error and ensure proper syntax and robust error handling."

    result = diagnose_and_repair(
        target_file=t_file,
        issue_description=issue,
        error_traceback=tb,
        player=player
    )

    if result.get("status") == "SUCCESS":
        msg = (
            f"Autonomous Self-Correction Completed by H.O.M.E.R:\n"
            f"• Target File: {result.get('file')}\n"
            f"• Result: Verified and patched successfully.\n"
            f"• Safety Backup: {result.get('backup_created')}\n"
            f"The codebase has healed itself and is ready for continued execution."
        )
    else:
        msg = (
            f"Self-Correction Alert: {result.get('status')}\n"
            f"Details: {result.get('message', 'Unknown failure')}\n"
            f"No changes were committed to prevent destabilizing the system."
        )

    return msg


TOOL = {
    "name": "self_correct_code",
    "description": (
        "JARVIS's Autonomous Self-Correction and Code Healing engine, managed by H.O.M.E.R. "
        "Use this tool whenever an action fails, an exception occurs, a script breaks, "
        "or code needs to be modified/repaired autonomously. JARVIS writes and fixes its "
        "own code, verifies syntax, and restores functionality."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "target_file": {
                "type": "STRING",
                "description": "Path or filename to repair (e.g. 'actions/web_downloader.py', 'ui.py', or 'actions/coworker_dispatch.py')."
            },
            "issue_description": {
                "type": "STRING",
                "description": "Detailed description of the bug, defect, or missing logic that needs fixing."
            },
            "error_traceback": {
                "type": "STRING",
                "description": "Optional error traceback or exception log."
            }
        },
        "required": ["issue_description"]
    },
    "handler": self_correct_code,
}
