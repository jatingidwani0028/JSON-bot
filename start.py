"""
/start and /help command handlers + main folder navigation.
"""

import logging
from aiogram import Router
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery

from services.folder_service import list_folders
from utils.keyboards import folder_list_keyboard, folder_actions_keyboard

router = Router()
logger = logging.getLogger(__name__)

HELP_TEXT = """
🤖 *JSON File Manager Bot*

*Admin Commands:*
`/create_folder <name>` — Create a new folder
`/upload <folder>` — Set active folder for upload (then send .json file)

*Retrieval Commands:*
`/get_json <folder> <number>` — Fetch a specific JSON file
`/next_unused <folder>` — Get the next unused JSON

*Status Commands:*
`/mark_used <folder> <number>` — Mark JSON as USED
`/mark_unused <folder> <number>` — Mark JSON as UNUSED

*Info Commands:*
`/stats <folder>` — Folder statistics
`/unused <folder>` — List unused JSON numbers
`/preview <folder> <number>` — Preview JSON content
`/folders` — List all folders

*Admin Commands:*
`/backup <folder>` — Download folder as ZIP

Use /folders to browse with buttons 📁
"""


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    """Welcome message with folder list."""
    logger.info("User %s started the bot", message.from_user.id)
    folders = await list_folders()

    if not folders:
        await message.answer(
            "👋 Welcome to *JSON File Manager*!\n\n"
            "No folders yet. Use `/create_folder <name>` to get started.",
            parse_mode="Markdown",
        )
        return

    await message.answer(
        "👋 Welcome to *JSON File Manager*!\n\nSelect a folder:",
        reply_markup=folder_list_keyboard(folders),
        parse_mode="Markdown",
    )


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    await message.answer(HELP_TEXT, parse_mode="Markdown")


@router.message(Command("folders"))
async def cmd_folders(message: Message) -> None:
    """List all folders as inline buttons."""
    folders = await list_folders()
    if not folders:
        await message.answer("📂 No folders found. Use `/create_folder <name>` to create one.")
        return
    await message.answer(
        "📂 *Select a folder:*",
        reply_markup=folder_list_keyboard(folders),
        parse_mode="Markdown",
    )


@router.callback_query(lambda c: c.data.startswith("folder_select:"))
async def cb_folder_select(callback: CallbackQuery) -> None:
    """Handle folder selection from inline keyboard."""
    folder_name = callback.data.split(":", 1)[1]
    await callback.message.edit_text(
        f"📁 *Folder: {folder_name}*\n\nChoose an action:",
        reply_markup=folder_actions_keyboard(folder_name),
        parse_mode="Markdown",
    )
    await callback.answer()


@router.callback_query(lambda c: c.data == "action:back")
async def cb_back(callback: CallbackQuery) -> None:
    """Return to folder list."""
    folders = await list_folders()
    await callback.message.edit_text(
        "📂 *Select a folder:*",
        reply_markup=folder_list_keyboard(folders),
        parse_mode="Markdown",
    )
    await callback.answer()
