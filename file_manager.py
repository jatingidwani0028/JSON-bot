"""
File system utilities — disk I/O for JSON files and folders.
"""

from pathlib import Path
from config import JSON_STORAGE_DIR
import logging

logger = logging.getLogger(__name__)


def create_folder_on_disk(folder_name: str) -> Path:
    """Create a folder directory inside json_storage/."""
    path = JSON_STORAGE_DIR / folder_name
    path.mkdir(parents=True, exist_ok=True)
    logger.debug("Folder created on disk: %s", path)
    return path


def save_json_to_disk(folder_name: str, json_number: int, content: bytes) -> Path:
    """Write raw JSON bytes to disk and return the file path."""
    folder_path = JSON_STORAGE_DIR / folder_name
    folder_path.mkdir(parents=True, exist_ok=True)  # safety

    file_path = folder_path / f"json_{json_number}.json"
    file_path.write_bytes(content)
    logger.debug("Saved JSON file: %s", file_path)
    return file_path


def get_json_path(folder_name: str, json_number: int) -> Path:
    """Return the expected path for a JSON file (may or may not exist)."""
    return JSON_STORAGE_DIR / folder_name / f"json_{json_number}.json"


def delete_json_from_disk(folder_name: str, json_number: int) -> bool:
    """Delete a JSON file from disk. Returns True if deleted."""
    path = get_json_path(folder_name, json_number)
    if path.exists():
        path.unlink()
        logger.debug("Deleted JSON file: %s", path)
        return True
    return False
