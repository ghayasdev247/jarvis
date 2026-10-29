"""
core/sfx.py — Authentic Iron Man & Sci-Fi Sound Effects Engine for J.A.R.V.I.S.
Plays authentic high-tech studio audio assets with mathematical synthesis fallback.
Zero-latency and non-blocking.
"""
from __future__ import annotations

import os
import sys
import threading
from pathlib import Path

try:
    import winsound
    _WINSOUND_OK = True
except Exception:
    _WINSOUND_OK = False

try:
    import sounddevice as sd
    import numpy as np
    _SD_OK = True
except Exception:
    _SD_OK = False

SR = 24000


def _get_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent


BASE_DIR = _get_base_dir()
AUDIO_DIR = BASE_DIR / "audio"


def _play_wav(wav_name: str) -> bool:
    """Play a WAV file asynchronously using native Windows hardware audio."""
    path = AUDIO_DIR / wav_name
    if path.exists() and _WINSOUND_OK:
        try:
            winsound.PlaySound(str(path), winsound.SND_FILENAME | winsound.SND_ASYNC)
            return True
        except Exception:
            pass
    return False


def _play_synth(samples: np.ndarray):
    """Play synthesized audio if wav asset is absent."""
    if not _SD_OK or samples is None:
        return

    def _worker():
        try:
            sd.play(samples, samplerate=SR, blocking=False)
        except Exception:
            pass

    threading.Thread(target=_worker, daemon=True, name="jarvis-sfx").start()


def _envelope(length: int, attack: float = 0.05, decay: float = 0.95) -> np.ndarray:
    att_samples = int(length * attack)
    dec_samples = length - att_samples
    att = np.linspace(0.0, 1.0, att_samples, endpoint=False)
    dec = np.linspace(1.0, 0.0, dec_samples)
    return np.concatenate([att, dec])


def play_boot():
    """Iron Man Arc Reactor power-up / initialization SFX."""
    if _play_wav("initialize.wav"):
        return
    try:
        dur = 0.8
        t = np.linspace(0, dur, int(SR * dur), endpoint=False)
        f_sweep = np.linspace(140, 520, len(t))
        wave = (0.45 * np.sin(2 * np.pi * f_sweep * t) +
                0.25 * np.sin(2 * np.pi * (f_sweep * 1.5) * t)) * _envelope(len(t), 0.15, 0.85)
        _play_synth(wave.astype(np.float32))
    except Exception:
        pass


def play_listening():
    """Iron Man suit HUD mic activation / listening SFX."""
    if _play_wav("mic.wav"):
        return
    try:
        dur = 0.18
        t = np.linspace(0, dur, int(SR * dur), endpoint=False)
        sig = (0.35 * np.sin(2 * np.pi * 880.0 * t) +
               0.25 * np.sin(2 * np.pi * 1320.0 * t)) * _envelope(len(t), 0.04, 0.96)
        _play_synth(sig.astype(np.float32))
    except Exception:
        pass


def play_interrupted():
    """Iron Man HUD blip / fast cutoff SFX."""
    if _play_wav("button.wav"):
        return
    try:
        dur = 0.06
        t = np.linspace(0, dur, int(SR * dur), endpoint=False)
        sig = 0.30 * np.sin(2 * np.pi * np.linspace(600, 220, len(t)) * t) * _envelope(len(t), 0.1, 0.9)
        _play_synth(sig.astype(np.float32))
    except Exception:
        pass


def play_action():
    """Iron Man task execution confirmation SFX."""
    if _play_wav("action.wav"):
        return
    try:
        dur = 0.24
        t = np.linspace(0, dur, int(SR * dur), endpoint=False)
        sig = (0.28 * np.sin(2 * np.pi * 523.25 * t) +
               0.22 * np.sin(2 * np.pi * 783.99 * t)) * _envelope(len(t), 0.08, 0.92)
        _play_synth(sig.astype(np.float32))
    except Exception:
        pass


def play_optimized():
    """Iron Man Stark system repulsor access granted / optimized SFX."""
    if _play_wav("access_granted.wav"):
        return
    try:
        dur = 0.45
        t = np.linspace(0, dur, int(SR * dur), endpoint=False)
        f = np.linspace(240, 880, len(t))
        sig = 0.35 * np.sin(2 * np.pi * f * t) * _envelope(len(t), 0.1, 0.9)
        _play_synth(sig.astype(np.float32))
    except Exception:
        pass


def play_alert():
    """Iron Man suit alert / warning SFX."""
    if _play_wav("alert.wav"):
        return
    try:
        dur = 0.3
        t = np.linspace(0, dur, int(SR * dur), endpoint=False)
        sig = 0.35 * np.sin(2 * np.pi * 440.0 * t) * _envelope(len(t), 0.05, 0.95)
        _play_synth(sig.astype(np.float32))
    except Exception:
        pass
