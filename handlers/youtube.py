# AcXNeko - YouTube Downloader
# =============================================================================
# Project   : AcxNekoBot
# Developer : Kazeru
# GitHub    : https://github.com/Rsslnew
# Telegram  : https://telegram.me/K69661

import os
import re
import asyncio
import logging
import json

from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from neko_art import *
from config import MAX_CONCURRENT_DOWNLOADS
from utils.progress import ProgressTracker
from utils.extras import check_force_sub, check_spam, check_daily_limit, increment_daily_count

logger = logging.getLogger(__name__)

YT_PATTERNS = [
    re.compile(r'(?:https?://)?(?:www\.)?youtube\.com/watch\?v=([a-zA-Z0-9_-]{11})'),
    re.compile(r'(?:https?://)?(?:www\.)?youtu\.be/([a-zA-Z0-9_-]{11})'),
    re.compile(r'(?:https?://)?(?:www\.)?youtube\.com/shorts/([a-zA-Z0-9_-]{11})'),
]

active_yt = {}
yt_urls = {}

def extract_yt_id(url: str) -> str | None:
    for p in YT_PATTERNS:
        m = p.search(url)
        if m:
            return m.group(1)
    return None


def is_yt(url: str) -> bool:
    return extract_yt_id(url) is not None


async def yt_info(url: str) -> dict:

    try:
        proc = await asyncio.create_subprocess_exec(
            "yt-dlp", "--dump-json", "--no-download", "-f", "best", url,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=30)
        if proc.returncode == 0 and stdout:
            return json.loads(stdout.decode().strip().split("\n")[0])
    except Exception as e:
        logger.error(f"yt-dlp info error: {e}")
    return {}


async def yt_dl(url: str, out_dir: str, fmt: str, quality: str, msg, uid: int, total_size: int = 0):

    os.makedirs(out_dir, exist_ok=True)
    tmpl = os.path.join(out_dir, "%(title)s.%(ext)s")

    # Init ProgressTracker
    tracker = ProgressTracker(msg, total_size, "download")

    if fmt == "audio":
        cmd = [
            "yt-dlp",
            "-f", "bestaudio[ext=m4a]/bestaudio",
            "--extract-audio", "--audio-format", "mp3", "--audio-quality", "0",
            "-o", tmpl, "--newline", "--progress",
            url
        ]
    else:
        if quality == "720":
            fspec = "best[height<=720][filesize<<1800M]/best[height<=720]"
        elif quality == "480":
            fspec = "best[height<=480][filesize<<1800M]/best[height<=480]"
        else:
            fspec = "best[filesize<<1800M]/bestvideo[filesize<<1800M]+bestaudio/best"
        cmd = [
            "yt-dlp", "-f", fspec, "-o", tmpl,
            "--newline", "--progress", "--merge-output-format", "mp4",
            url
        ]

    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )

    fp = None

    while True:
        if not active_yt.get(uid, True):
            proc.kill()
            tracker.stop()
            raise asyncio.CancelledError()

        line = await proc.stdout.readline()
        if not line:
            break

        txt = line.decode("utf-8", errors="ignore").strip()

        # Parse progress & update ProgressTracker
        if "[download]" in txt and "%" in txt:
            try:
                pct = float(txt.split("%")[0].split()[-1])
                if total_size > 0:
                    current_bytes = int(pct * total_size / 100)
                    await tracker.update(current_bytes)
                else:
                    # Fallback kalau size tidak diketahui: edit manual
                    pass
            except Exception:
                pass

        # Deteksi filename
        if "Destination:" in txt:
            fp = txt.split("Destination:", 1)[1].strip()
        elif "[Merger]" in txt and '"' in txt:
            try:
                fp = txt.split('"')[1]
            except:
                pass

    await proc.wait()
    tracker.stop()

    # Fallback cari file terbaru
    if not fp or not os.path.exists(fp):
        files = [os.path.join(out_dir, f) for f in os.listdir(out_dir)]
        files = [f for f in files if os.path.isfile(f)]
        if files:
            fp = max(files, key=os.path.getctime)

    return fp


def register(bot: Client, db):
    """Register semua handler YouTube."""

    # ==================== /yt COMMAND ====================
    @bot.on_message(filters.command("yt"))
    async def yt_cmd(c, m):
        user = m.from_user
        if not user:
            return

        uid = user.id
        if await db.is_banned(uid):
            return await m.reply_text(f"{NEKO_ANGRY}\n\n**You are banned!** 😾")
        if not await check_force_sub(bot, uid, m):
            return
        if not await check_spam(uid, m):
            return
        if not await check_daily_limit(uid, db, m):
            return

        await db.add_user(uid, user.username, user.first_name)

        if len(m.command) < 2:
            return await m.reply_text(
                f"{NEKO_CONFUSED}\n\n"
                "**Usage:**\n"
                "`/yt <youtube_link>` — download video\n"
                "`/yt <link> audio` — download MP3\n\n"
                "**Examples:**\n"
                "`/yt https://youtu.be/RvnkAtWcKYg`\n"
                "`/yt https://youtu.be/RvnkAtWcKYg audio`"
            )

        url = m.command[1]
        if not is_yt(url):
            return await m.reply_text(f"{NEKO_ANGRY}\n\n**Invalid YouTube link!** 😾")

        fmt = "audio" if len(m.command) > 2 and m.command[2].lower() == "audio" else "video"

        # Cek concurrent
        if len([v for v in active_yt.values() if v is True]) >= MAX_CONCURRENT_DOWNLOADS:
            return await m.reply_text("⏳ **Server busy!** Please wait...")

        loading = await m.reply_text(f"{NEKO_LOADING}\n\n**Fetching info...** 🔍")

        try:
            info = await yt_info(url)
            title = info.get("title", "YouTube Video")
            dur = info.get("duration", 0)
            mins, secs = divmod(dur, 60)
            hrs, mins = divmod(mins, 60)
            dstr = f"{hrs:02d}:{mins:02d}:{secs:02d}" if hrs else f"{mins:02d}:{secs:02d}"

            # Ambil total size untuk ProgressTracker
            total_size = 0
            if info.get("filesize"):
                total_size = info["filesize"]
            elif info.get("filesize_approx"):
                total_size = info["filesize_approx"]

            await loading.edit_text(
                f"**╭━━━━━ 🎬 Video Found ━━━━━╮**\n\n"
                f"🎵 **{title[:55]}{'...' if len(title) > 55 else ''}**\n"
                f"⏱ **Duration:** {dstr}\n"
                f"📦 **Format:** {'🎵 MP3' if fmt == 'audio' else '📹 Video'}\n\n"
                f"**╰━━━━━━━━━━━━━━━━━━━━━━━━━━╯**"
            )

            if fmt == "audio":
                await loading.delete()
                await run_dl(m, url, "audio", "best", uid, title, db, total_size)
            else:
                kb = InlineKeyboardMarkup([
                    [
                        InlineKeyboardButton("🎬 Best", callback_data=f"ytq|best|{uid}"),
                        InlineKeyboardButton("📺 720p", callback_data=f"ytq|720|{uid}")
                    ],
                    [
                        InlineKeyboardButton("📱 480p", callback_data=f"ytq|480|{uid}"),
                        InlineKeyboardButton("🎵 Audio Only", callback_data=f"ytq|audio|{uid}")
                    ],
                    [InlineKeyboardButton("❌ Cancel", callback_data="cancel")]
                ])
                yt_urls[uid] = (url, total_size)
                await loading.edit_text(
                    f"**╭━━━━━ 🎬 Select Quality ━━━━━╮**\n\n"
                    f"🎵 **{title[:40]}**\n\n"
                    f"**╰━━━━━━━━━━━━━━━━━━━━━━━━━━╯**",
                    reply_markup=kb
                )

        except Exception as e:
            logger.error(f"YT cmd error: {e}")
            await loading.edit_text(f"{NEKO_SAD}\n\n**Failed!** 😿\n`{str(e)[:100]}`")

    # ==================== CALLBACK QUALITY ====================
    @bot.on_callback_query(filters.regex(r"^ytq\|(.+?)\|(\d+)$"))
    async def ytq_cb(c, cq):
        parts = cq.data.split("|")
        q = parts[1]
        uid = int(parts[2])

        if cq.from_user.id != uid:
            return await cq.answer("Bukan pesananmu!", show_alert=True)

        data = yt_urls.pop(uid, None)
        if not data:
            return await cq.answer("Session expired, send link again.", show_alert=True)

        url, total_size = data
        await cq.message.delete()

        info = await yt_info(url)
        title = info.get("title", "YouTube Video")
        fmt = "audio" if q == "audio" else "video"
        qmap = {"best": "best", "720": "720", "480": "480", "audio": "best"}
        await run_dl(cq.message, url, fmt, qmap.get(q, "best"), uid, title, db, total_size)

    # ==================== AUTO DETECT YT LINK ====================
    @bot.on_message(
        filters.regex(r'(?:https?://)?(?:www\.)?(?:youtube\.com|youtu\.be)/[^\s]+')
        & ~filters.command([
            "yt", "start", "help", "settings", "cancel", "cancel_yt",
            "dl", "bdl", "login", "logout", "whoami", "myplan", "premium",
            "set_caption", "see_caption", "del_caption", "set_thumb",
            "view_thumb", "del_thumb", "broadcast", "ban", "unban",
            "users", "premium_users", "stats"
        ])
    )
    async def auto_yt(c, m):
        if not m.text:
            return

        urls = re.findall(r'(?:https?://)?(?:www\.)?(?:youtube\.com|youtu\.be)/[^\s]+', m.text)
        if not urls:
            return

        url = urls[0]
        if not is_yt(url):
            return

        uid = m.from_user.id
        info = await yt_info(url)
        total_size = info.get("filesize") or info.get("filesize_approx") or 0
        yt_urls[uid] = (url, total_size)

        kb = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("📹 Video", callback_data=f"ytauto|video|{uid}"),
                InlineKeyboardButton("🎵 Audio", callback_data=f"ytauto|audio|{uid}")
            ],
            [InlineKeyboardButton("❌ Ignore", callback_data="cancel")]
        ])
        await m.reply_text(
            f"{NEKO_FOUND}\n\n**YouTube link detected!** 🎬\nPilih format:",
            reply_markup=kb
        )

    @bot.on_callback_query(filters.regex(r"^ytauto\|(video|audio)\|(\d+)$"))
    async def ytauto_cb(c, cq):
        parts = cq.data.split("|")
        fmt = parts[1]
        uid = int(parts[2])

        if cq.from_user.id != uid:
            return await cq.answer("Bukan pesananmu!", show_alert=True)

        data = yt_urls.pop(uid, None)
        if not data:
            return await cq.answer("Expired, kirim ulang link.", show_alert=True)

        url, total_size = data
        await cq.message.delete()

        info = await yt_info(url)
        title = info.get("title", "YouTube Video")
        await run_dl(cq.message, url, fmt, "best", uid, title, db, total_size)

    # ==================== CANCEL YT ====================
    @bot.on_message(filters.command("cancel_yt"))
    async def cancel_yt(c, m):
        uid = m.from_user.id
        active_yt[uid] = False
        await m.reply_text(f"{NEKO_SLEEP}\n\n**Download cancelled!** 💤")

    # ==================== CORE DOWNLOAD & UPLOAD ====================
    async def run_dl(message, url, fmt, quality, uid, title, db, total_size: int = 0):
        progress = await message.reply_text(
            f"**╭━━━ 📥 Starting Download ━━━╮**\n\n"
            f"`{'○' * 20}`\n\n"
            f"**0.0%**\n\n"
            f"**╰━━━━━━━━━━━━━━━━━━━━━━╯**"
        )
        active_yt[uid] = True

        try:
            fp = await yt_dl(url, "downloads/youtube", fmt, quality, progress, uid, total_size)

            if not fp or not os.path.exists(fp):
                await progress.delete()
                return await message.reply_text(f"{NEKO_SAD}\n\n**Download failed!** 😿")

            size = os.path.getsize(fp)
            if size > 2 * 1024 * 1024 * 1024:
                os.remove(fp)
                await progress.delete()
                return await message.reply_text(f"{NEKO_ANGRY}\n\n**File too large!** > 2GB 😿")

            await progress.delete()

            caption = await db.get_caption(uid) or f"🎬 **{title}**\n\n📥 Downloaded via AcxNeko"
            thumb = await db.get_thumbnail(uid)
            thumb = thumb if thumb and os.path.exists(thumb) else None

            upload_msg = await message.reply_text(f"{NEKO_UPLOAD}\n\n**Uploading...** 📤")
            upload_tracker = ProgressTracker(upload_msg, size, "upload")

            async def upload_progress(current, total):
                await upload_tracker.update(current)

            try:
                if fmt == "audio":
                    await message.reply_audio(fp, caption=caption, title=title, thumb=thumb, progress=upload_progress)
                else:
                    await message.reply_video(fp, caption=caption, supports_streaming=True, thumb=thumb, progress=upload_progress)
            except Exception as e:
                logger.error(f"Upload error: {e}")
                upload_tracker.stop()
                await message.reply_document(fp, caption=caption, thumb=thumb)
            finally:
                upload_tracker.stop()
                try:
                    await upload_msg.delete()
                except:
                    pass
                try:
                    if os.path.exists(fp):
                        os.remove(fp)
                except:
                    pass

            # Update stats
            await db.increment_download(uid)
            await increment_daily_count(uid, db)

            await message.reply_text(f"{NEKO_SUCCESS}\n\n**Done! Nyaa~!** 🎉")

        except asyncio.CancelledError:
            await message.reply_text(f"{NEKO_SLEEP}\n\n**Cancelled!** 💤")
        except Exception as e:
            logger.error(f"YT run_dl error: {e}")
            await message.reply_text(f"{NEKO_ANGRY}\n\n**Failed!** 😿\n`{str(e)[:150]}`")
        finally:
            active_yt.pop(uid, None)
