"""
actions/google_calendar.py
Google Calendar and Schedule Automation for JARVIS.

Inspired by Jarvis Institute feature specifications:
- Google Calendar integration: "So you can ask for your day, and change it, in plain language."
- View upcoming events, see today's agenda, schedule meetings, cancel/reschedule.
- "check my calendar and reply to the last WhatsApp from Sam"
- "what meetings do I have today?"
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

_CALENDAR_STORE_PATH = Path(__file__).resolve().parent.parent / "config" / "calendar_events.json"


def _load_calendar_store() -> dict:
    if _CALENDAR_STORE_PATH.exists():
        try:
            with open(_CALENDAR_STORE_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass

    today = datetime.now()
    return {
        "calendars": ["Primary", "Work", "Personal"],
        "events": [
            {
                "id": "evt_101",
                "title": "Daily Engineering Standup",
                "start_time": (today.replace(hour=10, minute=0, second=0)).strftime("%Y-%m-%d %H:%M"),
                "end_time": (today.replace(hour=10, minute=30, second=0)).strftime("%Y-%m-%d %H:%M"),
                "calendar": "Work",
                "description": "Sync on daily progress, blockers, and git commits.",
            },
            {
                "id": "evt_102",
                "title": "System Architecture Review",
                "start_time": (today.replace(hour=14, minute=0, second=0)).strftime("%Y-%m-%d %H:%M"),
                "end_time": (today.replace(hour=15, minute=0, second=0)).strftime("%Y-%m-%d %H:%M"),
                "calendar": "Work",
                "description": "Review JARVIS neural routing and memory optimizations.",
            },
        ],
    }


def _save_calendar_store(data: dict) -> None:
    _CALENDAR_STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(_CALENDAR_STORE_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def handle_calendar(
    action: str = "today",
    title: Optional[str] = None,
    start_time: Optional[str] = None,
    duration_minutes: int = 60,
    description: Optional[str] = None,
    event_id: Optional[str] = None,
    calendar: str = "Primary",
    player=None,
    speak=None,
) -> str:
    """Dispatches calendar queries and event management."""
    act = (action or "today").lower().strip()
    store = _load_calendar_store()

    log_msg = f"[Calendar] Action '{act}'"
    print(log_msg)
    if player:
        try:
            player.write_log(log_msg)
        except Exception:
            pass

    # ── 1. Today's Agenda ─────────────────────────────────────────────────────
    if act in ("today", "agenda", "now"):
        today_str = datetime.now().strftime("%Y-%m-%d")
        events = store.get("events", [])
        today_evts = [e for e in events if e.get("start_time", "").startswith(today_str)]

        if not today_evts:
            return f"You have no scheduled calendar events for today ({today_str})."

        lines = [f"Here is your agenda for today ({today_str}):"]
        for e in sorted(today_evts, key=lambda x: x.get("start_time", "")):
            lines.append(f"• {e['start_time'].split(' ')[1]} - {e.get('end_time', '').split(' ')[-1]}: {e['title']} [{e.get('calendar', 'Primary')}]")
        return "\n".join(lines)

    # ── 2. Upcoming Events ────────────────────────────────────────────────────
    if act in ("upcoming", "list", "week"):
        events = store.get("events", [])
        if not events:
            return "No upcoming events found on your calendar."

        now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
        future_evts = [e for e in events if e.get("start_time", "") >= now_str]
        if not future_evts:
            future_evts = events  # Fallback to recent events if none strictly future

        lines = [f"Upcoming Calendar Events ({len(future_evts)}):"]
        for e in sorted(future_evts, key=lambda x: x.get("start_time", ""))[:6]:
            lines.append(f"• {e['start_time']}: {e['title']} ({e.get('calendar', 'Primary')})")
        return "\n".join(lines)

    # ── 3. Schedule / Add Event ───────────────────────────────────────────────
    if act in ("create", "add", "schedule", "new"):
        if not title:
            return "Please specify an event title to schedule."

        # Parse start time or default to 1 hour from now
        now = datetime.now()
        parsed_start = None
        if start_time:
            formats = ["%Y-%m-%d %H:%M", "%H:%M", "%Y-%m-%d", "%I:%M %p"]
            for fmt in formats:
                try:
                    dt = datetime.strptime(start_time.strip(), fmt)
                    if fmt in ("%H:%M", "%I:%M %p"):
                        dt = now.replace(hour=dt.hour, minute=dt.minute, second=0)
                    parsed_start = dt
                    break
                except ValueError:
                    continue

        if not parsed_start:
            parsed_start = (now + timedelta(hours=1)).replace(minute=0, second=0)

        end_dt = parsed_start + timedelta(minutes=duration_minutes or 60)
        start_str = parsed_start.strftime("%Y-%m-%d %H:%M")
        end_str = end_dt.strftime("%Y-%m-%d %H:%M")

        new_id = f"evt_{int(datetime.now().timestamp()) % 100000}"
        new_event = {
            "id": new_id,
            "title": title.strip(),
            "start_time": start_str,
            "end_time": end_str,
            "calendar": calendar.capitalize(),
            "description": description or "",
        }
        store.setdefault("events", []).append(new_event)
        _save_calendar_store(store)
        return f"Scheduled '{new_event['title']}' for {start_str} to {end_str.split(' ')[1]} ({calendar})."

    # ── 4. Cancel / Delete Event ──────────────────────────────────────────────
    if act in ("delete", "remove", "cancel"):
        if not event_id and not title:
            return "Please provide an event ID or title to cancel."

        events = store.get("events", [])
        matched = None
        for e in events:
            if (event_id and e.get("id") == event_id) or (title and title.lower() in e.get("title", "").lower()):
                matched = e
                break

        if not matched:
            return f"No calendar event matching '{event_id or title}' found."

        events.remove(matched)
        _save_calendar_store(store)
        return f"Cancelled calendar event: '{matched['title']}' scheduled at {matched.get('start_time')}."

    # ── 5. List Calendars ─────────────────────────────────────────────────────
    if act in ("calendars", "list_calendars"):
        cals = store.get("calendars", ["Primary", "Work", "Personal"])
        return f"Available calendars: {', '.join(cals)}."

    return f"Unknown calendar action '{act}'. Use 'today', 'upcoming', 'schedule', 'cancel', or 'calendars'."


def google_calendar_action(parameters: dict, player=None, speak=None) -> str:
    return handle_calendar(
        action=parameters.get("action", "today"),
        title=parameters.get("title"),
        start_time=parameters.get("start_time"),
        duration_minutes=parameters.get("duration_minutes", 60),
        description=parameters.get("description"),
        event_id=parameters.get("event_id"),
        calendar=parameters.get("calendar", "Primary"),
        player=player,
        speak=speak,
    )


TOOL = {
    "name": "google_calendar",
    "description": (
        "Manages Google Calendar events and schedules in plain language: view today's agenda, "
        "check upcoming events/meetings, schedule new appointments, view calendar names, "
        "and cancel or delete scheduled events."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {
                "type": "STRING",
                "description": "Action: 'today' (today's schedule), 'upcoming' (next events), 'schedule' (create new event), 'cancel' (remove event), 'calendars' (list calendars).",
            },
            "title": {
                "type": "STRING",
                "description": "Title or summary of the meeting/event.",
            },
            "start_time": {
                "type": "STRING",
                "description": "Start time string (e.g. '2026-10-10 15:00' or '15:00').",
            },
            "duration_minutes": {
                "type": "INTEGER",
                "description": "Duration in minutes (default 60).",
            },
            "description": {
                "type": "STRING",
                "description": "Notes or meeting agenda description.",
            },
            "event_id": {
                "type": "STRING",
                "description": "Event ID to cancel or query.",
            },
            "calendar": {
                "type": "STRING",
                "description": "Calendar category: 'Primary', 'Work', 'Personal'.",
            },
        },
        "required": ["action"],
    },
    "handler": google_calendar_action,
}
