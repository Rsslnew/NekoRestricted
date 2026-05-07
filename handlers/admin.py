"""
# AcXNeko - SaveContent video channel with privat or not
# =============================================================================
# Project   : AcxNekoBor
# Developer : Kazeru
# GitHub    : https://github.com/Rsslnew
# Telegram  : https://telegram.me/K69661
"""

import asyncio
from datetime import datetime, timedelta
from pyrogram import Client, filters

from config import ADMINS
from neko_art import *

def register(bot: Client, db):
    """Register admin handlers."""

    # ==================== SAFE USER ====================
    def get_user_safe(message):
        user = message.from_user
        if not user:
            return None, None
        return user, user.id

    # ==================== ADMIN CHECK ====================
    def is_admin(func):
        async def wrapper(client, message):
            user, user_id = get_user_safe(message)
            if not user:
                await message.reply_text("❌ Cannot identify user.")
                return

            if user_id not in ADMINS:
                await message.reply_text(
                    f"{NEKO_ANGRY}\n\n**Admin only command!** 😾"
                )
                return

            return await func(client, message)

        return wrapper

    # ==================== BROADCAST ====================
    @bot.on_message(filters.command("broadcast"))
    @is_admin
    async def broadcast_command(client, message):

        if len(message.command) < 2 and not message.reply_to_message:
            await message.reply_text("Usage: `/broadcast <message>`")
            return

        broadcast_msg = message.reply_to_message or message
        users = await db.get_all_users()

        success, failed = 0, 0
        status_msg = await message.reply_text("📡 Broadcasting...")

        for user_id in users:
            try:
                await broadcast_msg.copy(user_id)
                success += 1
            except Exception:
                failed += 1

            await asyncio.sleep(0.1)

        await status_msg.edit_text(
            f"✅ Done\nSuccess: {success}\nFailed: {failed}"
        )

    # ==================== BAN ====================
    @bot.on_message(filters.command("ban"))
    @is_admin
    async def ban_command(client, message):

        if len(message.command) < 2 and not message.reply_to_message:
            await message.reply_text("Usage: `/ban <user_id>` or reply.")
            return

        if message.reply_to_message:
            target = message.reply_to_message.from_user
            if not target:
                await message.reply_text("❌ Cannot get user.")
                return
            user_id = target.id
        else:
            try:
                user_id = int(message.command[1])
            except:
                await message.reply_text("❌ Invalid ID.")
                return

        await db.ban_user(user_id)
        await message.reply_text(f"🚫 User {user_id} banned.")

    # ==================== UNBAN ====================
    @bot.on_message(filters.command("unban"))
    @is_admin
    async def unban_command(client, message):

        if len(message.command) < 2:
            await message.reply_text("Usage: `/unban <user_id>`")
            return

        try:
            user_id = int(message.command[1])
        except:
            await message.reply_text("❌ Invalid ID.")
            return

        await db.unban_user(user_id)
        await message.reply_text(f"✅ User {user_id} unbanned.")

    # ==================== ADD PREMIUM ====================
    @bot.on_message(filters.command("add_premium"))
    @is_admin
    async def add_premium_command(client, message):

        if len(message.command) < 2:
            await message.reply_text("Usage: `/add_premium <user_id> [days]`")
            return

        try:
            user_id = int(message.command[1])
        except:
            await message.reply_text("❌ Invalid ID.")
            return

        try:
            days = int(message.command[2]) if len(message.command) > 2 else 30
        except:
            days = 30

        expiry = datetime.utcnow() + timedelta(days=days)
        await db.add_premium(user_id, expiry)

        await message.reply_text(
            f"💎 Premium granted\nUser: {user_id}\nDays: {days}"
        )

    # ==================== REMOVE PREMIUM ====================
    @bot.on_message(filters.command("remove_premium"))
    @is_admin
    async def remove_premium_command(client, message):

        if len(message.command) < 2:
            await message.reply_text("Usage: `/remove_premium <user_id>`")
            return

        try:
            user_id = int(message.command[1])
        except:
            await message.reply_text("❌ Invalid ID.")
            return

        await db.remove_premium(user_id)
        await message.reply_text(f"✅ Premium removed from {user_id}")

    # ==================== USERS ====================
    @bot.on_message(filters.command("users"))
    @is_admin
    async def users_command(client, message):

        total = await db.get_total_users()
        premium = await db.get_premium_users()

        await message.reply_text(
            f"👥 Total: {total}\n💎 Premium: {premium}\n🆓 Free: {total - premium}"
        )

    # ==================== PREMIUM USERS ====================
    @bot.on_message(filters.command("premium_users"))
    @is_admin
    async def premium_users_command(client, message):

        premium_users = await db.get_premium_users()
        await message.reply_text(f"💎 Premium Users:\n{premium_users}")