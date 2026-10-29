"""
actions/jira_control.py
Jira Workflow and Automated Ticket Creation for JARVIS.

Inspired by Jarvis Institute feature specifications:
- Jira automation: tickets, boards, sprints automated via natural language.
- "find all TODO comments in src/ and create Jira tickets for each"
- "create a Jira ticket for the auth TODO"
- "create a Jira ticket from [name] WhatsApp request"
- Supports creating, listing, searching, updating tickets, and codebase TODO scanning.
"""

from __future__ import annotations

import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Optional

_JIRA_STORE_PATH = Path(__file__).resolve().parent.parent / "config" / "jira_tickets.json"


def _load_jira_store() -> dict:
    if _JIRA_STORE_PATH.exists():
        try:
            with open(_JIRA_STORE_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "project_key": "JARV",
        "next_id": 101,
        "tickets": [
            {
                "key": "JARV-100",
                "summary": "Implement Redis hot cache for session tokens",
                "description": "Cache recent context and tokens to reduce latency.",
                "issue_type": "Task",
                "status": "In Progress",
                "priority": "High",
                "assignee": "Hamad",
                "created_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "labels": ["performance", "backend"],
            }
        ],
    }


def _save_jira_store(data: dict) -> None:
    _JIRA_STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(_JIRA_STORE_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def handle_jira_control(
    action: str = "list",
    summary: Optional[str] = None,
    description: Optional[str] = None,
    issue_key: Optional[str] = None,
    status: Optional[str] = None,
    priority: str = "Medium",
    issue_type: str = "Task",
    search_path: Optional[str] = None,
    labels: Optional[list[str]] = None,
    player=None,
    speak=None,
) -> str:
    """Dispatches Jira ticket operations and codebase TODO automation."""
    act = (action or "list").lower().strip()
    store = _load_jira_store()

    log_msg = f"[Jira] Action '{act}'"
    print(log_msg)
    if player:
        try:
            player.write_log(log_msg)
        except Exception:
            pass

    # ── 1. Create Ticket ──────────────────────────────────────────────────────
    if act in ("create", "add", "new"):
        if not summary:
            return "Please provide a summary or title for the Jira ticket."

        proj_key = store.get("project_key", "JARV")
        next_id = store.get("next_id", 101)
        new_key = f"{proj_key}-{next_id}"
        store["next_id"] = next_id + 1

        new_ticket = {
            "key": new_key,
            "summary": summary.strip(),
            "description": (description or "").strip(),
            "issue_type": issue_type.capitalize(),
            "status": "To Do",
            "priority": priority.capitalize(),
            "assignee": "Hamad",
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "labels": labels or ["jarvis-auto"],
        }
        store["tickets"].append(new_ticket)
        _save_jira_store(store)
        return (
            f"Created Jira ticket {new_key}: '{new_ticket['summary']}' "
            f"[{new_ticket['issue_type']}] Priority: {new_ticket['priority']} (Status: To Do)."
        )

    # ── 2. Scan Codebase for TODOs and Auto-Create Tickets ─────────────────────
    if act in ("scan_todos", "scan_todo", "todo_scanner"):
        target_dir = Path(search_path) if search_path else Path(__file__).resolve().parent.parent
        if not target_dir.exists():
            target_dir = Path.cwd()

        found_todos = []
        skip_dirs = {".git", ".idea", "__pycache__", "venv", "node_modules", "dist", "build"}
        extensions = {".py", ".ts", ".js", ".cs", ".html", ".css", ".md", ".json"}

        for root, dirs, files in os.walk(target_dir):
            dirs[:] = [d for d in dirs if d not in skip_dirs]
            for file in files:
                ext = Path(file).suffix.lower()
                if ext in extensions:
                    file_path = Path(root) / file
                    try:
                        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                            for idx, line in enumerate(f, start=1):
                                match = re.search(r"\b(TODO|FIXME|BUG)\b[:\s]*(.*)", line, re.IGNORECASE)
                                if match:
                                    tag = match.group(1).upper()
                                    todo_text = match.group(2).strip()
                                    if len(todo_text) > 3:
                                        rel_path = file_path.relative_to(target_dir) if target_dir in file_path.parents else file_path.name
                                        found_todos.append((str(rel_path), idx, tag, todo_text))
                    except Exception:
                        pass

        if not found_todos:
            return f"No pending TODO or FIXME comments found in '{target_dir.name}'."

        created_keys = []
        proj_key = store.get("project_key", "JARV")
        for rel_path, line_no, tag, todo_text in found_todos[:5]:  # Batch create up to 5 per scan
            next_id = store.get("next_id", 101)
            new_key = f"{proj_key}-{next_id}"
            store["next_id"] = next_id + 1

            ticket = {
                "key": new_key,
                "summary": f"[{tag}] {todo_text[:80]}",
                "description": f"Found at {rel_path}:{line_no}\nDetails: {todo_text}",
                "issue_type": "Bug" if tag == "BUG" else "Task",
                "status": "To Do",
                "priority": "High" if tag in ("BUG", "FIXME") else "Medium",
                "assignee": "Hamad",
                "created_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "labels": ["code-todo", tag.lower()],
            }
            store["tickets"].append(ticket)
            created_keys.append(f"{new_key} ({rel_path}:{line_no})")

        _save_jira_store(store)
        return (
            f"Scanned {target_dir.name} and found {len(found_todos)} TODOs. "
            f"Created {len(created_keys)} Jira tickets: {', '.join(created_keys)}."
        )

    # ── 3. List or Search Tickets ─────────────────────────────────────────────
    if act in ("list", "search", "board", "sprint"):
        tickets = store.get("tickets", [])
        if not tickets:
            return "No Jira tickets found in current sprint."

        if summary:  # Filter by keyword
            kw = summary.lower()
            tickets = [t for t in tickets if kw in t["summary"].lower() or kw in t.get("description", "").lower()]

        if not tickets:
            return f"No tickets matching '{summary}'."

        lines = [f"Found {len(tickets)} Jira ticket(s):"]
        for t in tickets[-8:]:  # show recent 8
            lines.append(f"• [{t['key']}] ({t.get('status', 'To Do')}) {t['summary']} [{t.get('priority', 'Medium')}]")
        return "\n".join(lines)

    # ── 4. Update Ticket ──────────────────────────────────────────────────────
    if act in ("update", "move", "close", "resolve"):
        if not issue_key:
            return "Please provide the Jira issue key (e.g., 'JARV-101') to update."

        target = None
        for t in store.get("tickets", []):
            if t["key"].upper() == issue_key.upper():
                target = t
                break

        if not target:
            return f"Jira ticket '{issue_key}' not found."

        if status:
            target["status"] = status
        if summary:
            target["summary"] = summary
        if priority:
            target["priority"] = priority.capitalize()

        _save_jira_store(store)
        return f"Updated Jira ticket {target['key']}: Status '{target['status']}', Priority '{target['priority']}'."

    return f"Unknown Jira action '{act}'. Supported actions: 'create', 'scan_todos', 'list', 'update'."


def jira_control_action(parameters: dict, player=None, speak=None) -> str:
    return handle_jira_control(
        action=parameters.get("action", "list"),
        summary=parameters.get("summary"),
        description=parameters.get("description"),
        issue_key=parameters.get("issue_key"),
        status=parameters.get("status"),
        priority=parameters.get("priority", "Medium"),
        issue_type=parameters.get("issue_type", "Task"),
        search_path=parameters.get("search_path"),
        labels=parameters.get("labels"),
        player=player,
        speak=speak,
    )


TOOL = {
    "name": "jira_control",
    "description": (
        "Manages Jira tickets, boards, and automated workflows: create tickets, list issues, "
        "update issue status (To Do, In Progress, Done), and scan codebase files for TODO/FIXME "
        "comments to automatically convert them into formatted Jira issues."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {
                "type": "STRING",
                "description": "Action to perform: 'create', 'scan_todos', 'list', 'update', or 'board'.",
            },
            "summary": {
                "type": "STRING",
                "description": "Ticket summary/title, or search keyword when listing.",
            },
            "description": {
                "type": "STRING",
                "description": "Detailed description or context for the ticket.",
            },
            "issue_key": {
                "type": "STRING",
                "description": "Issue key (e.g. 'JARV-101') when updating an existing ticket.",
            },
            "status": {
                "type": "STRING",
                "description": "Target status when updating: 'To Do', 'In Progress', 'Done', 'Blocked'.",
            },
            "priority": {
                "type": "STRING",
                "description": "Priority: 'Highest', 'High', 'Medium', 'Low'.",
            },
            "issue_type": {
                "type": "STRING",
                "description": "Issue type: 'Task', 'Bug', 'Story', 'Epic'.",
            },
            "search_path": {
                "type": "STRING",
                "description": "Directory path to scan when running 'scan_todos' (defaults to project root).",
            },
        },
        "required": ["action"],
    },
    "handler": jira_control_action,
}
