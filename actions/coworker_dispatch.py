"""
actions/coworker_dispatch.py — Tool for JARVIS to command his 4 Co-Workers:
- FRIDAY  (Web, Downloads, Browser)
- EDITH   (Security, Vision, Camera, Permissions)
- HOMER   (Coding, Scripts, Files, Systems)
- JOCASTA (Research, Intelligence, Data, Search)
"""
from __future__ import annotations

import time
from core.coworkers import get_manager

MANAGER = get_manager()


def delegate_coworker(
    parameters: dict = None,
    worker: str = "",
    command: str = "",
    context: str = "",
    player=None,
    **kwargs
) -> str:
    """Assign an order/directive from JARVIS to one or all of his 4 subordinates."""
    params = parameters or {}
    w_name = params.get("worker") or worker or "all"
    cmd = params.get("command") or command or "report status and stand by"
    ctx = params.get("context") or context or ""

    w_lower = w_name.lower().strip()

    # Handle "all" / "everyone" / "squad"
    if w_lower in ("all", "everyone", "squad", "team", "all agents", "agents", "coworkers", "co-workers"):
        lines = [
            f"JARVIS Commander Broadcast: '{cmd}'",
            "----------------------------------------------"
        ]
        for cid, cw in MANAGER.coworkers.items():
            MANAGER.assign_task(cid, cmd)
            lines.append(f"[OK] {cw.name} [{cw.title}]: Online & Executing (ACTIVE)")

        report = "\n".join(lines)
        if player:
            if hasattr(player, "show_squad_view"):
                player.show_squad_view(True, target_worker="all")
            if hasattr(player, "write_log"):
                player.write_log(f"[Squad] Tactical 4-Agent Stage opened in center HUD.")
        return report

    # Check for close/dismiss command
    if any(k in cmd.lower() or k in w_lower for k in ("close", "hide", "dismiss", "band karo", "hatao")):
        if player and hasattr(player, "close_squad_view"):
            player.close_squad_view()
        return "Co-worker view dismissed. Restored JARVIS main HUD."

    # Single coworker delegation
    w = MANAGER.get_coworker(w_name)
    if not w:
        # Default fallback: broadcast status if unknown
        lines = [f"Co-worker '{w_name}' not individually matched. Reporting all squad members:"]
        for cid, cw in MANAGER.coworkers.items():
            lines.append(f"• {cw.name} ({cw.title}) - Status: {cw.status}")
        return "\n".join(lines)

    MANAGER.assign_task(w.id, cmd)
    log_msg = f"[{w.name}] Order from JARVIS: '{cmd}'"

    if player:
        if hasattr(player, "show_squad_view"):
            # Bring specifically this co-worker to the solo center stage
            player.show_squad_view(True, target_worker=w.id)
        if hasattr(player, "write_log"):
            player.write_log(log_msg)

    report = (
        f"Order dispatched to {w.name} ({w.title}).\n"
        f"Directive: '{cmd}'\n"
        f"Status: {w.name} is now ACTIVE and solo stage opened in center HUD."
    )
    return report



def coworker_status(
    parameters: dict = None,
    worker: str = "all",
    player=None,
    **kwargs
) -> str:
    """Check the live operational status of JARVIS's co-workers."""
    params = parameters or {}
    w_name = params.get("worker") or worker or "all"

    if w_name.lower() in ("all", "everyone", ""):
        lines = ["=== JARVIS SUBORDINATE SQUAD STATUS ==="]
        for cw in MANAGER.coworkers.values():
            lines.append(
                f"• {cw.name} [{cw.status}] - {cw.title}\n"
                f"  Role: {cw.specialty}\n"
                f"  Task: {cw.current_task} (Completed: {cw.completed_tasks})"
            )
        res = "\n".join(lines)
    else:
        cw = MANAGER.get_coworker(w_name)
        if not cw:
            return f"Subordinate '{w_name}' not found."
        res = (
            f"{cw.name} [{cw.status}] - {cw.title}\n"
            f"Specialty: {cw.specialty}\n"
            f"Current directive: {cw.current_task}\n"
            f"Total tasks completed: {cw.completed_tasks}"
        )

    if player and hasattr(player, "write_log"):
        player.write_log(f"[Squad] Status inspection complete.")
    return res


TOOL = {
    "name": "delegate_coworker",
    "description": (
        "JARVIS's command delegation system. Use this tool whenever JARVIS assigns, directs, "
        "or commands his 4 subordinates to assist with a task, or when summoning the squad:\n"
        "- 'all': Commands all 4 subordinates simultaneously.\n"
        "- 'friday': Operations, web browsing, downloading, network monitoring.\n"
        "- 'edith': Tactical vision, security, camera feeds, desktop defense.\n"
        "- 'homer': Engineering, coding, compiling, system scripts, file organizing.\n"
        "- 'jocasta': Intelligence, data analysis, deep search, report synthesis.\n"
        "Allows JARVIS to issue orders to any co-worker and display their live status."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "worker": {
                "type": "STRING",
                "description": "Name of subordinate: 'friday', 'edith', 'homer', 'jocasta', or 'all'.",
                "enum": ["all", "friday", "edith", "homer", "jocasta"]
            },
            "command": {
                "type": "STRING",
                "description": "The exact instruction or task JARVIS is commanding the co-worker to perform."
            },
            "context": {
                "type": "STRING",
                "description": "Optional background info or parameters for the task."
            }
        }
    },
    "handler": delegate_coworker,
}
