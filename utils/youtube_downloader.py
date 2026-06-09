import os
import asyncio
import logging
import yt_dlp
from pathlib import Path
from typing import Optional, Any


logger = logging.getLogger(__name__)
SUPPORTED_DOMAINS = [
    "youtube.com", "youtu.be",
]


def is_youtube_url(url: str) -> bool:

    return any(domain in url.lower() for domain in SUPPORTED_DOMAINS)


def get_video_info(url: str) -> Optional[dict]:

    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'noplaylist': True,
        'extract_flat': False,
        'cookiesfrombrowser': None,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)

            formats = []
            seen_heights = set()

            for f in info.get('formats', []):
                if f.get('vcodec') != 'none':
                    height = f.get('height')
                    if height and height not in seen_heights:
                        seen_heights.add(height)
                        format_str = f"{f['format_id']}+bestaudio/best"
                        formats.append({
                            'format_id': format_str,
                            'height': height,
                            'filesize': f.get('filesize', 0) or f.get('filesize_approx', 0),
                        })

            formats.sort(key=lambda x: x['height'])

            return {
                'title': info.get('title', 'Unknown'),
                'duration': info.get('duration', 0),
                'uploader': info.get('uploader', 'Unknown'),
                'filesize': info.get('filesize', 0) or info.get('filesize_approx', 0),
                'resolution': f"{info.get('width', '?')}x{info.get('height', '?')}",
                'url': url,
                'formats': formats,
            }
    except Exception as e:
        logger.warning(f"Failed to get info for {url}: {e}")
        return None


def download_video(
    url: str,
    download_dir: str = None,
    max_height: int = 720,
    max_filesize_mb: int = 1900,
    progress: Optional[Any] = None,
    format_type: str = "mp4",
    format_id: str = None,
    loop: asyncio.AbstractEventLoop = None,
) -> Optional[Path]:

    if download_dir is None:
        download_dir = "downloads"

    Path(download_dir).mkdir(parents=True, exist_ok=True)

    if loop is None:
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

    def progress_hook(d):
        if d['status'] == 'downloading':
            downloaded = d.get('downloaded_bytes', 0)
            total = d.get('total_bytes') or d.get('total_bytes_estimate', 0)
            if total > 0 and progress:
                try:
                    asyncio.run_coroutine_threadsafe(
                        progress.render(downloaded, total, "Download"),
                        loop
                    )
                except Exception:
                    pass

    if format_type == "mp3":
        ydl_opts = {
            'outtmpl': f'{download_dir}/%(title).80s_%(id)s.%(ext)s',
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'quiet': True,
            'no_warnings': True,
            'noplaylist': True,
            'progress_hooks': [progress_hook],
            'cookiesfrombrowser': None,
        }
    else:
        if format_id:
            format_str = format_id
        else:
            format_str = f'bestvideo[height<={max_height}]+bestaudio/best[height<={max_height}]'

        ydl_opts = {
            'outtmpl': f'{download_dir}/%(title).80s_%(id)s.%(ext)s',
            'format': format_str,
            'merge_output_format': 'mp4',
            'max_filesize': max_filesize_mb * 1024 * 1024,
            'quiet': True,
            'no_warnings': True,
            'noplaylist': True,
            'nocheckcertificate': True,
            'progress_hooks': [progress_hook],
            'cookiesfrombrowser': None,
        }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)

            if format_type == "mp3":
                base = filename.rsplit('.', 1)[0]
                mp3_file = f"{base}.mp3"
                if os.path.exists(mp3_file):
                    return Path(mp3_file)

            if not filename.endswith('.mp4') and format_type != "mp3":
                base = filename.rsplit('.', 1)[0]
                filename = f"{base}.mp4"

            filepath = Path(filename)
            if filepath.exists():
                return filepath
            return None

    except Exception as e:
        logger.error(f"Download failed: {e}")
        return None
        