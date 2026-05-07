"""
# AcXNeko - SaveContent video channel with privat or not
# =============================================================================
# Project   : AcxNekoBor
# Developer : Kazeru
# GitHub    : https://github.com/Rsslnew
# Telegram  : https://telegram.me/K69661
"""

import os
from pyrogram import Client, filters
from neko_art import *

def register(bot: Client, db):
    """Register settings handlers."""

    # ==================== SAFE USER HELPER ====================
    def get_user_safe(message):
        user = message.from_user
        if not user:
            return None, None
        return user, user.id

    # ==================== SETTINGS ====================
    @bot.on_message(filters.command("settings"))
    async def settings_command(client, message):
        user, user_id = get_user_safe(message)
        if not user:
            await message.reply_text("❌ Cannot identify user.")
            return

        if await db.is_banned(user_id):
            await message.reply_text(f"{NEKO_ANGRY}\n\n**You are banned!** 😾")
            return

        user_data = await db.get_user(user_id)

        caption = user_data.get("settings", {}).get("caption") if user_data else None
        thumbnail = user_data.get("settings", {}).get("thumbnail") if user_data else None
        downloads = user_data.get("download_count", 0) if user_data else 0
        is_premium = user_data.get("is_premium", False) if user_data else False

        settings_text = (
            f"∧,,,∧\n"
            f"( ・ω・)⚙  **Settings**\n\n"
            f"🎨 **Caption:** {'✅ Set' if caption else '❌ Not set'}\n"
            f"🖼 **Thumbnail:** {'✅ Set' if thumbnail else '❌ Not set'}\n"
            f"💎 **Plan:** {'✨ Premium' if is_premium else '🆓 Free'}\n"
            f"📥 **Downloads:** {downloads}\n\n"
            f"**📝 Caption Commands:**\n"
            f"`/set_caption <text>` - Set custom caption\n"
            f"`/see_caption` - View your caption\n"
            f"`/del_caption` - Delete caption\n\n"
            f"**🖼 Thumbnail Commands:**\n"
            f"`/set_thumb` - Reply to an image\n"
            f"`/view_thumb` - View thumbnail\n"
            f"`/del_thumb` - Delete thumbnail"
        )
        await message.reply_text(settings_text)

    # ==================== SET CAPTION ====================
    @bot.on_message(filters.command("set_caption"))
    async def set_caption(client, message):
        user, user_id = get_user_safe(message)
        if not user:
            return

        if len(message.command) < 2:
            await message.reply_text(
                "❌ **Usage:** `/set_caption <your text>`\n"
                "Example: `/set_caption Downloaded by @username`"
            )
            return

        caption = message.text.split(maxsplit=1)[1]
        await db.set_caption(user_id, caption)

        await message.reply_text(
            f"✅ **Caption saved!**\n"
            f"📝 `{caption[:200]}`"
        )

    # ==================== SEE CAPTION ====================
    @bot.on_message(filters.command("see_caption"))
    async def see_caption(client, message):
        user, user_id = get_user_safe(message)
        if not user:
            return

        caption = await db.get_caption(user_id)

        if caption:
            await message.reply_text(f"📝 **Your Caption:**\n`{caption}`")
        else:
            await message.reply_text("❌ **No caption set!**\nUse `/set_caption <text>`")

    # ==================== DELETE CAPTION ====================
    @bot.on_message(filters.command("del_caption"))
    async def del_caption(client, message):
        user, user_id = get_user_safe(message)
        if not user:
            return

        await db.delete_caption(user_id)
        await message.reply_text("✅ **Caption deleted!**")

    # ==================== SET THUMB ====================
    @bot.on_message(filters.command("set_thumb"))
    async def set_thumb(client, message):
        user, user_id = get_user_safe(message)
        if not user:
            return

        if not message.reply_to_message or not message.reply_to_message.photo:
            await message.reply_text(
                "❌ **Reply to an image** to set it as thumbnail!\n"
                "Example: Reply to a photo with `/set_thumb`"
            )
            return

        os.makedirs("thumbnails", exist_ok=True)
        thumb_path = f"thumbnails/{user_id}.jpg"

        try:
            await message.reply_to_message.download(thumb_path)
            await db.set_thumbnail(user_id, thumb_path)
            await message.reply_text("🖼 **Thumbnail set successfully!** ✅")
        except Exception:
            await message.reply_text("❌ **Failed to set thumbnail.**")

    # ==================== VIEW THUMB ====================
    @bot.on_message(filters.command("view_thumb"))
    async def view_thumb(client, message):
        user, user_id = get_user_safe(message)
        if not user:
            return

        thumb_path = await db.get_thumbnail(user_id)

        if thumb_path and os.path.exists(thumb_path):
            await message.reply_photo(thumb_path, caption="🖼 **Your Thumbnail**")
        else:
            await message.reply_text("❌ **No thumbnail set!**\nReply to an image with `/set_thumb`")

    # ==================== DELETE THUMB ====================
    @bot.on_message(filters.command("del_thumb"))
    async def del_thumb(client, message):
        user, user_id = get_user_safe(message)
        if not user:
            return

        thumb_path = await db.get_thumbnail(user_id)

        if thumb_path and os.path.exists(thumb_path):
            try:
                os.remove(thumb_path)
            except:
                pass

        await db.delete_thumbnail(user_id)
        await message.reply_text("✅ **Thumbnail deleted!**")

    # ==================== MY PLAN ====================
    @bot.on_message(filters.command("myplan"))
    async def myplan_command(client, message):
        user, user_id = get_user_safe(message)
        if not user:
            return

        is_premium = await db.is_premium(user_id)
        user_data = await db.get_user(user_id)
        downloads = user_data.get("download_count", 0) if user_data else 0

        if is_premium:
            expiry = user_data.get("premium_expiry", "Forever") if user_data else "Forever"
            text = (
                f"💎 **Premium Plan** ✨\n\n"
                f"📥 Downloads: **{downloads}** (Unlimited)\n"
                f"⏰ Expiry: **{expiry}**\n\n"
                f"✅ All features unlocked!"
            )
        else:
            text = (
                f"🆓 **Free Plan**\n\n"
                f"📥 Downloads: **{downloads}/10** today\n"
                f"💡 Upgrade to premium for unlimited access!\n"
                f"Contact @K69661"
            )

        await message.reply_text(text)

    # ==================== PREMIUM INFO ====================
    @bot.on_message(filters.command("premium"))
    async def premium_info(client, message):
        await message.reply_text(
            f"💎 **AcxNeko Premium** ✨\n\n"
            f"**Benefits:**\n"
            f"✨ Unlimited downloads\n"
            f"🎨 Custom captions\n"
            f"🖼 Custom thumbnails\n"
            f"⚡ Priority support\n"
            f"🔐 Access all features\n\n"
            f"**How to get:**\n"
            f"📩 Contact @K69661 for pricing\n\n"
            f"💡 Use `/myplan` to check your status"
        )
        
    # ============= Status ======≠
    
    @bot.on_message(filters.command("stats"))
    async def stats_command(client, message):
        import psutil
        
        cpu = psutil.cpu_percent()
        ram = psutil.virtual_memory().percent
        disk = psutil.disk_usage('/').percent
        total_users = await db.get_total_users()
        premium_users = await db.get_premium_users()
    
        text = (
            f"📊 **Bot Stats**\n\n"
            f"👥 Users: **{total_users}**\n"
            f"💎 Premium: **{premium_users}**\n"
            f"🖥 CPU: **{cpu}%**\n"
            f"💾 RAM: **{ram}%**\n"
            f"💿 Disk: **{disk}%**"
        )
        await message.reply_text(text)