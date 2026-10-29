"""
core/voice_assets.py — Comprehensive Voice & Audio Pack Manager for J.A.R.V.I.S.

Discovers, indexes, and integrates all voice packs and audio assets located in `audio/`:
1. Google Urdu (Pakistan) Voice Pack (`audio/google, Urdu (Pakistan) 51`):
   - ur-pk-x-cfn: Urdu (Pakistan) I (Female)
   - ur-pk-x-urf: Urdu (Pakistan) II (Female)
   - ur-pk-x-urm: Urdu (Pakistan) III (Male)
   - Deep neural TFLite & SeANet pipeline models (burdock, seanet)
2. Gemini Global Voice Pack (`audio/gemini`):
   - 53 multi-language neural voice profiles
3. Studio Audio & Voice Assets (12 WAV files):
   - access_granted.wav, initialize.wav, alert.wav, apperance_loading.wav,
     button.wav, hover.wav, hover_button.wav, loading.wav, mic.wav,
     trading.wav, websearch.wav, action.wav
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import yaml
    _YAML_OK = True
except Exception:
    _YAML_OK = False


def _get_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent


BASE_DIR = _get_base_dir()
AUDIO_DIR = BASE_DIR / "audio"
URDU_PACK_DIR = AUDIO_DIR / "google, Urdu (Pakistan) 51"
GEMINI_PACK_DIR = AUDIO_DIR / "gemini"


class _CustomYamlLoader(yaml.SafeLoader if _YAML_OK else object):
    pass


if _YAML_OK:
    _CustomYamlLoader.add_multi_constructor(
        "tag:yaml.org,2002:",
        lambda loader, suffix, node: (
            loader.construct_mapping(node)
            if isinstance(node, yaml.MappingNode)
            else loader.construct_sequence(node)
        ),
    )


class VoiceAssetManager:
    """Manages audio folder voice packs, models, and WAV sound assets."""

    def __init__(self):
        self._urdu_voices: List[Dict[str, Any]] = []
        self._gemini_voices: List[Dict[str, Any]] = []
        self._audio_files: List[str] = []
        self.reload()

    def reload(self) -> None:
        """Scan and index all assets in audio/."""
        self._load_urdu_pack()
        self._load_gemini_pack()
        self._load_audio_files()

    def _load_urdu_pack(self) -> None:
        cfg_file = URDU_PACK_DIR / "config.yaml"
        if cfg_file.exists() and _YAML_OK:
            try:
                with open(cfg_file, "r", encoding="utf-8") as f:
                    data = yaml.load(f, Loader=_CustomYamlLoader)
                    self._urdu_voices = data.get("google", []) if isinstance(data, dict) else []
            except Exception as e:
                print(f"[VoiceAssets] Warning loading Urdu pack config: {e}")
        else:
            # Fallback default definition
            self._urdu_voices = [
                {"code": "ur-pk-x-cfn", "name": "Urdu (Pakistan) I", "gender": 0, "locale": "ur-PK"},
                {"code": "ur-pk-x-urf", "name": "Urdu (Pakistan) II", "gender": 0, "locale": "ur-PK"},
                {"code": "ur-pk-x-urm", "name": "Urdu (Pakistan) III", "gender": 1, "locale": "ur-PK"},
            ]

    def _load_gemini_pack(self) -> None:
        cfg_file = GEMINI_PACK_DIR / "config.yaml"
        if cfg_file.exists() and _YAML_OK:
            try:
                with open(cfg_file, "r", encoding="utf-8") as f:
                    data = yaml.load(f, Loader=_CustomYamlLoader)
                    self._gemini_voices = data.get("gemini", []) if isinstance(data, dict) else []
            except Exception as e:
                print(f"[VoiceAssets] Warning loading Gemini pack config: {e}")

    def _load_audio_files(self) -> None:
        if AUDIO_DIR.exists():
            self._audio_files = sorted([f.name for f in AUDIO_DIR.glob("*.wav")])
        else:
            self._audio_files = []

    def get_urdu_voices(self) -> List[Dict[str, Any]]:
        """Returns registered Google Urdu voices from audio pack."""
        return list(self._urdu_voices)

    def get_gemini_voices(self) -> List[Dict[str, Any]]:
        """Returns registered Gemini voices from audio pack."""
        return list(self._gemini_voices)

    def get_audio_files(self) -> List[str]:
        """Returns list of WAV audio filenames in audio/."""
        return list(self._audio_files)

    def resolve_voice(self, identifier: str) -> Optional[str]:
        return self.resolve_voice_mapping(identifier)

    def resolve_voice_mapping(self, identifier: str) -> Optional[str]:
        """
        Resolves a user-provided voice identifier/code/alias to a known TTS voice model.
        Maps Google Urdu pack codes (ur-pk-x-urm, etc.) to corresponding high-fidelity synthesis.
        """
        key = (identifier or "").lower().strip()
        # Google Urdu pack codes
        if key in ("ur-pk-x-cfn", "google_urdu_1", "urdu_1", "urdu_f1"):
            return "ur-PK-UzmaNeural"
        if key in ("ur-pk-x-urf", "google_urdu_2", "urdu_2", "urdu_f2"):
            return "ur-PK-UzmaNeural"
        if key in ("ur-pk-x-urm", "google_urdu_3", "urdu_3", "urdu_m", "google_urdu"):
            return "ur-PK-AsadNeural"

        # Direct neural voice matches
        if "ur-pk-asad" in key:
            return "ur-PK-AsadNeural"
        if "ur-pk-uzma" in key:
            return "ur-PK-UzmaNeural"
        if "en-us-guy" in key:
            return "en-US-GuyNeural"
        if "en-us-jenny" in key:
            return "en-US-JennyNeural"
        if "en-gb-ryan" in key:
            return "en-GB-RyanNeural"

        # General Urdu aliases
        if "asad" in key or ("male" in key and "ur" in key):
            return "ur-PK-AsadNeural"
        if "uzma" in key or ("female" in key and "ur" in key):
            return "ur-PK-UzmaNeural"
        if "salman" in key:
            return "ur-IN-SalmanNeural"
        if "gul" in key:
            return "ur-IN-GulNeural"

        # English aliases
        if "guy" in key:
            return "en-US-GuyNeural"
        if "aria" in key:
            return "en-US-AriaNeural"
        if "jenny" in key:
            return "en-US-JennyNeural"
        if "ryan" in key:
            return "en-GB-RyanNeural"

        # If it's already a valid neural name like xxxNeural, return original
        if "neural" in key:
            return identifier

        return identifier

    def get_summary(self) -> Dict[str, Any]:
        """Provides a complete summary of all discovered voices and audio assets."""
        return {
            "audio_wav_files": len(self._audio_files),
            "google_urdu_voices": len(self._urdu_voices),
            "gemini_voices": len(self._gemini_voices),
            "urdu_voices_list": [
                f"{v.get('code')}: {v.get('name')} ({'Male' if v.get('gender') == 1 else 'Female'})"
                for v in self._urdu_voices
            ],
            "wav_assets": self._audio_files,
        }


# Global singleton instance
voice_manager = VoiceAssetManager()


def resolve_voice(identifier: str) -> Optional[str]:
    """Module-level helper to resolve voice codes to synthesis voices."""
    return voice_manager.resolve_voice(identifier)
