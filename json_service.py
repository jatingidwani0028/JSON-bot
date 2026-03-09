"""
JSON file service — upload, retrieval, status tracking, statistics.
"""

import json
import logging
from pathlib import Path
from typing import Optional

from database.database import get_db
from database.models import JsonFile
from services.folder_service import get_folder_by_name
from utils.file_manager import save_json_to_disk, get_json_path
from config import UNUSED_DISPLAY_LIMIT

logger = logging.getLogger(__name__)


async def save_json_file(folder_name: str, content: bytes) -> tuple[bool, str]:
    """
    Validate, number, and persist a new JSON file.
    Returns (success, message).
    """
    # 1. Validate JSON content
    try:
        json.loads(content)
    except json.JSONDecodeError as exc:
        return False, f"❌ Invalid JSON: {exc}"

    # 2. Resolve folder
    folder = await get_folder_by_name(folder_name)
    if not folder:
        return False, f"❌ Folder *{folder_name}* does not exist. Create it first with /create_folder."

    async with await get_db() as db:
        # 3. Assign next incremental number
        async with db.execute(
            "SELECT COALESCE(MAX(json_number), 0) + 1 FROM json_files WHERE folder_id = ?",
            (folder.id,),
        ) as cur:
            row = await cur.fetchone()
            next_number: int = row[0]

        # 4. Save file to disk
        file_path = save_json_to_disk(folder_name, next_number, content)

        # 5. Persist metadata
        await db.execute(
            """
            INSERT INTO json_files (folder_id, json_number, file_path, status)
            VALUES (?, ?, ?, 'UNUSED')
            """,
            (folder.id, next_number, str(file_path)),
        )
        await db.commit()

    logger.info("Saved JSON #%d to folder '%s'", next_number, folder_name)
    return True, f"✅ JSON saved as *#{next_number}* in folder *{folder_name}*."


async def get_json_file(folder_name: str, json_number: int) -> tuple[Optional[Path], str]:
    """
    Retrieve path to a JSON file by folder + number.
    Returns (path | None, message).
    """
    folder = await get_folder_by_name(folder_name)
    if not folder:
        return None, f"❌ Folder *{folder_name}* not found."

    async with await get_db() as db:
        async with db.execute(
            """
            SELECT file_path FROM json_files
            WHERE folder_id = ? AND json_number = ?
            """,
            (folder.id, json_number),
        ) as cur:
            row = await cur.fetchone()

    if not row:
        return None, f"❌ JSON *#{json_number}* not found in folder *{folder_name}*."

    path = Path(row["file_path"])
    if not path.exists():
        return None, f"❌ File for JSON *#{json_number}* is missing on disk."

    return path, f"📄 Sending JSON file *#{json_number}* from *{folder_name}*"


async def set_json_status(folder_name: str, json_number: int, status: str) -> tuple[bool, str]:
    """
    Mark a JSON file USED or UNUSED.
    Returns (success, message).
    """
    folder = await get_folder_by_name(folder_name)
    if not folder:
        return False, f"❌ Folder *{folder_name}* not found."

    async with await get_db() as db:
        async with db.execute(
            "SELECT id FROM json_files WHERE folder_id = ? AND json_number = ?",
            (folder.id, json_number),
        ) as cur:
            row = await cur.fetchone()

        if not row:
            return False, f"❌ JSON *#{json_number}* not found in *{folder_name}*."

        await db.execute(
            "UPDATE json_files SET status = ? WHERE id = ?",
            (status, row["id"]),
        )
        await db.commit()

    emoji = "✅" if status == "USED" else "🔄"
    logger.info("Marked JSON #%d in '%s' as %s", json_number, folder_name, status)
    return True, f"{emoji} JSON *#{json_number}* in *{folder_name}* marked as *{status}*."


async def get_unused_json_numbers(folder_name: str) -> tuple[list[int], str]:
    """
    Return list of unused JSON numbers for a folder.
    """
    folder = await get_folder_by_name(folder_name)
    if not folder:
        return [], f"❌ Folder *{folder_name}* not found."

    async with await get_db() as db:
        async with db.execute(
            """
            SELECT json_number FROM json_files
            WHERE folder_id = ? AND status = 'UNUSED'
            ORDER BY json_number
            LIMIT ?
            """,
            (folder.id, UNUSED_DISPLAY_LIMIT),
        ) as cur:
            rows = await cur.fetchall()

    numbers = [r["json_number"] for r in rows]
    return numbers, ""


async def get_next_unused(folder_name: str) -> tuple[Optional[Path], int, str]:
    """
    Retrieve the next UNUSED JSON file (lowest number).
    Returns (path, json_number, message).
    """
    folder = await get_folder_by_name(folder_name)
    if not folder:
        return None, 0, f"❌ Folder *{folder_name}* not found."

    async with await get_db() as db:
        async with db.execute(
            """
            SELECT id, json_number, file_path FROM json_files
            WHERE folder_id = ? AND status = 'UNUSED'
            ORDER BY json_number
            LIMIT 1
            """,
            (folder.id,),
        ) as cur:
            row = await cur.fetchone()

    if not row:
        return None, 0, f"⚠️ No unused JSON files in *{folder_name}*."

    path = Path(row["file_path"])
    if not path.exists():
        return None, row["json_number"], f"❌ File for JSON *#{row['json_number']}* missing on disk."

    return path, row["json_number"], ""


async def preview_json(folder_name: str, json_number: int) -> tuple[str, str]:
    """
    Return a pretty-printed preview (first 50 lines) of a JSON file.
    Returns (preview_text, error_message).
    """
    path, msg = await get_json_file(folder_name, json_number)
    if not path:
        return "", msg

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        preview = json.dumps(data, indent=2, ensure_ascii=False)
        lines = preview.split("\n")
        if len(lines) > 50:
            preview = "\n".join(lines[:50]) + "\n... (truncated)"
        return preview, ""
    except Exception as exc:
        return "", f"❌ Failed to read JSON: {exc}"


async def backup_folder(folder_name: str) -> tuple[Optional[Path], str]:
    """
    Create a zip backup of all JSON files in a folder.
    Returns (zip_path | None, message).
    """
    import zipfile
    import tempfile
    from config import JSON_STORAGE_DIR

    folder = await get_folder_by_name(folder_name)
    if not folder:
        return None, f"❌ Folder *{folder_name}* not found."

    folder_disk_path = JSON_STORAGE_DIR / folder_name
    if not folder_disk_path.exists():
        return None, f"❌ Folder *{folder_name}* has no files on disk."

    json_files = list(folder_disk_path.glob("*.json"))
    if not json_files:
        return None, f"⚠️ No JSON files found in *{folder_name}*."

    # Write zip to a temp file
    tmp = Path(tempfile.mktemp(suffix=f"_{folder_name}_backup.zip"))
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zf:
        for jf in json_files:
            zf.write(jf, arcname=jf.name)

    logger.info("Backup created for folder '%s': %s (%d files)", folder_name, tmp, len(json_files))
    return tmp, f"🗜️ Backup of *{folder_name}* — {len(json_files)} files."
