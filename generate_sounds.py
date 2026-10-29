"""
Synthesize high-tech JARVIS sci-fi sound effects and store them in assets/sounds.
Uses pure Python standard library (wave, math, struct) for pristine, zero-dependency audio.
"""
import math
import struct
import wave
from pathlib import Path

SAMPLE_RATE = 44100
SOUNDS_DIR = Path(__file__).resolve().parent / "assets" / "sounds"
SOUNDS_DIR.mkdir(parents=True, exist_ok=True)


def _write_wav(filename: str, samples: list[float]):
    filepath = SOUNDS_DIR / filename
    with wave.open(str(filepath), "wb") as wav_file:
        wav_file.setnchannels(1)  # Mono
        wav_file.setsampwidth(2)  # 16-bit
        wav_file.setframerate(SAMPLE_RATE)
        # Convert float (-1.0 to 1.0) to 16-bit PCM integer (-32767 to 32767)
        raw_data = bytearray()
        for s in samples:
            clamped = max(-1.0, min(1.0, s))
            val = int(clamped * 32767)
            raw_data.extend(struct.pack("<h", val))
        wav_file.writeframes(raw_data)
    print(f"[SoundSynth] Generated: {filename} ({len(samples)/SAMPLE_RATE:.2f}s)")


def gen_startup():
    """Iron Man Mark-LV Arc Reactor power up sound (deep pulse rising into crisp tech chime)."""
    duration = 1.6
    n_samples = int(duration * SAMPLE_RATE)
    samples = []
    for i in range(n_samples):
        t = i / SAMPLE_RATE
        # Sub-bass power rise: 80Hz -> 480Hz
        freq = 80 + 400 * (t / duration) ** 1.8
        sub = math.sin(2 * math.pi * freq * t) * (0.6 * math.sin(math.pi * t / duration))
        
        # High harmonics cyber chime in second half
        harm = 0.0
        if t > 0.5:
            rel_t = t - 0.5
            chime_env = math.exp(-rel_t * 3.5)
            harm = 0.4 * (
                math.sin(2 * math.pi * 1200 * t) +
                0.5 * math.sin(2 * math.pi * 2400 * t) +
                0.3 * math.sin(2 * math.pi * 3600 * t)
            ) * chime_env
        
        # Power pulse oscillation
        pulse = 0.8 + 0.2 * math.sin(2 * math.pi * 18 * t)
        samples.append((sub + harm) * pulse * 0.85)
    _write_wav("jarvis_startup.wav", samples)


def gen_listen():
    """HUD listening activation beep (crisp dual high-frequency blip)."""
    duration = 0.22
    n_samples = int(duration * SAMPLE_RATE)
    samples = []
    for i in range(n_samples):
        t = i / SAMPLE_RATE
        env = math.exp(-t * 22)
        # 1760Hz (A6) with 3520Hz shimmer
        sig = (math.sin(2 * math.pi * 1760 * t) + 0.3 * math.sin(2 * math.pi * 3520 * t)) * env
        samples.append(sig * 0.75)
    _write_wav("jarvis_listening.wav", samples)


def gen_process():
    """Target acquired / processing confirmation blip (two-tone quick chime: 880Hz -> 1320Hz)."""
    duration = 0.28
    n_samples = int(duration * SAMPLE_RATE)
    samples = []
    for i in range(n_samples):
        t = i / SAMPLE_RATE
        if t < 0.12:
            env = math.exp(-t * 18)
            f = 880
        else:
            t2 = t - 0.12
            env = math.exp(-t2 * 16)
            f = 1320
        sig = math.sin(2 * math.pi * f * t) * env
        samples.append(sig * 0.7)
    _write_wav("jarvis_processing.wav", samples)


def gen_success():
    """Action completed / Task success sequence (rapid triad: 660Hz -> 880Hz -> 1320Hz)."""
    duration = 0.40
    n_samples = int(duration * SAMPLE_RATE)
    samples = []
    for i in range(n_samples):
        t = i / SAMPLE_RATE
        step = int(t / 0.11)
        sub_t = t - step * 0.11
        env = math.exp(-sub_t * 20)
        freqs = [660, 880, 1320, 1760]
        f = freqs[min(step, len(freqs)-1)]
        sig = math.sin(2 * math.pi * f * t) * env
        samples.append(sig * 0.65)
    _write_wav("jarvis_success.wav", samples)


def gen_alert():
    """System alert / Error sound (descending warning pulse)."""
    duration = 0.35
    n_samples = int(duration * SAMPLE_RATE)
    samples = []
    for i in range(n_samples):
        t = i / SAMPLE_RATE
        env = math.exp(-t * 8)
        f = 520 - 180 * (t / duration)
        sig = (math.sin(2 * math.pi * f * t) + 0.4 * math.sin(2 * math.pi * (f * 2) * t)) * env
        samples.append(sig * 0.7)
    _write_wav("jarvis_alert.wav", samples)


if __name__ == "__main__":
    gen_startup()
    gen_listen()
    gen_process()
    gen_success()
    gen_alert()
    print("[SoundSynth] All JARVIS sound effects generated successfully!")
