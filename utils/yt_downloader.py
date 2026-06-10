"""YouTube downloader wrapper using yt-dlp (no cookies)"""

import os
import logging
import yt_dlp
from pathlib import Path

logger = logging.getLogger(__name__)


def is_youtube(url: str) -> bool:
    return any(d in url.lower() for d in ("youtube.com", "youtu.be"))


def get_info(url: str) -> dict | None:
    
    try:
        with yt_dlp.YoutubeDL({
            "quiet": True,
            "no_warnings": True,
            "noplaylist": True,
            "cookiesfrombrowser": None,
        }) as ydl:
            info = ydl.extract_info(url, download=False)

            resolutions = {}
            for f in info.get("formats", []):
                if f.get("vcodec") != "none" and f.get("height"):
                    h = f["height"]
                    if h not in resolutions:
                        resolutions[h] = {
                            "format_id": f"{f['format_id']}+bestaudio/best",
                            "height": h,
                            "size": f.get("filesize") or f.get("filesize_approx", 0),
                        }

            return {
                "title": info.get("title", "Unknown"),
                "uploader": info.get("uploader", "Unknown"),
                "duration": info.get("duration", 0),
                "url": url,
                "formats": sorted(resolutions.values(), key=lambda x: x["height"]),
            }
    except Exception as e:
        logger.warning(f"get_info failed: {e}")
        return None


def download(
    url: str,
    out_dir: str = "downloads",
    fmt_type: str = "mp4",
    format_id: str | None = None,
    max_mb: int = 1900,
) -> Path | None:

    os.makedirs(out_dir, exist_ok=True)

    if fmt_type == "mp3":
        opts = {
            "outtmpl": f"{out_dir}/%(title).80s_%(id)s.%(ext)s",
            "format": "bestaudio/best",
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }],
            "quiet": True,
            "no_warnings": True,
            "noplaylist": True,
            "cookiesfrombrowser": None,
        }
    else:
        fmt = format_id or f"bestvideo[height<=720]+bestaudio/best[height<=720]"
        opts = {
            "outtmpl": f"{out_dir}/%(title).80s_%(id)s.%(ext)s",
            "format": fmt,
            "merge_output_format": "mp4",
            "max_filesize": max_mb * 1024 * 1024,
            "quiet": True,
            "no_warnings": True,
            "noplaylist": True,
            "nocheckcertificate": True,
            "cookiesfrombrowser": None,
        }

    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filepath = ydl.prepare_filename(info)

            if fmt_type == "mp3":
                mp3 = filepath.rsplit(".", 1)[0] + ".mp3"
                if os.path.exists(mp3):
                    return Path(mp3)
                return None

            if not filepath.endswith(".mp4"):
                filepath = filepath.rsplit(".", 1)[0] + ".mp4"

            return Path(filepath) if os.path.exists(filepath) else None

    except Exception as e:
        logger.error(f"download failed: {e}")
        return None
