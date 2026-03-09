"""
Data models (dataclasses) representing database rows.
These are used throughout the application for type safety.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class Folder:
    id: int
    folder_name: str
    created_at: str


@dataclass
class JsonFile:
    id: int
    folder_id: int
    json_number: int
    file_path: str
    status: str  # 'USED' | 'UNUSED'
    created_at: str


@dataclass
class FolderStats:
    folder_name: str
    total: int
    used: int
    unused: int
