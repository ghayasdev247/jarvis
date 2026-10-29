"""
memory/profile_manager.py
Personalized User Profile Manager for JARVIS.

Inspired by Jarvis Institute feature specifications:
- Stores user profile in config/profile.json (role, current projects, tech stack, preferences, custom instructions).
- Cached in-memory with a 60-second TTL for zero-latency prompt construction.
- Formats profile context cleanly for injection into system instructions.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from threading import RLock
from typing import Any, Dict, List, Optional


def get_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent


BASE_DIR = get_base_dir()
CONFIG_DIR = BASE_DIR / "config"
PROFILE_PATH = CONFIG_DIR / "profile.json"

_lock = RLock()
_cache_profile: Optional[Dict[str, Any]] = None
_cache_timestamp: float = 0.0
CACHE_TTL_SECONDS: float = 60.0  # 60s cache as specified


def _default_profile() -> Dict[str, Any]:
    return {
        "user_name": "Hamad",
        "role": "Software Engineer & AI Builder",
        "organization": "",
        "current_projects": [
            "JARVIS Personal AI Assistant (Mark LV)",
            "System Automation and Developer Tooling",
        ],
        "tech_stack": [
            "Python",
            "TypeScript/JavaScript",
            "PowerShell/Bash",
            "Docker",
            "Git",
            "Gemini API",
        ],
        "preferences": {
            "response_style": "concise, direct, highly competent",
            "confirmation_for_destructive_actions": True,
            "show_code_diffs": True,
        },
        "custom_instructions": (
            "Prioritize fast action execution. Avoid unnecessary conversational fluff. "
            "Report status clearly and confirm when tasks finish."
        ),
    }


def load_profile(force_reload: bool = False) -> Dict[str, Any]:
    """Loads profile with 60-second memory caching."""
    global _cache_profile, _cache_timestamp
    now = time.monotonic()

    with _lock:
        if not force_reload and _cache_profile is not None and (now - _cache_timestamp) < CACHE_TTL_SECONDS:
            return dict(_cache_profile)

        if not PROFILE_PATH.exists():
            data = _default_profile()
            save_profile(data)
            _cache_profile = data
            _cache_timestamp = now
            return dict(data)

        try:
            raw = PROFILE_PATH.read_text(encoding="utf-8")
            data = json.loads(raw)
            if not isinstance(data, dict):
                data = _default_profile()
            _cache_profile = data
            _cache_timestamp = now
            return dict(data)
        except Exception as e:
            print(f"[Profile] Error loading profile: {e}")
            if _cache_profile is not None:
                return dict(_cache_profile)
            return _default_profile()


def save_profile(data: Dict[str, Any]) -> None:
    """Saves profile to disk and resets memory cache."""
    global _cache_profile, _cache_timestamp
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with _lock:
        try:
            PROFILE_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")
            _cache_profile = dict(data)
            _cache_timestamp = time.monotonic()
        except Exception as e:
            print(f"[Profile] Error saving profile: {e}")


def update_profile_field(key: str, value: Any) -> str:
    """Updates a specific field in the profile."""
    profile = load_profile(force_reload=True)
    profile[key] = value
    save_profile(profile)
    return f"Profile updated: '{key}' set."


def add_project(project_name: str) -> str:
    profile = load_profile(force_reload=True)
    projects: list = profile.get("current_projects", [])
    if project_name not in projects:
        projects.append(project_name)
        profile["current_projects"] = projects
        save_profile(profile)
        return f"Added '{project_name}' to current projects."
    return f"'{project_name}' is already in projects."


def remove_project(project_name: str) -> str:
    profile = load_profile(force_reload=True)
    projects: list = profile.get("current_projects", [])
    if project_name in projects:
        projects.remove(project_name)
        profile["current_projects"] = projects
        save_profile(profile)
        return f"Removed '{project_name}' from current projects."
    return f"'{project_name}' was not found in projects."


def format_profile_for_prompt() -> str:
    """Formats the profile for system prompt injection."""
    p = load_profile()
    lines = ["[PERSONALIZED USER PROFILE]"]
    if p.get("user_name"):
        lines.append(f"User Name: {p['user_name']}")
    if p.get("role"):
        lines.append(f"Role: {p['role']}")
    if p.get("organization"):
        lines.append(f"Organization: {p['organization']}")
    if p.get("current_projects"):
        lines.append(f"Active Projects: {', '.join(p['current_projects'])}")
    if p.get("tech_stack"):
        lines.append(f"Tech Stack: {', '.join(p['tech_stack'])}")
    if p.get("custom_instructions"):
        lines.append(f"Custom Instructions: {p['custom_instructions']}")
    lines.append("")
    return "\n".join(lines)
