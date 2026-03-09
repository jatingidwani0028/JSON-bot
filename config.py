"""
Configuration file for the Telegram JSON Manager Bot.
Update BOT_TOKEN and ADMIN_IDS before running.
"""

import os
from pathlib import Path

# ─── Bot Credentials ────────────────────────────────────────────────────────
BOT_TOKEN: str = os.getenv("BOT_TOKEN", "8699319947:AAHvnLrxUo3grJnszxhlyqv09dCiU6CbE5")

# ─── Admin Control ───────────────────────────────────────────────────────────
# Add Telegram user IDs of admins here (integers)
ADMIN_IDS: list[int] = [
    8403558393,  # Replace with your Telegram user ID
]

# ─── Paths ───────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent
JSON_STORAGE_DIR = BASE_DIR / "json_storage"
DATABASE_PATH = BASE_DIR / "database" / "json_manager.db"
LOG_FILE = BASE_DIR / "logs" / "bot.log"

# Ensure directories exist
JSON_STORAGE_DIR.mkdir(parents=True, exist_ok=True)
DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

# ─── Performance Settings ────────────────────────────────────────────────────
# How many unused JSON IDs to show in /unused command
UNUSED_DISPLAY_LIMIT: int = 50

# Max JSON file size in bytes (5 MB default)
MAX_JSON_FILE_SIZE: int = 5 * 1024 * 1024

# Cache TTL in seconds
CACHE_TTL: int = 300
