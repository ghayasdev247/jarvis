"""
actions/youtube_downloader.py
High-Definition YouTube Video and Audio Downloader for JARVIS via yt-dlp.

Capabilities:
- Download YouTube videos directly as MP4 (1080p, 720p, 480p, or best quality).
- Extract and download audio-only tracks as M4A or MP3.
- Accepts direct YouTube video URLs or search queries (auto-resolves first result).
- Automatically discovers local ffmpeg executable for high-quality audio/video muxing.
- Saves files directly to user's Downloads or specified directory.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional
from urllib.parse import quote_plus


def _find_ffmpeg() -> Optional[str]:
    """Finds ffmpeg binary on the system."""
    which_ffmpeg = shutil.which("ffmpeg")
    if which_ffmpeg:
        return which_ffmpeg

    # Common Windows installation locations
    candidates = [
        Path(r"C:\Program Files (x86)\accessible youtube downloader pro\ffmpeg.exe"),
        Path(r"C:\Renova Games\RenovaMusic\lib\ffmpeg.exe"),
        Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "ffmpeg" / "bin" / "ffmpeg.exe",
        Path(os.environ.get("ProgramFiles", "")) / "ffmpeg" / "bin" / "ffmpeg.exe",
    ]
    for c in candidates:
        if c.exists():
            return str(c)
    return None


def _get_default_download_dir() -> Path:
    """Returns user's Downloads folder or falls back to JARVIS downloads."""
    downloads = Path.home() / "Downloads"
    if not downloads.exists():
        downloads = Path(__file__).resolve().parent.parent / "downloads"
    downloads.mkdir(parents=True, exist_ok=True)
    return downloads


def _extract_video_url(query_or_url: str) -> str:
    """Returns valid URL or searches for one."""
    s = query_or_url.strip()
    if re.match(r"^https?://(www\.)?(youtube\.com|youtu\.be)/", s):
        return s

    # Fallback to scraping first search match
    try:
        import requests
        search_url = f"https://www.youtube.com/results?search_query={quote_plus(s)}&sp=EgIQAQ%3D%3D"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0.0.0 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9",
        }
        r = requests.get(search_url, headers=headers, timeout=10)
        vids = re.findall(r'"videoId":"([A-Za-z0-9_-]{11})"', r.text)
        if vids:
            return f"https://www.youtube.com/watch?v={vids[0]}"
    except Exception:
        pass

    # yt-dlp search prefix format
    return f"ytsearch1:{s}"


def download_youtube(
    url_or_query: str,
    format_type: str = "video",
    quality: str = "best",
    output_dir: Optional[str] = None,
    player=None,
    speak=None,
) -> str:
    """Downloads YouTube video or audio using yt-dlp."""
    if not url_or_query:
        return "Please provide a YouTube video URL or search query to download."

    dest_dir = Path(output_dir) if output_dir else _get_default_download_dir()
    dest_dir.mkdir(parents=True, exist_ok=True)

    target_url = _extract_video_url(url_or_query)
    is_audio_only = format_type.lower() in ("audio", "mp3", "m4a", "music")

    ffmpeg_path = _find_ffmpeg()

    try:
        import yt_dlp
    except ImportError:
        return "yt-dlp is not installed. Please install it using 'pip install yt-dlp'."

    # Construct format specifier based on quality and availability of ffmpeg
    if is_audio_only:
        fmt = "bestaudio[ext=m4a]/bestaudio/best"
        out_tmpl = str(dest_dir / "%(title)s [%(id)s].%(ext)s")
    else:
        if quality in ("1080p", "1080"):
            fmt = "bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[height<=1080][ext=mp4]/best"
        elif quality in ("720p", "720"):
            fmt = "bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[height<=720][ext=mp4]/best"
        elif quality in ("480p", "480"):
            fmt = "bestvideo[height<=480][ext=mp4]+bestaudio[ext=m4a]/best[height<=480][ext=mp4]/best"
        else:
            fmt = "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best"
        out_tmpl = str(dest_dir / "%(title)s [%(id)s].%(ext)s")

    ydl_opts = {
        "outtmpl": out_tmpl,
        "format": fmt,
        "quiet": True,
        "no_warnings": True,
        "ignoreerrors": False,
        "nocheckcertificate": True,
    }

    if ffmpeg_path:
        ydl_opts["ffmpeg_location"] = ffmpeg_path

    log_msg = f"[YouTube Downloader] Starting download: {url_or_query} -> {dest_dir}"
    print(log_msg)
    if player:
        try:
            player.write_log(log_msg)
        except Exception:
            pass

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(target_url, download=True)
            if "entries" in info:
                info = info["entries"][0]  # If ytsearch was used

            title = info.get("title", "Video")
            duration = info.get("duration", 0)
            mins, secs = divmod(duration, 60)
            filesize = info.get("filesize") or info.get("filesize_approx") or 0
            size_mb = f"{filesize / (1024 * 1024):.1f} MB" if filesize else "Unknown size"

            filename = ydl.prepare_filename(info)
            # If merged, file might end with mp4 or mkv
            downloaded_file = Path(filename)
            if not downloaded_file.exists():
                stem = downloaded_file.stem
                for f in dest_dir.glob(f"{stem}*"):
                    downloaded_file = f
                    break

            result_msg = (
                f"Successfully downloaded '{title}' ({mins}m {secs}s, {size_mb}).\n"
                f"Saved to: {downloaded_file}"
            )
            print(f"[YouTube Downloader] Completed: {downloaded_file}")
            if player:
                try:
                    player.write_log(f"JARVIS: Downloaded {title}")
                except Exception:
                    pass
            if speak:
                speak(f"Download complete, sir. Saved {title} to your Downloads.")

            return result_msg
    except Exception as e:
        err_msg = f"Failed to download YouTube video: {e}"
        print(f"[YouTube Downloader] Error: {err_msg}")
        return err_msg


def youtube_downloader_action(parameters: dict, player=None, speak=None) -> str:
    params = parameters or {}
    url_or_query = params.get("url") or params.get("query") or params.get("video") or ""
    format_type = params.get("format", "video")
    quality = params.get("quality", "best")
    output_dir = params.get("output_dir")

    return download_youtube(
        url_or_query=url_or_query,
        format_type=format_type,
        quality=quality,
        output_dir=output_dir,
        player=player,
        speak=speak,
    )


TOOL = {
    "name": "youtube_downloader",
    "description": (
        "Downloads YouTube videos and audio tracks to local disk using yt-dlp: download high-definition "
        "MP4 video (1080p, 720p, 480p, or best available) or audio-only (M4A/MP3) by providing a video URL "
        "or search keywords. Files are saved directly into the user's Downloads folder."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "url": {
                "type": "STRING",
                "description": "YouTube video URL (e.g. 'https://www.youtube.com/watch?v=...') or search query.",
            },
            "query": {
                "type": "STRING",
                "description": "Search query if no direct URL is provided (e.g. 'Rick Astley Never Gonna Give You Up').",
            },
            "format": {
                "type": "STRING",
                "description": "'video' (default, downloads MP4) or 'audio' (extracts audio only).",
            },
            "quality": {
                "type": "STRING",
                "description": "Video resolution quality: 'best', '1080p', '720p', '480p', '360p'.",
            },
            "output_dir": {
                "type": "STRING",
                "description": "Optional custom folder path to save the downloaded file.",
            },
        },
        "required": [],
    },
    "handler": youtube_downloader_action,
}
