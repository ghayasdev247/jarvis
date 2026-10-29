"""
actions/profile_tool.py
Action to inspect and update the user's personalized profile (profile.json).
"""

from __future__ import annotations
import json
from typing import Optional
from memory.profile_manager import (
    load_profile,
    update_profile_field,
    add_project,
    remove_project,
    format_profile_for_prompt,
)


def handle_profile(
    action: str = "view",
    field: Optional[str] = None,
    value: Optional[str] = None,
    project_name: Optional[str] = None,
    player=None,
    speak=None,
) -> str:
    act = (action or "view").lower().strip()

    if act in ("view", "show", "get"):
        p = load_profile()
        return "User Profile:\n" + json.dumps(p, indent=2)

    elif act == "summary":
        return format_profile_for_prompt()

    elif act in ("update", "set"):
        if not field or value is None:
            return "Please provide both 'field' (e.g., 'role', 'custom_instructions') and 'value'."
        res = update_profile_field(field, value)
        if player:
            player.write_log(f"Profile: Updated {field}")
        return res

    elif act == "add_project":
        name = project_name or value
        if not name:
            return "Please provide 'project_name'."
        res = add_project(name)
        if player:
            player.write_log(f"Profile: {res}")
        return res

    elif act == "remove_project":
        name = project_name or value
        if not name:
            return "Please provide 'project_name'."
        res = remove_project(name)
        if player:
            player.write_log(f"Profile: {res}")
        return res

    return "Unknown action. Choose from: 'view', 'summary', 'update', 'add_project', 'remove_project'."


def profile_action(parameters: dict, player=None, speak=None) -> str:
    action = parameters.get("action", "view")
    field = parameters.get("field")
    value = parameters.get("value")
    project_name = parameters.get("project_name")
    return handle_profile(
        action=action,
        field=field,
        value=value,
        project_name=project_name,
        player=player,
        speak=speak,
    )


TOOL = {
    "name": "manage_profile",
    "description": (
        "Manages the user's personalized profile (profile.json). Use to view current profile, "
        "update user role, add or remove active projects, or adjust custom instructions and preferences."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {
                "type": "STRING",
                "description": "Action: 'view', 'summary', 'update', 'add_project', or 'remove_project'.",
            },
            "field": {
                "type": "STRING",
                "description": "Field name to update (e.g. 'role', 'custom_instructions', 'organization').",
            },
            "value": {
                "type": "STRING",
                "description": "Value to assign to the field.",
            },
            "project_name": {
                "type": "STRING",
                "description": "Name of project to add or remove.",
            },
        },
        "required": ["action"],
    },
    "handler": profile_action,
}
