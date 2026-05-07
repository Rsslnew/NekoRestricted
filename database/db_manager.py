# AcXNeko - SaveContent video channel with privat or not
# =============================================================================
# Project   : AcxNekoBor
# Developer : Kazeru
# GitHub    : https://github.com/Rsslnew
# Telegram  : https://telegram.me/K69661

import logging
from datetime import datetime
from typing import Optional
from motor.motor_asyncio import AsyncIOMotorClient
from config import DB_URI, DB_NAME

logger = logging.getLogger(__name__)

class Database:
    """MongoDB database manager class."""

    def __init__(self):
        self.client = None
        self.db = None
        self.users = None

    async def connect(self):
        """Connect to MongoDB."""
        try:
            self.client = AsyncIOMotorClient(DB_URI)
            self.db = self.client[DB_NAME]
            self.users = self.db["users"]

            # Test connection
            await self.client.admin.command("ping")
            logger.info("MongoDB connected successfully!")

            # Create indexes
            await self.users.create_index("user_id", unique=True)
            logger.info("Database indexes created!")

        except Exception as e:
            logger.error(f"MongoDB connection failed: {e}")
            raise

    async def disconnect(self):
        """Close MongoDB connection."""
        if self.client:
            self.client.close()
            logger.info("MongoDB connection closed.")

    # ==================== USER MANAGEMENT ====================
    async def add_user(self, user_id: int, username: str = None, first_name: str = None):
        """Add a new user to database."""
        user_data = {
            "user_id": user_id,
            "username": username,
            "first_name": first_name,
            "joined_date": datetime.utcnow(),
            "is_banned": False,
            "is_premium": False,
            "premium_expiry": None,
            "download_count": 0,
            "settings": {
                "caption": None,
                "thumbnail": None,
                "thumb_mode": False,
                "delete_words": [],
                "replace_words": {}
            }
        }

        try:
            await self.users.update_one(
                {"user_id": user_id},
                {"$setOnInsert": user_data},
                upsert=True
            )
            logger.info(f"User {user_id} added/updated in database.")
        except Exception as e:
            logger.error(f"Error adding user {user_id}: {e}")

    async def get_user(self, user_id: int):
        """Get user data from database."""
        try:
            return await self.users.find_one({"user_id": user_id})
        except Exception as e:
            logger.error(f"Error getting user {user_id}: {e}")
            return None

    async def update_user(self, user_id: int, data: dict):
        """Update user data."""
        try:
            await self.users.update_one(
                {"user_id": user_id},
                {"$set": data}
            )
            logger.info(f"User {user_id} data updated.")
        except Exception as e:
            logger.error(f"Error updating user {user_id}: {e}")

    # ==================== BAN MANAGEMENT ====================
    async def ban_user(self, user_id: int):
        """Ban a user."""
        await self.update_user(user_id, {"is_banned": True})

    async def unban_user(self, user_id: int):
        """Unban a user."""
        await self.update_user(user_id, {"is_banned": False})

    async def is_banned(self, user_id: int) -> bool:
        """Check if user is banned."""
        user = await self.get_user(user_id)
        return user.get("is_banned", False) if user else False

    # ==================== PREMIUM MANAGEMENT ====================
    async def add_premium(self, user_id: int, expiry: datetime = None):
        """Grant premium access to user."""
        await self.update_user(user_id, {
            "is_premium": True,
            "premium_expiry": expiry
        })

    async def remove_premium(self, user_id: int):
        """Remove premium access from user."""
        await self.update_user(user_id, {
            "is_premium": False,
            "premium_expiry": None
        })

    async def is_premium(self, user_id: int) -> bool:
        """Check if user has premium access."""
        user = await self.get_user(user_id)
        if not user:
            return False

        if user.get("is_premium", False):
            expiry = user.get("premium_expiry")
            if expiry and expiry < datetime.utcnow():
                await self.remove_premium(user_id)
                return False
            return True
        return False

    # ==================== SETTINGS MANAGEMENT ====================
    async def set_caption(self, user_id: int, caption: str):
        """Set custom caption for user."""
        await self.users.update_one(
            {"user_id": user_id},
            {"$set": {"settings.caption": caption}}
        )

    async def get_caption(self, user_id: int):
        """Get user's custom caption."""
        user = await self.get_user(user_id)
        return user.get("settings", {}).get("caption") if user else None

    async def delete_caption(self, user_id: int):
        """Delete user's custom caption."""
        await self.users.update_one(
            {"user_id": user_id},
            {"$set": {"settings.caption": None}}
        )

    async def set_thumbnail(self, user_id: int, thumbnail: str):
        """Set custom thumbnail for user."""
        await self.users.update_one(
            {"user_id": user_id},
            {"$set": {"settings.thumbnail": thumbnail}}
        )

    async def get_thumbnail(self, user_id: int):
        """Get user's custom thumbnail."""
        user = await self.get_user(user_id)
        return user.get("settings", {}).get("thumbnail") if user else None

    async def delete_thumbnail(self, user_id: int):
        """Delete user's custom thumbnail."""
        await self.users.update_one(
            {"user_id": user_id},
            {"$set": {"settings.thumbnail": None}}
        )

    # ==================== STATISTICS ====================
    async def increment_download(self, user_id: int):
        """Increment user's download count."""
        await self.users.update_one(
            {"user_id": user_id},
            {"$inc": {"download_count": 1}}
        )

    async def get_total_users(self) -> int:
        """Get total number of users."""
        try:
            return await self.users.count_documents({})
        except Exception as e:
            logger.error(f"Error counting users: {e}")
            return 0

    async def get_premium_users(self) -> int:
        """Get number of premium users."""
        try:
            return await self.users.count_documents({"is_premium": True})
        except Exception as e:
            logger.error(f"Error counting premium users: {e}")
            return 0

    async def get_all_users(self):
        """Get all users for broadcast."""
        try:
            cursor = self.users.find({})
            users = []
            async for user in cursor:
                users.append(user["user_id"])
            return users
        except Exception as e:
            logger.error(f"Error getting all users: {e}")
            return []

    async def get_banned_users(self):
        """Get all banned users."""
        try:
            cursor = self.users.find({"is_banned": True})
            users = []
            async for user in cursor:
                users.append(user)
            return users
        except Exception as e:
            logger.error(f"Error getting banned users: {e}")
            return []

# ==================== SESSION MANAGEMENT ====================
    async def store_user_session(self, user_id: int, session_string: str):
        """Store user session string for persistent login."""
        try:
            await self.users.update_one(
                {"user_id": user_id},
                {"$set": {
                    "session_string": session_string,
                    "last_login": datetime.utcnow()
                }}
            )
            logger.info(f"Session stored for user {user_id}")
        except Exception as e:
            logger.error(f"Error storing session for {user_id}: {e}")
    
    async def get_user_session(self, user_id: int) -> Optional[str]:
        """Get user's stored session string."""
        try:
            user = await self.get_user(user_id)
            if user:
                return user.get("session_string")
            return None
        except Exception as e:
            logger.error(f"Error getting session for {user_id}: {e}")
            return None
    
    async def delete_user_session(self, user_id: int):
        """Delete user's stored session."""
        try:
            await self.users.update_one(
                {"user_id": user_id},
                {"$unset": {"session_string": "", "last_login": ""}}
            )
            logger.info(f"Session deleted for user {user_id}")
        except Exception as e:
            logger.error(f"Error deleting session for {user_id}: {e}")
    
    async def get_all_user_sessions(self) -> dict:
        """Get all stored user sessions (for restore on restart)."""
        try:
            cursor = self.users.find(
                {"session_string": {"$exists": True}},
                {"user_id": 1, "session_string": 1}
            )
            sessions = {}
            async for user in cursor:
                sessions[user["user_id"]] = user["session_string"]
            return sessions
        except Exception as e:
            logger.error(f"Error getting all sessions: {e}")
            return {}