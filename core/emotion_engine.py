"""
core/emotion_engine.py
Emotional Intelligence and Mood Perception Engine for JARVIS.

Detects user mood (Stressed, Frustrated, Tired, Excited, Focused, Neutral),
tracks emotional sentiment, and provides real-time behavioral guidance so
JARVIS responds with appropriate empathy, tone, warmth, and pacing.
"""

from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

_EMOTION_STORE_PATH = Path(__file__).resolve().parent.parent / "memory" / "emotion_history.json"


@dataclass
class MoodState:
    mood: str = "NEUTRAL"
    intensity: float = 0.5  # 0.0 to 1.0
    detected_at: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    triggers: List[str] = field(default_factory=list)
    behavioral_directive: str = "Maintain professional, respectful, and steady composure."


class EmotionEngine:
    """Manages affective computing, sentiment classification, and behavioral adaptation."""

    MOOD_DIRECTIVES = {
        "STRESSED": (
            "The user is feeling stressed or overwhelmed. Maintain a calm, grounding, reassuring presence. "
            "Keep sentences clear, eliminate unnecessary questions, and handle micro-steps autonomously to reduce cognitive load."
        ),
        "FRUSTRATED": (
            "The user is frustrated, irritated, or stuck. Display utmost patience, acknowledge the friction with zero defensiveness, "
            "avoid cheerfulness or excuses, and deliver direct, immediate solutions."
        ),
        "FATIGUED": (
            "The user is tired, exhausted, or working late. Speak gently and concisely. Keep answers brief and offer to handle "
            "tasks or queue them for tomorrow."
        ),
        "EXCITED": (
            "The user is energized, pleased, or celebrating success. Match their momentum with warm, genuine enthusiasm, "
            "compliment accomplishments tastefully, and keep energy high."
        ),
        "FOCUSED": (
            "The user is in deep work / flow state. Deliver ultra-sharp, concise, data-driven outputs with zero conversational fluff."
        ),
        "SAD": (
            "The user is feeling down or disappointed. Be warm, supportive, and understanding. Offer quiet encouragement."
        ),
        "NEUTRAL": (
            "The user is composed and standard. Maintain natural British poise, sharp intelligence, and dry wit."
        ),
    }

    _current_mood = MoodState()

    @classmethod
    def _load_history(cls) -> List[dict]:
        if _EMOTION_STORE_PATH.exists():
            try:
                with open(_EMOTION_STORE_PATH, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return []

    @classmethod
    def _save_history(cls, entry: dict) -> None:
        _EMOTION_STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
        hist = cls._load_history()
        hist.append(entry)
        if len(hist) > 100:
            hist = hist[-100:]
        with open(_EMOTION_STORE_PATH, "w", encoding="utf-8") as f:
            json.dump(hist, f, indent=2, ensure_ascii=False)

    @classmethod
    def analyze_text(cls, text: str) -> MoodState:
        """Analyzes text for emotional markers, sentiment, and tone cues."""
        s = text.lower()
        matched_mood = "NEUTRAL"
        intensity = 0.5
        triggers = []

        # 1. Frustration / Irritation
        frust_cues = ["hate this", "damn", "annoying", "broken again", "why won't", "stupid", "ugh", "not working", "fails", "nonsense"]
        if any(c in s for c in frust_cues) or "!" in text and ("again" in s or "stop" in s):
            matched_mood = "FRUSTRATED"
            intensity = 0.85
            triggers = [c for c in frust_cues if c in s]

        # 2. Stress / Overwhelm
        stress_cues = ["stressed", "overwhelmed", "urgent", "emergency", "too much work", "panicking", "hurry", "asap", "deadline", "cannot handle"]
        if any(c in s for c in stress_cues):
            matched_mood = "STRESSED"
            intensity = 0.9
            triggers = [c for c in stress_cues if c in s]

        # 3. Fatigue / Exhaustion
        fatigue_cues = ["tired", "exhausted", "sleepy", "drained", "late night", "need sleep", "headache", "brain dead", "gonna pass out"]
        if any(c in s for c in fatigue_cues):
            matched_mood = "FATIGUED"
            intensity = 0.8
            triggers = [c for c in fatigue_cues if c in s]

        # 4. Excitement / Joy
        joy_cues = ["awesome", "brilliant", "great job", "love it", "amazing", "finally worked", "hell yeah", "let's go", "hurray", "wonderful", "perfect"]
        if any(c in s for c in joy_cues) or "!!!" in text:
            matched_mood = "EXCITED"
            intensity = 0.85
            triggers = [c for c in joy_cues if c in s]

        # 5. Deep Focus
        focus_cues = ["fast", "only give me code", "no explanation", "strictly", "benchmark", "profile this", "optimize"]
        if any(c in s for c in focus_cues) and len(s) < 80:
            matched_mood = "FOCUSED"
            intensity = 0.75
            triggers = [c for c in focus_cues if c in s]

        directive = cls.MOOD_DIRECTIVES.get(matched_mood, cls.MOOD_DIRECTIVES["NEUTRAL"])
        cls._current_mood = MoodState(
            mood=matched_mood,
            intensity=intensity,
            detected_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            triggers=triggers,
            behavioral_directive=directive,
        )

        cls._save_history({
            "mood": matched_mood,
            "intensity": intensity,
            "detected_at": cls._current_mood.detected_at,
            "triggers": triggers,
            "sample": text[:120],
        })

        return cls._current_mood

    @classmethod
    def get_current_mood(cls) -> MoodState:
        return cls._current_mood

    @classmethod
    def set_override(cls, mood_name: str, reason: str = "user specified") -> MoodState:
        m_upper = mood_name.upper().strip()
        if m_upper in cls.MOOD_DIRECTIVES:
            cls._current_mood = MoodState(
                mood=m_upper,
                intensity=1.0,
                detected_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                triggers=[reason],
                behavioral_directive=cls.MOOD_DIRECTIVES[m_upper],
            )
            return cls._current_mood
        return cls._current_mood


emotion_engine = EmotionEngine()
