import os
import asyncio
import logging
from pathlib import Path
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from neko_art import NEKO_LOADING, NEKO_SUCCESS, NEKO_SAD, NEKO_CONFUSED
from utils.progress import ProgressTracker
from config import MAX_FILE_SIZE
from utils.youtube_downloader import is_youtube_url, get_video_info, download_video

logger = logging.getLogger(__name__)
PENDING = {}


class YTProgressAdapter:

    def __init__(self, message, action="download"):
        self.message = message
        self.action = action
        self.tracker = None
        try:
            self.loop = asyncio.get_event_loop()
        except RuntimeError:
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)

    def _ensure_tracker(self, total):
        if self.tracker is None and total > 0:
            self.tracker = ProgressTracker(self.message, total, self.action)
        if self.tracker and self.tracker.total != total:
            self.tracker.total = total

    async def _do_update(self, current, total):
        self._ensure_tracker(total)
        if self.tracker:
            await self.tracker.update(current)

    def render(self, current, total, action_name):
        try:
            if self.loop.is_running():
                asyncio.run_coroutine_threadsafe(
                    self._do_update(current, total),
                    self.loop
                )
        except Exception:
            pass


def register(bot: Client, db):
    """Register YouTube handler."""

    @bot.on_message(filters.command("yt"))
    async def youtube_command(client, message):
        if len(message.command) < 2:
            await message.reply_text(
                f"{NEKO_CONFUSED}\n\n"
                f"**Usage:** `/yt <youtube_link>`\n\n"
                f"Example:\n"
                f"`/yt https://youtube.com/watch?v=xxxxx`",
                disable_web_page_preview=True
            )
            return

        url = message.command[1]

        if not is_youtube_url(url):
            await message.reply_text(
                f"{NEKO_CONFUSED}\n\n"
                f"**Not a YouTube link!** 😾",
                disable_web_page_preview=True
            )
            return

        status = await message.reply_text(
            f"{NEKO_LOADING}\n\n🔍 **Fetching video info...**",
            disable_web_page_preview=True
        )

        loop = asyncio.get_event_loop()
        info = await loop.run_in_executor(None, get_video_info, url)

        if not info:
            try:
                await status.edit_text(
                    f"{NEKO_SAD}\n\n❌ **Failed to get video info.**\n\n"
                    f"💡 Possible reasons:\n"
                    f"• Video is private/restricted\n"
                    f"• YouTube blocked the request\n"
                    f"• Try again later",
                    disable_web_page_preview=True
                )
            except Exception:
                await message.reply_text(
                    f"{NEKO_SAD}\n\n❌ **Failed to get video info.**",
                    disable_web_page_preview=True
                )
            return

        user_id = message.from_user.id
        PENDING[user_id] = {"url": url, "info": info, "status_msg": status}

        # Format duration
        duration = "?"
        if info.get('duration'):
            m, s = divmod(int(info['duration']), 60)
            h, m = divmod(m, 60)
            duration = f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"

        size_mb = (info.get('filesize') or 0) / 1024 / 1024
        size_text = f"{size_mb:.1f} MB" if size_mb > 0 else "Unknown"

        text = (
            f"🎬 **{info['title'][:100]}**\n"
            f"👤 **{info['uploader']}**\n"
            f"⏱️ **{duration}** | 📦 **{size_text}**\n\n"
            f"**Select format:**"
        )

        buttons = [[InlineKeyboardButton("🎵 MP3 (Audio)", callback_data="yt_mp3")]]

        for fmt in (info.get('formats') or []):
            h = fmt['height']
            s = fmt.get('filesize', 0) / 1048576 if fmt.get('filesize') else 0
            label = f"🎬 {h}p MP4"
            if s > 0:
                label += f" (~{s:.0f}MB)"
            buttons.append(
                [InlineKeyboardButton(label, callback_data=f"yt_mp4_{fmt['format_id']}_{h}")]
            )

        buttons.append([InlineKeyboardButton("❌ Cancel", callback_data="yt_cancel")])

        try:
            await status.edit_text(
                text,
                reply_markup=InlineKeyboardMarkup(buttons),
                disable_web_page_preview=True
            )
        except Exception as e:
            logger.warning(f"Edit failed, sending new message: {e}")
            try:
                await status.delete()
            except:
                pass
            new_msg = await message.reply_text(
                text,
                reply_markup=InlineKeyboardMarkup(buttons),
                disable_web_page_preview=True
            )
            PENDING[user_id]["status_msg"] = new_msg

    @bot.on_callback_query(filters.regex(r"^yt_"))
    async def youtube_callback(client, callback_query):
        user_id = callback_query.from_user.id
        data = callback_query.data

        pending = PENDING.pop(user_id, None)
        if not pending:
            await callback_query.answer("Session expired. Please send /yt again.", show_alert=True)
            return

        url = pending["url"]
        info = pending["info"]
        status_msg = pending["status_msg"]

        if data == "yt_cancel":
            try:
                await status_msg.edit_text(
                    f"{NEKO_SAD}\n\n❌ **Cancelled.**",
                    disable_web_page_preview=True
                )
            except:
                pass
            await callback_query.answer()
            return

        # Parse format
        fmt_type = "mp4"
        fmt_id = None
        height = "?"

        if data == "yt_mp3":
            fmt_type = "mp3"
            try:
                await status_msg.edit_text(
                    f"{NEKO_LOADING}\n\n📥 **Downloading MP3...**",
                    disable_web_page_preview=True
                )
            except:
                pass
        elif data.startswith("yt_mp4_"):
            parts = data.split("_")
            height = parts[-1]
            fmt_id = "_".join(parts[2:-1])
            try:
                await status_msg.edit_text(
                    f"{NEKO_LOADING}\n\n📥 **Downloading {height}p MP4...**",
                    disable_web_page_preview=True
                )
            except:
                pass

        await callback_query.answer("Download started!", show_alert=False)

        # Download
        loop = asyncio.get_event_loop()
        progress = YTProgressAdapter(status_msg, "download")

        try:
            filepath = await loop.run_in_executor(
                None,
                lambda: download_video(
                    url,
                    download_dir="downloads",
                    format_type=fmt_type,
                    format_id=fmt_id,
                    max_filesize_mb=MAX_FILE_SIZE // (1024 * 1024),
                    progress=progress,
                    loop=loop,
                )
            )
        except Exception as e:
            logger.error(f"YouTube download error: {e}")
            try:
                await status_msg.edit_text(
                    f"{NEKO_SAD}\n\n❌ **Download failed:** `{str(e)[:200]}`",
                    disable_web_page_preview=True
                )
            except:
                await callback_query.message.reply_text(
                    f"{NEKO_SAD}\n\n❌ **Download failed.**"
                )
            return

        if not filepath or not filepath.exists():
            try:
                await status_msg.edit_text(
                    f"{NEKO_SAD}\n\n❌ **Download failed.**\n\n"
                    f"Video may be restricted or too large.",
                    disable_web_page_preview=True
                )
            except:
                pass
            return

        # Check size
        file_size = filepath.stat().st_size
        size_mb = file_size / 1024 / 1024

        if file_size > MAX_FILE_SIZE:
            try:
                await status_msg.edit_text(
                    f"{NEKO_SAD}\n\n"
                    f"❌ **File too large!** "
                    f"({size_mb:.1f} MB > {MAX_FILE_SIZE/1024/1024:.0f} MB limit)",
                    disable_web_page_preview=True
                )
            except:
                pass
            try:
                filepath.unlink()
            except:
                pass
            return

        try:
            await status_msg.edit_text(
                f"{NEKO_LOADING}\n\n📤 **Uploading...**",
                disable_web_page_preview=True
            )
        except:
            pass

        # Upload with progress
        upload_progress = YTProgressAdapter(status_msg, "upload")

        async def upload_progress_callback(current, total):
            upload_progress.render(current, total, "Upload")

        try:
            if fmt_type == "mp3":
                await callback_query.message.reply_audio(
                    str(filepath),
                    caption=f"🎵 **{info['title'][:80]}**\n📦 {size_mb:.1f} MB",
                    progress=upload_progress_callback
                )
            else:
                await callback_query.message.reply_video(
                    str(filepath),
                    caption=f"🎬 **{info['title'][:80]}**\n📦 {size_mb:.1f} MB",
                    supports_streaming=True,
                    progress=upload_progress_callback
                )

            try:
                await status_msg.edit_text(
                    f"{NEKO_SUCCESS}\n\n✅ **Done!** 📦 {size_mb:.1f} MB",
                    disable_web_page_preview=True
                )
            except:
                pass

        except Exception as e:
            logger.error(f"YouTube upload error: {e}")
            # Fallback to document
            try:
                await callback_query.message.reply_document(
                    str(filepath),
                    caption=f"📦 **{info['title'][:80]}**\n📦 {size_mb:.1f} MB"
                )
                try:
                    await status_msg.edit_text(
                        f"{NEKO_SUCCESS}\n\n✅ **Sent as document!**",
                        disable_web_page_preview=True
                    )
                except:
                    pass
            except Exception as e2:
                logger.error(f"Fallback upload failed: {e2}")
                try:
                    await status_msg.edit_text(
                        f"{NEKO_SAD}\n\n❌ **Upload failed.**",
                        disable_web_page_preview=True
                    )
                except:
                    pass

        finally:
            try:
                filepath.unlink()
            except:
                pass
