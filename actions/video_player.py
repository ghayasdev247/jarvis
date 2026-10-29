"""
actions/video_player.py
Plays local and online video/audio where the avatar normally is on the HUD.
Supports local media files, URLs, and YouTube with resilient fallbacks.
"""
from __future__ import annotations

import os
import re
import sys
import threading
import webbrowser
from pathlib import Path

_YT = re.compile(r"(youtube\.com/|youtu\.be/)", re.I)

_MEDIA_EXTS = {
    ".mp4", ".mkv", ".avi", ".webm", ".mov", ".wmv",
    ".m4a", ".mp3", ".wav", ".flac", ".aac", ".ogg"
}
_AUDIO_EXTS = {".m4a", ".mp3", ".wav", ".flac", ".aac", ".ogg"}

# Sequence counter to avoid playing stale requests
_open_lock = threading.Lock()
_open_seq = 0

# Music track history & queue for intelligent 'next' / 'skip'
_track_history: list[dict] = []
_current_track: dict = {"query": "", "title": "", "source": ""}
_track_queue: list[str] = []

def _find_next_related(current_query: str, current_title: str, history_titles: list[str]) -> str:
    """Finds the next fresh track by searching YouTube for related content."""
    try:
        import yt_dlp
    except Exception:
        return ""
    seed = (current_query or current_title or "trending music hits").strip()
    clean_seed = re.sub(r"https?://\S+|ytsearch\d*:", "", seed, flags=re.I).strip()
    if not clean_seed:
        clean_seed = "trending music hits"

    opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "extract_flat": True,
        "socket_timeout": 6,
    }
    norm_hist = [t.lower() for t in history_titles if t]
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            res = ydl.extract_info(f"ytsearch8:{clean_seed}", download=False)
            entries = (res or {}).get("entries") or []
            for e in entries:
                if not e:
                    continue
                t = (e.get("title") or "").strip()
                u = e.get("url") or e.get("webpage_url") or ""
                if t and not any(h in t.lower() for h in norm_hist):
                    return u or t
    except Exception:
        pass
    return ""


def _begin_open() -> int:
    global _open_seq
    with _open_lock:
        _open_seq += 1
        return _open_seq


def _still_wanted(token: int) -> bool:
    with _open_lock:
        return token == _open_seq


def _is_url(text: str) -> bool:
    return text.lower().startswith(("http://", "https://", "file://"))


def _is_audio(path_or_url: str) -> bool:
    try:
        suffix = Path(path_or_url.split("?")[0]).suffix.lower()
        return suffix in _AUDIO_EXTS
    except Exception:
        return False


def _find_local_media(text: str) -> str:
    """Finds an existing media file by exact path, relative path, or search across media directories."""
    raw = (text or "").strip().strip('"').strip("'")
    if not raw:
        return ""

    # 1. Exact path check
    try:
        p = Path(raw).expanduser().resolve()
        if p.exists() and p.is_file():
            return str(p)
    except Exception:
        pass

    # 2. Check known roots
    candidates_dirs = [
        Path("D:/"),
        Path.home() / "Videos",
        Path.home() / "Downloads",
        Path.home() / "Music",
        Path.home() / "Desktop",
        Path("C:/"),
    ]

    # Try direct join
    for folder in candidates_dirs:
        try:
            if folder.exists():
                joined = folder / raw
                if joined.exists() and joined.is_file():
                    return str(joined)
        except Exception:
            continue

    # 3. Fuzzy match: Search for files containing key terms
    keywords = [w.lower() for w in re.split(r"[\s_\-\.]+", raw) if len(w) > 1]
    if not keywords:
        return ""

    for folder in candidates_dirs:
        try:
            if not folder.exists() or not folder.is_dir():
                continue
            for item in folder.iterdir():
                try:
                    if item.is_file() and item.suffix.lower() in _MEDIA_EXTS:
                        item_name_lower = item.name.lower()
                        # If all keywords match
                        if all(k in item_name_lower for k in keywords):
                            return str(item)
                except Exception:
                    continue
        except Exception:
            continue

    # Try any keyword match if all didn't match
    if len(keywords) > 1:
        for folder in candidates_dirs:
            try:
                if not folder.exists() or not folder.is_dir():
                    continue
                for item in folder.iterdir():
                    try:
                        if item.is_file() and item.suffix.lower() in _MEDIA_EXTS:
                            item_name_lower = item.name.lower()
                            if any(k in item_name_lower for k in keywords if len(k) > 3):
                                return str(item)
                    except Exception:
                        continue
            except Exception:
                continue

    return ""


def _resolve_youtube(url_or_query: str, target_quality: str | None = None) -> tuple[str, str, str, str]:
    """Resolves YouTube stream URLs using yt-dlp with clean error handling and selectable resolution."""
    try:
        import yt_dlp
    except Exception:
        return "", "", "", (
            "yt-dlp is not installed. Run: pip install yt-dlp"
        )

    # Determine resolution limit
    from memory.config_manager import get_player_quality
    qual = (target_quality or get_player_quality() or "144p").strip().lower()
    height_cap = 144
    if qual in ("144p", "144"):
        height_cap = 144
    elif qual in ("240p", "240"):
        height_cap = 240
    elif qual in ("360p", "360"):
        height_cap = 360
    elif qual in ("480p", "480"):
        height_cap = 480
    elif qual in ("720p", "720"):
        height_cap = 720
    elif qual in ("1080p", "1080"):
        height_cap = 1080
    elif qual in ("best", "max"):
        height_cap = 9999

    if _YT.search(url_or_query) or url_or_query.startswith("ytsearch"):
        query = url_or_query
    else:
        query = f"ytsearch1:{url_or_query}"
    opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "noplaylist": True,
        "socket_timeout": 10,
        "nocheckcertificate": True,
    }

    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(query, download=False)
        if info and info.get("entries"):
            info = info["entries"][0]
        if not info:
            return "", "", "", "nothing was found for that."
    except Exception as e:
        err_msg = str(e)
        if "10054" in err_msg or "Connection aborted" in err_msg or "Connection reset" in err_msg:
            return "", "", "", "network connection to YouTube was reset/blocked"
        if "429" in err_msg or "Too Many Requests" in err_msg:
            return "", "", "", "YouTube rate limit encountered"
        return "", "", "", f"could not resolve video stream: {err_msg[:80]}"

    formats = [
        f for f in (info.get("formats") or [])
        if str(f.get("protocol") or "").startswith("http") and f.get("url")
    ]

    def has(f, key):
        return f.get(key) not in (None, "none")

    def is_h264(f):
        v = str(f.get("vcodec") or "").lower()
        return "avc1" in v or "h264" in v

    def is_aac(f):
        a = str(f.get("acodec") or "").lower()
        return "mp4a" in a or "aac" in a or f.get("ext") == "m4a"

    def best(candidates):
        if not candidates:
            return None
        return max(
            candidates,
            key=lambda f: (
                f.get("language_preference") or 0,
                f.get("tbr") or 0,
            ),
        )

    # 1. Combined H.264 stream at or below requested height
    combined = best([
        f for f in formats
        if has(f, "vcodec") and has(f, "acodec") and is_h264(f)
        and (f.get("height") or 0) <= height_cap
    ])
    if combined:
        return combined["url"], "", info.get("title") or "", ""

    # 2. Split video stream: strictly prefer native H.264 (avc1) compatible with Windows Media Foundation
    video = best([
        f for f in formats
        if has(f, "vcodec") and not has(f, "acodec") and is_h264(f)
        and (f.get("height") or 0) <= height_cap
    ])
    if not video:
        # Fallback to lowest available H.264 if none <= height_cap (e.g. 240p or 360p H.264)
        h264_all = [
            f for f in formats
            if has(f, "vcodec") and not has(f, "acodec") and is_h264(f)
        ]
        if h264_all:
            video = min(h264_all, key=lambda f: f.get("height") or 9999)

    if not video:
        # Fallback to any video at or below height cap if no H.264 available
        video = best([
            f for f in formats
            if has(f, "vcodec") and not has(f, "acodec")
            and (f.get("height") or 0) <= height_cap
        ])
    if not video:
        # Absolute fallback to smallest available video stream
        video = min(
            [f for f in formats if has(f, "vcodec") and not has(f, "acodec")],
            key=lambda f: f.get("height") or 9999,
            default=None
        )

    # Audio stream: strictly prefer AAC / M4A (mp4a) compatible with Windows Media Foundation
    audio = best([
        f for f in formats
        if has(f, "acodec") and not has(f, "vcodec") and is_aac(f)
    ])
    if not audio:
        audio = best([f for f in formats if has(f, "acodec") and not has(f, "vcodec")])

    if not video:
        # If still no split video, check any combined stream
        any_combined = best([f for f in formats if has(f, "vcodec") and has(f, "acodec")])
        if any_combined:
            return any_combined["url"], "", info.get("title") or "", ""
        return "", "", "", "no playable stream was offered for that video."

    return video["url"], (audio or {}).get("url", ""), info.get("title") or "", ""


def _search_page(query: str) -> str:
    from urllib.parse import quote_plus
    return f"https://www.youtube.com/results?search_query={quote_plus(query)}"


def video_player(
    parameters: dict = None,
    response=None,
    player=None,
    session_memory=None,
) -> str:
    params = parameters or {}

    # Handle parameter name variations
    action = (params.get("action") or "play").strip().lower()
    source = (
        params.get("source")
        or params.get("query")
        or params.get("video")
        or params.get("url")
        or params.get("name")
        or params.get("title")
        or ""
    ).strip()
    quality = (params.get("quality") or params.get("resolution") or "").strip().lower()

    # Action alias mapping
    if action in ("start", "open", "run", "resume"):
        action = "play"
    elif action in ("pause", "exit"):
        action = "stop"
    elif action in ("sound", "sound_on"):
        action = "unmute"
    elif action in ("set_quality", "quality", "change_quality", "resolution"):
        action = "quality"
    elif action in ("next", "skip", "forward"):
        action = "next"
    elif action in ("previous", "prev", "back"):
        action = "previous"

    # ---- quality ----------------------------------------------------------
    if action == "quality":
        from memory.config_manager import save_player_quality, get_player_quality
        target_q = quality or source or "144p"
        save_player_quality(target_q)
        active_q = get_player_quality()
        return f"Video player quality set to {active_q}."

    # ---- stop -------------------------------------------------------------
    if action in ("stop", "close", "hide"):
        _begin_open()
        if player:
            was_opening = not player.video_is_playing()
            player.stop_video()
            if was_opening:
                return "Stopped it before it opened."
            return "Closed the video."
        return "Video playback stopped."

    # ---- sound / mute -----------------------------------------------------
    if action in ("mute", "unmute", "sound_on", "sound_off"):
        if player:
            if not player.video_is_playing():
                return "Nothing is playing right now."
            muted = action in ("mute", "sound_off")
            player.set_video_muted(muted)
            return "Muted the video." if muted else "Turned the video sound on."
        return f"{action.capitalize()} executed."

    # ---- next / skip ------------------------------------------------------
    if action == "next":
        target = source or ""
        if not target and _track_queue:
            target = _track_queue.pop(0)
        if not target:
            last_q = _current_track.get("query") or _current_track.get("title") or "music"
            hist = [t.get("title", "") for t in _track_history if t.get("title")]
            if _current_track.get("title"):
                hist.append(_current_track["title"])
            target = _find_next_related(last_q, _current_track.get("title", ""), hist) or f"{last_q} next song"
        source = target
        action = "play"

    # ---- previous ---------------------------------------------------------
    if action == "previous":
        if len(_track_history) >= 2:
            _track_history.pop()  # remove current
            prev = _track_history.pop()
            source = prev.get("source") or prev.get("title") or prev.get("query")
            action = "play"
        else:
            return "No previous track in history."

    # ---- play -------------------------------------------------------------
    if not source:
        return "What video or audio file should I play?"

    _current_track["query"] = source
    _current_track["source"] = source

    # Check for requested mute status
    requested_muted = params.get("muted")

    # 1. Local file check (including smart search)
    local = _find_local_media(source)
    if local:
        is_aud = _is_audio(local)
        # Default unmuted (sound ON) unless user explicitly specified muted=True
        should_mute = bool(requested_muted) if requested_muted is not None else False

        if player:
            player.show_video(local, Path(local).name, muted=should_mute)
            mute_status = "muted" if should_mute else "with sound"
            return f"Playing {Path(local).name} on the display ({mute_status})."
        else:
            # Headless fallback: open with system media player
            try:
                os.startfile(local)
                return f"Playing {Path(local).name} in system media player."
            except Exception as e:
                return f"Opened {Path(local).name}: {e}"

    # 2. Direct media URL
    if _is_url(source) and not _YT.search(source):
        is_aud = _is_audio(source)
        should_mute = bool(requested_muted) if requested_muted is not None else (not is_aud)
        title = source.rsplit("/", 1)[-1][:44]

        if player:
            player.show_video(source, title, muted=should_mute)
            return f"Playing {title} on the display."
        else:
            webbrowser.open(source)
            return f"Opened media URL in browser: {source}"

    # 3. Headless check for YouTube
    if player is None:
        target = source if _YT.search(source) else _search_page(source)
        webbrowser.open(target)
        return f"Opened video in browser: {target}"

    # 4. Asynchronous YouTube / Web resolution
    token = _begin_open()
    threading.Thread(
        target=_play_youtube,
        args=(player, source, token, requested_muted, quality),
        daemon=True,
        name="video-open",
    ).start()

    return f"status=opening source={source}"


def _play_youtube(player, source: str, token: int, requested_muted: bool | None = None, target_quality: str | None = None) -> None:
    """Resolves and plays online video stream in background thread."""
    try:
        url, audio_url, title, err = _resolve_youtube(source, target_quality=target_quality)
    except Exception as e:
        url = audio_url = title = ""
        err = str(e)

    if not _still_wanted(token):
        return

    if url:
        try:
            should_mute = False if requested_muted is None else bool(requested_muted)
            player.show_video(url, title or source, muted=should_mute, audio_source=audio_url)
            _current_track["title"] = title or source
            _current_track["source"] = source
            _current_track["query"] = source
            _track_history.append({"title": title or source, "source": source, "query": source})
            if len(_track_history) > 50:
                _track_history.pop(0)
            return
        except Exception as e:
            err = str(e)

    # Resolution failed: Fall back to browser
    page = source if _YT.search(source) else _search_page(source)
    try:
        webbrowser.open(page)
    except Exception:
        pass

    clean_err = err or "Stream unavailable"
    _say(
        player,
        f"Tell the user, in one short sentence in their own language: "
        f"'{source}' could not be streamed into the HUD ({clean_err}), "
        f"so it has been opened in the browser instead."
    )


def _say(player, instruction: str) -> None:
    if player is not None and hasattr(player, "request_say"):
        try:
            player.request_say(instruction)
        except Exception:
            pass


# ── Tool declaration (auto-discovered by core/action_loader.py) ──────────────
TOOL = {
    "name": "video_player",
    "description": (
        "Plays videos or audio files on the assistant's HUD display, or opens them. "
        "Supports playing local video/music files (e.g. from D: or Videos/Downloads/Music), "
        "direct media URLs, or online videos. Can stop, pause, mute, unmute, or change video quality/resolution (e.g. '144p'). "
        "Use whenever the user wants to play, watch, listen to, stop media, or change playback quality."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {
                "type": "STRING",
                "description": "'play', 'next' / 'skip' for next song, 'previous' for back, 'stop' to pause/close, 'unmute', 'mute', 'quality'.",
                "enum": ["play", "stop", "next", "skip", "previous", "mute", "unmute", "quality"],
            },
            "source": {
                "type": "STRING",
                "description": "Local video/music file name or path, direct media URL, video title/query to play, or resolution e.g. '144p'.",
            },
            "quality": {
                "type": "STRING",
                "description": "Video quality/resolution limit: '144p', '240p', '360p', '480p', '720p', '1080p'.",
            },
            "muted": {
                "type": "BOOLEAN",
                "description": "Whether to start muted (default True for videos, False for music/audio).",
            },
        },
        "required": ["action"],
    },
    "handler": video_player,
}
