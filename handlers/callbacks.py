"""
# AcXNeko - SaveContent video channel with privat or not
# =============================================================================
# Project   : AcxNekoBor
# Developer : Kazeru
# GitHub    : https://github.com/Rsslnew
# Telegram  : https://telegram.me/K69661
"""

from pyrogram import Client
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import ADMINS
from neko_art import *

def back_button():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 Back to Menu", callback_data="back_to_start")]
    ])

def main_menu():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📖 Help", callback_data="help"),
            InlineKeyboardButton("ℹ️ About", callback_data="about")
        ],
        [
            InlineKeyboardButton("⚙️ Settings", callback_data="settings_main"),
            InlineKeyboardButton("💎 Premium", callback_data="premium_info")
        ]
    ])

def register(bot: Client, db, user_client: Client):
    """Register callback handlers."""

    @bot.on_callback_query()
    async def callback_handler(client, callback_query):
        # ==================== SAFE USER ====================
        user = callback_query.from_user
        if not user:
            await callback_query.answer("Cannot identify user", show_alert=True)
            return

        user_id = user.id
        first_name = user.first_name or "User"
        data = callback_query.data or ""

        # ==================== ADMIN CHECK ====================
        if data.startswith("admin_"):
            if user_id not in ADMINS:
                await callback_query.answer("Admin only!", show_alert=True)
                return

        # ==================== BACK TO START ====================
        
        if data == "back_to_start":
            # Cek premium
            is_premium = await db.is_premium(user_id)
            premium_status = "✅ Active" if is_premium else "❌ Inactive - Use /premium to upgrade!"
            
            keyboard = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("📢 Update Channel", url="https://t.me/ACxio999"),
                    InlineKeyboardButton("💬 Support Group", url="https://t.me/ACxio6660")
                ],
                [
                    InlineKeyboardButton("👤 Developer", url="https://t.me/K69661"),
                    InlineKeyboardButton("📖 Help", callback_data="help")
                ],
                [
                    InlineKeyboardButton("⚙️ Settings", callback_data="settings_main"),
                    InlineKeyboardButton("💎 Premium", callback_data="premium_info")
                ],
                [
                    InlineKeyboardButton("🔒 Close", callback_data="cancel")
                ]
            ])
            
            await callback_query.message.edit_text(
                f"**Hi {first_name}!** 😁\n\n"
                f"I am **AcxNeko** - Save Restricted Content Bot\n\n"
                f"🐾 I can help you retrieve and forward restricted content from Telegram posts.\n\n"
                f"💎 **Premium Status:** {premium_status}\n\n",
                reply_markup=keyboard
            )

        # ==================== DOWNLOAD ====================
        elif data.startswith("dl_"):
            url = data[3:]
            await callback_query.message.delete()
            await client.send_message(callback_query.message.chat.id, f"/dl {url}")

        # ==================== CANCEL ====================
        elif data == "cancel":
            await callback_query.message.delete()

        # ==================== HELP ====================
        elif data == "help":
            help_text = (
                "∧,,,∧\n"
                "( ・ω・)ﾉ  **AcxNeko Help**\n\n"
                "📥 `/dl <link>` - Download single post\n"
                "📦 `/bdl <s> <e>` - Batch download\n"
                "🔐 `/login` - Login your account\n"
                "🚪 `/logout` - Logout session\n"
                "👤 `/whoami` - Check status\n"
                "⚙️ `/settings` - Settings menu\n"
                "💎 `/myplan` - Your plan\n\n"
                "🎨 `/set_caption` - Set caption\n"
                "🖼 `/set_thumb` - Set thumbnail\n\n"
                "📌 **Example:**\n"
                "`/dl https://t.me/ch/100`\n"
                "`/bdl https://t.me/ch/100 https://t.me/ch/120`\n\n"
                "ฅ^•ﻌ•^ฅ"
            )
            await callback_query.message.edit_text(help_text, reply_markup=back_button())

        # ==================== ABOUT ====================
        elif data == "about":
            about_text = (
                "∧,,,∧\n"
                "( ^ω^)  **About AcxNeko**\n\n"
                "🐱 **Version:** 2.0.0\n"
                "💾 **Database:** MongoDB\n"
                "👤 **Creator:** @K69661\n"
                "📚 **Library:** Pyrogram\n\n"
                "**Features:**\n"
                "📥 Restricted content downloader\n"
                "🔐 Dual login mode\n"
                "📊 Progress bar with Neko\n"
                "📦 Batch download support\n\n"
                "Made with ❤️ and 🐱"
            )
            await callback_query.message.edit_text(about_text, reply_markup=back_button())

        # ==================== SETTINGS ====================
        elif data == "settings_main":
            user_data = await db.get_user(user_id)
            caption = user_data.get("settings", {}).get("caption") if user_data else None
            thumbnail = user_data.get("settings", {}).get("thumbnail") if user_data else None
            is_premium = user_data.get("is_premium", False) if user_data else False
            download_count = user_data.get("download_count", 0) if user_data else 0

            settings_text = (
                "∧,,,∧\n"
                "( ・ω・)⚙  **Settings**\n\n"
                f"🎨 **Caption:** {'✅ Set' if caption else '❌ Not set'}\n"
                f"🖼 **Thumbnail:** {'✅ Set' if thumbnail else '❌ Not set'}\n"
                f"💎 **Plan:** {'✨ Premium' if is_premium else '🆓 Free'}\n"
                f"📥 **Downloads:** {download_count}\n\n"
                "**Commands:**\n"
                "`/set_caption <text>` - Set caption\n"
                "`/see_caption` - View caption\n"
                "`/del_caption` - Delete caption\n"
                "`/set_thumb` - Set thumbnail\n"
                "`/view_thumb` - View thumbnail\n"
                "`/del_thumb` - Delete thumbnail"
            )
            await callback_query.message.edit_text(settings_text, reply_markup=back_button())

        # ==================== PREMIUM ====================
        elif data == "premium_info":
            premium_text = (
                "∧,,,∧\n"
                "( ・ω・)✨  **AcxNeko Premium**\n\n"
                "**Benefits:**\n"
                "✨ Unlimited downloads\n"
                "✨ Custom captions\n"
                "✨ Custom thumbnails\n"
                "✨ Priority support\n\n"
                "**How to get:**\n"
                "Contact @K69661\n\n"
                "ฅ^•ﻌ•^ฅ"
            )
            await callback_query.message.edit_text(premium_text, reply_markup=back_button())

        # ==================== ANSWER ====================
        try:
            await callback_query.answer()
        except:
            pass