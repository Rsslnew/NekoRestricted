# AcXNeko - SaveContent video channel with privat or not
# =============================================================================
# Project   : AcxNekoBor
# Developer : Kazeru
# GitHub    : https://github.com/Rsslnew
# Telegram  : https://telegram.me/K69661

import asyncio
import logging
from pyrogram import Client, filters
from pyrogram.errors import (
    SessionPasswordNeeded, PhoneCodeInvalid,
    PhoneCodeExpired, PasswordHashInvalid
)

from config import ALLOW_USER_LOGIN, MAX_LOGIN_USERS, API_ID, API_HASH
from neko_art import *

logger = logging.getLogger(__name__)

user_clients = {}
pending_logins = {}

def register(bot: Client, db, admin_client=None):
    """Register authentication handlers."""

    async def get_user_client(user_id):
        if user_id == "admin":
            return admin_client

        if user_id in user_clients:
            client = user_clients[user_id]
            try:
                await client.get_me()
                return client
            except Exception:
                try:
                    await client.stop()
                except:
                    pass
                del user_clients[user_id]
                await db.delete_user_session(user_id)

        session_string = await db.get_user_session(user_id)
        if session_string:
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
                return client
            except Exception as e:
                logger.warning(f"Failed to restore session for {user_id}: {e}")
                await db.delete_user_session(user_id)

        return admin_client

    @bot.on_message(filters.command("login"))
    async def login_command(client, message):
        user = message.from_user
        if not user:
            await message.reply_text("**Cannot identify user!** 😾")
            return

        user_id = user.id

        if not ALLOW_USER_LOGIN:
            await message.reply_text("**User login is currently disabled!**")
            return

        if user_id in user_clients:
            await message.reply_text("**You're already logged in!** ✅\nUse `/logout` first.")
            return

        if len(user_clients) >= MAX_LOGIN_USERS:
            await message.reply_text(f"**Login slots full!** 😿")
            return

        pending_logins[user_id] = {"step": "phone", "chat_id": message.chat.id}

        await message.reply_text(
            f"{NEKO_WAVE}\n\n"
            "**🐱 Login to AcxNeko**\n\n"
            "📱 Send your **phone number** with country code.\n"
            "Example: `+6281234567890`\n\n"
            "❌ Type `/cancel` to abort"
        )

    @bot.on_message(filters.text & ~filters.command([
        "login", "logout", "dl", "bdl", "start", "help", "cancel",
        "add_premium", "remove_premium", "whoami", "myplan", "premium",
        "settings", "set_caption", "see_caption", "del_caption",
        "set_thumb", "view_thumb", "del_thumb", "broadcast",
        "ban", "unban", "users", "premium_users", "stats"
    ]))
    async def handle_login_input(client, message):
        user = message.from_user
        if not user:
            return

        user_id = user.id

        # Cancel: fix ✅
        if message.text and message.text.strip() == "/cancel":
            if user_id in pending_logins:
                del pending_logins[user_id]
            return

        if user_id not in pending_logins:
            return

        state = pending_logins[user_id]

        # Step 1: Phone number
        if state["step"] == "phone":
            phone_number = message.text.strip()

            if not phone_number.startswith("+") or not phone_number[1:].isdigit():
                await message.reply_text(f"{NEKO_ANGRY}\n\n**Invalid phone format!** 😾")
                return

            pending_logins[user_id] = {"step": "code", "phone": phone_number, "chat_id": message.chat.id}

            status_msg = await message.reply_text(f"{NEKO_LOADING}\n\n**Sending code...** 📨")

            try:
                temp_client = Client(f"temp_{user_id}", api_id=API_ID, api_hash=API_HASH, in_memory=True)
                await temp_client.connect()

                sent_code = await temp_client.send_code(phone_number)
                pending_logins[user_id]["temp_client"] = temp_client
                pending_logins[user_id]["phone_code_hash"] = sent_code.phone_code_hash

                await status_msg.edit_text(
                    f"{NEKO_FOUND}\n\n"
                    f"**Code sent to** `{phone_number}` 📱\n\n"
                    "Enter the code **with spaces**:\n"
                    "Example: `1 2 3 4 5`"
                )
            except Exception as e:
                await temp_client.disconnect()
                del pending_logins[user_id]
                await status_msg.edit_text(f"❌ Failed: `{str(e)[:100]}`")

        # Step 2: Verification code
        elif state["step"] == "code":
            verification_code = message.text.strip()
            # codee with spasi like 1 2 3 4 5
            temp_client = state.get("temp_client")

            if not temp_client:
                del pending_logins[user_id]
                await message.reply_text("❌ Session expired.")
                return

            status_msg = await message.reply_text(f"{NEKO_LOADING}\n\n**Verifying...** 🔐")

            try:
                try:
                    await temp_client.sign_in(state["phone"], state["phone_code_hash"], verification_code)
                except SessionPasswordNeeded:
                    pending_logins[user_id]["step"] = "password"
                    await status_msg.edit_text(f"{NEKO_CONFUSED}\n\n**🔐 2FA Enabled!**\nEnter your password:")
                    return

                session_string = await temp_client.export_session_string()
                await db.store_user_session(user_id, session_string)

                await temp_client.disconnect()
                del pending_logins[user_id]

                new_client = Client(f"user_{user_id}", api_id=API_ID, api_hash=API_HASH, session_string=session_string, in_memory=True)
                await new_client.start()
                user_clients[user_id] = new_client

                me = await new_client.get_me()

                await status_msg.edit_text(
                    f"{NEKO_SUCCESS}\n\n"
                    f"**Login Successful!** 🎉\n\n"
                    f"👤 {me.first_name}\n"
                    f"📱 {state['phone']}\n\n"
                    "✅ You can now access private channels!"
                )

            except PhoneCodeInvalid:
                await temp_client.disconnect()
                del pending_logins[user_id]
                await status_msg.edit_text("❌ Invalid code!")
            except PhoneCodeExpired:
                await temp_client.disconnect()
                del pending_logins[user_id]
                await status_msg.edit_text("⏰ Code expired!")
            except Exception as e:
                await temp_client.disconnect()
                del pending_logins[user_id]
                await status_msg.edit_text(f"❌ Failed: `{str(e)[:100]}`")

        # Step 3: 2FA Password
        elif state["step"] == "password":
            password = message.text.strip()
            temp_client = state.get("temp_client")

            if not temp_client:
                del pending_logins[user_id]
                await message.reply_text("❌ Session expired.")
                return

            status_msg = await message.reply_text(f"{NEKO_LOADING}\n\n**Checking...** 🔐")

            try:
                await temp_client.check_password(password)

                session_string = await temp_client.export_session_string()
                await db.store_user_session(user_id, session_string)

                await temp_client.disconnect()
                del pending_logins[user_id]

                new_client = Client(f"user_{user_id}", api_id=API_ID, api_hash=API_HASH, session_string=session_string, in_memory=True)
                await new_client.start()
                user_clients[user_id] = new_client

                me = await new_client.get_me()

                await status_msg.edit_text(
                    f"{NEKO_SUCCESS}\n\n"
                    f"**Login Successful!** 🎉\n\n"
                    f"👤 {me.first_name}\n"
                    f"📱 {state.get('phone', 'N/A')}\n\n"
                    "✅ You can now access private channels!"
                )

            except PasswordHashInvalid:
                await temp_client.disconnect()
                del pending_logins[user_id]
                await status_msg.edit_text(f"{NEKO_ANGRY}\n\n**Wrong password!** 😾")
            except Exception as e:
                await temp_client.disconnect()
                del pending_logins[user_id]
                await status_msg.edit_text(f"❌ Failed: `{str(e)[:100]}`")

    @bot.on_message(filters.command("logout"))
    async def logout_command(client, message):
        user = message.from_user
        if not user:
            return

        user_id = user.id

        if user_id not in user_clients:
            await message.reply_text("❌ Not logged in.")
            return

        try:
            await user_clients[user_id].stop()
        except:
            pass

        del user_clients[user_id]
        await db.delete_user_session(user_id)

        await message.reply_text("✅ Logged out successfully.")

    @bot.on_message(filters.command("whoami"))
    async def whoami_command(client, message):
        user_id = message.from_user.id

        if user_id in user_clients:
            try:
                me = await user_clients[user_id].get_me()
                await message.reply_text(f"{NEKO_FOUND}\n\n**🔐 Logged In**\n\n👤 {me.first_name}\n💎 Personal Account")
            except Exception:
                await message.reply_text(f"{NEKO_SAD}\n\n**Session expired!** Use `/login`.")
        else:
            if admin_client:
                await message.reply_text(f"{NEKO_FOUND}\n\n**🤖 Default Mode**\n💡 Use `/login` for private channels.")
            else:
                await message.reply_text(f"{NEKO_SAD}\n\n**No account!** Use `/login`.")

    return get_user_client