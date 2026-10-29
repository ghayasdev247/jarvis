"""
core/narrator.py
High-Performance Real-Time Voice Narrator for JARVIS.

Provides fast, low-latency natural voice narration matching rapid text responses.
Supports bilingual English and Urdu language & voice synthesis via Azure Neural TTS:
- Urdu Pakistan: ur-PK-AsadNeural (Male), ur-PK-UzmaNeural (Female)
- Urdu India: ur-IN-SalmanNeural (Male), ur-IN-GulNeural (Female)
- English Natural: en-US-GuyNeural, en-US-AriaNeural, en-GB-RyanNeural
"""

from __future__ import annotations

import asyncio
import json
import os
import queue
import re
import tempfile
import threading
import time
from pathlib import Path
from typing import Optional

_CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "narrator_config.json"

_URDU_RANGE_RE = re.compile(r"[\u0600-\u06FF\u0750-\u077F\uFB50-\uFDFF\uFE70-\uFEFF]")
_ROMAN_URDU_WORDS = {
    "aap", "kaise", "kya", "hai", "hain", "shukriya", "theek", "hum", "mujhe",
    "batao", "karo", "nahin", "nahi", "bohot", "acha", "achi", "kaam", "mera",
    "meri", "apka", "apki", "karen", "salam", "assalam", "walaikum", "khuda", "hafiz"
}

_VOICE_MAP = {
    "urdu_male": "ur-PK-AsadNeural",
    "urdu_female": "ur-PK-UzmaNeural",
    "urdu_in_male": "ur-IN-SalmanNeural",
    "urdu_in_female": "ur-IN-GulNeural",
    "english_male": "en-US-GuyNeural",
    "english_female": "en-US-AriaNeural",
    "british_male": "en-GB-RyanNeural",
}


def _load_config() -> dict:
    if _CONFIG_PATH.exists():
        try:
            with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "enabled": False,
        "auto_narrate": False,
        "default_urdu_voice": "ur-PK-AsadNeural",
        "default_english_voice": "en-US-GuyNeural",
        "speed": "0%",
        "volume": "+0%",
        "current_language": "auto",
    }


def _save_config(data: dict) -> None:
    _CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(_CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def is_urdu_text(text: str) -> bool:
    """Detects whether text is in Urdu script or Roman Urdu."""
    if not text:
        return False
    # Check Urdu Unicode block
    if _URDU_RANGE_RE.search(text):
        return True
    # Check Roman Urdu keywords
    words = set(re.findall(r"\b[a-zA-Z]+\b", text.lower()))
    matches = words.intersection(_ROMAN_URDU_WORDS)
    return len(matches) >= 2 or (len(words) <= 3 and len(matches) >= 1)


class VoiceNarrator:
    """Thread-safe, non-blocking streaming voice narrator."""

    def __init__(self):
        self.config = _load_config()
        self._queue: queue.Queue = queue.Queue()
        self._stop_event = threading.Event()
        self._current_process = None
        self._mixer_initialized = False
        self._lock = threading.Lock()
        self._on_speaking_state = None

        # Start background worker thread
        self._worker_thread = threading.Thread(target=self._worker_loop, daemon=True, name="NarratorWorker")
        self._worker_thread.start()

    def set_speaking_callback(self, callback):
        """Register a callback fn(bool) to be called when narration starts or ends."""
        self._on_speaking_state = callback


    def _ensure_mixer(self):
        if not self._mixer_initialized:
            try:
                import pygame
                if not pygame.mixer.get_init():
                    pygame.mixer.init(frequency=24000, size=-16, channels=2, buffer=4096)
                self._mixer_initialized = True
            except Exception as e:
                print(f"[Narrator] Mixer init warning: {e}")

    def _worker_loop(self):
        """Pulls text items from the queue and speaks them using edge_tts with SAPI fallback."""
        self._ensure_mixer()
        while not self._stop_event.is_set():
            try:
                item = self._queue.get(timeout=0.2)
            except queue.Empty:
                continue

            if item is None:
                break

            text, voice, rate, volume = item
            try:
                self._synthesize_and_play(text, voice, rate, volume)
            except Exception as e:
                print(f"[Narrator] Playback error: {e}")
            finally:
                self._queue.task_done()

    def _synthesize_and_play(self, text: str, voice: str, rate: str, volume: str):
        # Resolve voice aliases from Google Urdu pack & Gemini pack
        try:
            from core.voice_assets import voice_manager
            resolved = voice_manager.resolve_voice(voice)
            if resolved:
                voice = resolved
        except Exception:
            pass

        if not voice:
            voice = "ur-PK-AsadNeural" if is_urdu_text(text) else "en-US-GuyNeural"

        # Clean markdown formatting so narrator speaks naturally
        clean_text = re.sub(r"[*_`#~\[\]\(\)>]", " ", text)
        clean_text = re.sub(r"https?://\S+", "link", clean_text)
        clean_text = re.sub(r"\s+", " ", clean_text).strip()
        if not clean_text:
            return

        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tf:
            temp_path = tf.name

        tts_success = False
        try:
            import edge_tts
            async def _run_tts():
                communicate = edge_tts.Communicate(clean_text, voice, rate=rate, volume=volume)
                await communicate.save(temp_path)

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(_run_tts())
                if os.path.exists(temp_path) and os.path.getsize(temp_path) > 100:
                    tts_success = True
            finally:
                try:
                    loop.close()
                except Exception:
                    pass
        except Exception as e:
            print(f"[Narrator] edge_tts synthesis warning: {e}")

        # Fallback to Windows SAPI speech if edge_tts is unavailable or failed
        if not tts_success:
            try:
                import subprocess
                ps_script = f"""
                Add-Type -AssemblyName System.Speech;
                $synth = New-Object System.Speech.Synthesis.SpeechSynthesizer;
                $synth.Speak([Console]::InputEncoding.GetString([System.Text.Encoding]::UTF8.GetBytes('{clean_text[:200]}')));
                """
                subprocess.run(["powershell", "-NoProfile", "-Command", ps_script], timeout=8, creationflags=0x08000000)
            except Exception as se:
                print(f"[Narrator] Offline SAPI speech failed: {se}")
            finally:
                if os.path.exists(temp_path):
                    try: os.unlink(temp_path)
                    except Exception: pass
            return

        # Play audio using pygame.mixer with smooth buffer
        try:
            import pygame
            self._ensure_mixer()
            if self._on_speaking_state:
                try: self._on_speaking_state(True)
                except Exception: pass
            pygame.mixer.music.load(temp_path)
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy() and not self._stop_event.is_set():
                time.sleep(0.04)
            pygame.mixer.music.stop()
            pygame.mixer.music.unload()
        except Exception as e:
            print(f"[Narrator] Mixer playback failed: {e}")
        finally:
            if self._on_speaking_state:
                try: self._on_speaking_state(False)
                except Exception: pass
            try:
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
            except Exception:
                pass

    def speak(
        self,
        text: str,
        voice: Optional[str] = None,
        language: Optional[str] = None,
        rate: Optional[str] = None,
        interrupt: bool = True,
    ) -> None:
        """Enqueues text to be spoken asynchronously."""
        if not self.config.get("enabled", False) or not text.strip():
            return

        if interrupt:
            self.stop()

        # Determine voice
        chosen_voice = voice
        if not chosen_voice:
            is_urdu = False
            if language:
                is_urdu = language.lower() in ("ur", "urdu", "pk")
            else:
                is_urdu = is_urdu_text(text)

            if is_urdu:
                chosen_voice = self.config.get("default_urdu_voice", "ur-PK-AsadNeural")
            else:
                chosen_voice = self.config.get("default_english_voice", "en-US-GuyNeural")

        rate_val = rate or self.config.get("speed", "+10%")
        volume = self.config.get("volume", "+0%")

        self._queue.put((text, chosen_voice, rate_val, volume))

    def speak_instant(self, text: str, voice: Optional[str] = None, rate: Optional[str] = None) -> None:
        """Speaks immediately, interrupting any ongoing narration."""
        self.speak(text, voice=voice, rate=rate, interrupt=True)

    def stop(self) -> None:
        """Interrupts current speech and clears pending queue."""
        try:
            while not self._queue.empty():
                try:
                    self._queue.get_nowait()
                    self._queue.task_done()
                except queue.Empty:
                    break
            import pygame
            if self._mixer_initialized and pygame.mixer.get_init():
                pygame.mixer.music.stop()
        except Exception:
            pass

    def set_urdu_voice(self, voice_alias_or_name: str) -> str:
        """Sets the active Urdu voice model."""
        v = _VOICE_MAP.get(voice_alias_or_name.lower(), voice_alias_or_name)
        self.config["default_urdu_voice"] = v
        _save_config(self.config)
        return f"Narrator Urdu voice set to '{v}'."

    def set_english_voice(self, voice_alias_or_name: str) -> str:
        """Sets the active English voice model."""
        v = _VOICE_MAP.get(voice_alias_or_name.lower(), voice_alias_or_name)
        self.config["default_english_voice"] = v
        _save_config(self.config)
        return f"Narrator English voice set to '{v}'."

    def set_speed(self, speed_str: str) -> str:
        """Adjusts speech speed (e.g., '+0%', '+10%', '+20%')."""
        s = speed_str if speed_str.startswith(("+", "-")) else f"+{speed_str}"
        if not s.endswith("%"):
            s = f"{s}%"
        self.config["speed"] = s
        _save_config(self.config)
        return f"Narrator speed set to '{s}'."

    def set_enabled(self, enabled: bool) -> str:
        self.config["enabled"] = enabled
        if not enabled:
            self.stop()
        _save_config(self.config)
        return f"Narrator {'enabled' if enabled else 'disabled'}."

    def set_auto_narrate(self, auto: bool) -> str:
        self.config["auto_narrate"] = auto
        _save_config(self.config)
        return f"Auto-narration is now {'ON' if auto else 'OFF'}."

    def get_status(self) -> dict:
        """Returns the active narrator configuration."""
        return dict(self.config)

    def test_voice(self, language: str = "both", wait: bool = False) -> str:
        """Plays test audio to verify speakers and speech synthesis in Urdu and English."""
        lang = (language or "both").lower().strip()
        self.stop()

        if lang in ("ur", "urdu", "pk"):
            urdu_text = "السلام علیکم جناب! میں جے اے آر وی آئی ایس ہوں۔ اردو آڈیو وائس سسٹم کامیابی کے ساتھ فعال اور مربوط ہو چکا ہے۔"
            self.speak(urdu_text, voice=self.config.get("default_urdu_voice", "ur-PK-AsadNeural"), language="ur", interrupt=True)
            msg = "Playing Urdu voice test (ur-PK-AsadNeural)..."
        elif lang in ("en", "english"):
            en_text = "Hello Sir! J.A.R.V.I.S audio voice system is fully integrated, operational, and ready."
            self.speak(en_text, voice=self.config.get("default_english_voice", "en-US-GuyNeural"), language="en", interrupt=True)
            msg = "Playing English voice test (en-US-GuyNeural)..."
        else:
            # Both: Urdu followed by English
            urdu_text = "السلام علیکم جناب! جے اے آر وی آئی ایس اردو آڈیو سسٹم فعال ہے۔"
            en_text = "Audio voice integration test complete. System is fully operational."
            self.speak(urdu_text, voice=self.config.get("default_urdu_voice", "ur-PK-AsadNeural"), language="ur", interrupt=True)
            self._queue.put((en_text, self.config.get("default_english_voice", "en-US-GuyNeural"), self.config.get("speed", "+10%"), "+0%"))
            msg = "Playing bilingual voice test (Urdu & English)..."

        if wait:
            self.wait_until_done()

        return msg

    def wait_until_done(self, timeout: float = 15.0) -> None:
        """Blocks until all queued audio synthesis and playback completes."""
        start = time.monotonic()
        try:
            self._queue.join()
        except Exception:
            pass
        import pygame
        while time.monotonic() - start < timeout:
            if pygame.mixer.get_init() and pygame.mixer.music.get_busy():
                time.sleep(0.05)
            else:
                break


narrator = VoiceNarrator()
