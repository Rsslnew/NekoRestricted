import os
import time
import asyncio
import logging
from pathlib import Path
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from neko_art import NEKO_LOADING, NEKO_SUCCESS, NEKO_SAD, NEKO_CONFUSED
from config import MAX_FILE_SIZE
from utils.yt_downloader import is_youtube, get_info, download

logger = logging.getLogger(__name__)

PENDING = {}
_last_edit = {}
MIN_EDIT = 5


async def safe_edit(msg, text):
    if not msg:
        return
    cid = msg.chat.id
    now = time.time()
    if cid in _last_edit and now - _last_edit[cid] < MIN_EDIT:
        return
    _last_edit[cid] = now
    try:
        await msg.edit_text(text)
    except Exception:
        pass


def _fmt_duration(sec):
    if not sec:
        return "?"
    m, s = divmod(int(sec), 60)
    h, m = divmod(m, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def register(bot: Client, db):

    @bot.on_message(filters.command("yt"))
    async def yt_cmd(c, m):
        if len(m.command) < 2:
            await m.reply_text(
                "**Usage:** `/yt <youtube_link>`\n\n"
                "Example: `/yt https://youtu.be/dQw4w9WgXcQ`",
                disable_web_page_preview=True
            )
            return

        url = m.command[1]
        if not is_youtube(url):
            await m.reply_text("❌ **Bukan link YouTube!**", disable_web_page_preview=True)
            return

        status = await m.reply_text(f"{NEKO_LOADING}\n🔍 Mengambil info video...")

        loop = asyncio.get_event_loop()
        info = await loop.run_in_executor(None, get_info, url)

        if not info:
            await status.edit_text(
                f"{NEKO_SAD}\n❌ **Gagal mengambil info video.**\n\n"
            )
            return

        user_id = m.from_user.id
        PENDING[user_id] = {"url": url, "info": info}

        dur = _fmt_duration(info.get("duration"))
        size = sum(f.get("size", 0) for f in info["formats"]) / 1024 / 1024
        size_txt = f"{size:.0f} MB" if size > 0 else "Unknown"

        text = (
            f"🎬 **{info['title'][:100]}**\n"
            f"👤 **{info['uploader']}**\n"
            f"⏱️ **{dur}** | 📦 **{size_txt}**\n\n"
            f"**Pilih format:**"
        )

        buttons = [[InlineKeyboardButton("🎵 MP3 (Audio)", callback_data="yt_mp3")]]
        for f in info["formats"]:
            h = f["height"]
            s = f.get("size", 0) / 1048576
            label = f"🎬 {h}p MP4"
            if s > 0:
                label += f" (~{s:.0f}MB)"
            buttons.append([InlineKeyboardButton(label, callback_data=f"yt_mp4_{h}")])
        buttons.append([InlineKeyboardButton("❌ Batal", callback_data="yt_cancel")])

        await status.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons))

    @bot.on_callback_query(filters.regex(r"^yt_"))
    async def yt_cb(c, q):
        user_id = q.from_user.id
        data = q.data

        pending = PENDING.pop(user_id, None)
        if not pending:
            await q.answer("Session expired. Kirim /yt lagi.", show_alert=True)
            return

        url = pending["url"]
        info = pending["info"]
        msg = q.message

        if data == "yt_cancel":
            await safe_edit(msg, f"{NEKO_SAD}\n❌ **Dibatalkan.**")
            await q.answer()
            return

        # Tentukan format
        fmt_type = "mp4"
        format_id = None
        label = "?"

        if data == "yt_mp3":
            fmt_type = "mp3"
            label = "MP3"
            await safe_edit(msg, f"{NEKO_LOADING}\n📥 Download MP3...")
        elif data.startswith("yt_mp4_"):
            h = data.replace("yt_mp4_", "")
            label = f"{h}p MP4"

            for f in info["formats"]:
                if str(f["height"]) == h:
                    format_id = f["format_id"]
                    break
            await safe_edit(msg, f"{NEKO_LOADING}\n📥 Download {label}...")

        await q.answer(f"Downloading {label}...", show_alert=False)

        loop = asyncio.get_event_loop()
        filepath = await loop.run_in_executor(
            None,
            lambda: download(
                url,
                out_dir="downloads",
                fmt_type=fmt_type,
                format_id=format_id,
                max_mb=MAX_FILE_SIZE // (1024 * 1024),
            )
        )

        if not filepath or not filepath.exists():
            await safe_edit(msg, f"{NEKO_SAD}\n❌ **Download gagal.**\n\nVideo mungkin restricted atau terlalu besar.")
            return

        size = filepath.stat().st_size
        size_mb = size / 1024 / 1024

        if size > MAX_FILE_SIZE:
            await safe_edit(msg, f"{NEKO_SAD}\n❌ **File terlalu besar!** ({size_mb:.1f} MB)")
            try:
                filepath.unlink()
            except:
                pass
            return

        await safe_edit(msg, f"{NEKO_LOADING}\n📤 Upload {size_mb:.1f} MB...")

        try:
            if fmt_type == "mp3":
                await msg.reply_audio(
                    str(filepath),
                    caption=f"🎵 **{info['title'][:80]}**\n📦 {size_mb:.1f} MB"
                )
            else:
                await msg.reply_video(
                    str(filepath),
                    caption=f"🎬 **{info['title'][:80]}**\n📦 {size_mb:.1f} MB",
                    supports_streaming=True
                )

            await safe_edit(msg, f"{NEKO_SUCCESS}\n✅ **Selesai!** 📦 {size_mb:.1f} MB")

        except Exception as e:
            logger.error(f"Upload error: {e}")
            # Fallback document
            await msg.reply_document(
                str(filepath),
                caption=f"📦 **{info['title'][:80]}**\n📦 {size_mb:.1f} MB"
            )
            await safe_edit(msg, f"{NEKO_SUCCESS}\n✅ **Terkirim sebagai document!**")

        finally:
            try:
                filepath.unlink()
            except:
                pass
