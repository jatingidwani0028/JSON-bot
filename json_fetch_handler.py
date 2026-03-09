"""
JSON retrieval and status-marking handlers.
"""

import logging
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, FSInputFile

from services.json_service import (
    get_json_file, set_json_status, get_next_unused, preview_json
)
from config import ADMIN_IDS
from utils.keyboards import folder_actions_keyboard, back_keyboard

router = Router()
logger = logging.getLogger(__name__)


# ── /get_json <folder> <number> ───────────────────────────────────────────────

@router.message(Command("get_json"))
async def cmd_get_json(message: Message) -> None:
    """Retrieve a specific JSON file by number."""
    parts = message.text.split()
    if len(parts) != 3:
        await message.answer(
            "⚠️ Usage: `/get_json <folder> <number>`\nExample: `/get_json folder_1 5`",
            parse_mode="Markdown",
        )
        return

    folder_name = parts[1].lower()
    try:
        json_number = int(parts[2])
        if json_number < 1:
            raise ValueError
    except ValueError:
        await message.answer("❌ JSON number must be a positive integer.")
        return

    path, msg = await get_json_file(folder_name, json_number)
    if not path:
        await message.answer(msg, parse_mode="Markdown")
        return

    await message.answer(msg, parse_mode="Markdown")
    await message.answer_document(
        FSInputFile(path, filename=f"{folder_name}_json_{json_number}.json"),
        caption=f"📄 JSON #{json_number} from *{folder_name}*",
        parse_mode="Markdown",
    )
    logger.info("User %s downloaded JSON #%d from '%s'", message.from_user.id, json_number, folder_name)


# ── /next_unused <folder> ─────────────────────────────────────────────────────

@router.message(Command("next_unused"))
async def cmd_next_unused(message: Message) -> None:
    """Get the next unused JSON file from a folder."""
    parts = message.text.split()
    if len(parts) != 2:
        await message.answer("⚠️ Usage: `/next_unused <folder>`", parse_mode="Markdown")
        return

    folder_name = parts[1].lower()
    path, json_number, err = await get_next_unused(folder_name)

    if err:
        await message.answer(err, parse_mode="Markdown")
        return

    await message.answer(
        f"⚡ Next unused JSON is *#{json_number}* in *{folder_name}*",
        parse_mode="Markdown",
    )
    await message.answer_document(
        FSInputFile(path, filename=f"{folder_name}_json_{json_number}.json"),
        caption=f"⚡ Next unused JSON #{json_number}",
    )
    logger.info("User %s got next unused JSON #%d from '%s'", message.from_user.id, json_number, folder_name)


# ── /mark_used and /mark_unused ───────────────────────────────────────────────

@router.message(Command("mark_used"))
async def cmd_mark_used(message: Message) -> None:
    await _mark_status(message, "USED")


@router.message(Command("mark_unused"))
async def cmd_mark_unused(message: Message) -> None:
    await _mark_status(message, "UNUSED")


async def _mark_status(message: Message, status: str) -> None:
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("⛔ Only admins can change JSON status.")
        return

    cmd = "mark_used" if status == "USED" else "mark_unused"
    parts = message.text.split()
    if len(parts) != 3:
        await message.answer(
            f"⚠️ Usage: `/{cmd} <folder> <number>`",
            parse_mode="Markdown",
        )
        return

    folder_name = parts[1].lower()
    try:
        json_number = int(parts[2])
    except ValueError:
        await message.answer("❌ JSON number must be an integer.")
        return

    success, msg = await set_json_status(folder_name, json_number, status)
    await message.answer(msg, parse_mode="Markdown")


# ── /preview <folder> <number> ────────────────────────────────────────────────

@router.message(Command("preview"))
async def cmd_preview(message: Message) -> None:
    """Show a truncated JSON preview inline."""
    parts = message.text.split()
    if len(parts) != 3:
        await message.answer("⚠️ Usage: `/preview <folder> <number>`", parse_mode="Markdown")
        return

    folder_name = parts[1].lower()
    try:
        json_number = int(parts[2])
    except ValueError:
        await message.answer("❌ JSON number must be an integer.")
        return

    preview, err = await preview_json(folder_name, json_number)
    if err:
        await message.answer(err, parse_mode="Markdown")
        return

    await message.answer(
        f"🔍 *Preview — {folder_name} #{json_number}*\n\n```json\n{preview}\n```",
        parse_mode="Markdown",
    )


# ── Inline button handlers ─────────────────────────────────────────────────────

@router.callback_query(lambda c: c.data.startswith("action:get:"))
async def cb_get_json(callback: CallbackQuery) -> None:
    folder_name = callback.data.split(":", 2)[2]
    await callback.message.answer(
        f"📥 To get a JSON file from *{folder_name}*, use:\n`/get_json {folder_name} <number>`",
        parse_mode="Markdown",
    )
    await callback.answer()


@router.callback_query(lambda c: c.data.startswith("action:next_unused:"))
async def cb_next_unused(callback: CallbackQuery) -> None:
    folder_name = callback.data.split(":", 2)[2]
    path, json_number, err = await get_next_unused(folder_name)

    if err:
        await callback.message.answer(err, parse_mode="Markdown")
        await callback.answer()
        return

    await callback.message.answer(
        f"⚡ Next unused JSON is *#{json_number}* in *{folder_name}*",
        parse_mode="Markdown",
    )
    await callback.message.answer_document(
        FSInputFile(path, filename=f"{folder_name}_json_{json_number}.json"),
    )
    await callback.answer()


@router.callback_query(lambda c: c.data.startswith("action:preview:"))
async def cb_preview(callback: CallbackQuery) -> None:
    folder_name = callback.data.split(":", 2)[2]
    await callback.message.answer(
        f"🔍 To preview a JSON from *{folder_name}*, use:\n`/preview {folder_name} <number>`",
        parse_mode="Markdown",
    )
    await callback.answer()
