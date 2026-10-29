"""
actions/hud_browser.py
Holographic Cyber Browser embedded directly in the central JARVIS HUD stage.
Allows browsing web pages, documentation, search results, and sites inside the HUD.
"""
from __future__ import annotations

from typing import Any
from urllib.parse import quote_plus


def hud_browser(
    parameters: dict = None,
    response=None,
    player=None,
    session_memory=None,
) -> str:
    params = parameters or {}
    action = (params.get("action") or "open").strip().lower()
    url = (params.get("url") or "").strip()
    query = (params.get("query") or "").strip()

    if action in ("close", "hide", "dismiss", "exit"):
        if player and hasattr(player, "close_hud_browser"):
            player.close_hud_browser()
            return "Closed the HUD cyber browser and restored the holographic HUD."
        return "HUD browser closed."

    target_url = url
    if not target_url and query:
        target_url = f"https://www.google.com/search?q={quote_plus(query)}"
    elif action == "search" and (query or url):
        q = query or url
        target_url = f"https://www.google.com/search?q={quote_plus(q)}"
    elif not target_url:
        target_url = "https://www.google.com"

    if player and hasattr(player, "show_hud_browser"):
        player.show_hud_browser(target_url, title=query or url)
        return f"Opened {target_url} directly inside the central JARVIS HUD display."
    elif player and hasattr(player, "write_log"):
        player.write_log(f"SYS: HUD browser opened for {target_url}")
        return f"Loaded {target_url} on HUD."

    return f"HUD browser loaded: {target_url}"


TOOL = {
    "name": "hud_browser",
    "description": (
        "Opens, searches, or closes the web browser embedded directly in the central JARVIS HUD interface. "
        "Use whenever the user asks to browse or search on HUD ('hud main browser kholo', 'show browser on hud', "
        "'hud me search karo', 'open site in hud', 'hud browser band karo'). "
        "Operates directly on the HUD stage without leaving the JARVIS interface."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {
                "type": "STRING",
                "description": "'open' to open a site or default browser, 'close' to close HUD browser, 'search' to search Google in HUD.",
                "enum": ["open", "close", "search"],
            },
            "url": {
                "type": "STRING",
                "description": "Web URL to open in HUD (e.g. 'youtube.com', 'google.com', 'wikipedia.org').",
            },
            "query": {
                "type": "STRING",
                "description": "Search query to search on Google inside the HUD browser.",
            },
        },
        "required": ["action"],
    },
    "handler": hud_browser,
}
