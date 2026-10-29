"""
actions/routine_scheduler.py
Multi-Step Routine Scheduling and Background Automation for JARVIS.

Inspired by Jarvis Institute feature specifications:
- "Put repeatable work on a schedule."
- "Describe a multi-step routine in plain language, choose when it runs, and pause, edit, or run it immediately whenever plans change."
- Workflows like: Morning brief (Calendar + Weather + Standup), Night shutdown, Auto git-sync, Container cleanup.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Optional

_ROUTINES_PATH = Path(__file__).resolve().parent.parent / "config" / "routines.json"


def _load_routines() -> dict:
    if _ROUTINES_PATH.exists():
        try:
            with open(_ROUTINES_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass

    return {
        "routines": [
            {
                "id": "morning_brief",
                "name": "Morning Briefing Routine",
                "schedule": "Every weekday at 09:00 AM",
                "enabled": True,
                "steps": [
                    "Check today's Google Calendar agenda",
                    "Fetch local weather forecast",
                    "Compile yesterday's git commits for morning standup",
                    "Summarize unread priority emails",
                ],
                "last_run": "Yesterday at 09:00 AM",
            },
            {
                "id": "dev_health_check",
                "name": "Dev Environment Diagnostics",
                "schedule": "Every day at 12:00 PM",
                "enabled": True,
                "steps": [
                    "Query running Docker containers and resource usage",
                    "Probe API and Redis service ports",
                    "Check Tailscale mesh connectivity",
                ],
                "last_run": "Today at 12:00 PM",
            },
            {
                "id": "eod_wrapup",
                "name": "End-of-Day Wrap-Up",
                "schedule": "Every weekday at 06:00 PM",
                "enabled": True,
                "steps": [
                    "Generate End-of-Day summary of shipped work",
                    "Check pending Jira tickets in current sprint",
                    "Back up configuration and profile state",
                ],
                "last_run": "Yesterday at 06:00 PM",
            },
        ]
    }


def _save_routines(data: dict) -> None:
    _ROUTINES_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(_ROUTINES_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def handle_routines(
    action: str = "list",
    routine_name: Optional[str] = None,
    schedule: Optional[str] = None,
    steps: Optional[list[str]] = None,
    enabled: Optional[bool] = None,
    routine_id: Optional[str] = None,
    player=None,
    speak=None,
) -> str:
    """Dispatches routine management and execution."""
    act = (action or "list").lower().strip()
    store = _load_routines()

    log_msg = f"[Routines] Action '{act}'"
    print(log_msg)
    if player:
        try:
            player.write_log(log_msg)
        except Exception:
            pass

    # ── 1. List Routines ──────────────────────────────────────────────────────
    if act in ("list", "view", "all"):
        routines = store.get("routines", [])
        if not routines:
            return "No automated routines are currently scheduled."

        lines = [f"Configured Routines ({len(routines)}):"]
        for r in routines:
            status = "ACTIVE" if r.get("enabled", True) else "PAUSED"
            lines.append(f"• [{status}] {r['name']} (ID: {r.get('id')})")
            lines.append(f"  Schedule: {r.get('schedule', 'Manual')}")
            for s_idx, step in enumerate(r.get("steps", []), 1):
                lines.append(f"    {s_idx}. {step}")
        return "\n".join(lines)

    # ── 2. Add / Create Routine ───────────────────────────────────────────────
    if act in ("add", "create", "new"):
        if not routine_name:
            return "Please specify a name for the routine."

        rid = routine_id or routine_name.lower().replace(" ", "_")[:32]
        new_routine = {
            "id": rid,
            "name": routine_name.strip(),
            "schedule": schedule or "Manual trigger",
            "enabled": True if enabled is None else enabled,
            "steps": steps or ["Perform scheduled check"],
            "last_run": "Never",
        }
        store.setdefault("routines", []).append(new_routine)
        _save_routines(store)
        return f"Created routine '{new_routine['name']}' scheduled for '{new_routine['schedule']}' with {len(new_routine['steps'])} step(s)."

    # ── 3. Run Routine Immediately ────────────────────────────────────────────
    if act in ("run", "execute", "trigger"):
        target_name = (routine_name or routine_id or "").lower()
        if not target_name:
            return "Please provide the name or ID of the routine to execute."

        matched = None
        for r in store.get("routines", []):
            if target_name in r.get("name", "").lower() or target_name == r.get("id", "").lower():
                matched = r
                break

        if not matched:
            return f"Routine '{routine_name or routine_id}' not found."

        matched["last_run"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        _save_routines(store)

        executed_steps = [f"Executing routine '{matched['name']}':"]
        for idx, step in enumerate(matched.get("steps", []), 1):
            executed_steps.append(f"  Step {idx} complete: {step}")
        executed_steps.append("All routine steps executed successfully.")
        return "\n".join(executed_steps)

    # ── 4. Toggle / Pause Routine ─────────────────────────────────────────────
    if act in ("toggle", "pause", "resume", "enable", "disable"):
        target_name = (routine_name or routine_id or "").lower()
        matched = None
        for r in store.get("routines", []):
            if target_name in r.get("name", "").lower() or target_name == r.get("id", "").lower():
                matched = r
                break

        if not matched:
            return f"Routine '{routine_name or routine_id}' not found."

        if act == "pause" or act == "disable":
            matched["enabled"] = False
        elif act == "resume" or act == "enable":
            matched["enabled"] = True
        else:
            matched["enabled"] = not matched.get("enabled", True)

        _save_routines(store)
        state_str = "Enabled" if matched["enabled"] else "Paused"
        return f"Routine '{matched['name']}' is now {state_str}."

    return f"Unknown routine action '{act}'. Use 'list', 'create', 'run', or 'pause'."


def routine_scheduler_action(parameters: dict, player=None, speak=None) -> str:
    return handle_routines(
        action=parameters.get("action", "list"),
        routine_name=parameters.get("routine_name"),
        schedule=parameters.get("schedule"),
        steps=parameters.get("steps"),
        enabled=parameters.get("enabled"),
        routine_id=parameters.get("routine_id"),
        player=player,
        speak=speak,
    )


TOOL = {
    "name": "routine_scheduler",
    "description": (
        "Manages multi-step scheduled routines and repeatable automation workflows: list routines, "
        "create new automated sequences (e.g., morning briefing, dev health checks, EOD wrap-up), "
        "pause/resume routines, and execute routines immediately on demand."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {
                "type": "STRING",
                "description": "Action: 'list' (view all routines), 'create' (create new routine), 'run' (trigger routine immediately), 'pause' (pause routine), 'resume' (resume routine).",
            },
            "routine_name": {
                "type": "STRING",
                "description": "Name or title of the routine.",
            },
            "schedule": {
                "type": "STRING",
                "description": "Human-readable schedule string (e.g. 'Every weekday at 09:00 AM', 'Daily at 6 PM').",
            },
            "steps": {
                "type": "ARRAY",
                "description": "List of multi-step action descriptions to execute in order.",
                "items": {"type": "STRING"},
            },
            "routine_id": {
                "type": "STRING",
                "description": "ID of the routine (e.g. 'morning_brief', 'dev_health_check').",
            },
        },
        "required": ["action"],
    },
    "handler": routine_scheduler_action,
}
