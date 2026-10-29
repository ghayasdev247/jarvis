"""
actions/accessibility_control.py
WCAG 2.2 AAA Accessibility and NVDA Screen Reader Controller for J.A.R.V.I.S.

Provides actions for blind and visually impaired users:
- Toggle or query Accessibility Mode (WCAG AAA High Contrast theme)
- Test or query NVDA screen reader integration and Braille output
- Read screen status, prompt state, or re-read last JARVIS response
"""
from __future__ import annotations

from typing import Optional
from core.accessibility import accessibility_manager


def handle_accessibility_control(
    action: str = "status",
    message: Optional[str] = None,
    player=None,
    speak=None,
) -> str:
    act = (action or "status").lower().strip()

    if act in ("toggle", "switch"):
        main_win = getattr(player, "_win", None) if player else None
        new_state = accessibility_manager.toggle(main_win)
        state_str = "ENABLED (WCAG 2.2 AAA Ultra-High Contrast + NVDA)" if new_state else "DISABLED (Standard Mode)"
        return f"Accessibility mode has been {state_str}."

    if act in ("on", "enable", "activate"):
        main_win = getattr(player, "_win", None) if player else None
        if not accessibility_manager.is_active:
            accessibility_manager.activate_aaa_mode(main_win)
        return "Accessibility mode Level Triple A is now ACTIVE with NVDA screen reader integration."

    if act in ("off", "disable", "deactivate"):
        main_win = getattr(player, "_win", None) if player else None
        if accessibility_manager.is_active:
            accessibility_manager.deactivate_aaa_mode(main_win)
        return "Accessibility mode is now DEACTIVATED. Standard visual theme restored."

    if act in ("read_screen", "screen_status", "describe_screen"):
        main_win = getattr(player, "_win", None) if player else None
        accessibility_manager.read_screen_status(main_win)
        return "Screen and system status has been read aloud to screen reader."

    if act in ("read_last", "repeat_response", "read_response"):
        accessibility_manager.read_last_response()
        return "Latest response read aloud."

    if act in ("announce", "speak", "nvda"):
        if not message:
            return "Please provide a message to announce to screen reader."
        accessibility_manager.announce(message, interrupt=True)
        return f"Announced to screen reader: {message}"

    # Default: status
    nvda_on = accessibility_manager.is_nvda_active()
    active = accessibility_manager.is_active
    return (
        f"=== J.A.R.V.I.S. WCAG 2.2 AAA Accessibility Status ===\n"
        f"• Mode: {'ACTIVE (WCAG AAA)' if active else 'OFF (Standard Theme)'}\n"
        f"• NVDA Screen Reader: {'DETECTED & RUNNING' if nvda_on else 'OFFLINE / STANDBY'}\n"
        f"• Tactile Braille Output: {'SUPPORTED' if nvda_on else 'STANDBY'}\n"
        f"• Keyboard Shortcuts:\n"
        f"   - Ctrl+F2: Toggle Accessibility Mode\n"
        f"   - Ctrl+L: Focus Command Prompt Input\n"
        f"   - Ctrl+R: Read Latest JARVIS Response\n"
        f"   - Ctrl+H: Read Screen & System Status Aloud\n"
        f"   - Escape: Interrupt Speech & Dismiss Dialogs\n"
    )


def accessibility_control_action(parameters: dict, player=None, speak=None) -> str:
    params = parameters or {}
    return handle_accessibility_control(
        action=params.get("action", "status"),
        message=params.get("message"),
        player=player,
        speak=speak,
    )


TOOL = {
    "name": "accessibility_control",
    "description": (
        "Controls WCAG 2.2 AAA Accessibility Mode and NVDA Screen Reader integration for blind or visually impaired users. "
        "Allows toggling high-contrast mode, checking NVDA status, announcing messages to screen readers, "
        "or reading screen and prompt state aloud."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {
                "type": "STRING",
                "description": "Action: 'status' (report status), 'toggle' (toggle AAA mode), 'on' (enable), 'off' (disable), 'read_screen' (read current UI state), 'read_last' (repeat last response), 'announce' (announce message)",
                "enum": ["status", "toggle", "on", "off", "read_screen", "read_last", "announce"],
            },
            "message": {
                "type": "STRING",
                "description": "Custom message text to announce aloud via screen reader when action is 'announce'.",
            },
        },
        "required": ["action"],
    },
    "handler": accessibility_control_action,
}
