"""
actions/web_downloader.py — Universal Smart Web Downloader for JARVIS.

Handles intelligent downloading of ANY web content requested by the user:
1. Software & Apps (e.g. VLC, Chrome, VS Code, Git, Python, Discord, etc.)
   - Searches official sources, identifies the direct installer link (.exe / .msi),
     downloads it to the Downloads folder, and alerts the user.
2. Direct URLs (files, PDFs, ZIPs, EXEs, ISOs, documents, images, audio, video).
3. YouTube / Vimeo / Twitter / TikTok / Soundcloud videos & audios (via yt-dlp).
4. Media & Document search:
   - Images, Wallpapers, Photos (via DDGS)
   - PDFs, Papers, Books (via DDGS)
   - Audio, Songs, MP3s (via yt-dlp search)
"""
from __future__ import annotations

import mimetypes
import os
import re
import sys
import threading
import time
import urllib.parse
from pathlib import Path
from typing import Optional, Tuple

try:
    import requests
    _REQUESTS = True
except ImportError:
    _REQUESTS = False

try:
    import yt_dlp
    _YTDLP = True
except ImportError:
    _YTDLP = False

try:
    from bs4 import BeautifulSoup
    _BS4 = True
except ImportError:
    _BS4 = False


def _get_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent


def _get_downloads_dir() -> Path:
    p = Path.home() / "Downloads"
    p.mkdir(parents=True, exist_ok=True)
    return p


def _sanitize_filename(name: str) -> str:
    clean = re.sub(r'[\\/*?:"<>|]', "", name).strip()
    clean = re.sub(r"\s+", "_", clean)
    return clean[:80] or f"download_{int(time.time())}"


def _format_size(size_bytes: int) -> str:
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"


def _download_url(url: str, output_dir: Path, custom_filename: Optional[str] = None) -> Tuple[bool, str, Path | None]:
    """Download direct web link using requests with stream mode."""
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        )
    }
    try:
        # First check response headers
        head_resp = requests.head(url, headers=headers, timeout=15, allow_redirects=True)
        ct = head_resp.headers.get("content-type", "").lower()
        target_url = head_resp.url or url

        # If link serves an HTML redirect/mirror page rather than a binary:
        if "text/html" in ct or head_resp.status_code != 200:
            page_resp = requests.get(url, headers=headers, timeout=15)
            if _BS4:
                soup = BeautifulSoup(page_resp.text, "html.parser")
                mirrors = []
                for a in soup.find_all("a"):
                    href = a.get("href")
                    if not href:
                        continue
                    full_m = urllib.parse.urljoin(page_resp.url, href)
                    m_low = full_m.lower()
                    if (m_low.endswith(".exe") or m_low.endswith(".msi") or m_low.endswith(".zip")) and "videolan.org" not in m_low and "shrirangkahale" not in m_low:
                        mirrors.append(full_m)
                    elif ("mirror" in m_low or "click here" in a.text.lower()) and (".exe" in m_low or ".msi" in m_low):
                        mirrors.append(full_m)

                for m_url in mirrors:
                    try:
                        m_head = requests.head(m_url, headers=headers, timeout=10, allow_redirects=True)
                        if m_head.status_code == 200 and "text/html" not in m_head.headers.get("content-type", "").lower():
                            target_url = m_head.url or m_url
                            break
                    except Exception:
                        continue

        # Now download the real target stream
        with requests.get(target_url, stream=True, headers=headers, timeout=40, allow_redirects=True) as r:
            r.raise_for_status()

            # Determine filename
            fname = custom_filename
            if not fname:
                cd = r.headers.get("content-disposition", "")
                if "filename=" in cd:
                    matches = re.findall(r'filename\*?=(?:UTF-8\'\')?["\']?([^"\';\r\n]+)', cd)
                    if matches:
                        fname = urllib.parse.unquote(matches[0].strip())

            if not fname:
                parsed = urllib.parse.urlparse(r.url or target_url)
                cand = Path(parsed.path).name
                if cand and "." in cand:
                    fname = cand
                else:
                    c_type = r.headers.get("content-type", "").split(";")[0].strip()
                    ext = mimetypes.guess_extension(c_type) or ".bin"
                    fname = f"download_{int(time.time())}{ext}"

            fname = _sanitize_filename(fname)
            dest = output_dir / fname

            if dest.exists():
                stem = dest.stem
                suffix = dest.suffix
                dest = output_dir / f"{stem}_{int(time.time())}{suffix}"

            total_bytes = 0
            with open(dest, "wb") as f:
                for chunk in r.iter_content(chunk_size=65536):
                    if chunk:
                        f.write(chunk)
                        total_bytes += len(chunk)

            # Verification: If the downloaded file is tiny (< 50KB) and starts with HTML tags, it's not a real binary
            if dest.suffix.lower() in (".exe", ".msi", ".zip", ".iso") and total_bytes < 50000:
                try:
                    with open(dest, "rb") as check_f:
                        start_bytes = check_f.read(200).decode("utf-8", errors="ignore").lower()
                        if "<html" in start_bytes or "<!doctype html" in start_bytes:
                            dest.unlink(missing_ok=True)
                            return False, "Received HTML webpage instead of binary installer.", None
                except Exception:
                    pass

            size_str = _format_size(total_bytes)
            return True, f"Successfully downloaded '{dest.name}' ({size_str}) to your Downloads folder: {dest}", dest

    except Exception as e:
        return False, f"Direct download failed: {e}", None




def _search_and_download_software(query: str, output_dir: Path) -> Tuple[bool, str, Path | None]:
    """Finds official windows installer (.exe / .msi) for software like VLC, Chrome, Discord etc."""
    try:
        from ddgs import DDGS
        app_name = re.sub(r"(?i)\b(download|get|install|software|setup|pc|windows|for)\b", "", query).strip()
        if not app_name:
            app_name = query.strip()

        search_query = f"{app_name} official download windows installer .exe"
        with DDGS(timeout=15) as d:
            results = list(d.text(search_query, max_results=6))

        if not results:
            return False, f"No download results found for '{app_name}'.", None

        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            )
        }

        # Check search results for direct exe/msi download or landing pages
        for r in results:
            page_url = r.get("href") or r.get("url", "")
            if not page_url:
                continue

            low_url = page_url.lower()
            if low_url.endswith(".exe") or low_url.endswith(".msi") or low_url.endswith(".zip"):
                ok, msg, path = _download_url(page_url, output_dir)
                if ok:
                    return True, f"Downloaded {app_name} installer: {path.name}", path

            # Fetch page HTML and look for official download buttons/links
            try:
                resp = requests.get(page_url, headers=headers, timeout=12)
                if resp.status_code == 200:
                    if _BS4:
                        soup = BeautifulSoup(resp.text, "html.parser")
                        candidates = []
                        for a in soup.find_all("a"):
                            href = a.get("href")
                            if not href:
                                continue
                            full_url = urllib.parse.urljoin(page_url, href)
                            h_low = full_url.lower()
                            if h_low.endswith(".exe") or h_low.endswith(".msi"):
                                candidates.append((full_url, 10))
                            elif ("download" in h_low or "get" in h_low) and (".exe" in h_low or "win" in h_low or "setup" in h_low):
                                candidates.append((full_url, 5))

                        # Sort candidates by confidence
                        candidates.sort(key=lambda x: x[1], reverse=True)
                        for cand_url, _ in candidates[:3]:
                            ok, msg, path = _download_url(cand_url, output_dir)
                            if ok:
                                return True, f"Downloaded {app_name} installer: {path.name}", path
                    else:
                        exe_links = re.findall(r'href=[\'"](https?://[^\s\'"]+\.(?:exe|msi))[\'"]', resp.text, re.IGNORECASE)
                        for el in exe_links[:3]:
                            ok, msg, path = _download_url(el, output_dir)
                            if ok:
                                return True, f"Downloaded {app_name} installer: {path.name}", path

            except Exception:
                continue

        return False, f"Could not find direct automated installer link for '{app_name}'.", None
    except Exception as e:
        return False, f"Software download search failed: {e}", None


def _download_media_ytdlp(query_or_url: str, output_dir: Path, is_audio: bool = False) -> Tuple[bool, str, Path | None]:
    """Download video or audio using yt-dlp."""
    if not _YTDLP:
        return False, "yt-dlp is not installed.", None

    node_exe = Path(r"C:\Program Files\nodejs\node.exe")
    ydl_opts = {
        "outtmpl": str(output_dir / "%(title).60s.%(ext)s"),
        "quiet": True,
        "no_warnings": True,
        "windowsfilenames": True,
        "socket_timeout": 30,
    }

    if node_exe.exists():
        ydl_opts["js_runtimes"] = {"node": {"path": str(node_exe)}}
        ydl_opts["remote_components"] = ["ejs:github"]

    if is_audio:
        ydl_opts["format"] = "bestaudio/best"
        ydl_opts["postprocessors"] = [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192",
        }]
    else:
        ydl_opts["format"] = "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best"

    target = query_or_url
    if not (target.startswith("http://") or target.startswith("https://")):
        target = f"ytsearch1:{query_or_url}"

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(target, download=True)
            if "entries" in info and info["entries"]:
                info = info["entries"][0]
            title = info.get("title", "Media")
            ext = "mp3" if is_audio else info.get("ext", "mp4")
            return True, f"Downloaded '{title}' as {ext.upper()} into your Downloads folder.", output_dir
    except Exception as e:
        return False, f"Media download failed: {e}", None


def _search_and_download_image(query: str, output_dir: Path) -> Tuple[bool, str, Path | None]:
    """Search DuckDuckGo for high-res images and download the first valid match."""
    try:
        from ddgs import DDGS
        with DDGS(timeout=15) as d:
            results = list(d.images(query, max_results=5))
            if not results:
                return False, f"No images found for '{query}'.", None

            for item in results:
                img_url = item.get("image")
                if img_url and img_url.startswith("http"):
                    clean_name = _sanitize_filename(f"{query[:30]}_{int(time.time())}.jpg")
                    success, msg, path = _download_url(img_url, output_dir, clean_name)
                    if success:
                        return True, f"Downloaded image for '{query}' to your Downloads folder ({path.name}).", path

            return False, f"Could not download any image results for '{query}'.", None
    except Exception as e:
        return False, f"Image search and download failed: {e}", None


def _search_and_download_pdf(query: str, output_dir: Path) -> Tuple[bool, str, Path | None]:
    """Search DuckDuckGo for PDF/documents matching the query and download."""
    try:
        from ddgs import DDGS
        with DDGS(timeout=15) as d:
            results = list(d.text(f"{query} filetype:pdf", max_results=5))
            if not results:
                results = list(d.text(query, max_results=5))

            for r in results:
                url = r.get("href") or r.get("url", "")
                if url and (url.endswith(".pdf") or "pdf" in url.lower() or url.startswith("http")):
                    success, msg, path = _download_url(url, output_dir)
                    if success:
                        return True, f"Downloaded document for '{query}': {path.name}", path

            return False, f"No downloadable documents found for '{query}'.", None
    except Exception as e:
        return False, f"Document search failed: {e}", None


# ── Action entry point ───────────────────────────────────────────────────────
def web_downloader(
    parameters: dict,
    player=None,
    **kwargs
) -> str:
    """Intelligently downloads any software, file, video, audio, image, or document from the web."""
    params = parameters or {}
    url = (params.get("url") or "").strip()
    query = (params.get("query") or "").strip()
    category = (params.get("category") or "auto").lower().strip()
    custom_name = (params.get("filename") or "").strip() or None
    save_folder = params.get("save_folder")

    dest_dir = Path(save_folder).expanduser().resolve() if save_folder else _get_downloads_dir()
    dest_dir.mkdir(parents=True, exist_ok=True)

    target_desc = url or query
    if not target_desc:
        return "Please specify what you want to download (a URL, software name, video/song name, image topic, or document query)."

    if player and hasattr(player, "write_log"):
        player.write_log(f"[Download] Processing: {target_desc[:50]}...")

    # Safe logging without non-ASCII unicode arrows that break Windows CP1252 consoles
    print(f"[WebDownloader] >> category={category} url={url!r} query={query!r}")

    # Update CoWorker F.R.I.D.A.Y state to show activity
    try:
        from core.coworkers import get_manager
        get_manager().assign_task("friday", f"Downloading: {target_desc[:30]}")
    except Exception:
        pass

    # Play processing sound effect if available
    try:
        from core.sfx import play_sfx
        play_sfx("processing")
    except Exception:
        pass

    success = False
    result_msg = ""
    file_path = None

    # Case 1: Direct URL provided
    if url and (url.startswith("http://") or url.startswith("https://")):
        is_video_host = any(h in url.lower() for h in ("youtube.com", "youtu.be", "vimeo.com", "tiktok.com", "twitter.com", "x.com", "instagram.com/reel", "soundcloud.com"))
        
        if is_video_host or category in ("video", "audio", "music", "song"):
            is_audio = category in ("audio", "music", "song", "mp3")
            success, result_msg, file_path = _download_media_ytdlp(url, dest_dir, is_audio=is_audio)
        else:
            success, result_msg, file_path = _download_url(url, dest_dir, custom_name)

    # Case 2: Query-based download (User asks: "download vlc", "download video of X", etc.)
    else:
        search_term = query or url

        # Detect software / app keywords first
        software_keywords = ("software", "installer", "app", "application", "vlc", "chrome", "setup", "exe", "msi", "program", "tool", "player")
        is_software = category in ("software", "app", "installer") or any(w in search_term.lower() for w in software_keywords)

        if is_software and category not in ("video", "audio", "song", "image"):
            success, result_msg, file_path = _search_and_download_software(search_term, dest_dir)
            if not success:
                # Fallback to general download or media
                success, result_msg, file_path = _download_media_ytdlp(search_term, dest_dir, is_audio=False)

        elif category in ("video", "youtube", "clip"):
            success, result_msg, file_path = _download_media_ytdlp(search_term, dest_dir, is_audio=False)

        elif category in ("audio", "song", "music", "mp3", "podcast"):
            success, result_msg, file_path = _download_media_ytdlp(search_term, dest_dir, is_audio=True)

        elif category in ("image", "photo", "picture", "wallpaper"):
            success, result_msg, file_path = _search_and_download_image(search_term, dest_dir)

        elif category in ("pdf", "document", "book", "paper"):
            success, result_msg, file_path = _search_and_download_pdf(search_term, dest_dir)

        else:
            # Auto-detect intent from query keywords
            lower_q = search_term.lower()
            if any(w in lower_q for w in ("song", "music", "audio", "track", "mp3", "sound")):
                success, result_msg, file_path = _download_media_ytdlp(search_term, dest_dir, is_audio=True)
            elif any(w in lower_q for w in ("video", "trailer", "clip", "movie", "reel")):
                success, result_msg, file_path = _download_media_ytdlp(search_term, dest_dir, is_audio=False)
            elif any(w in lower_q for w in ("image", "photo", "picture", "wallpaper", "pic")):
                success, result_msg, file_path = _search_and_download_image(search_term, dest_dir)
            elif any(w in lower_q for w in ("pdf", "document", "book", "guide", "paper")):
                success, result_msg, file_path = _search_and_download_pdf(search_term, dest_dir)
            else:
                # Try software installer first
                success, result_msg, file_path = _search_and_download_software(search_term, dest_dir)
                if not success:
                    success, result_msg, file_path = _download_media_ytdlp(search_term, dest_dir, is_audio=False)
                if not success:
                    success, result_msg, file_path = _search_and_download_pdf(search_term, dest_dir)

    # Play completion sound
    try:
        from core.sfx import play_sfx
        play_sfx("success" if success else "alert")
    except Exception:
        pass

    # Update CoWorker F.R.I.D.A.Y status
    try:
        from core.coworkers import get_manager
        get_manager().complete_task("friday", result_msg[:40] if success else "Failed")
    except Exception:
        pass

    if player and hasattr(player, "write_log"):
        player.write_log(f"[Download] {result_msg[:70]}")

    print(f"[WebDownloader] [OK] {result_msg}")
    return result_msg


# ── Tool declaration (auto-discovered by core/action_loader.py) ──────────────
TOOL = {
    "name": "web_downloader",
    "description": (
        "THE ultimate tool for DOWNLOADING anything from the web. "
        "Use this tool whenever the user asks to: "
        "(1) Download software, apps, or programs (e.g. VLC, Chrome, VS Code, Discord, Python). "
        "(2) Download a file from any URL or web link. "
        "(3) Download a video from YouTube, Twitter, TikTok, or the web. "
        "(4) Download a song, music, MP3, audio, or podcast from the web. "
        "(5) Download images, photos, or wallpapers of any subject. "
        "(6) Download PDFs, documents, books, or papers. "
        "ALWAYS call this tool when the user says: 'download [X]', 'vlc download karo', "
        "'download video/song/image/pdf', or provides a link to download."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "query": {
                "type": "STRING",
                "description": "What to search for and download (e.g. 'vlc', 'chrome', 'Iron Man 4k wallpaper', 'Coldplay song', 'Python cheatsheet PDF')"
            },
            "url": {
                "type": "STRING",
                "description": "Direct URL or webpage link to download from, if provided."
            },
            "category": {
                "type": "STRING",
                "description": "auto | software | video | audio | image | pdf | file",
                "enum": ["auto", "software", "video", "audio", "image", "pdf", "file"]
            },
            "filename": {
                "type": "STRING",
                "description": "Optional custom filename to save as."
            },
            "save_folder": {
                "type": "STRING",
                "description": "Optional custom destination folder. Defaults to user's Downloads folder."
            }
        }
    },
    "handler": web_downloader,
}
