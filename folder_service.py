"""
Folder service — all business logic related to folder management.
"""

import logging
from typing import Optional
from database.database import get_db
from database.models import Folder, FolderStats
from utils.file_manager import create_folder_on_disk

logger = logging.getLogger(__name__)


async def create_folder(folder_name: str) -> tuple[bool, str]:
    """
    Create a new folder in DB and on disk.
    Returns (success: bool, message: str).
    """
    folder_name = folder_name.strip().lower()
    if not folder_name.isidentifier() and not all(
        c.isalnum() or c == "_" for c in folder_name
    ):
        return False, "❌ Invalid folder name. Use only letters, numbers, and underscores."

    async with await get_db() as db:
        # Check for duplicate
        async with db.execute(
            "SELECT id FROM folders WHERE folder_name = ?", (folder_name,)
        ) as cur:
            if await cur.fetchone():
                return False, f"⚠️ Folder *{folder_name}* already exists."

        # Insert into DB
        await db.execute(
            "INSERT INTO folders (folder_name) VALUES (?)", (folder_name,)
        )
        await db.commit()

    # Create on disk
    create_folder_on_disk(folder_name)
    logger.info("Created folder: %s", folder_name)
    return True, f"✅ Folder *{folder_name}* created successfully."


async def list_folders() -> list[Folder]:
    """Return all folders ordered by name."""
    async with await get_db() as db:
        async with db.execute(
            "SELECT id, folder_name, created_at FROM folders ORDER BY folder_name"
        ) as cur:
            rows = await cur.fetchall()
    return [Folder(id=r["id"], folder_name=r["folder_name"], created_at=r["created_at"]) for r in rows]


async def get_folder_by_name(folder_name: str) -> Optional[Folder]:
    """Retrieve a single folder by name (case-insensitive)."""
    async with await get_db() as db:
        async with db.execute(
            "SELECT id, folder_name, created_at FROM folders WHERE folder_name = ?",
            (folder_name.lower(),),
        ) as cur:
            row = await cur.fetchone()
    if row:
        return Folder(id=row["id"], folder_name=row["folder_name"], created_at=row["created_at"])
    return None


async def get_folder_stats(folder_name: str) -> Optional[FolderStats]:
    """Return usage statistics for a folder."""
    folder = await get_folder_by_name(folder_name)
    if not folder:
        return None

    async with await get_db() as db:
        async with db.execute(
            """
            SELECT
                COUNT(*)                                   AS total,
                SUM(CASE WHEN status='USED'   THEN 1 ELSE 0 END) AS used,
                SUM(CASE WHEN status='UNUSED' THEN 1 ELSE 0 END) AS unused
            FROM json_files
            WHERE folder_id = ?
            """,
            (folder.id,),
        ) as cur:
            row = await cur.fetchone()

    return FolderStats(
        folder_name=folder.folder_name,
        total=row["total"] or 0,
        used=row["used"] or 0,
        unused=row["unused"] or 0,
    )
