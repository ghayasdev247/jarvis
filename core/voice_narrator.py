"""
core/voice_narrator.py
Compatibility alias forwarding to core.narrator.
"""
from core.narrator import narrator, VoiceNarrator, is_urdu_text

__all__ = ["narrator", "VoiceNarrator", "is_urdu_text"]
