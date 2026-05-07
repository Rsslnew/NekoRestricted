# AcXNeko - SaveContent video channel with privat or not
# =============================================================================
# Project   : AcxNekoBor
# Developer : Kazeru
# GitHub    : https://github.com/Rsslnew
# Telegram  : https://telegram.me/K69661

import time
from neko_art import NEKO_DOWNLOADING, NEKO_UPLOAD, NEKO_PROGRESS_FILLED, NEKO_PROGRESS_EMPTY

class ProgressTracker:
    """Modern progress bar with Neko themes & animations."""

    def __init__(self, message, total_size: int, action: str = "download"):
        self.message = message
        self.total = total_size
        self.current = 0
        self.start_time = time.time()
        self.action = action  # "download" or "upload"
        self.done = False
        
        # Animation frames
        self.frames = {
            "download": ["⬇️", "📥", "⏬", "📨"],
            "upload": ["⬆️", "📤", "⏫", "📨"]
        }
        
        self.fill = "●"
        self.empty = "○"

    def stop(self):
        """Stop updating"""
        self.done = True

    async def update(self, current: int):
        """Update progress display."""
        if self.done:
            return
            
        self.current = current

        if self.total > 0:
            percent = current * 100 / self.total
            bar_length = 20
            filled = int(bar_length * current / self.total)
            bar = self.fill * filled + self.empty * (bar_length - filled)

            elapsed = time.time() - self.start_time
            speed = current / (elapsed + 0.1)
            eta = (self.total - current) / (speed + 0.1)

            # Format sizes
            current_mb = current / 1024 / 1024
            total_mb = self.total / 1024 / 1024

            # Speed format
            if speed > 1024 * 1024:
                speed_text = f"{speed / 1024 / 1024:.1f} MB/s"
            elif speed > 1024:
                speed_text = f"{speed / 1024:.0f} KB/s"
            else:
                speed_text = f"{speed:.0f} B/s"

            # ETA format
            if eta > 3600:
                eta_text = f"{eta / 3600:.1f}h"
            elif eta > 60:
                eta_text = f"{eta / 60:.0f}m {eta % 60:.0f}s"
            else:
                eta_text = f"{eta:.0f}s"

            # Animation frame
            frames = self.frames.get(self.action, ["🔄"])
            frame_idx = int(percent / 25) % len(frames)
            
            # Action text
            action_text = "Downloading" if self.action == "download" else "Uploading"

            # Modern design
            text = (
                f"**╭━━━ {frames[frame_idx]} {action_text} ━━━╮**\n\n"
                f"`{bar}`\n\n"
                f"**{percent:.1f}%**\n"
                f"📦 **{current_mb:.1f}** / **{total_mb:.1f} MB**\n\n"
                f"⚡ **{speed_text}**  ⏳ **{eta_text}**\n\n"
                f"**╰━━━━━━━━━━━━━━━━━━━━━━╯**"
            )

            try:
                await self.message.edit_text(text)
            except Exception:
                pass


class ClassicProgress:
    """Simple classic progress bar (original style)."""

    def __init__(self, message, total_size: int):
        self.message = message
        self.total = total_size
        self.current = 0
        self.start_time = time.time()

    async def update(self, current: int):
        """Update progress display."""
        self.current = current

        if self.total > 0:
            percent = current * 100 / self.total
            bar_length = 20
            filled = int(bar_length * current / self.total)
            bar = NEKO_PROGRESS_FILLED * filled + NEKO_PROGRESS_EMPTY * (bar_length - filled)

            elapsed = time.time() - self.start_time
            speed = current / (elapsed + 0.1)
            eta = (self.total - current) / (speed + 0.1)

            try:
                await self.message.edit_text(
                    f"{NEKO_DOWNLOADING}\n\n"
                    f"`{bar}`\n"
                    f"**{percent:.1f}%** | "
                    f"**{current / 1024 / 1024:.1f}/{self.total / 1024 / 1024:.1f} MB**\n"
                    f"⚡ **{speed / 1024 / 1024:.1f} MB/s** | ⏳ **{eta:.0f}s**"
                )
            except Exception:
                pass


class RateLimitTracker:
    """Track and display rate limit countdown."""

    def __init__(self, message, wait_time: int):
        self.message = message
        self.wait_time = wait_time
        self.done = False

    def stop(self):
        """Stop updating."""
        self.done = True

    async def countdown(self):
        """Display countdown in real-time."""
        for remaining in range(self.wait_time, 0, -10):
            if self.done:
                return
            
            minutes = remaining // 60
            seconds = remaining % 60
            
            text = (
                f"**╭━━━ ⏳ Rate Limited ━━━╮**\n\n"
                f"⏰ Waiting: **{minutes}m {seconds}s**\n"
                f"🔄 Auto-retry after countdown...\n\n"
                f"**╰━━━━━━━━━━━━━━━━━━━━╯**"
            )
            
            try:
                await self.message.edit_text(text)
            except:
                pass
            
            await self.safe_sleep(min(10, remaining))

    async def safe_sleep(self, seconds):
        """Sleep without blocking."""
        import asyncio
        await asyncio.sleep(seconds)