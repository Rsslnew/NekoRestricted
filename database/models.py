# AcXNeko - SaveContent video channel with privat or not
# =============================================================================
# Project   : AcxNekoBor
# Developer : Kazeru
# GitHub    : https://github.com/Rsslnew
# Telegram  : https://telegram.me/K69661

from dataclasses import dataclass, field
from typing import List, Dict, Optional
from datetime import datetime

@dataclass
class UserSettings:
    """User settings model."""
    caption: Optional[str] = None
    thumbnail: Optional[str] = None
    thumb_mode: bool = False
    delete_words: List[str] = field(default_factory=list)
    replace_words: Dict[str, str] = field(default_factory=dict)

@dataclass
class User:
    user_id: int
    username: Optional[str] = None
    first_name: Optional[str] = None
    joined_date: datetime = field(default_factory=datetime.utcnow)
    is_banned: bool = False
    is_premium: bool = False
    premium_expiry: Optional[datetime] = None
    download_count: int = 0
    settings: UserSettings = field(default_factory=UserSettings)

    def to_dict(self) -> dict:
        return {
            "user_id": self.user_id,
            "username": self.username,
            "first_name": self.first_name,
            "joined_date": self.joined_date,
            "is_banned": self.is_banned,
            "is_premium": self.is_premium,
            "premium_expiry": self.premium_expiry,
            "download_count": self.download_count,
            "settings": {
                "caption": self.settings.caption,
                "thumbnail": self.settings.thumbnail,
                "thumb_mode": self.settings.thumb_mode,
                "delete_words": self.settings.delete_words,
                "replace_words": self.settings.replace_words,
            }
        }