# AcXNeko - SaveContent video channel with privat or not
# =============================================================================
# Project   : AcxNekoBor
# Developer : Kazeru
# GitHub    : https://github.com/Rsslnew
# Telegram  : https://telegram.me/K69661

import re
import time
import os
from typing import Tuple, Optional

def extract_link_info(url: str) -> Tuple[Optional[str], Optional[int]]:
    """Extract chat ID and message ID from Telegram link."""
    patterns = [
        r"(?:https?://)?(?:t\.me|telegram\.(?:me|dog))/([^/]+)/(\d+)",
        r"(?:https?://)?(?:t\.me|telegram\.(?:me|dog))/c/(\d+)/(\d+)",
    ]
    for pattern in patterns:
        match = re.match(pattern, url)
        if match:
            chat_id = match.group(1)
            msg_id = int(match.group(2))
            if chat_id.isdigit() and len(chat_id) >= 10:
                chat_id = int(f"-100{chat_id}")
            return chat_id, msg_id
    return None, None

def format_time(seconds: float) -> str:
    """Format seconds to human readable string."""
    if seconds < 60:
        return f"{seconds:.0f}s"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.1f}m"
    else:
        hours = seconds / 3600
        return f"{hours:.1f}h"

def format_size(size_bytes: float) -> str:
    """Format bytes to human readable string."""
    if size_bytes < 1024:
        return f"{size_bytes:.0f} B"
    elif size_bytes < 1048576:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1073741824:
        return f"{size_bytes / 1048576:.1f} MB"
    else:
        return f"{size_bytes / 1073741824:.1f} GB"

def format_speed(speed: float) -> str:
    """Format speed to human readable string."""
    if speed > 1024 * 1024:
        return f"{speed / 1024 / 1024:.1f} MB/s"
    elif speed > 1024:
        return f"{speed / 1024:.0f} KB/s"
    else:
        return f"{speed:.0f} B/s"

def format_eta(seconds: float) -> str:

    if seconds > 3600:
        return f"{seconds / 3600:.1f}h"
    elif seconds > 60:
        return f"{seconds / 60:.0f}m {seconds % 60:.0f}s"
    else:
        return f"{seconds:.0f}s"

def get_file_extension(file_path: str) -> str:

    return os.path.splitext(file_path)[1].lower()

def clean_filename(filename: str) -> str:
    return re.sub(r'[<>:"/\\|?*]', '_', filename)