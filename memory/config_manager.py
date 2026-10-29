import json
import sys
from pathlib import Path

def get_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent

BASE_DIR    = get_base_dir()
CONFIG_DIR  = BASE_DIR / "config"
CONFIG_FILE = CONFIG_DIR / "api_keys.json"

def ensure_config_dir() -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)

def config_exists() -> bool:
    return CONFIG_FILE.exists()

def save_api_keys(gemini_api_key: str) -> None:
    ensure_config_dir()

    data: dict = {}
    if CONFIG_FILE.exists():
        try:
            data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        except Exception:
            data = {}

    data["gemini_api_key"] = gemini_api_key.strip()

    CONFIG_FILE.write_text(
        json.dumps(data, indent=2),
        encoding="utf-8"
    )

BACKUP_DIR = CONFIG_DIR / "backups"

DEFAULT_SYSTEM_CONFIG: dict = {
    "assistant_name": "JARVIS",
    "user_name": "Meer Hamad Ali Khosa",
    "assistant_persona": "stark",
    "response_verbosity": "concise",
    "emotion_mode": "adaptive",
    "language_preference": "auto",
    "ui_color": "#00d4ff",
    "live_model": "models/gemini-3.8-flash-live-preview",
    "voice_name": "Charon",
    "unrestricted_mode": True,
    "barge_in_enabled": False,
    "push_to_talk_enabled": False,
    "wake_word_enabled": False,
    "hud_style": "face",
    "camera_index": 0,
    "startup_video_enabled": True,
    "startup_video_shuffle": True,
    "startup_video_path": "videos/startup_loader.mp4",
    "input_device": "System default",
    "output_device": "System default",
    "accessibility_mode": True,
    "tts_engine": "sapi5",
    "sapi5_voice": "Microsoft David Desktop - English (United States)",
    "urdu_voice": "ur-PK-AsadNeural",
    "narrator_speed": 1.15,
    "narrator_config": {
        "enabled": True,
        "auto_narrate": True,
        "default_urdu_voice": "ur-PK-AsadNeural",
        "default_english_voice": "en-US-GuyNeural",
        "speed": "+10%",
        "volume": "+0%",
        "current_language": "auto"
    },
    "feature_preservation_enabled": True,
    "config_version": "5.0.0"
}

def create_config_backup(tag: str = "auto") -> str:
    """Create an automatic timestamped backup of the current configuration and memory."""
    try:
        BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        import datetime
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        target = BACKUP_DIR / f"config_backup_{tag}_{ts}.json"
        if CONFIG_FILE.exists():
            target.write_text(CONFIG_FILE.read_text(encoding="utf-8"), encoding="utf-8")
        
        mem_path = BASE_DIR / "memory" / "long_term.json"
        if mem_path.exists():
            mem_target = BACKUP_DIR / f"memory_backup_{tag}_{ts}.json"
            mem_target.write_text(mem_path.read_text(encoding="utf-8"), encoding="utf-8")
        
        backups = sorted(BACKUP_DIR.glob("config_backup_*.json"), key=lambda p: p.stat().st_mtime)
        if len(backups) > 20:
            for old in backups[:-20]:
                try: old.unlink()
                except Exception: pass
        return str(target.name)
    except Exception as e:
        print(f"[config_manager] Backup creation notice: {e}")
        return ""

def list_config_backups() -> list[dict]:
    """List all available config backups sorted newest first."""
    if not BACKUP_DIR.exists():
        return []
    res = []
    for p in sorted(BACKUP_DIR.glob("config_backup_*.json"), key=lambda x: x.stat().st_mtime, reverse=True):
        res.append({
            "name": p.name,
            "path": str(p),
            "size": p.stat().st_size,
            "mtime": p.stat().st_mtime
        })
    return res

def restore_config_backup(backup_name: str) -> tuple[bool, str]:
    """Safely restore a backup while non-destructively preserving any newly added feature keys."""
    try:
        target = BACKUP_DIR / backup_name
        if not target.exists():
            return False, f"Backup {backup_name} not found."
        
        backup_data = json.loads(target.read_text(encoding="utf-8"))
        if not isinstance(backup_data, dict):
            return False, "Invalid backup data structure."
        
        merged = dict(DEFAULT_SYSTEM_CONFIG)
        if CONFIG_FILE.exists():
            try:
                cur = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
                if isinstance(cur, dict):
                    merged.update(cur)
            except Exception:
                pass
        merged.update(backup_data)
        
        ensure_config_dir()
        CONFIG_FILE.write_text(json.dumps(merged, indent=4), encoding="utf-8")
        return True, f"Successfully restored configuration from {backup_name}."
    except Exception as e:
        return False, f"Failed to restore backup: {e}"

def ensure_features_and_config_preserved() -> dict:
    """Non-destructive feature preservation engine:
    Guarantees that updating JARVIS never deletes or hides previous user settings,
    API keys, memory, or newly introduced feature flags.
    """
    ensure_config_dir()
    if not CONFIG_FILE.exists():
        CONFIG_FILE.write_text(json.dumps(DEFAULT_SYSTEM_CONFIG, indent=4), encoding="utf-8")
        return dict(DEFAULT_SYSTEM_CONFIG)

    try:
        data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            data = {}
    except Exception:
        data = {}

    modified = False
    backups = list_config_backups()
    import time
    if not backups or (time.time() - backups[0]["mtime"]) > 21600:
        create_config_backup("auto")

    for k, default_val in DEFAULT_SYSTEM_CONFIG.items():
        if k not in data or data[k] is None:
            data[k] = default_val
            modified = True
        elif isinstance(default_val, dict) and isinstance(data[k], dict):
            for sub_k, sub_val in default_val.items():
                if sub_k not in data[k]:
                    data[k][sub_k] = sub_val
                    modified = True

    if modified:
        try:
            CONFIG_FILE.write_text(json.dumps(data, indent=4), encoding="utf-8")
        except Exception as e:
            print(f"[config_manager] Feature preservation save notice: {e}")

    return data

# Execute feature preservation verification on module load
try:
    ensure_features_and_config_preserved()
except Exception:
    pass

def load_api_keys() -> dict:
    if not CONFIG_FILE.exists():
        return ensure_features_and_config_preserved()
    try:
        return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"Failed to load api_keys.json: {e}")
        return ensure_features_and_config_preserved()

def get_gemini_key() -> str | None:
    return load_api_keys().get("gemini_api_key")

def is_configured() -> bool:
    key = get_gemini_key()
    return bool(key and len(key) > 15)


def get_assistant_name() -> str:
    """Return the configured assistant name, or 'JARVIS' if not set."""
    return load_api_keys().get("assistant_name", "JARVIS") or "JARVIS"


def get_user_name() -> str:
    """Return the configured user name for addressing."""
    return load_api_keys().get("user_name", "")


def save_assistant_config(assistant_name: str, user_name: str) -> None:
    """Persist assistant name and user name to config."""
    ensure_config_dir()
    data: dict = {}
    if CONFIG_FILE.exists():
        try:
            data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        except Exception:
            data = {}
    data["assistant_name"] = assistant_name.strip() or "JARVIS"
    data["user_name"] = user_name.strip()
    CONFIG_FILE.write_text(json.dumps(data, indent=4), encoding="utf-8")


# ── Assistant voice ──────────────────────────────────────────────────────────
# Comprehensive Google Gemini Live / Google AI Studio voice catalog (30 core prebuilt voices).
VOICES_CACHE_FILE = CONFIG_DIR / "voices_cache.json"

DEFAULT_VOICES_DATA: dict[str, dict] = {
    "Charon": {
        "gender": "Male",
        "style": "Informative / Deep",
        "description": "Deep, authoritative, and articulate (JARVIS classic signature voice).",
    },
    "Puck": {
        "gender": "Male",
        "style": "Upbeat / Lively",
        "description": "Crisp, energetic, and engaging masculine voice.",
    },
    "Aoede": {
        "gender": "Female",
        "style": "Breezy / Soft",
        "description": "Breezy, light, and natural melodic feminine voice.",
    },
    "Kore": {
        "gender": "Female",
        "style": "Firm / Clear",
        "description": "Confident, assertive, and energetic feminine voice.",
    },
    "Fenrir": {
        "gender": "Male",
        "style": "Excitable / Passionate",
        "description": "Dynamic, vibrant, and enthusiastic masculine voice.",
    },
    "Zephyr": {
        "gender": "Female",
        "style": "Bright / Dynamic",
        "description": "Lively, clear, and modern feminine voice.",
    },
    "Achernar": {
        "gender": "Female",
        "style": "Soft / Warm",
        "description": "Calm, soothing, higher-pitched feminine voice.",
    },
    "Achird": {
        "gender": "Male",
        "style": "Friendly / Warm",
        "description": "Warm, conversational, and approachable masculine voice.",
    },
    "Algenib": {
        "gender": "Male",
        "style": "Gravelly / Resonant",
        "description": "Grounded, textured, and hard-hitting masculine voice.",
    },
    "Algieba": {
        "gender": "Male",
        "style": "Smooth / Polished",
        "description": "Polished, smooth, and relaxed masculine voice.",
    },
    "Alnilam": {
        "gender": "Male",
        "style": "Firm / Commanding",
        "description": "Commanding, direct, and authoritative masculine voice.",
    },
    "Autonoe": {
        "gender": "Female",
        "style": "Bright / Cheerful",
        "description": "Bright, uplifting, and cheerful feminine voice.",
    },
    "Callirrhoe": {
        "gender": "Female",
        "style": "Easy-going / Relaxed",
        "description": "Easy-going, comfortable, and casual feminine voice.",
    },
    "Despina": {
        "gender": "Female",
        "style": "Smooth / Balanced",
        "description": "Balanced, smooth, and pleasant feminine voice.",
    },
    "Enceladus": {
        "gender": "Male",
        "style": "Breathy / Gentle",
        "description": "Breathy, gentle, and quiet masculine voice.",
    },
    "Erinome": {
        "gender": "Female",
        "style": "Clear / Articulate",
        "description": "Crisp, clear, and articulate feminine voice.",
    },
    "Gacrux": {
        "gender": "Female",
        "style": "Mature / Professional",
        "description": "Mature, composed, and professional feminine voice.",
    },
    "Iapetus": {
        "gender": "Male",
        "style": "Clear / Resonant",
        "description": "Clear, resonant, and balanced masculine voice.",
    },
    "Laomedeia": {
        "gender": "Female",
        "style": "Upbeat / Enthusiastic",
        "description": "Enthusiastic, positive, and vibrant feminine voice.",
    },
    "Leda": {
        "gender": "Female",
        "style": "Youthful / Fresh",
        "description": "Youthful, modern, and expressive feminine voice.",
    },
    "Orus": {
        "gender": "Male",
        "style": "Firm / Steady",
        "description": "Firm, grounded, and steady masculine voice.",
    },
    "Pulcherrima": {
        "gender": "Male",
        "style": "Forward / Confident",
        "description": "Direct, confident, and forward masculine voice.",
    },
    "Rasalgethi": {
        "gender": "Male",
        "style": "Informative / Precise",
        "description": "Knowledgeable, precise, and articulate masculine voice.",
    },
    "Sadachbia": {
        "gender": "Male",
        "style": "Lively / Expressive",
        "description": "Lively, expressive, and engaging masculine voice.",
    },
    "Sadaltager": {
        "gender": "Male",
        "style": "Knowledgeable / Sophisticated",
        "description": "Sophisticated, knowledgeable, and calm masculine voice.",
    },
    "Schedar": {
        "gender": "Male",
        "style": "Even / Balanced",
        "description": "Even-toned, stable, and neutral masculine voice.",
    },
    "Sulafat": {
        "gender": "Female",
        "style": "Warm / Inviting",
        "description": "Warm, gentle, and welcoming feminine voice.",
    },
    "Umbriel": {
        "gender": "Male",
        "style": "Mellow / Relaxed",
        "description": "Mellow, relaxed, and easy-going masculine voice.",
    },
    "Vindemiatrix": {
        "gender": "Female",
        "style": "Gentle / Thoughtful",
        "description": "Gentle, thoughtful, and serene feminine voice.",
    },
    "Zubenelgenubi": {
        "gender": "Male",
        "style": "Casual / Natural",
        "description": "Casual, down-to-earth, and natural masculine voice.",
    },
}

DEFAULT_VOICE = "Charon"

def get_available_voices_dict() -> dict[str, dict]:
    """Return dictionary of voice_name -> metadata {gender, style, description}."""
    voices = dict(DEFAULT_VOICES_DATA)
    if VOICES_CACHE_FILE.exists():
        try:
            cached = json.loads(VOICES_CACHE_FILE.read_text(encoding="utf-8"))
            if isinstance(cached, dict):
                for k, v in cached.items():
                    if isinstance(v, dict):
                        voices[k] = v
                    elif isinstance(v, str):
                        voices[k] = {"gender": "Voice", "style": "Google AI Studio", "description": v}
        except Exception:
            pass
    return voices

def get_available_voices() -> list[str]:
    """Return list of all available voice names."""
    return list(get_available_voices_dict().keys())

# Exposed mutable list for backward compatibility with imports
AVAILABLE_VOICES: list[str] = list(DEFAULT_VOICES_DATA.keys())
if VOICES_CACHE_FILE.exists():
    try:
        _c = json.loads(VOICES_CACHE_FILE.read_text(encoding="utf-8"))
        if isinstance(_c, dict):
            for _k in _c.keys():
                if _k not in AVAILABLE_VOICES:
                    AVAILABLE_VOICES.append(_k)
    except Exception:
        pass

_voice_change_subscribers = []

def register_voice_change_listener(fn) -> None:
    """Register a callback fn(voice_name: str) triggered when the voice is updated."""
    if fn not in _voice_change_subscribers:
        _voice_change_subscribers.append(fn)

def unregister_voice_change_listener(fn) -> None:
    if fn in _voice_change_subscribers:
        _voice_change_subscribers.remove(fn)

def _notify_voice_change(new_voice: str) -> None:
    for cb in list(_voice_change_subscribers):
        try:
            cb(new_voice)
        except Exception as e:
            print(f"[config_manager] Error notifying voice listener: {e}")

def get_voice() -> str:
    """Return the configured Live voice, falling back to DEFAULT_VOICE if unset or unrecognised."""
    raw = load_api_keys().get("voice_name", DEFAULT_VOICE) or DEFAULT_VOICE
    raw_str = str(raw).strip()
    avail = get_available_voices()
    # Case-insensitive match against available voices
    for v in avail:
        if v.lower() == raw_str.lower():
            return v
    return DEFAULT_VOICE

def save_voice(voice_name: str) -> None:
    """Persist the chosen Live voice and notify active session listeners."""
    ensure_config_dir()
    data: dict = {}
    if CONFIG_FILE.exists():
        try:
            data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        except Exception:
            data = {}
    v_raw = (voice_name or "").strip()
    avail = get_available_voices()
    chosen = DEFAULT_VOICE
    for v in avail:
        if v.lower() == v_raw.lower():
            chosen = v
            break

    prev = data.get("voice_name")
    data["voice_name"] = chosen
    CONFIG_FILE.write_text(json.dumps(data, indent=4), encoding="utf-8")

    if prev != chosen:
        _notify_voice_change(chosen)

def fetch_google_ai_studio_voices(api_key: str = None) -> tuple[bool, str, dict]:
    """Fetch all available voices from Google AI Studio / Gemini API.
    
    Returns (success: bool, message: str, voices_dict: dict)
    """
    if not api_key:
        api_key = load_api_keys().get("gemini_api_key", "").strip()
    if not api_key:
        return False, "Gemini API key is not configured.", {}

    import urllib.request
    headers = {"User-Agent": "JARVIS-AI-Studio-Client/1.0"}
    fetched = {}
    token = None

    try:
        # Fetch up to 10 pages from Google AI Studio endpoint
        for _ in range(10):
            url = f"https://generativelanguage.googleapis.com/v1beta/voices?key={api_key}"
            if token:
                url += f"&pageToken={token}"
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=10) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
                for v in payload.get("voices", []):
                    name = v.get("display_name") or v.get("name") or v.get("id")
                    if not name:
                        continue
                    gender = (v.get("gender") or "Neutral").capitalize()
                    desc = v.get("description") or v.get("persona") or "Google AI Studio Voice"
                    accent = v.get("accent") or ""
                    persona = v.get("persona") or ""
                    parts = [gender]
                    if accent:
                        parts.append(accent)
                    if persona:
                        parts.append(persona)
                    style = " • ".join(parts)
                    fetched[name] = {
                        "gender": gender,
                        "style": style,
                        "description": desc,
                        "id": v.get("id", name),
                        "type": v.get("type", "prebuilt")
                    }
                token = payload.get("next_page_token")
                if not token:
                    break

        if fetched:
            all_v = dict(DEFAULT_VOICES_DATA)
            all_v.update(fetched)
            ensure_config_dir()
            VOICES_CACHE_FILE.write_text(json.dumps(all_v, indent=4), encoding="utf-8")
            AVAILABLE_VOICES.clear()
            AVAILABLE_VOICES.extend(list(all_v.keys()))
            return True, f"Successfully fetched {len(fetched)} voices from Google AI Studio.", all_v
        else:
            return False, "No voices returned from Google AI Studio.", {}
    except Exception as e:
        return False, f"Failed to fetch voices: {e}", {}


def get_wake_word_enabled() -> bool:
    """Whether local wake-word gating is on (assistant sleeps until 'Hey Jarvis')."""
    return load_api_keys().get("wake_word_enabled", False)


def save_wake_word_enabled(enabled: bool) -> None:
    ensure_config_dir()
    data: dict = {}
    if CONFIG_FILE.exists():
        try:
            data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        except Exception:
            data = {}
    data["wake_word_enabled"] = bool(enabled)
    CONFIG_FILE.write_text(json.dumps(data, indent=4), encoding="utf-8")


def get_push_to_talk_enabled() -> bool:
    """Hold-a-key-to-speak. When on, the mic is closed unless the chord is held."""
    return load_api_keys().get("push_to_talk_enabled", False)


def save_push_to_talk_enabled(enabled: bool) -> None:
    _save_flag("push_to_talk_enabled", enabled)


HUD_STYLES = ("face", "core")


def get_hud_style() -> str:
    """Which centrepiece the HUD draws: the animated head, or the reactor core.

    Taste, not capability — both render in the same software painter and cost
    about the same. Defaults to the head because that is what MARK LIV shipped
    with; anyone who preferred the older look can switch back in ⚙ and the
    choice survives a restart.
    """
    v = str(load_api_keys().get("hud_style", "face")).strip().lower()
    return v if v in HUD_STYLES else "face"


def save_hud_style(style: str) -> None:
    s = str(style or "").strip().lower()
    _save_flag("hud_style", s if s in HUD_STYLES else "face")


# ── Live-session tuning ──────────────────────────────────────────────────────
# Everything here is optional and has a working default, so an untouched
# config behaves exactly like a configured one. Each value is also a way out:
# if a future model dislikes one of these, set it back and nothing else changes.

def get_thinking_enabled() -> bool:
    """Whether the Live model may spend tokens thinking before it answers.

    Off by default. A voice assistant is judged on how fast it starts talking,
    and the reasoning that actually needs deliberation in this app is delegated
    to the planning tools, which run on a separate non-Live model.
    """
    return bool(load_api_keys().get("thinking_enabled", False))


def save_thinking_enabled(enabled: bool) -> None:
    _save_flag("thinking_enabled", enabled)


def get_turn_tuning() -> dict:
    """How eagerly the server decides you have stopped speaking.

    OFF by default, and that default was earned. Cutting turns shorter looks
    like a free speed win and is not: proactive audio has to judge whether an
    utterance was even addressed to the assistant, and a turn clipped early
    gives it less to judge, so it stays quiet — and the reply to your first
    sentence only arrives once your second one has given it enough context.
    That reads as the assistant being a turn behind, which is far worse than
    the fraction of a second the tuning saves.

    Turn it on with "turn_tuning": {"enabled": true} if your own microphone and
    speaking pace suit it. `silence_ms` is the one that is felt: the pause the
    server sits through before accepting your turn is over.
    """
    cfg = load_api_keys().get("turn_tuning")
    cfg = cfg if isinstance(cfg, dict) else {}

    def _int(key, default, lo, hi):
        try:
            return max(lo, min(hi, int(cfg.get(key, default))))
        except (TypeError, ValueError):
            return default

    return {
        "enabled":    bool(cfg.get("enabled", True)),
        "silence_ms": _int("silence_ms", 400, 200, 3000),
        "prefix_ms":  _int("prefix_ms", 100, 0, 1000),
        # "high" = quicker to decide speech has ended.
        "end_sensitivity":   str(cfg.get("end_sensitivity", "high")).lower(),
        "start_sensitivity": str(cfg.get("start_sensitivity", "high")).lower(),
    }


def save_turn_tuning(values: dict) -> None:
    ensure_config_dir()
    data: dict = {}
    if CONFIG_FILE.exists():
        try:
            data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        except Exception:
            data = {}
    cur = data.get("turn_tuning")
    cur = dict(cur) if isinstance(cur, dict) else {}
    cur.update(values or {})
    data["turn_tuning"] = cur
    CONFIG_FILE.write_text(json.dumps(data, indent=4), encoding="utf-8")


def get_proactive_audio_enabled() -> bool:
    """Whether the model gets to decide an utterance was not aimed at it and
    stay quiet.

    On by default — it is what stops the assistant answering the room. But it
    is also the first thing to switch off if replies ever seem to arrive a turn
    late: what looks like lag is usually the model having judged your previous
    sentence as not addressed to it, and only changing its mind once the next
    one arrives.
    """
    return bool(load_api_keys().get("proactive_audio", True))


def save_proactive_audio_enabled(enabled: bool) -> None:
    _save_flag("proactive_audio", enabled)


MEDIA_RESOLUTIONS = ("default", "low", "medium", "high")


def get_media_resolution() -> str:
    """How finely the model tokenises the screenshots and camera frames it is
    sent. 'medium' keeps on-screen text readable at a fraction of the tokens a
    full-resolution frame costs; 'low' is cheaper still but starts losing small
    text, which is most of what screen captures are for."""
    v = str(load_api_keys().get("media_resolution", "medium")).strip().lower()
    return v if v in MEDIA_RESOLUTIONS else "medium"


def save_media_resolution(value: str) -> None:
    v = str(value or "").strip().lower()
    _save_flag("media_resolution", v if v in MEDIA_RESOLUTIONS else "medium")


PLAYER_QUALITIES = ("144p", "240p", "360p", "480p", "720p", "1080p", "best")


def get_player_quality() -> str:
    """Configured video player stream resolution (e.g. '144p', '360p', '720p')."""
    v = str(load_api_keys().get("player_quality", "144p")).strip().lower()
    if not v.endswith("p") and v.isdigit():
        v = f"{v}p"
    return v if v in PLAYER_QUALITIES else "144p"


def save_player_quality(quality: str) -> None:
    """Save user-selected player quality to persistent config."""
    q = str(quality or "").strip().lower()
    if not q.endswith("p") and q.isdigit():
        q = f"{q}p"
    if q not in PLAYER_QUALITIES:
        q = "144p"
    _save_flag("player_quality", q)


def _save_flag(key: str, value) -> None:
    """Read-modify-write one key without disturbing the rest of the config."""
    ensure_config_dir()
    data: dict = {}
    if CONFIG_FILE.exists():
        try:
            data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        except Exception:
            data = {}
    data[key] = bool(value) if isinstance(value, bool) else value
    CONFIG_FILE.write_text(json.dumps(data, indent=4), encoding="utf-8")


def get_brief_enabled() -> bool:
    return load_api_keys().get("morning_brief_enabled", True)


def save_brief_enabled(enabled: bool) -> None:
    ensure_config_dir()
    data: dict = {}
    if CONFIG_FILE.exists():
        try:
            data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        except Exception:
            data = {}
    data["morning_brief_enabled"] = enabled
    CONFIG_FILE.write_text(json.dumps(data, indent=4), encoding="utf-8")


# ── Audio devices ────────────────────────────────────────────────────────────
# Stored as device NAMES, not sounddevice indices. Indices shift every time a
# USB device is plugged in or removed, so a saved index silently starts pointing
# at a different microphone. The empty string means "system default", which is
# both the factory setting and what an unresolvable saved device falls back to —
# so unplugging a headset degrades to the built-in speakers instead of crashing.

def _patch_config(**fields) -> None:
    """Read-modify-write one or more keys in api_keys.json.

    Every setter in this file open-coded this. Collapsing it here means a new
    setting is one line, and there is one place where a corrupt config file is
    handled instead of nine."""
    ensure_config_dir()
    data: dict = {}
    if CONFIG_FILE.exists():
        try:
            data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        except Exception:
            data = {}
    data.update(fields)
    CONFIG_FILE.write_text(json.dumps(data, indent=4), encoding="utf-8")


def get_input_device() -> str:
    """Microphone device name, or '' for the system default."""
    return (load_api_keys().get("input_device", "") or "").strip()


def save_input_device(name: str) -> None:
    _patch_config(input_device=(name or "").strip())


def get_output_device() -> str:
    """Speaker device name, or '' for the system default."""
    return (load_api_keys().get("output_device", "") or "").strip()


def save_output_device(name: str) -> None:
    _patch_config(output_device=(name or "").strip())


def get_plugin_enabled(plugin_name: str) -> bool:
    """Plugins are enabled by default the moment they're discovered (opt-out model)."""
    return load_api_keys().get("plugins_enabled", {}).get(plugin_name, True)


# ── Per-plugin settings ("tokens" / connection details) ───────────────────────
# Generic store so a plugin can declare its own config fields (PLUGIN_SETTINGS)
# and the settings UI renders + persists them WITHOUT any core edit — keeping the
# drop-in model intact. Values live under plugin_config[<namespace>][<key>].
# A namespace defaults to the plugin name, but a suite of plugins (e.g. the
# several printer plugins) can share ONE namespace.
def get_plugin_config(namespace: str) -> dict:
    """All stored values for a namespace (empty dict if none set yet)."""
    cfg = load_api_keys().get("plugin_config")
    val = cfg.get(namespace) if isinstance(cfg, dict) else None
    return dict(val) if isinstance(val, dict) else {}


def get_plugin_setting(namespace: str, key: str, default=None):
    """A single value from a namespace, or `default` if unset."""
    return get_plugin_config(namespace).get(key, default)


def save_plugin_config(namespace: str, values: dict) -> None:
    """Merge `values` into a namespace's stored config (read-modify-write, like
    every other helper here). Only the provided keys are touched."""
    ensure_config_dir()
    data: dict = {}
    if CONFIG_FILE.exists():
        try:
            data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        except Exception:
            data = {}
    pc = data.get("plugin_config")
    if not isinstance(pc, dict):
        pc = {}
    cur = pc.get(namespace)
    if not isinstance(cur, dict):
        cur = {}
    cur.update(values)
    pc[namespace] = cur
    data["plugin_config"] = pc
    CONFIG_FILE.write_text(json.dumps(data, indent=4), encoding="utf-8")


def save_plugin_enabled(plugin_name: str, enabled: bool) -> None:
    ensure_config_dir()
    data: dict = {}
    if CONFIG_FILE.exists():
        try:
            data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        except Exception:
            data = {}
    plugins_cfg = data.get("plugins_enabled")
    if not isinstance(plugins_cfg, dict):
        plugins_cfg = {}
    plugins_cfg[plugin_name] = enabled
    data["plugins_enabled"] = plugins_cfg
    CONFIG_FILE.write_text(json.dumps(data, indent=4), encoding="utf-8")


def get_barge_in_enabled() -> bool:
    """Return whether barge-in (interruption while speaking) is enabled. Default False."""
    return bool(load_api_keys().get("barge_in_enabled", False))


def save_barge_in_enabled(enabled: bool) -> None:
    ensure_config_dir()
    data = load_api_keys()
    data["barge_in_enabled"] = bool(enabled)
    CONFIG_FILE.write_text(json.dumps(data, indent=4), encoding="utf-8")


def get_urdu_voice() -> str:
    """Return the selected Urdu neural voice model (default: ur-PK-UzmaNeural)."""
    return load_api_keys().get("urdu_voice", "ur-PK-UzmaNeural")


def get_language_preference() -> str:
    """Return the language preference: 'auto', 'english', or 'urdu'."""
    return load_api_keys().get("language_preference", "auto")


def get_accessibility_mode() -> bool:
    """Return whether WCAG AAA Accessibility mode is enabled. Default False."""
    return bool(load_api_keys().get("accessibility_mode", False))


def save_accessibility_mode(enabled: bool) -> None:
    """Persist accessibility mode setting."""
    ensure_config_dir()
    data = load_api_keys()
    data["accessibility_mode"] = bool(enabled)
    CONFIG_FILE.write_text(json.dumps(data, indent=4), encoding="utf-8")



# ── Co-Worker Built-in Voices ───────────────────────────────────────────────
DEFAULT_COWORKER_VOICES = {
    "friday": "Aoede",
    "edith": "Kore",
    "homer": "Puck",
    "jocasta": "Fenrir",
}


def get_coworker_voices() -> dict[str, str]:
    """Return mapping of coworker_id -> voice_name, falling back to defaults."""
    cfg = load_api_keys().get("coworker_voices", {})
    if not isinstance(cfg, dict):
        cfg = {}
    result = dict(DEFAULT_COWORKER_VOICES)
    for cid, voice in cfg.items():
        if voice in AVAILABLE_VOICES:
            result[cid.lower().strip()] = voice
    return result


def get_coworker_voice(cid: str) -> str:
    """Return configured voice for a specific subordinate, or their default."""
    voices = get_coworker_voices()
    return voices.get(cid.lower().strip(), DEFAULT_COWORKER_VOICES.get(cid.lower().strip(), DEFAULT_VOICE))


def save_coworker_voice(cid: str, voice_name: str) -> None:
    """Persist a coworker's voice choice without altering others."""
    ensure_config_dir()
    data: dict = {}
    if CONFIG_FILE.exists():
        try:
            data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        except Exception:
            data = {}
    cv = data.get("coworker_voices")
    if not isinstance(cv, dict):
        cv = dict(DEFAULT_COWORKER_VOICES)
    v = (voice_name or "").strip()
    if v in AVAILABLE_VOICES:
        cv[cid.lower().strip()] = v
    data["coworker_voices"] = cv
    CONFIG_FILE.write_text(json.dumps(data, indent=4), encoding="utf-8")
