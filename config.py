# AcXNeko - SaveContent video channel with privat or not
# =============================================================================
# Project   : AcxNekoBor
# Developer : Kazeru
# GitHub    : https://github.com/Rsslnew
# Telegram  : https://telegram.me/K69661

import os
from dotenv import load_dotenv

# Load environment variables from config.env
load_dotenv("config.env", override=True)

# ==================== REQUIRED CONFIGURATION ====================
API_ID = int(os.getenv("API_ID", 0))
API_HASH = os.getenv("API_HASH", "")
BOT_TOKEN = os.getenv("BOT_TOKEN", "")

# ==================== SESSION MODE ====================
SESSION_STRING = os.getenv("SESSION_STRING", "")

ALLOW_USER_LOGIN = os.getenv("ALLOW_USER_LOGIN", "True").lower() == "true"
MAX_LOGIN_USERS = int(os.getenv("MAX_LOGIN_USERS", "100"))

# ==================== DATABASE CONFIGURATION ====================
DB_URI = os.getenv("DB_URI", "u mongo")
DB_NAME = os.getenv("DB_NAME", "AcxNekoDB")

# ==================== ADMIN CONFIGURATION ====================
ADMINS = os.getenv("ADMINS", "")

# ==================== OPTIONAL CONFIGURATION ====================
FORWARD_CHAT_ID = os.getenv("FORWARD_CHAT_ID", "")

LOG_CHANNEL = os.getenv("LOG_CHANNEL", "")

ERROR_MESSAGE = os.getenv("ERROR_MESSAGE", "True").lower() == "true"
KEEP_ALIVE = os.getenv("KEEP_ALIVE", "False").lower() == "true"
KEEP_ALIVE_URL = os.getenv("KEEP_ALIVE_URL", "")

# ==================== DOWNLOAD LIMITS ====================
# Free user daily limit
FREE_DAILY_LIMIT = int(os.getenv("FREE_DAILY_LIMIT", "10"))

# Max concurrent downloads
MAX_CONCURRENT_DOWNLOADS = int(os.getenv("MAX_CONCURRENT_DOWNLOADS", "3"))

# Batch download delay (seconds between posts)
BATCH_DELAY = float(os.getenv("BATCH_DELAY", "1.0"))

# ==================== FILE SIZE LIMITS ====================
# Telegram max file size: 2GB
MAX_FILE_SIZE = int(os.getenv("MAX_FILE_SIZE", str(2000 * 1024 * 1024)))

# ==================== TEMP DIRECTORY ====================
TEMP_DIR = os.getenv("TEMP_DIR", "downloads")
THUMB_DIR = os.getenv("THUMB_DIR", "thumbnails")
LOG_DIR = os.getenv("LOG_DIR", "logs")

# ==================== VALIDATION ====================
def validate_config():
    """
    Validate required configuration.
    Prints errors and exits if critical config is missing.
    """
    errors = []
    warnings = []

    # Critical checks✅
    if not API_ID:
        errors.append("❌ API_ID is required! Get it from https://my.telegram.org")
    
    if not API_HASH:
        errors.append("❌ API_HASH is required! Get it from https://my.telegram.org")
    
    if not BOT_TOKEN:
        errors.append("❌ BOT_TOKEN is required! Get it from @BotFather")
    
    if not DB_URI:
        errors.append("❌ DB_URI is required! Get it from MongoDB Atlas or local instance")

    # At least one download mode must be available
    if not SESSION_STRING and not ALLOW_USER_LOGIN:
        errors.append(
            "❌ Either SESSION_STRING or ALLOW_USER_LOGIN must be configured!\n"
            "   • SESSION_STRING: For admin fallback account\n"
            "   • ALLOW_USER_LOGIN=True: For user login mode"
        )

    # Warnings (non-critical)
    if not SESSION_STRING:
        warnings.append(
            "⚠️  SESSION_STRING not set. Admin fallback disabled.\n"
            "   Users MUST /login to download content."
        )
    
    if not ALLOW_USER_LOGIN:
        warnings.append(
            "⚠️  ALLOW_USER_LOGIN is disabled.\n"
            "   Users cannot login with their own accounts.\n"
            "   Private channel access may be limited."
        )
    
    if not ADMINS:
        warnings.append(
            "⚠️  No ADMINS configured.\n"
            "   Admin commands will not be available.\n"
            "   Set ADMINS=your_telegram_id in config.env"
        )

    # Print warnings
    if warnings:
        print("\n" + "=" * 50)
        print("⚠️  WARNINGS:")
        print("=" * 50)
        for warning in warnings:
            print(f"  {warning}")
        print("=" * 50 + "\n")

    # Print errors and exit
    if errors:
        print("\n" + "=" * 50)
        print("❌ CONFIGURATION ERRORS:")
        print("=" * 50)
        for error in errors:
            print(f"  {error}")
        print("=" * 50)
        print("\n💡 Please fix the errors above in your config.env file.")
        print("   Then restart the bot.\n")
        exit(1)

    # Success
    print("=" * 50)
    print("✅ Configuration Validated Successfully!")
    print("=" * 50)
    print(f"  🤖 Bot Token: {'Set' if BOT_TOKEN else 'MISSING'}")
    print(f"  👤 Admin Session: {'Set' if SESSION_STRING else 'Not Set (Login Mode Only)'}")
    print(f"  🔐 User Login: {'Enabled' if ALLOW_USER_LOGIN else 'Disabled'}")
    print(f"  💾 Database: {'Set' if DB_URI else 'MISSING'}")
    print(f"  👑 Admins: {len(ADMINS)} user(s)")
    print(f"  📤 Forward: {'Enabled' if FORWARD_CHAT_ID else 'Disabled'}")
    print(f"  📝 Log Channel: {'Enabled' if LOG_CHANNEL else 'Disabled'}")
    print("=" * 50 + "\n")

# ==================== AUTO VALIDATE ON IMPORT ====================
validate_config()

# ==================== HELPER FUNCTIONS ====================
def get_config_dict() -> dict:
    """
    Get all configuration as a dictionary.
    Useful for debugging and logging.
    """
    return {
        "api_id": API_ID,
        "api_hash": "***HIDDEN***",
        "bot_token": "***HIDDEN***",
        "session_string_set": bool(SESSION_STRING),
        "allow_user_login": ALLOW_USER_LOGIN,
        "max_login_users": MAX_LOGIN_USERS,
        "db_uri": DB_URI.split("@")[-1] if "@" in DB_URI else DB_URI,  # Hide dont remove ☠️
        "db_name": DB_NAME,
        "admins": ADMINS,
        "forward_chat_id": FORWARD_CHAT_ID,
        "log_channel": LOG_CHANNEL,
        "error_message": ERROR_MESSAGE,
        "keep_alive": KEEP_ALIVE,
        "free_daily_limit": FREE_DAILY_LIMIT,
        "max_concurrent": MAX_CONCURRENT_DOWNLOADS,
        "batch_delay": BATCH_DELAY,
        "max_file_size": MAX_FILE_SIZE,
    }

def is_admin(user_id: int) -> bool:
    """Check if a user is admin."""
    return user_id in ADMINS

def can_download(user_id: int, is_premium: bool, download_count: int) -> bool:
    """Check if user can download based on limits."""
    if is_premium:
        return True
    return download_count < FREE_DAILY_LIMIT

# ==================== EXPORT ALL ====================
__all__ = [
    "API_ID", "API_HASH", "BOT_TOKEN",
    "SESSION_STRING", "ALLOW_USER_LOGIN", "MAX_LOGIN_USERS",
    "DB_URI", "DB_NAME",
    "ADMINS",
    "FORWARD_CHAT_ID", "LOG_CHANNEL",
    "ERROR_MESSAGE", "KEEP_ALIVE", "KEEP_ALIVE_URL",
    "FREE_DAILY_LIMIT", "MAX_CONCURRENT_DOWNLOADS", "BATCH_DELAY",
    "MAX_FILE_SIZE",
    "TEMP_DIR", "THUMB_DIR", "LOG_DIR",
    "is_admin", "can_download", "get_config_dict",
]