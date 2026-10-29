"""
actions/narrator_control.py
Voice Narrator and Urdu Speech Controller for JARVIS.

Enables fast voice narration of text and responses, with full native Urdu
and English neural speech support:
- Urdu Voices: ur-PK-AsadNeural (Male), ur-PK-UzmaNeural (Female), ur-IN-SalmanNeural
- English Voices: en-US-GuyNeural, en-US-AriaNeural, en-GB-RyanNeural
- Speed tuning for instant, low-latency spoken replies matching text speed.
"""

from __future__ import annotations

from typing import Optional
from core.narrator import narrator, is_urdu_text


def handle_narrator_control(
    action: str = "status",
    text: Optional[str] = None,
    language: Optional[str] = None,
    voice: Optional[str] = None,
    speed: Optional[str] = None,
    auto_narrate: Optional[bool] = None,
    player=None,
    speak=None,
) -> str:
    """Dispatches narrator controls and Urdu speech synthesis."""
    act = (action or "status").lower().strip()

    # ── 1. Narrate / Speak ────────────────────────────────────────────────────
    if act in ("narrate", "speak", "read"):
        if not text:
            return "Please provide the text to narrate aloud."

        lang = language or ("ur" if is_urdu_text(text) else "en")
        narrator.speak(text=text, voice=voice, language=lang, interrupt=True)

        lang_label = "Urdu" if lang.lower() in ("ur", "urdu", "pk") else "English"
        log_msg = f"[Narrator] Narrating in {lang_label} ({len(text)} chars)..."
        print(log_msg)
        if player:
            try:
                player.write_log(log_msg)
            except Exception:
                pass
        return f"Narrating in {lang_label}: \"{text[:100]}{'...' if len(text) > 100 else ''}\""

    # ── 2. Stop ───────────────────────────────────────────────────────────────
    if act in ("stop", "mute", "silence", "cancel"):
        narrator.stop()
        return "Voice narration stopped."

    # ── 3. Test Voice / Audio ─────────────────────────────────────────────────
    if act in ("test", "test_voice", "test_audio", "voice_test"):
        target_lang = language or "both"
        msg = narrator.test_voice(target_lang, wait=False)
        if player:
            try:
                player.write_log(f"[Narrator] {msg}")
            except Exception:
                pass
        return f"{msg} (Audio voice integration is active and playing)."

    # ── 4. Play Audio Asset from audio/ folder ────────────────────────────────
    if act in ("play_sound", "play_sfx", "sfx", "sound"):
        sound_name = text or voice or "access_granted"
        from core import sfx
        ok = sfx.play_sound(sound_name)
        if ok:
            return f"Playing audio asset: '{sound_name}' from project audio/ folder."
        else:
            avail = ", ".join(sfx.list_available_sounds())
            return f"Audio asset '{sound_name}' not found. Available sounds in audio/: {avail}"

    # ── 5. List Audio Assets ──────────────────────────────────────────────────
    if act in ("list_sounds", "sounds", "audio_assets"):
        from core import sfx
        sounds = sfx.list_available_sounds()
        return f"Integrated audio assets in project audio/ folder ({len(sounds)} files):\n• " + "\n• ".join(sounds)

    # ── 6. List Voices & Voice Packs ──────────────────────────────────────────
    if act in ("list_voices", "voices", "voice_packs", "urdu_voices"):
        from core.voice_assets import voice_manager
        summary = voice_manager.get_summary()
        u_list = "\n".join([f"  • {v}" for v in summary.get("urdu_voices_list", [])])
        return (
            f"=== Integrated Voice Assets in audio/ Folder ===\n"
            f"• Installed Voice Packs:\n"
            f"  1. Google Urdu (Pakistan) Pack ({summary.get('google_urdu_voices')} neural profiles):\n"
            f"{u_list}\n"
            f"  2. Gemini Global Voice Pack ({summary.get('gemini_voices')} languages)\n"
            f"  3. Azure Urdu Voices: ur-PK-AsadNeural (Male), ur-PK-UzmaNeural (Female)\n"
            f"• Audio SFX & Voice Assets: {summary.get('audio_wav_files')} WAV files in audio/"
        )

    # ── 7. Set Voice ──────────────────────────────────────────────────────────
    if act in ("voice", "set_voice"):
        if not voice:
            return "Please specify a voice name or alias (e.g. 'ur-pk-x-urm', 'asad', 'uzma', 'guy', 'ur-PK-AsadNeural')."
        
        from core.voice_assets import voice_manager
        resolved = voice_manager.resolve_voice_mapping(voice)
        target_v = resolved or voice

        v_lower = target_v.lower()
        if "asad" in v_lower or "pk_male" in v_lower or "urm" in v_lower:
            return narrator.set_urdu_voice("ur-PK-AsadNeural")
        elif "uzma" in v_lower or "pk_female" in v_lower or "cfn" in v_lower or "urf" in v_lower:
            return narrator.set_urdu_voice("ur-PK-UzmaNeural")
        elif "salman" in v_lower:
            return narrator.set_urdu_voice("ur-IN-SalmanNeural")
        elif "gul" in v_lower:
            return narrator.set_urdu_voice("ur-IN-GulNeural")
        elif "aria" in v_lower:
            return narrator.set_english_voice("en-US-AriaNeural")
        elif "guy" in v_lower:
            return narrator.set_english_voice("en-US-GuyNeural")
        elif "ur" in v_lower:
            return narrator.set_urdu_voice(target_v)
        else:
            return narrator.set_english_voice(target_v)

    # ── 8. Set Speed ──────────────────────────────────────────────────────────
    if act in ("speed", "set_speed", "rate"):
        if not speed:
            return "Please specify speed (e.g. '+10%', '+15%', '+0%')."
        return narrator.set_speed(speed)

    # ── 9. Auto-Narrate Toggle ────────────────────────────────────────────────
    if act in ("auto", "auto_narrate", "toggle_auto"):
        new_val = not narrator.config.get("auto_narrate", False) if auto_narrate is None else auto_narrate
        return narrator.set_auto_narrate(new_val)

    # ── 10. Status ────────────────────────────────────────────────────────────
    cfg = narrator.config
    from core.voice_assets import voice_manager
    v_summary = voice_manager.get_summary()
    return (
        f"=== Fast Voice Narrator & Audio Assets Status ===\n"
        f"• Status: {'ENABLED' if cfg.get('enabled') else 'DISABLED'}\n"
        f"• Auto-Narrate: {'ON' if cfg.get('auto_narrate') else 'OFF'}\n"
        f"• Urdu Voice: {cfg.get('default_urdu_voice')} (Pakistan Neural / Asad)\n"
        f"• English Voice: {cfg.get('default_english_voice')} (Natural Guy)\n"
        f"• Speed: {cfg.get('speed')} (Fast conversational delivery)\n"
        f"• Integrated Voice Packs: Google Urdu (Pakistan) [{v_summary.get('google_urdu_voices')} profiles], Gemini [{v_summary.get('gemini_voices')} profiles]\n"
        f"• Audio Files in audio/: {v_summary.get('audio_wav_files')} assets active"
    )


def narrator_control_action(parameters: dict, player=None, speak=None) -> str:
    params = parameters or {}
    return handle_narrator_control(
        action=params.get("action", "status"),
        text=params.get("text"),
        language=params.get("language"),
        voice=params.get("voice"),
        speed=params.get("speed"),
        auto_narrate=params.get("auto_narrate"),
        player=player,
        speak=speak,
    )


TOOL = {
    "name": "narrator_control",
    "description": (
        "Controls real-time Voice Narrator and Urdu/English neural speech synthesis. "
        "Allows speaking text aloud in natural Urdu or English, stopping speech, changing speed or voices, "
        "and checking audio status."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {
                "type": "STRING",
                "description": "Action to perform: 'narrate' (speak text), 'stop' (stop speaking), 'test' (test audio), 'status' (get narrator status), 'speed' (set speed e.g. '+15%'), 'voice' (set voice), 'auto_narrate' (toggle auto narration)",
                "enum": ["narrate", "stop", "test", "status", "speed", "voice", "auto_narrate"],
            },
            "text": {
                "type": "STRING",
                "description": "Text to speak or narrate aloud (Urdu or English).",
            },
            "language": {
                "type": "STRING",
                "description": "Language code: 'ur' for Urdu, 'en' for English, or 'auto'.",
            },
            "voice": {
                "type": "STRING",
                "description": "Voice name e.g. 'ur-PK-AsadNeural', 'ur-PK-UzmaNeural', 'en-US-GuyNeural'.",
            },
            "speed": {
                "type": "STRING",
                "description": "Playback rate e.g. '+10%', '+20%', '0%'.",
            },
            "auto_narrate": {
                "type": "BOOLEAN",
                "description": "Whether to automatically narrate responses.",
            },
        },
        "required": ["action"],
    },
    "handler": narrator_control_action,
}


