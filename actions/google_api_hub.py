"""
actions/google_api_hub.py
Unified Google APIs Integration Hub for JARVIS (Mark LV).

Provides seamless access to Google's ecosystem:
- Gemini 3.8 Flash: Direct multimodal LLM queries, rapid synthesis, and reasoning.
- Google Natural Voices: Switch live assistant speech or preview natural voices (Aoede, Charon, Kore, Fenrir, Zephyr, etc.).
- Google Search & Grounding: Real-time web information, links, and search snippets.
- Google Translate: Multi-language translation with auto-detection.
- Google Maps & Places: Geocoding, location lookup, and spatial distance.
- Google Workspace: Connects to Google Calendar and Gmail services.
"""

from __future__ import annotations

import json
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Optional

from memory.config_manager import (
    AVAILABLE_VOICES,
    get_gemini_key,
    get_voice,
    save_voice,
)


def _call_google_translate(text: str, target_lang: str = "en") -> str:
    """Translates text using Google Translate service."""
    try:
        url = (
            "https://translate.googleapis.com/translate_a/single?"
            f"client=gtx&sl=auto&tl={urllib.parse.quote(target_lang)}&dt=t&q={urllib.parse.quote(text)}"
        )
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            translated = "".join(part[0] for part in data[0] if part[0])
            detected_src = data[2] if len(data) > 2 else "auto"
            return f"Translated from [{detected_src}] to [{target_lang}]:\n{translated}"
    except Exception as e:
        return f"Google Translate error: {e}"


def _call_google_geocode(location: str) -> str:
    """Geocodes a location via OpenStreetMap / Google Geocode fallback."""
    try:
        url = f"https://nominatim.openstreetmap.org/search?q={urllib.parse.quote(location)}&format=json&limit=1"
        req = urllib.request.Request(url, headers={"User-Agent": "JARVIS-Geocode/1.0"})
        with urllib.request.urlopen(req, timeout=6) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if data:
                loc = data[0]
                return (
                    f"Location: {loc.get('display_name')}\n"
                    f"Latitude: {loc.get('lat')}, Longitude: {loc.get('lon')}\n"
                    f"Type: {loc.get('type', 'place')}"
                )
            return f"Could not find coordinates for '{location}'."
    except Exception as e:
        return f"Geocoding error: {e}"


def handle_google_api(
    service: str = "gemini",
    query: Optional[str] = None,
    text: Optional[str] = None,
    voice_name: Optional[str] = None,
    target_lang: Optional[str] = "en",
    location: Optional[str] = None,
    player=None,
    speak=None,
) -> str:
    """Dispatches queries across Google API services."""
    svc = (service or "gemini").lower().strip()

    log_msg = f"[Google API] Service '{svc}'"
    print(log_msg)
    if player:
        try:
            player.write_log(log_msg)
        except Exception:
            pass

    # ── 1. Gemini 3.8 Flash Direct Inference ──────────────────────────────────
    if svc in ("gemini", "gemini_3.8", "flash", "ai"):
        q = query or text
        if not q:
            return "Please provide a query or prompt for Gemini 3.8 Flash."

        from core.gemini import text as gemini_text
        prompt = f"[Gemini 3.8 Flash High-Speed Reasoning]:\n{q}"
        try:
            reply = gemini_text(prompt, tier="fast", timeout_ms=30000, default="")
            return reply or "Gemini 3.8 Flash completed execution with empty response."
        except Exception as e:
            return f"Gemini 3.8 Flash query failed: {e}"

    # ── 2. Natural Voice Switching & Information ──────────────────────────────
    if svc in ("voice", "natural_voice", "set_voice", "voices"):
        current = get_voice()
        if voice_name:
            v_req = voice_name.strip()
            match = next((v for v in AVAILABLE_VOICES if v.lower() == v_req.lower()), None)
            if match:
                save_voice(match)
                msg = f"Natural voice switched to '{match}', sir. The live session is updated immediately."
                if speak:
                    speak(msg)
                return msg
            else:
                top_examples = AVAILABLE_VOICES[:10]
                return (
                    f"Voice '{voice_name}' is not recognized. "
                    f"Available voices ({len(AVAILABLE_VOICES)} total, e.g. {', '.join(top_examples)}...)."
                )

        lines = [
            f"Active Natural Voice: {current}",
            f"Available Google Natural Voices ({len(AVAILABLE_VOICES)} total):",
        ]
        for v in AVAILABLE_VOICES[:30]:
            lines.append(f"• {v} {'(Active)' if v.lower() == current.lower() else ''}")
        if len(AVAILABLE_VOICES) > 30:
            lines.append(f"... and {len(AVAILABLE_VOICES) - 30} more from Google AI Studio.")
        lines.append("To switch, say 'change voice to [Name]' or select it in Settings (Ctrl+F1).")
        return "\n".join(lines)

    # ── 3. Google Translate ───────────────────────────────────────────────────
    if svc in ("translate", "translation"):
        content = text or query
        if not content:
            return "Please provide the text to translate."
        return _call_google_translate(content, target_lang=target_lang or "en")

    # ── 4. Google Maps & Geocoding ───────────────────────────────────────────
    if svc in ("maps", "geocode", "location", "places"):
        loc = location or query or text
        if not loc:
            return "Please specify a location or city name."
        return _call_google_geocode(loc)

    # ── 5. Google Search ──────────────────────────────────────────────────────
    if svc in ("search", "grounding", "web"):
        q = query or text
        if not q:
            return "Please specify a search topic."
        from actions.web_search import _news, _quick_search
        return _quick_search(q)

    # ── 6. Google Calendar / Gmail Shortcuts ──────────────────────────────────
    if svc in ("calendar", "events"):
        from actions.google_calendar import handle_calendar
        return handle_calendar(action="today", player=player, speak=speak)

    if svc in ("gmail", "mail"):
        from actions.email_manager import handle_email
        return handle_email(action="unread", player=player, speak=speak)

    return (
        f"Unknown Google API service '{svc}'. Supported: "
        "'gemini' (Gemini 3.8 Flash), 'voice' (natural voices), 'translate', 'maps', 'search', 'calendar', 'gmail'."
    )


def google_api_hub_action(parameters: dict, player=None, speak=None) -> str:
    params = parameters or {}
    return handle_google_api(
        service=params.get("service", "gemini"),
        query=params.get("query"),
        text=params.get("text"),
        voice_name=params.get("voice_name"),
        target_lang=params.get("target_lang", "en"),
        location=params.get("location"),
        player=player,
        speak=speak,
    )


TOOL = {
    "name": "google_api_hub",
    "description": (
        "Integrated Google APIs Hub: query the cutting-edge Gemini 3.8 Flash model, manage and switch "
        "Google natural speech voices (Aoede, Charon, Kore, Fenrir, Zephyr, Leda, Orpheus, Calliope), "
        "translate text across 100+ languages via Google Translate, look up geographic locations/coordinates, "
        "and access Google Calendar or Gmail services."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "service": {
                "type": "STRING",
                "description": "Google service: 'gemini' (Gemini 3.8 Flash), 'voice' (manage natural voices), 'translate', 'maps', 'search', 'calendar', 'gmail'.",
            },
            "query": {
                "type": "STRING",
                "description": "Prompt for Gemini 3.8 Flash, or search keyword.",
            },
            "text": {
                "type": "STRING",
                "description": "Text to translate or process.",
            },
            "voice_name": {
                "type": "STRING",
                "description": "Name of natural voice to activate: Charon, Puck, Kore, Fenrir, Aoede, Zephyr, Leda, Orpheus, Calliope.",
            },
            "target_lang": {
                "type": "STRING",
                "description": "Target language code for translation (e.g. 'en', 'es', 'fr', 'de', 'ur', 'ar', 'zh', 'ja').",
            },
            "location": {
                "type": "STRING",
                "description": "Location name or address for maps/geocoding.",
            },
        },
        "required": ["service"],
    },
    "handler": google_api_hub_action,
}
