"""
Statistics and reporting handlers.
"""

import logging
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, FSInputFile

from services.folder_service import get_folder_stats
from services.json_service import get_unused_json_numbers, backup_folder
from config import ADMIN_IDS
from utils.keyboards import folder_actions_keyboard

router = Router()
logger = logging.getLogger(__name__)


# ── /stats <folder> ───────────────────────────────────────────────────────────

@router.message(Command("stats"))
async def cmd_stats(message: Message) -> None:
    parts = message.text.split()
    if len(parts) != 2:
        await message.answer("⚠️ Usage: `/stats <folder>`", parse_mode="Markdown")
        return

    folder_name = parts[1].lower()
    stats = await get_folder_stats(folder_name)
    if not stats:
        await message.answer(f"❌ Folder *{folder_name}* not found.", parse_mode="Markdown")
        return

    pct_used = (stats.used / stats.total * 100) if stats.total else 0
    bar_filled = int(pct_used / 5)
    bar = "█" * bar_filled + "░" * (20 - bar_filled)

    await message.answer(
        f"📊 *Statistics — {stats.folder_name}*\n\n"
        f"Total JSON files : `{stats.total}`\n"
        f"✅ Used          : `{stats.used}`\n"
        f"🔄 Unused        : `{stats.unused}`\n\n"
        f"`[{bar}]` {pct_used:.1f}% used",
        parse_mode="Markdown",
    )


# ── /unused <folder> ──────────────────────────────────────────────────────────

@router.message(Command("unused"))
async def cmd_unused(message: Message) -> None:
    parts = message.text.split()
    if len(parts) != 2:
        await message.answer("⚠️ Usage: `/unused <folder>`", parse_mode="Markdown")
        return

    folder_name = parts[1].lower()
    numbers, err = await get_unused_json_numbers(folder_name)

    if err:
        await message.answer(err, parse_mode="Markdown")
        return

    if not numbers:
        await message.answer(f"✅ No unused JSON files in *{folder_name}*.", parse_mode="Markdown")
        return

    numbers_str = ", ".join(str(n) for n in numbers)
    await message.answer(
        f"🔄 *Unused JSON files in {folder_name}:*\n\n`{numbers_str}`\n\n"
        f"_(Showing up to 50 results)_",
        parse_mode="Markdown",
    )


# ── /backup <folder> ──────────────────────────────────────────────────────────

@router.message(Command("backup"))
async def cmd_backup(message: Message) -> None:
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("⛔ Only admins can create backups.")
        return

    parts = message.text.split()
    if len(parts) != 2:
        await message.answer("⚠️ Usage: `/backup <folder>`", parse_mode="Markdown")
        return

    folder_name = parts[1].lower()
    await message.answer("🗜️ Creating backup, please wait...", parse_mode="Markdown")

    zip_path, msg = await backup_folder(folder_name)
    if not zip_path:
        await message.answer(msg, parse_mode="Markdown")
        return

    await message.answer_document(
        FSInputFile(zip_path, filename=f"{folder_name}_backup.zip"),
        caption=msg,
        parse_mode="Markdown",
    )

    # Clean up temp file
    zip_path.unlink(missing_ok=True)
    logger.info("Admin %s downloaded backup for folder '%s'", message.from_user.id, folder_name)


# ── Inline button handlers ─────────────────────────────────────────────────────

@router.callback_query(lambda c: c.data.startswith("action:stats:"))
async def cb_stats(callback: CallbackQuery) -> None:
    folder_name = callback.data.split(":", 2)[2]
    stats = await get_folder_stats(folder_name)

    if not stats:
        await callback.message.answer(f"❌ Folder *{folder_name}* not found.", parse_mode="Markdown")
        await callback.answer()
        return

    pct_used = (stats.used / stats.total * 100) if stats.total else 0
    bar_filled = int(pct_used / 5)
    bar = "█" * bar_filled + "░" * (20 - bar_filled)

    await callback.message.edit_text(
        f"📊 *Statistics — {stats.folder_name}*\n\n"
        f"Total : `{stats.total}`\n"
        f"✅ Used   : `{stats.used}`\n"
        f"🔄 Unused : `{stats.unused}`\n\n"
        f"`[{bar}]` {pct_used:.1f}% used",
        reply_markup=folder_actions_keyboard(folder_name),
        parse_mode="Markdown",
    )
    await callback.answer()


@router.callback_query(lambda c: c.data.startswith("action:unused:"))
async def cb_unused(callback: CallbackQuery) -> None:
    folder_name = callback.data.split(":", 2)[2]
    numbers, err = await get_unused_json_numbers(folder_name)

    if err:
        await callback.message.answer(err, parse_mode="Markdown")
        await callback.answer()
        return

    if not numbers:
        text = f"✅ No unused JSON files in *{folder_name}*."
    else:
        numbers_str = ", ".join(str(n) for n in numbers)
        text = f"🔄 *Unused in {folder_name}:*\n`{numbers_str}`"

    await callback.message.edit_text(
        text,
        reply_markup=folder_actions_keyboard(folder_name),
        parse_mode="Markdown",
    )
    await callback.answer()


@router.callback_query(lambda c: c.data.startswith("action:backup:"))
async def cb_backup(callback: CallbackQuery) -> None:
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("⛔ Admins only.", show_alert=True)
        return

    folder_name = callback.data.split(":", 2)[2]
    await callback.message.answer("🗜️ Creating backup...")

    zip_path, msg = await backup_folder(folder_name)
    if not zip_path:
        await callback.message.answer(msg, parse_mode="Markdown")
        await callback.answer()
        return

    await callback.message.answer_document(
        FSInputFile(zip_path, filename=f"{folder_name}_backup.zip"),
        caption=msg,
        parse_mode="Markdown",
    )
    zip_path.unlink(missing_ok=True)
    await callback.answer("Backup sent!")
