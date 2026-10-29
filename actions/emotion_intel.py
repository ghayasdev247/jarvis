"""
actions/emotion_intel.py
Emotional Intelligence and Mood Behavioral Controller for JARVIS.

Allows JARVIS to:
- Detect user emotional states (Frustrated, Stressed, Fatigued, Excited, Focused, Neutral).
- Adapt communication tone, pacing, empathy, and initiative to match user mood.
- Report current emotional telemetry and log emotional shifts over time.
"""

from __future__ import annotations

from typing import Optional
from core.emotion_engine import emotion_engine


def handle_emotion_intel(
    action: str = "status",
    message_text: Optional[str] = None,
    mood_override: Optional[str] = None,
    player=None,
    speak=None,
) -> str:
    """Manages emotional intelligence and mood adaptation."""
    act = (action or "status").lower().strip()

    if act in ("analyze", "detect"):
        if not message_text:
            return "Please provide user message text to analyze emotional tone."
        state = emotion_engine.analyze_text(message_text)
        return (
            f"Detected Mood: {state.mood} (Confidence: {int(state.intensity * 100)}%)\n"
            f"Triggers: {', '.join(state.triggers) if state.triggers else 'Subtle conversational cues'}\n"
            f"Directive: {state.behavioral_directive}"
        )

    if act in ("set", "override"):
        if not mood_override:
            return "Please specify the target mood (e.g. 'STRESSED', 'TIRED', 'EXCITED', 'FOCUSED', 'CALM')."
        state = emotion_engine.set_override(mood_override)
        msg = f"Understood, sir. Emotional behavioral stance set to {state.mood}. Directive: {state.behavioral_directive}"
        if speak:
            speak(f"Understood, sir. Adapting my demeanor to {state.mood.lower()}.")
        return msg

    # Default: status
    state = emotion_engine.get_current_mood()
    return (
        f"=== Emotional Intelligence Telemetry ===\n"
        f"Current Mood: {state.mood} (Intensity: {int(state.intensity * 100)}%)\n"
        f"Active Directive: {state.behavioral_directive}\n"
        f"Last Detected: {state.detected_at}"
    )


def emotion_intel_action(parameters: dict, player=None, speak=None) -> str:
    params = parameters or {}
    return handle_emotion_intel(
        action=params.get("action", "status"),
        message_text=params.get("message_text"),
        mood_override=params.get("mood_override"),
        player=player,
        speak=speak,
    )


TOOL = {
    "name": "emotion_intel",
    "description": (
        "Perceives and adapts to user emotions and moods: analyze conversational sentiment, detect emotional "
        "states (Stressed, Frustrated, Tired, Excited, Focused, Calm), and view or update behavioral guidelines "
        "so JARVIS responds with appropriate empathy, soothing tone, or high-speed precision."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {
                "type": "STRING",
                "description": "Action: 'status' (view current emotional telemetry), 'analyze' (detect mood from text), 'set' (manually override mood).",
            },
            "message_text": {
                "type": "STRING",
                "description": "User speech or message text to analyze for sentiment/mood.",
            },
            "mood_override": {
                "type": "STRING",
                "description": "Mood state to set: 'STRESSED', 'FRUSTRATED', 'FATIGUED', 'EXCITED', 'FOCUSED', 'NEUTRAL'.",
            },
        },
        "required": ["action"],
    },
    "handler": emotion_intel_action,
}
