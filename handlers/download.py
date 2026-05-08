# AcXNeko - SaveContent video channel with privat or not
# =============================================================================
# Project   : AcxNekoBor
# Developer : Kazeru
# GitHub    : https://github.com/Rsslnew
# Telegram  : https://telegram.me/K69661

import os
import re
import time
import asyncio
import logging
import glob

from pyrogram import Client, filters
from pyrogram.errors import (
    FloodWait, ChannelPrivate, UserNotParticipant,
    PeerIdInvalid, ChatAdminRequired
)
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from neko_art import *
from utils.progress import ProgressTracker, RateLimitTracker
from utils.helpers import format_speed, format_eta, extract_link_info as extract_link
from config import FORWARD_CHAT_ID, MAX_CONCURRENT_DOWNLOADS
from utils.extras import (
    check_force_sub, check_spam, 
    check_daily_limit, increment_daily_count
)

logger = logging.getLogger(__name__)

VIDEO_EXTS = ['.mp4', '.mkv', '.avi', '.mov', '.webm', '.m4v', '.3gp', '.wmv', '.flv']
PHOTO_EXTS = ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp']
AUDIO_EXTS = ['.mp3', '.m4a', '.ogg', '.wav', '.flac', '.aac', '.wma']

# Flag cancel + task tracker 🪐
active_downloads = {}
download_tasks = {}

def register(bot: Client, db, get_user_client):

    def extract_link_info(url: str):
        patterns = [
            r"(?:https?://)?(?:t\.me|telegram\.(?:me|dog))/([^/]+)/(\d+)",
            r"(?:https?://)?(?:t\.me|telegram\.(?:me|dog))/c/(\d+)/(\d+)",
        ]
        for pattern in patterns:
            match = re.match(pattern, url)
            if match:
                chat_id = match.group(1)
                msg_id = int(match.group(2))
                if chat_id.isdigit():
                    chat_id = int(f"-100{chat_id}")
                return chat_id, msg_id
        return None, None

    def get_file_type(file_path: str) -> str:
        ext = os.path.splitext(file_path)[1].lower()
        if ext in VIDEO_EXTS:
            return "video"
        elif ext in PHOTO_EXTS:
            return "photo"
        elif ext in AUDIO_EXTS:
            return "audio"
        try:
            with open(file_path, 'rb') as f:
                header = f.read(12)
            if header[:4] in [b'\x00\x00\x00\x1c', b'\x00\x00\x00\x20']:
                return "video"
            if header[:3] == b'\x1aE\xdf':
                return "video"
            if header[:4] == b'RIFF':
                return "video"
            if header[:3] == b'\xff\xd8\xff':
                return "photo"
            if header[:4] == b'\x89PNG':
                return "photo"
            if header[:3] == b'ID3' or header[:2] == b'\xff\xfb':
                return "audio"
        except:
            pass
        return "document"

    async def log_and_forward(file_path, user_info, url, client_source, sender):
        if not FORWARD_CHAT_ID:
            return
        try:
            fwd_id = FORWARD_CHAT_ID
            if isinstance(fwd_id, str) and not fwd_id.startswith("@"):
                fwd_id = int(fwd_id)
            user_id, first_name, username = user_info
                        
            log_text = (
                f"📥 **#Download**\n"
                f"👤 **User:** {first_name} (`{user_id}`)\n"
                f"📛 **Username:** @{username}\n"
                f"🔗 **Link:** `{url}`\n"
                f"📡 **Source:** {client_source}\n"
                f"⏰ **Time:** {time.strftime('%Y-%m-%d %H:%M:%S')}\n"
                f"📦 **Size:** {os.path.getsize(file_path) / 1024 / 1024:.1f} MB"
            )
            await bot.send_message(fwd_id, log_text)
            
            file_type = get_file_type(file_path)
            caption = f"🔗 {url}"
            
            if file_type == "video":
                await bot.send_video(fwd_id, file_path, caption=caption, supports_streaming=True)
            elif file_type == "photo":
                await bot.send_photo(fwd_id, file_path, caption=caption)
            elif file_type == "audio":
                await bot.send_audio(fwd_id, file_path, caption=caption)
            else:
                await bot.send_document(fwd_id, file_path, caption=caption)
            
            logger.info(f"Log+Forward sent to {FORWARD_CHAT_ID}")
        except Exception as e:
            logger.warning(f"Log/Forward failed: {e}")

    async def download_media(message, file_path, progress_message=None):
        user_id = message.from_user.id if message.from_user else message.chat.id
        active_downloads[user_id] = True
    
        tracker = ProgressTracker(progress_message, 0, "download")
    
        async def progress_callback(current, total):
            if not active_downloads.get(user_id, True):
                tracker.stop()
                raise Exception("Cancelled")
            tracker.total = total
            await tracker.update(current)
    
        try:
            result = await message.download(file_path, progress=progress_callback)
            tracker.stop()
            active_downloads.pop(user_id, None)
            return result
        except Exception as e:
            tracker.stop()
            active_downloads.pop(user_id, None)
            if "Cancelled" in str(e) or "No such file" in str(e):
                return None
            raise e

    async def send_media(message, file_path, caption, thumb_path=None):
        file_type = get_file_type(file_path)
        thumb = thumb_path if thumb_path and os.path.exists(thumb_path) else None
        file_size = os.path.getsize(file_path)
    
        if not file_path or not os.path.exists(file_path):
            return None
    
        total_mb = file_size / 1024 / 1024
        
        try:
            upload_msg = await message.reply_text("📤 Preparing upload...")
        except:
            upload_msg = None
    
        tracker = ProgressTracker(upload_msg, file_size, "upload") if upload_msg else None
    
        async def upload_progress(current, total):
            if tracker:
                await tracker.update(current)
    
        try:
            if file_type == "video":
                result = await message.reply_video(file_path, caption=caption, thumb=thumb, progress=upload_progress, supports_streaming=True)
            elif file_type == "photo":
                result = await message.reply_photo(file_path, caption=caption, progress=upload_progress)
            elif file_type == "audio":
                result = await message.reply_audio(file_path, caption=caption, thumb=thumb, progress=upload_progress)
            else:
                result = await message.reply_document(file_path, caption=caption, thumb=thumb, progress=upload_progress)
    
        except FloodWait as e:
        
            if tracker:
                tracker.stop()
            
            if upload_msg:
                rate_tracker = RateLimitTracker(upload_msg, e.value)
                await rate_tracker.countdown()
            
            try:
                if file_type == "video":
                    result = await message.reply_video(file_path, caption=caption, thumb=thumb, supports_streaming=True)
                else:
                    result = await message.reply_document(file_path, caption=caption, thumb=thumb)
            except Exception as e2:
                logger.error(f"Retry failed: {e2}")
                result = None
    
        except Exception as e:
            logger.warning(f"Send failed: {e}")
            if tracker:
                tracker.stop()
            try:
                result = await message.reply_document(file_path, caption=caption)
            except:
                result = None
    
        finally:
            if tracker:
                tracker.stop()
            try:
                if upload_msg:
                    await upload_msg.delete()
            except:
                pass
    
        return result

    # ==================== CANCEL ====================
    @bot.on_message(filters.command("cancel"))
    async def cancel_command(client, message):
        if message.from_user:
            user_id = message.from_user.id
        else:
            user_id = message.chat.id
        
        # flag💀
        active_downloads[user_id] = False
        
        # Cancel running task✅
        if user_id in download_tasks:
            try:
                download_tasks[user_id].cancel()
            except:
                pass
            download_tasks.pop(user_id, None)
        
        await asyncio.sleep(0.5)
        
        for f in glob.glob("downloads/*"):
            try:
                os.remove(f)
            except:
                pass
        
        await message.reply_text(f"{NEKO_SLEEP}\n\n**Download cancelled!** 💤")

    # ==================== DOWNLOAD SINGLE ====================

    @bot.on_message(filters.command("dl"))
    async def download_single(client, message):
        user = message.from_user
        if not user:
            await message.reply_text(f"{NEKO_ANGRY}\n\n**Cannot identify user!** 😾")
            return
    
        user_id = user.id
        username = user.username or "unknown"
        first_name = user.first_name or "unknown"
        
        if await db.is_banned(user_id):
            await message.reply_text(f"{NEKO_ANGRY}\n\n**You are banned!** 😾")
            return
        
        # ==================== FORCE SUBSCRIBE ====================
        if not await check_force_sub(bot, user_id, message):
            return
        
        # ==================== ANTI-SPAM ====================
        if not await check_spam(user_id, message):
            return
        
        # ==================== DAILY LIMIT ====================
        if not await check_daily_limit(user_id, db, message):
            return
        
        await db.add_user(user_id, username, first_name)
    
        if len(message.command) < 2:
            await message.reply_text(f"{NEKO_CONFUSED}\n\n**Usage:** `/dl <link>`")
            return
    
        url = message.command[1]
        chat_id, msg_id = extract_link_info(url)
    
        if not chat_id or not msg_id:
            await message.reply_text(f"{NEKO_ANGRY}\n\n**Invalid link!** 😾")
            return
    
        loading = await message.reply_text(NEKO_LOADING)
    
        download_client = None
        client_source = ""
    
        user_client = await get_user_client(user_id)
        if user_client:
            try:
                test_msg = await user_client.get_messages(chat_id, msg_id)
                if test_msg:
                    download_client = user_client
                    client_source = "your account"
                    await loading.edit_text(f"{NEKO_FOUND}\n\n**Using your account** ✅")
            except (ChannelPrivate, UserNotParticipant, PeerIdInvalid):
                await loading.edit_text(f"{NEKO_CONFUSED}\n\n**Cannot access** ❌\nTrying fallback...")
            except Exception as e:
                logger.warning(f"User client: {e}")
    
        if not download_client:
            admin_client = await get_user_client("admin")
            if admin_client:
                try:
                    test_msg = await admin_client.get_messages(chat_id, msg_id)
                    if test_msg:
                        download_client = admin_client
                        client_source = "admin account"
                        await loading.edit_text(f"{NEKO_FOUND}\n\n**Using admin** ✅")
                except (ChannelPrivate, UserNotParticipant, PeerIdInvalid):
                    pass
                except Exception as e:
                    logger.warning(f"Admin client: {e}")
    
        if not download_client:
            await loading.delete()
            await message.reply_text(f"{NEKO_SAD}\n\n**Cannot access!** 😿\nUse /login for private channels.")
            return
    
        # ==================== CONCURRENT LIMIT CHECK ====================
        active_count = len([d for d in active_downloads.values() if d])
        if active_count >= MAX_CONCURRENT_DOWNLOADS:
            await loading.delete()
            await message.reply_text(
                f"⏳ **Server busy!**\n"
                f"🔴 Active downloads: **{active_count}**/{MAX_CONCURRENT_DOWNLOADS}\n"
                f"🟢 Please wait a moment and try again..."
            )
            return
    
        # Track task
        task = asyncio.current_task()
        download_tasks[user_id] = task
    
        try:
            target_msg = await download_client.get_messages(chat_id, msg_id)
            if not target_msg:
                await loading.delete()
                await message.reply_text(f"{NEKO_SAD}\n\n**Not found!** 😿")
                return
            if target_msg.video:
                file_type_text = "📹 Video"
                file_size = target_msg.video.file_size or 0
            elif target_msg.document:
                file_type_text = "📄 Document"
                file_size = target_msg.document.file_size or 0
            elif target_msg.photo:
                file_type_text = "🖼 Photo"
                file_size = target_msg.photo.file_size or 0
            elif target_msg.audio:
                file_type_text = "🎵 Audio"
                file_size = target_msg.audio.file_size or 0
            else:
                file_type_text = "📦 Media"
                file_size = 0
            
            size_text = f"{file_size / 1024 / 1024:.1f} MB" if file_size > 0 else "Unknown"
            
            await loading.edit_text(
                f"**╭━━━━━ 🎯 Content Found ━━━━━╮**\n\n"
                f"📡 **Source:** {client_source}\n"
                f"📦 **Type:** {file_type_text}\n"
                f"💾 **Size:** {size_text}\n\n"
                f"**╰━━━━━━━━━━━━━━━━━━━━━━━━━━╯**"
            )
            os.makedirs("downloads", exist_ok=True)
            progress_msg = await message.reply_text(NEKO_DOWNLOADING)
    
            custom_caption = await db.get_caption(user_id)
    
            if target_msg.text and not target_msg.media:
                await progress_msg.delete()
                await message.reply_text(f"{NEKO_SUCCESS}\n\n📝 {custom_caption or target_msg.text}")
    
            elif target_msg.media:
                # ✅ Check cancel download 1
                if not active_downloads.get(user_id, True):
                    await progress_msg.delete()
                    await loading.delete()
                    await message.reply_text(f"{NEKO_SLEEP}\n\n**Download cancelled!** 💤")
                    return
    
                file_path = await download_media(target_msg, "downloads", progress_msg)
                await progress_msg.delete()
    
                # ✅ Check cancel download 2
                if not file_path:
                    await loading.delete()
                    await message.reply_text(f"{NEKO_SLEEP}\n\n**Download cancelled!** 💤")
                    return
    
                if not os.path.exists(file_path):
                    await message.reply_text(f"{NEKO_SAD}\n\n**Download failed!** 😿")
                    return
    
                caption = custom_caption or (target_msg.text[:1024] if target_msg.text else f"Downloaded via {client_source}")
                thumb_path = await db.get_thumbnail(user_id)
                await send_media(message, file_path, caption, thumb_path)
    
                # Log + Forward
                await log_and_forward(file_path, (user_id, first_name, username), url, client_source, download_client)
    
                if os.path.exists(file_path):
                    os.remove(file_path)
    
                await db.increment_download(user_id)
                await increment_daily_count(user_id, db)
                await message.reply_text(f"{NEKO_SUCCESS}\n\n**Done! Nyaa~!** 🎉\n📡 {client_source}")
    
        except FloodWait as e:
            await loading.delete()
            await asyncio.sleep(e.value)
        except asyncio.CancelledError:
            await loading.delete()
        except Exception as e:
            await loading.delete()
            if "Cancelled" in str(e):
                pass
            else:
                logger.error(f"Download error: {e}")
                await message.reply_text(f"{NEKO_ANGRY}\n\n**Failed!** 😿\n`{str(e)[:150]}`")
        finally:
            download_tasks.pop(user_id, None)
        
#=================BatchFix===============

    @bot.on_message(filters.command("bdl"))
    async def batch_download(client, message):
        user = message.from_user
        if not user:
            return
    
        user_id = user.id
        username = user.username or "unknown"
        first_name = user.first_name or "unknown"
    
        if await db.is_banned(user_id):
            return await message.reply_text(f"{NEKO_ANGRY}\n\n**Banned!**")
    
        if not await check_force_sub(bot, user_id, message):
            return
    
        if not await check_spam(user_id, message):
            return
    
        if not await check_daily_limit(user_id, db, message):
            return
    
        await db.add_user(user_id, username, first_name)
    
        if len(message.command) < 3:
            return await message.reply_text(f"{NEKO_CONFUSED}\n\n**Usage:** `/bdl <start> <end>`")
    
        start_chat, start_id = extract_link_info(message.command[1])
        end_chat, end_id = extract_link_info(message.command[2])
    
        if not all([start_chat, start_id, end_chat, end_id]) or start_chat != end_chat:
            return await message.reply_text(f"{NEKO_ANGRY}\n\n**Invalid links!**")
    
        if start_id > end_id:
            start_id, end_id = end_id, start_id
    
        total = end_id - start_id + 1
        dc = await get_user_client(user_id) or await get_user_client("admin")
        if not dc:
            return await message.reply_text(f"{NEKO_SAD}\n\n**No account!**")
    
        task = asyncio.current_task()
        download_tasks[user_id] = task
        active_downloads[user_id] = True
    
        status = await message.reply_text(
            f"**╭━━━━━ 📦 Batch Download ━━━━━╮**\n\n"
            f"📊 **Total:** {total} posts\n"
            f"📂 **Channel:** `{start_chat}`\n\n"
            f"**╰━━━━━━━━━━━━━━━━━━━━━━━━━━╯**"
        )
        success, failed = 0, 0
        os.makedirs("downloads", exist_ok=True)
    
        try:
            for i, mid in enumerate(range(start_id, end_id + 1)):
                if not active_downloads.get(user_id, True):
                    await status.edit_text(
                        f"**╭━━━━━ ❌ Cancelled ━━━━━╮**\n\n"
                        f"✅ {success} | ❌ {failed} | 📊 {total}\n\n"
                        f"**╰━━━━━━━━━━━━━━━━━━━━━━╯**"
                    )
                    return
    
                try:
                    msg = await dc.get_messages(start_chat, mid)
                    if msg and msg.media:
                        file_size = msg.video.file_size if msg.video else msg.document.file_size if msg.document else msg.audio.file_size if msg.audio else 0
                        progress_msg = await message.reply_text(
                            f"**╭━━━ ⬇️ File {i+1}/{total} ━━━╮**\n\n"
                            f"`{'○' * 20}`\n\n"
                            f"**0.0%**\n"
                            f"📦 **0.0** / **{file_size / 1024 / 1024:.1f} MB**\n\n"
                            f"**╰━━━━━━━━━━━━━━━━━━━━━━╯**"
                        )
                        
                        fp = await download_media(msg, "downloads", progress_msg)
                        await progress_msg.delete()
                        
                        if fp and os.path.exists(fp):
                            await send_media(message, fp, msg.text[:500] if msg.text else None)
                            batch_url = f"https://t.me/c/{str(start_chat)[4:]}/{mid}"
                            await log_and_forward(fp, (user_id, first_name, username), batch_url, "batch", dc)
                            os.remove(fp)
                            success += 1
                            await db.increment_download(user_id)
                            await increment_daily_count(user_id, db)
                    elif msg and msg.text:
                        await message.reply_text(f"📝 {msg.text[:500]}")
                        success += 1
                    
                    if i % 5 == 0:
                        percent = (i + 1) / total * 100
                        bar_length = 20
                        filled = int(bar_length * (i + 1) / total)
                        bar = "●" * filled + "○" * (bar_length - filled)
                        
                        await status.edit_text(
                            f"**╭━━━━━ 📦 Batch {i+1}/{total} ━━━━━╮**\n\n"
                            f"`{bar}`\n"
                            f"**{percent:.1f}%**\n"
                            f"✅ **{success}** | ❌ **{failed}**\n\n"
                            f"**╰━━━━━━━━━━━━━━━━━━━━━━━━━━╯**"
                        )
                    
                    await asyncio.sleep(1)
                except FloodWait as e:
                    await asyncio.sleep(e.value)
                except:
                    failed += 1
    
            await status.edit_text(
                f"**╭━━━━━ ✅ Batch Complete ━━━━━╮**\n\n"
                f"📊 Total: **{total}**\n"
                f"✅ Success: **{success}**\n"
                f"❌ Failed: **{failed}**\n\n"
                f"**╰━━━━━━━━━━━━━━━━━━━━━━━━━━╯**"
            )
        except asyncio.CancelledError:
            try:
                await status.edit_text(
                    f"**╭━━━━━ ❌ Cancelled ━━━━━╮**\n\n"
                    f"✅ {success} | ❌ {failed} | 📊 {total}\n\n"
                    f"**╰━━━━━━━━━━━━━━━━━━━━━━╯**"
                )
            except:
                pass
        finally:
            download_tasks.pop(user_id, None)
            active_downloads.pop(user_id, None)

    # ==================== AUTO-DETECT ====================
    @bot.on_message(
        filters.regex(r"(?:https?://)?(?:t\.me|telegram\.(?:me|dog))/[^/\s]+/\d+")
        & ~filters.command(["dl", "bdl", "start", "help", "login", "logout", "settings", "cancel"])
    )
    async def auto_detect_link(client, message):
        if not message.text:
            return
        urls = re.findall(r"(?:https?://)?(?:t\.me|telegram\.(?:me|dog))/[^/\s]+/\d+", message.text)
        if urls:
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("📥 Download", callback_data=f"dl_{urls[0]}"),
                 InlineKeyboardButton("📦 Batch", callback_data=f"batch_{urls[0]}")],
                [InlineKeyboardButton("❌ Cancel", callback_data="cancel")]
            ])
            await message.reply_text(f"{NEKO_FOUND}\n\n**Link detected!** 🐾", reply_markup=keyboard)