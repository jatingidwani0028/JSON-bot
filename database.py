"""
Database connection and initialization module.
Uses aiosqlite for fully async SQLite access.
"""

import aiosqlite
import logging
from pathlib import Path
from config import DATABASE_PATH

logger = logging.getLogger(__name__)

# Singleton connection pool reference
_db_path: str = str(DATABASE_PATH)


async def get_db() -> aiosqlite.Connection:
    """Open and return an async database connection with row factory."""
    conn = await aiosqlite.connect(_db_path)
    conn.row_factory = aiosqlite.Row  # Access columns by name
    await conn.execute("PRAGMA journal_mode=WAL")   # Better concurrency
    await conn.execute("PRAGMA synchronous=NORMAL") # Faster writes
    await conn.execute("PRAGMA cache_size=-64000")  # 64 MB cache
    await conn.execute("PRAGMA foreign_keys=ON")
    return conn


async def init_db() -> None:
    """Create all tables and indexes on startup."""
    logger.info("Initializing database at %s", _db_path)
    async with await get_db() as db:
        # ── Folders table ──────────────────────────────────────────────────
        await db.execute("""
            CREATE TABLE IF NOT EXISTS folders (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                folder_name TEXT    NOT NULL UNIQUE COLLATE NOCASE,
                created_at  TEXT    NOT NULL DEFAULT (datetime('now'))
            )
        """)

        # ── JSON files table ────────────────────────────────────────────────
        await db.execute("""
            CREATE TABLE IF NOT EXISTS json_files (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                folder_id   INTEGER NOT NULL REFERENCES folders(id) ON DELETE CASCADE,
                json_number INTEGER NOT NULL,
                file_path   TEXT    NOT NULL,
                status      TEXT    NOT NULL DEFAULT 'UNUSED' CHECK(status IN ('USED','UNUSED')),
                created_at  TEXT    NOT NULL DEFAULT (datetime('now')),
                UNIQUE(folder_id, json_number)
            )
        """)

        # ── Performance indexes ─────────────────────────────────────────────
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_json_folder_number
            ON json_files(folder_id, json_number)
        """)
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_json_status
            ON json_files(folder_id, status)
        """)
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_folders_name
            ON folders(folder_name)
        """)

        await db.commit()
    logger.info("Database initialized successfully.")
