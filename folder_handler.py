"""
Folder management handlers: /create_folder
"""

import logging
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from services.folder_service import create_folder
from utils.middlewares import admin_required

router = Router()
logger = logging.getLogger(__name__)


@router.message(Command("create_folder"))
async def cmd_create_folder(message: Message) -> None:
    """Admin-only: create a new folder."""
    from config import ADMIN_IDS
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("⛔ You are not authorized to create folders.")
        return

    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer(
            "⚠️ Usage: `/create_folder <folder_name>`\nExample: `/create_folder my_data`",
            parse_mode="Markdown",
        )
        return

    folder_name = parts[1].strip()
    success, msg = await create_folder(folder_name)
    await message.answer(msg, parse_mode="Markdown")

    if success:
        logger.info("Admin %s created folder '%s'", message.from_user.id, folder_name)
