"""
actions/data_collector.py — Web data collector for articles, videos, images, and audios.

Searches the web across multiple categories (articles, videos, images, audios),
extracts and synthesizes key data, and compiles a comprehensive dossier saved
as a clean .txt file on the user's Desktop or custom path.
"""
from __future__ import annotations

import datetime
import json
import os
import re
import sys
import time
from pathlib import Path

# Base dir and API config
def _get_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent

BASE_DIR = _get_base_dir()
API_CONFIG_PATH = BASE_DIR / "config" / "api_keys.json"


def _get_api_key() -> str:
    try:
        with open(API_CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f).get("gemini_api_key", "")
    except Exception:
        return ""


def _sanitize_filename(name: str) -> str:
    clean = re.sub(r'[\\/*?:"<>|]', "", name).strip()
    clean = re.sub(r"\s+", "_", clean)
    return clean[:40] or "web_data"


def _get_articles(query: str, max_results: int = 5) -> list[dict]:
    """Search for relevant articles and news reports."""
    results = []
    try:
        from ddgs import DDGS
        with DDGS(timeout=12) as d:
            # Try news first for fresh articles
            try:
                for r in d.news(query, max_results=max_results):
                    results.append({
                        "title": r.get("title", "").strip(),
                        "snippet": r.get("body", "").strip(),
                        "url": r.get("url", "").strip(),
                        "source": r.get("source", "").strip() or "News",
                        "date": r.get("date", "").strip(),
                    })
            except Exception:
                pass
            
            # If news yielded fewer than needed, backfill with text search
            if len(results) < max_results:
                needed = max_results - len(results)
                for r in d.text(f"{query} articles guide overview", max_results=needed):
                    results.append({
                        "title": r.get("title", "").strip(),
                        "snippet": r.get("body", "").strip(),
                        "url": r.get("href", "").strip(),
                        "source": "Web Article",
                        "date": "",
                    })
    except Exception as e:
        print(f"[DataCollector] ⚠️ Article search fallback error: {e}")

    return results[:max_results]


def _get_videos(query: str, max_results: int = 5) -> list[dict]:
    """Search for video links (YouTube and web)."""
    videos = []

    # Method 1: yt-dlp flat search (super fast and exact)
    try:
        import yt_dlp
        opts = {
            "quiet": True,
            "no_warnings": True,
            "skip_download": True,
            "extract_flat": True,
        }
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(f"ytsearch{max_results}:{query}", download=False)
            for entry in info.get("entries", []):
                vid_id = entry.get("id", "")
                url = entry.get("url") or (f"https://www.youtube.com/watch?v={vid_id}" if vid_id else "")
                if url:
                    videos.append({
                        "title": entry.get("title", "YouTube Video").strip(),
                        "url": url,
                        "channel": entry.get("uploader", "") or entry.get("channel", "YouTube"),
                        "duration": str(entry.get("duration", "")),
                    })
    except Exception as e:
        print(f"[DataCollector] ⚠️ yt-dlp video search error: {e}")

    # Method 2: DDGS videos search if needed
    if len(videos) < max_results:
        try:
            from ddgs import DDGS
            with DDGS(timeout=12) as d:
                for r in d.videos(query, max_results=max_results - len(videos)):
                    videos.append({
                        "title": r.get("title", "Video").strip(),
                        "url": r.get("content", "").strip(),
                        "channel": r.get("publisher", "").strip() or "Web Video",
                        "duration": r.get("duration", "").strip(),
                    })
        except Exception:
            pass

    return videos[:max_results]


def _get_images(query: str, max_results: int = 5) -> list[dict]:
    """Search for relevant images with titles and direct URLs."""
    images = []
    try:
        from ddgs import DDGS
        with DDGS(timeout=12) as d:
            for r in d.images(query, max_results=max_results):
                img_url = r.get("image", "").strip()
                if img_url:
                    images.append({
                        "title": r.get("title", "Image").strip(),
                        "url": img_url,
                        "source": r.get("url", "").strip(),
                        "thumbnail": r.get("thumbnail", "").strip(),
                        "dimensions": f"{r.get('width', '')}x{r.get('height', '')}",
                    })
    except Exception as e:
        print(f"[DataCollector] ⚠️ Image search error: {e}")

    return images[:max_results]


def _get_audios(query: str, max_results: int = 5) -> list[dict]:
    """Search for podcasts, audio tracks, and audio streaming sources."""
    audios = []
    try:
        from ddgs import DDGS
        with DDGS(timeout=12) as d:
            # Query podcasts and audio tracks
            for r in d.text(f"{query} podcast audio track episode soundcloud spotify", max_results=max_results):
                audios.append({
                    "title": r.get("title", "Audio / Podcast").strip(),
                    "snippet": r.get("body", "").strip(),
                    "url": r.get("href", "").strip(),
                    "platform": "Podcast / Audio Stream",
                })
    except Exception as e:
        print(f"[DataCollector] ⚠️ Audio search error: {e}")

    return audios[:max_results]


def _synthesize_overview(topic: str) -> str:
    """Generate an informative topic overview and key points via Gemini."""
    try:
        from core import gemini
        prompt = (
            f"Provide an authoritative, clear, and well-structured executive summary "
            f"about '{topic}'. Highlight key facts, history, importance, and future trends. "
            f"Keep it comprehensive yet concise (3-4 paragraphs or clear bullet points)."
        )
        resp = gemini.call(prompt, tier=gemini.FAST, timeout_ms=25_000)
        if resp and resp.text:
            return resp.text.strip()
    except Exception as e:
        print(f"[DataCollector] Overview generation fallback: {e}")

    return f"Comprehensive research and media compilation on {topic}."


def data_collector(
    parameters: dict,
    response=None,
    player=None,
    session_memory=None,
) -> str:
    """
    Collects web articles, videos, images, and audio sources on a topic,
    and compiles everything into a clean text (.txt) file.
    """
    params = parameters or {}
    topic = (params.get("topic") or params.get("query") or "").strip()
    if not topic:
        return "Please specify a topic or subject to collect data on."

    categories = params.get("categories")
    if not categories or not isinstance(categories, list):
        categories = ["articles", "videos", "images", "audios"]
    else:
        categories = [c.lower().strip() for c in categories]

    max_items = int(params.get("max_items_per_category") or 5)
    max_items = max(2, min(max_items, 12))
    save_file = params.get("save_to_file", True)

    if player:
        player.write_log(f"[DataCollector] Gathering data on: '{topic}'")

    print(f"[DataCollector] ▶ Collecting for '{topic}' categories={categories}")

    # 1. Gather data across categories
    articles = _get_articles(topic, max_items) if "articles" in categories else []
    videos = _get_videos(topic, max_items) if "videos" in categories else []
    images = _get_images(topic, max_items) if "images" in categories else []
    audios = _get_audios(topic, max_items) if "audios" in categories else []

    # 2. Synthesize overview
    overview = _synthesize_overview(topic)

    timestamp_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    file_timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

    # 3. Format complete text dossier
    lines = []
    lines.append("=" * 80)
    lines.append(f"JARVIS RESEARCH & DATA COLLECTION DOSSIER")
    lines.append(f"TOPIC: {topic.upper()}")
    lines.append(f"DATE COLLECTED: {timestamp_str}")
    lines.append("=" * 80)
    lines.append("")

    lines.append("── [1. EXECUTIVE SUMMARY & OVERVIEW] ────────────────────────────")
    lines.append(overview)
    lines.append("")

    if articles:
        lines.append("── [2. WEB ARTICLES & PUBLICATIONS] ─────────────────────────────")
        for i, a in enumerate(articles, 1):
            lines.append(f"{i}. {a['title']}")
            if a.get("source"):
                lines.append(f"   Source: {a['source']}" + (f" ({a['date']})" if a.get("date") else ""))
            if a.get("snippet"):
                lines.append(f"   Summary: {a['snippet']}")
            if a.get("url"):
                lines.append(f"   Link: {a['url']}")
            lines.append("")

    if videos:
        lines.append("── [3. VIDEOS & PRESENTATIONS] ──────────────────────────────────")
        for i, v in enumerate(videos, 1):
            lines.append(f"{i}. {v['title']}")
            if v.get("channel"):
                lines.append(f"   Channel/Platform: {v['channel']}")
            if v.get("url"):
                lines.append(f"   Watch URL: {v['url']}")
            lines.append("")

    if images:
        lines.append("── [4. IMAGES & VISUAL SOURCES] ─────────────────────────────────")
        for i, img in enumerate(images, 1):
            lines.append(f"{i}. {img['title']}")
            if img.get("dimensions"):
                lines.append(f"   Resolution: {img['dimensions']}")
            if img.get("url"):
                lines.append(f"   Direct Image URL: {img['url']}")
            if img.get("source"):
                lines.append(f"   Source Page: {img['source']}")
            lines.append("")

    if audios:
        lines.append("── [5. AUDIOS & PODCASTS] ───────────────────────────────────────")
        for i, au in enumerate(audios, 1):
            lines.append(f"{i}. {au['title']}")
            if au.get("snippet"):
                lines.append(f"   Details: {au['snippet']}")
            if au.get("url"):
                lines.append(f"   Listen Link: {au['url']}")
            lines.append("")

    lines.append("=" * 80)
    lines.append(f"Collected by JARVIS (Mark LV) Autonomous Data System.")
    lines.append("=" * 80)
    dossier_text = "\n".join(lines)

    # 4. Save to file
    out_path_str = params.get("file_path")
    if out_path_str:
        out_path = Path(out_path_str).expanduser().resolve()
    else:
        desktop_dir = Path.home() / "Desktop"
        clean_topic = _sanitize_filename(topic)
        out_path = desktop_dir / f"Collected_Data_{clean_topic}_{file_timestamp}.txt"

    if save_file:
        try:
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(dossier_text, encoding="utf-8")
            saved_msg = f"Saved full report to: {out_path.name} on your Desktop."
            print(f"[DataCollector] ✅ Saved report to {out_path}")
        except Exception as e:
            saved_msg = f"Could not save file to disk: {e}."
    else:
        saved_msg = "Data collected in memory."

    summary_spoken = (
        f"Sir, I have collected web data on '{topic}': "
        f"{len(articles)} articles, {len(videos)} videos, "
        f"{len(images)} images, and {len(audios)} audio sources. "
        f"{saved_msg}"
    )

    if player:
        player.write_log(f"JARVIS: {summary_spoken}")

    return summary_spoken


# ── Tool declaration (auto-discovered by core/action_loader.py) ──────────────
TOOL = {
    "name": "data_collector",
    "description": (
        "Collects comprehensive web research and multimedia data on ANY topic. "
        "Searches the web for: (1) Web articles & news, (2) Videos & YouTube links, "
        "(3) Direct image links & galleries, and (4) Audio tracks & podcasts. "
        "Synthesizes an executive summary and saves the complete organized dossier "
        "into a clean text (.txt) file on the Desktop. Use whenever the user asks to: "
        "'search web for audios, videos, images, articles and save to a txt file', "
        "'collect data on [topic]', 'gather research on [topic] into a text file', "
        "or create a data collection file about any subject."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "topic": {
                "type": "STRING",
                "description": "The topic, subject, or question to search and collect data on."
            },
            "categories": {
                "type": "ARRAY",
                "items": {"type": "STRING"},
                "description": "Categories to collect: 'articles', 'videos', 'images', 'audios'. Defaults to all four."
            },
            "save_to_file": {
                "type": "BOOLEAN",
                "description": "Whether to save the collected dossier to a .txt file (default: true)."
            },
            "file_path": {
                "type": "STRING",
                "description": "Optional custom file path for the .txt file. Defaults to Desktop."
            },
            "max_items_per_category": {
                "type": "INTEGER",
                "description": "Maximum number of items to gather for each category (default: 5)."
            }
        },
        "required": ["topic"]
    },
    "handler": data_collector,
}
