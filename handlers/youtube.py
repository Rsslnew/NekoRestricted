# AcXNeko - YouTube Downloader Module
# =============================================================================
# Project   : AcxNekoBot
# Developer : Kazeru
# GitHub    : https://github.com/Rsslnew
# Telegram  : https://telegram.me/K69661
#NEW YOUTUBE
import os
import re
import asyncio
import logging
import subprocess
from datetime import datetime

from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from neko_art import *
from utils.progress import ProgressTracker
from utils.extras import check_force_sub, check_spam, check_daily_limit, increment_daily_count
from config import FREE_DAILY_LIMIT, MAX_CONCURRENT_DOWNLOADS

logger = logging.getLogger(__name__)

# Regex untuk deteksi link YouTube
YT_REGEX = re.compile(
    r'(https?://)?(www\.)?(youtube|youtu|youtube-nocookie)\.(com|be)/'
    r'(watch\?v=|embed/|v/|.+\?v=)?([^&=%\?]{11})'
)

active_yt_downloads = {}

def register(bot: Client, db):


    def extract_yt_id(url: str) -> str | None:

        match = YT_REGEX.match(url)
        if match:
            return match.group(6)
        return None

    def get_video_info(url: str) -> dict:

        try:
            cmd = [
                "yt-dlp",
                "--dump-json",
                "--no-download",
                "-f", "best",
                url
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode == 0 and result.stdout:
                import json
                return json.loads(result.stdout.strip().split('\n')[0])
            return {}
        except Exception as e:
            logger.error(f"Info extraction error: {e}")
            return {}

    async def download_youtube(url: str, output_path: str, format_type: str = "video", 
                               quality: str = "best", progress_msg=None, user_id: int = None):
        """Download YouTube video/audio using yt-dlp."""
        
        output_template = os.path.join(output_path, "%(title)s.%(ext)s")
        
        if format_type == "audio":
            cmd = [
                "yt-dlp",
                "-f", "bestaudio[ext=m4a]/bestaudio",
                "--extract-audio",
                "--audio-format", "mp3",
                "--audio-quality", "0",
                "-o", output_template,
                "--newline",
                "--progress",
                url
            ]
        else:
            # Video format
            if quality == "best":
                format_spec = "best[filesize<<2G]/bestvideo[filesize<<2G]+bestaudio/best"
            elif quality == "720":
                format_spec = "best[height<=720][filesize<<2G]/best[height<=720]"
            elif quality == "480":
                format_spec = "best[height<=480][filesize<<2G]/best[height<=480]"
            else:
                format_spec = "best[filesize<<2G]/best"
            
            cmd = [
                "yt-dlp",
                "-f", format_spec,
                "-o", output_template,
                "--newline",
                "--progress",
                "--merge-output-format", "mp4",
                url
            ]

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        downloaded_file = None
        last_progress = 0

        while True:
            if user_id and not active_yt_downloads.get(user_id, True):
                process.kill()
                raise Exception("Cancelled")

            line = await process.stdout.readline()
            if not line:
                break

            line = line.decode('utf-8', errors='ignore').strip()
            
            # Parse progress
            if '[download]' in line and '%' in line:
                try:
                    percent_str = line.split('%')[0].split()[-1]
                    percent = float(percent_str)
                    
                    if progress_msg and percent - last_progress >= 5:
                        last_progress = percent
                        bar_length = 20
                        filled = int(bar_length * percent / 100)
                        bar = "●" * filled + "○" * (bar_length - filled)
                        
                        await progress_msg.edit_text(
                            f"**╭━━━ 📥 YouTube Download ━━━╮**\n\n"
                            f"`{bar}`\n\n"
                            f"**{percent:.1f}%**\n\n"
                            f"**╰━━━━━━━━━━━━━━━━━━━━━━╯**"
                        )
                except:
                    pass


            if 'Destination:' in line or 'Merged' in line:
                parts = line.split(':')
                if len(parts) > 1:
                    downloaded_file = parts[1].strip()

        await process.wait()
        

        if not downloaded_file or not os.path.exists(downloaded_file):
            files = os.listdir(output_path)
            if files:

                files = [os.path.join(output_path, f) for f in files]
                downloaded_file = max(files, key=os.path.getctime)
        
        return downloaded_file

    # ==================== YOUTUBE COMMAND ====================
    @bot.on_message(filters.command("yt"))
    async def youtube_command(client, message):
        user = message.from_user
        if not user:
            return

        user_id = user.id
        username = user.username or "unknown"
        first_name = user.first_name or "unknown"

        # Check banned
        if await db.is_banned(user_id):
            await message.reply_text(f"{NEKO_ANGRY}\n\n**You are banned!** 😾")
            return

        # Force sub
        if not await check_force_sub(bot, user_id, message):
            return

        # Anti spam
        if not await check_spam(user_id, message):
            return

        # Daily limit
        if not await check_daily_limit(user_id, db, message):
            return

        await db.add_user(user_id, username, first_name)

        if len(message.command) < 2:
            await message.reply_text(
                f"{NEKO_CONFUSED}\n\n"
                "**Usage:** `/yt <link>`\n\n"
                "**Examples:**\n"
                "`/yt https://youtube.com/watch?v=xxxxx`\n"
                "`/yt https://youtu.be/xxxxx`\n\n"
                "**Optional:** Tambahkan `audio` untuk MP3 only\n"
                "`/yt <link> audio`"
            )
            return

        url = message.command[1]
        format_type = "audio" if len(message.command) > 2 and message.command[2].lower() == "audio" else "video"

        # Validate URL
        video_id = extract_yt_id(url)
        if not video_id:
            await message.reply_text(f"{NEKO_ANGRY}\n\n**Invalid YouTube link!** 😾")
            return

        # Check concurrent
        active_count = len([d for d in active_yt_downloads.values() if d])
        if active_count >= MAX_CONCURRENT_DOWNLOADS:
            await message.reply_text(
                f"⏳ **Server busy!**\n"
                f"🔴 Active downloads: **{active_count}**/{MAX_CONCURRENT_DOWNLOADS}"
            )
            return

        # Get info
        loading = await message.reply_text(f"{NEKO_LOADING}\n\n**Fetching info...** 🔍")
        
        try:
            info = await asyncio.to_thread(get_video_info, url)
            title = info.get('title', 'Unknown Title')
            duration = info.get('duration', 0)
            uploader = info.get('uploader', 'Unknown')
            
            # Format duration
            mins, secs = divmod(duration, 60)
            hrs, mins = divmod(mins, 60)
            duration_str = f"{hrs:02d}:{mins:02d}:{secs:02d}" if hrs else f"{mins:02d}:{secs:02d}"
            
            await loading.edit_text(
                f"**╭━━━━━ 🎬 Video Found ━━━━━╮**\n\n"
                f"🎵 **{title[:50]}...**\n" if len(title) > 50 else f"🎵 **{title}**\n"
                f"👤 **Channel:** {uploader}\n"
                f"⏱ **Duration:** {duration_str}\n"
                f"📦 **Format:** {'🎵 MP3 (Audio)' if format_type == 'audio' else '📹 Video'}\n\n"
                f"**╰━━━━━━━━━━━━━━━━━━━━━━━━━━╯**"
            )

            # Quality selection for video
            if format_type == "video":
                keyboard = InlineKeyboardMarkup([
                    [
                        InlineKeyboardButton("🎬 Best", callback_data=f"yt_best_{video_id}"),
                        InlineKeyboardButton("📺 720p", callback_data=f"yt_720_{video_id}")
                    ],
                    [
                        InlineKeyboardButton("📱 480p", callback_data=f"yt_480_{video_id}"),
                        InlineKeyboardButton("🎵 Audio Only", callback_data=f"yt_audio_{video_id}")
                    ],
                    [InlineKeyboardButton("❌ Cancel", callback_data="cancel")]
                ])
                await loading.edit_text(
                    f"**╭━━━━━ 🎬 Select Quality ━━━━━╮**\n\n"
                    f"🎵 **{title[:40]}**\n\n"
                    f"**╰━━━━━━━━━━━━━━━━━━━━━━━━━━╯**",
                    reply_markup=keyboard
                )
                # Store URL in memory for callback
                active_yt_downloads[f"url_{user_id}"] = url
                return

            # Direct audio download
            await start_download(message, url, format_type, "best", user_id, title)

        except Exception as e:
            logger.error(f"YouTube info error: {e}")
            await loading.edit_text(f"{NEKO_SAD}\n\n**Failed to get info!** 😿\n`{str(e)[:100]}`")

    async def start_download(message, url, format_type, quality, user_id, title):
        """Start actual download and upload."""
        os.makedirs("downloads/youtube", exist_ok=True)
        
        progress_msg = await message.reply_text(
            f"**╭━━━ 📥 Starting Download ━━━╮**\n\n"
            f"`{'○' * 20}`\n\n"
            f"**0.0%**\n\n"
            f"**╰━━━━━━━━━━━━━━━━━━━━━━╯**"
        )

        active_yt_downloads[user_id] = True

        try:
            file_path = await download_youtube(
                url, "downloads/youtube", format_type, quality, 
                progress_msg, user_id
            )

            if not file_path or not os.path.exists(file_path):
                await progress_msg.delete()
                await message.reply_text(f"{NEKO_SAD}\n\n**Download failed!** 😿")
                return

            file_size = os.path.getsize(file_path)
            if file_size > 2 * 1024 * 1024 * 1024:  # 2GB limit
                os.remove(file_path)
                await progress_msg.delete()
                await message.reply_text(f"{NEKO_ANGRY}\n\n**File too large!** > 2GB 😿")
                return

            await progress_msg.delete()

            # Upload
            upload_msg = await message.reply_text(f"{NEKO_UPLOAD}\n\n**Uploading...** 📤")
            
            caption = await db.get_caption(user_id) or f"🎬 **{title}**\n\n📥 Downloaded via AcxNeko"
            thumb_path = await db.get_thumbnail(user_id)

            if format_type == "audio":
                await message.reply_audio(
                    file_path,
                    caption=caption,
                    title=title,
                    thumb=thumb_path if thumb_path and os.path.exists(thumb_path) else None
                )
            else:
                await message.reply_video(
                    file_path,
                    caption=caption,
                    supports_streaming=True,
                    thumb=thumb_path if thumb_path and os.path.exists(thumb_path) else None
                )

            await upload_msg.delete()
            await message.reply_text(f"{NEKO_SUCCESS}\n\n**Done! Nyaa~!** 🎉")

            # Update stats
            await db.increment_download(user_id)
            await increment_daily_count(user_id, db)

            # Cleanup
            if os.path.exists(file_path):
                os.remove(file_path)

        except Exception as e:
            if "Cancelled" in str(e):
                await message.reply_text(f"{NEKO_SLEEP}\n\n**Download cancelled!** 💤")
            else:
                logger.error(f"YouTube download error: {e}")
                await message.reply_text(f"{NEKO_ANGRY}\n\n**Failed!** 😿\n`{str(e)[:150]}`")
        finally:
            active_yt_downloads.pop(user_id, None)
            active_yt_downloads.pop(f"url_{user_id}", None)

    # ==================== CALLBACKS FOR QUALITY SELECTION ====================
    @bot.on_callback_query(filters.regex(r"^yt_(best|720|480|audio)_(.{11})$"))
    async def yt_quality_callback(client, callback_query):
        user_id = callback_query.from_user.id
        data = callback_query.data
        
        if user_id not in ADMINS and await db.is_banned(user_id):
            await callback_query.answer("You are banned!", show_alert=True)
            return

        # Extract quality and video id
        parts = data.split("_")
        quality = parts[1]
        video_id = parts[2]
        
        url = active_yt_downloads.get(f"url_{user_id}")
        if not url:
            await callback_query.answer("Session expired! Send link again.", show_alert=True)
            return

        await callback_query.message.delete()

        format_type = "audio" if quality == "audio" else "video"
        quality_map = {"best": "best", "720": "720", "480": "480"}
        selected_quality = quality_map.get(quality, "best")

        # Get title again
        info = await asyncio.to_thread(get_video_info, url)
        title = info.get('title', 'YouTube Video')

        await start_download(callback_query.message, url, format_type, selected_quality, user_id, title)

    # ==================== CANCEL YT DOWNLOAD ====================
    @bot.on_message(filters.command("cancel_yt"))
    async def cancel_yt_command(client, message):
        user_id = message.from_user.id
        active_yt_downloads[user_id] = False
        await message.reply_text(f"{NEKO_SLEEP}\n\n**Cancelling...** 💤")

    # ==================== AUTO DETECT YOUTUBE LINKS ====================
    @bot.on_message(
        filters.regex(r'(https?://)?(www\.)?(youtube|youtu)\.(com|be)/.+')
        & ~filters.command(["yt", "start", "help", "settings", "cancel"])
    )
    async def auto_detect_youtube(client, message):
        if not message.text:
            return
        
        urls = YT_REGEX.findall(message.text)
        if urls:
            # urls is list of tuples, get the full match
            full_urls = re.findall(r'(https?://)?(www\.)?(youtube|youtu)\.(com|be)/[^\s]+', message.text)
            if full_urls:
                url = ''.join(full_urls[0])
                keyboard = InlineKeyboardMarkup([
                    [
                        InlineKeyboardButton("📹 Video", callback_data=f"ytauto_video_{extract_yt_id(url)}"),
                        InlineKeyboardButton("🎵 Audio", callback_data=f"ytauto_audio_{extract_yt_id(url)}")
                    ],
                    [InlineKeyboardButton("❌ Ignore", callback_data="cancel")]
                ])
                await message.reply_text(
                    f"{NEKO_FOUND}\n\n**YouTube link detected!** 🎬\n\n"
                    f"Choose format:",
                    reply_markup=keyboard
                )
                active_yt_downloads[f"url_{message.from_user.id}"] = url

    @bot.on_callback_query(filters.regex(r"^ytauto_(video|audio)_(.{11})$"))
    async def yt_auto_callback(client, callback_query):
        user_id = callback_query.from_user.id
        data = callback_query.data
        
        parts = data.split("_")
        format_type = parts[1]
        video_id = parts[2]
        
        url = active_yt_downloads.get(f"url_{user_id}")
        if not url:
            await callback_query.answer("Expired!", show_alert=True)
            return

        await callback_query.message.delete()
        
        info = await asyncio.to_thread(get_video_info, url)
        title = info.get('title', 'YouTube Video')
        
        await start_download(callback_query.message, url, format_type, "best", user_id, title)
        