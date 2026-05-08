# AcXNeko - SaveContent video channel with privat or not
# =============================================================================
# Project   : AcxNekoBor
# Developer : Kazeru
# GitHub    : https://github.com/Rsslnew
# Telegram  : https://telegram.me/K69661

import os
import asyncio
import logging
from pyrogram import Client

from config import (
    API_ID, API_HASH, BOT_TOKEN,
    SESSION_STRING, ALLOW_USER_LOGIN
)
from database.db_manager import Database
from handlers import start_help, download, settings, admin, auth, callbacks
from neko_art import NEKO_BANNER, NEKO_SUCCESS, NEKO_SLEEP
from utils.extras import daily_reset_loop

# ==================== LOGGING SETUP ====================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# ==================== ADMIN CLIENT (FALLBACK) ====================
admin_client = None
if SESSION_STRING:
    admin_client = Client(
        "admin_session",
        api_id=API_ID,
        api_hash=API_HASH,
        session_string=SESSION_STRING,
        in_memory=True
    )

# ==================== BOT CLIENT ====================
bot = Client(
    "acx_neko_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
    in_memory=True
)

# ==================== DATABASE ====================
db = Database()

# ==================== GLOBAL USER CLIENTS STORE ====================
user_clients = {}

# ==================== REGISTER HANDLERS ====================
def register_handlers():
    """Register all command handlers."""
    
    # Auth handler (returns get_user_client function)
    get_user_client = auth.register(bot, db, admin_client)

    # Start & Help
    start_help.register(bot, db)

    # Download (pass get_user_client function)
    download.register(bot, db, get_user_client)

    # Settings
    settings.register(bot, db)

    # Admin
    admin.register(bot, db)

    # Callbacks (pass get_user_client function)
    callbacks.register(bot, db, get_user_client)

# ==================== MAIN ====================
async def main():
    """Main function to start the bot."""
    print(NEKO_BANNER)
    print("🐱 AcxNeko is starting...")
    print("📦 Connecting to MongoDB...")

    await db.connect()
    print(f"{NEKO_SUCCESS} MongoDB connected!")

    os.makedirs("downloads", exist_ok=True)
    os.makedirs("thumbnails", exist_ok=True)

    # Register handlers
    register_handlers()

    # Start admin client if configured
    if admin_client:
        await admin_client.start()
        me = await admin_client.get_me()
        print(f"👤 Admin Account: {me.first_name} (@{me.username if me.username else 'N/A'})")
    else:
        print("⚠️ No admin session configured. User login required.")

    # Restore saved user sessions from database
    saved_sessions = await db.get_all_user_sessions()
    for user_id, session_string in saved_sessions.items():
        try:
            client = Client(
                f"user_{user_id}",
                api_id=API_ID,
                api_hash=API_HASH,
                session_string=session_string,
                in_memory=True
            )
            await client.start()
            user_clients[user_id] = client
            logger.info(f"Restored session for user {user_id}")
        except Exception as e:
            logger.warning(f"Failed to restore session for user {user_id}: {e}")
            await db.delete_user_session(user_id)

    print(f"🔄 Restored {len(user_clients)} user sessions")

    # Start bot
    await bot.start()

    print(f"{NEKO_SUCCESS} Bot started successfully!")
    print(f"🤖 Bot: @{bot.me.username}")
    print(f"💾 Database: Connected")
    print(f"🔐 Login Mode: {'Enabled' if ALLOW_USER_LOGIN else 'Disabled'}")
    print(f"👤 Admin Fallback: {'Ready' if admin_client else 'None'}")
    print(f"🐱 Neko is purring and ready to serve!\n")

    # ==================== START DAILY RESET LOOP ====================
    asyncio.create_task(daily_reset_loop(db))
    print("🔄 Daily reset loop started!")

    await asyncio.Event().wait()

if __name__ == "__main__":
    try:
        bot.run(main())
    except KeyboardInterrupt:
        print(f"\n{NEKO_SLEEP} Bot stopped gracefully. Neko is sleeping...")
    except Exception as e:
        logger.error(f"Fatal error: {e}")