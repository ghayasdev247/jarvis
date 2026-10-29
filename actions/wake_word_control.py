"""
actions/wake_word_control.py — Tool for JARVIS to download, install, and manage Wake Word ('Hey Jarvis').
"""
from __future__ import annotations

from core.wake_word import is_installed, is_ready, install_and_download
from memory.config_manager import get_wake_word_enabled, save_wake_word_enabled


def wake_word_control(
    parameters: dict = None,
    action: str = "download",
    player=None,
    speak=None,
    **kwargs
) -> str:
    """Download, install, enable, disable, or inspect the local offline wake word detector."""
    params = parameters or {}
    act = (params.get("action") or action or "download").strip().lower()

    if act in ("download", "install", "setup", "download_models"):
        if is_ready():
            return "Wake word models ('Hey Jarvis') are already downloaded and fully ready on disk."

        msg = "Initiating wake word installation and model download..."
        if player and hasattr(player, "write_log"):
            player.write_log(f"[WakeWord] {msg}")

        ok, result_msg = install_and_download(
            logger=print,
            notify=lambda m: player.write_log(f"[WakeWord] {m}") if player and hasattr(player, "write_log") else None
        )

        if ok:
            save_wake_word_enabled(True)
            return f"Success: {result_msg} Wake word ('Hey Jarvis') is now active."
        else:
            return f"Wake word setup alert: {result_msg}"

    elif act in ("enable", "turn_on", "activate"):
        if not is_ready():
            # Automatically download if missing
            ok, result_msg = install_and_download()
            if not ok:
                return f"Cannot enable wake word: {result_msg}"
        save_wake_word_enabled(True)
        return "Wake word enabled. JARVIS will now respond to 'Hey Jarvis'."

    elif act in ("disable", "turn_off", "deactivate"):
        save_wake_word_enabled(False)
        return "Wake word disabled. JARVIS is in always-listening mode."

    elif act in ("status", "check"):
        installed = is_installed()
        ready = is_ready()
        enabled = get_wake_word_enabled()
        return (
            f"Wake Word Status:\n"
            f"• Installed: {installed}\n"
            f"• Models Ready: {ready}\n"
            f"• Enabled: {enabled}\n"
            f"Target wake phrase: 'Hey Jarvis'"
        )

    return f"Unknown wake word action '{act}'. Supported actions: 'download', 'enable', 'disable', 'status'."


TOOL = {
    "name": "wake_word_control",
    "description": (
        "Controls the local offline Wake Word ('Hey Jarvis') detector. "
        "Use this tool whenever the user asks to download wake word, install wake word, "
        "download models, enable wake word, disable wake word, or check wake word status. "
        "DO NOT use dev_agent or code compilers to download wake word — use this tool directly."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {
                "type": "STRING",
                "description": "Action to perform: 'download' (installs package and downloads ONNX models), 'enable', 'disable', or 'status'.",
                "enum": ["download", "enable", "disable", "status"]
            }
        },
        "required": ["action"]
    },
    "handler": wake_word_control,
}
