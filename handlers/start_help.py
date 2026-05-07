# AcXNeko - SaveContent video channel with privat or not
# =============================================================================
# Project   : AcxNekoBor
# Developer : Kazeru
# GitHub    : https://github.com/Rsslnew
# Telegram  : https://telegram.me/K69661

from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from neko_art import NEKO_WAVE, NEKO_HELP, NEKO_SLEEP, NEKO_ANGRY
from handlers.auth import user_clients

def register(bot: Client, db):
    """Register start and help handlers."""

    @bot.on_message(filters.command("start"))
    async def start_command(client, message):
        """Start command with Neko greeting."""
        user_id = message.from_user.id
        username = message.from_user.username or "unknown"
        first_name = message.from_user.first_name or "User"

        # Save user
        await db.add_user(user_id, username, first_name)

        # Check banned
        if await db.is_banned(user_id):
            await message.reply_text(
                f"{NEKO_ANGRY}\n\n"
                "**You have been banned!** 😾\n"
                "Contact admin if you think this is a mistake."
            )
            return

        # Login status
        try:
            is_logged_in = user_id in user_clients
            login_status = "🔐 Logged In" if is_logged_in else "🔓 Not Logged In"
        except:
            login_status = "🔓 Not Logged In"

        # status prem ✅
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

        await message.reply_text(
            f"**Hi {first_name}!** 😁\n\n"
            f"I am **AcxNeko** - Save Restricted Content Bot\n\n"
            f"🐾 I can help you retrieve and forward restricted content from Telegram posts.\n\n"
            f"💎 **Premium Status:** {premium_status}\n"
            f"🔐 **Login Status:** {login_status}\n\n",
            reply_markup=keyboard
        )

    @bot.on_message(filters.command("help"))
    async def help_command(client, message):
        """Help command."""
        user_id = message.from_user.id

        await db.add_user(user_id, message.from_user.username, message.from_user.first_name)

        help_text = f"""
{NEKO_HELP}

**📚 AcxNeko Help**

**Main Commands:**
🐾 `/dl <link>` - Download content from a single post
🐾 `/bdl <start> <end>` - Batch download multiple posts
🐾 `/start` - Start the bot
🐾 `/help` - Show this help
🐾 `/settings` - Open settings menu
🐾 `/myplan` - Check your current plan
🐾 `/premium` - View premium info

**Customization Commands:**
🎨 `/set_caption <text>` - Set custom caption
🎨 `/see_caption` - View current caption
🎨 `/del_caption` - Delete caption
🖼 `/set_thumb` - Set custom thumbnail (reply to image)
🖼 `/view_thumb` - View current thumbnail
🖼 `/del_thumb` - Delete thumbnail

**Batch Example:**
`/bdl https://t.me/channel/100 https://t.me/channel/120`

**Notes:**
📌 Bot must be a member of the source channel
📌 Max file size: 2GB

{NEKO_SLEEP}
        """
        await message.reply_text(help_text)