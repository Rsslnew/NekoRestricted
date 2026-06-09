import time
import asyncio
from datetime import datetime, timedelta
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import FREE_DAILY_LIMIT

user_last_request = {}
user_daily_downloads = {}

FORCE_SUB_CHANNEL = "@ACxio999"
SPAM_DELAY = 5


async def check_force_sub(bot, user_id, message=None):
    """Check if user joined force sub channel."""
    try:
        member = await bot.get_chat_member(FORCE_SUB_CHANNEL, user_id)
        if member.status in ("left", "kicked", "banned"):
            if message:
                keyboard = InlineKeyboardMarkup([
                    [InlineKeyboardButton("📢 Join Channel", url=f"https://t.me/{FORCE_SUB_CHANNEL.replace('@', '')}")],
                    [InlineKeyboardButton("🔄 Try Again", callback_data="check_sub")]
                ])
                await message.reply_text(
                    f"🔒 **Access Restricted!**\n\n"
                    f"You must join **{FORCE_SUB_CHANNEL}** to use this bot.\n\n"
                    f"After joining, click 'Try Again' or send /start",
                    reply_markup=keyboard
                )
            return False
        return True
    except Exception:
        return True

async def check_spam(user_id, message=None):
    """Check if user is spamming."""
    if user_id in user_last_request:
        elapsed = time.time() - user_last_request[user_id]
        if elapsed < SPAM_DELAY:
            if message:
                remaining = int(SPAM_DELAY - elapsed)
                await message.reply_text(f"⏳ **Slow down!** Wait {remaining}s...")
            return False
    user_last_request[user_id] = time.time()
    return True


async def check_daily_limit(user_id, db, message=None):

    today = datetime.now().strftime("%Y-%m-%d")
    user = await db.get_user(user_id)
    db_last_reset = None
    if user and user.get("last_reset"):
        db_last_reset = user["last_reset"].strftime("%Y-%m-%d") if isinstance(user["last_reset"], datetime) else str(user["last_reset"])[:10]

    db_count = user.get("daily_count", 0) if user else 0
    if user_id not in user_daily_downloads:
        user_daily_downloads[user_id] = {"date": db_last_reset or today, "count": db_count}

    if user_daily_downloads[user_id]["date"] != today:
        user_daily_downloads[user_id] = {"date": today, "count": db_count}
        await db.reset_daily_count(user_id)

    is_premium = await db.is_premium(user_id)
    if is_premium:
        return True

    count = user_daily_downloads[user_id]["count"]
    if count >= FREE_DAILY_LIMIT:
        if message:
            await message.reply_text(
                f"📊 **Daily Limit Reached!**\n\n"
                f"🔴 {count}/{FREE_DAILY_LIMIT} downloads used today\n"
                f"💎 Upgrade to premium for unlimited!\n"
                f"Contact @K69661"
            )
        return False

    return True


async def increment_daily_count(user_id, db):

    today = datetime.now().strftime("%Y-%m-%d")

    if user_id not in user_daily_downloads:
        user_daily_downloads[user_id] = {"date": today, "count": 0}

    user_daily_downloads[user_id]["count"] += 1
    await db.users.update_one(
        {"user_id": user_id},
        {"$inc": {"daily_count": 1}, "$set": {"last_reset": datetime.utcnow()}}
    )


async def daily_reset_loop(db):

    while True:
        now = datetime.now()
        tomorrow = (now + timedelta(days=1)).replace(hour=0, minute=0, second=1)
        seconds_until_midnight = (tomorrow - now).seconds
        await asyncio.sleep(seconds_until_midnight)

        user_daily_downloads.clear()
        await db.reset_all_daily_counts()
        print("🔄 Daily limits reset!")

async def load_daily_counts(db):
    all_users = await db.get_all_user_data()
    today = datetime.now().strftime("%Y-%m-%d")

    loaded = 0
    for user in all_users:
        user_id = user.get("user_id")
        if not user_id:
            continue

        last_reset = user.get("last_reset")
        if last_reset:
            last_reset_str = last_reset.strftime("%Y-%m-%d") if isinstance(last_reset, datetime) else str(last_reset)[:10]
        else:
            last_reset_str = ""

        if last_reset_str == today:
            count = user.get("daily_count", 0)
            user_daily_downloads[user_id] = {"date": today, "count": count}
            loaded += 1
        else:
            user_daily_downloads[user_id] = {"date": today, "count": 0}

    print(f"🔄 Restored {loaded} daily counts from DB")
