"""
JSON upload handler.
Supports:
  - /upload <folder> then send a .json file
  - Sending a .json file while in a selected folder (via callback state)
  - Inline button "Upload JSON"
"""

import logging
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, Document
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from services.json_service import save_json_file
from config import ADMIN_IDS, MAX_JSON_FILE_SIZE
from utils.keyboards import folder_actions_keyboard

router = Router()
logger = logging.getLogger(__name__)


class UploadState(StatesGroup):
    waiting_for_file = State()


# ── /upload <folder> command ──────────────────────────────────────────────────

@router.message(Command("upload"))
async def cmd_upload(message: Message, state: FSMContext) -> None:
    """Set the active upload folder, then wait for a JSON file."""
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("⛔ Only admins can upload JSON files.")
        return

    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer(
            "⚠️ Usage: `/upload <folder_name>`\nThen send a .json file.",
            parse_mode="Markdown",
        )
        return

    folder_name = parts[1].strip().lower()
    await state.set_state(UploadState.waiting_for_file)
    await state.update_data(folder_name=folder_name)
    await message.answer(
        f"📤 Ready to upload to *{folder_name}*.\nPlease send your `.json` file now.",
        parse_mode="Markdown",
    )


# ── Inline button "Upload JSON" ───────────────────────────────────────────────

@router.callback_query(lambda c: c.data.startswith("action:upload:"))
async def cb_upload_action(callback: CallbackQuery, state: FSMContext) -> None:
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("⛔ Admins only.", show_alert=True)
        return

    folder_name = callback.data.split(":", 2)[2]
    await state.set_state(UploadState.waiting_for_file)
    await state.update_data(folder_name=folder_name)
    await callback.message.answer(
        f"📤 Ready to upload to *{folder_name}*.\nPlease send your `.json` file now.",
        parse_mode="Markdown",
    )
    await callback.answer()


# ── Receive the JSON document ─────────────────────────────────────────────────

@router.message(UploadState.waiting_for_file, F.document)
async def handle_json_upload(message: Message, state: FSMContext) -> None:
    """Process the uploaded JSON document."""
    doc: Document = message.document

    # Validate file extension
    if not doc.file_name.endswith(".json"):
        await message.answer("❌ Please send a `.json` file.")
        return

    # Check file size
    if doc.file_size > MAX_JSON_FILE_SIZE:
        await message.answer(
            f"❌ File too large ({doc.file_size // 1024} KB). Max allowed: {MAX_JSON_FILE_SIZE // 1024} KB."
        )
        return

    data = await state.get_data()
    folder_name = data.get("folder_name")
    if not folder_name:
        await message.answer("❌ Session expired. Please use /upload again.")
        await state.clear()
        return

    # Download file bytes
    file = await message.bot.get_file(doc.file_id)
    bio = await message.bot.download_file(file.file_path)
    content: bytes = bio.read()

    # Save via service
    success, msg = await save_json_file(folder_name, content)
    await message.answer(msg, parse_mode="Markdown")

    if success:
        logger.info(
            "User %s uploaded JSON to folder '%s' (%d bytes)",
            message.from_user.id, folder_name, len(content),
        )

    # Stay in upload mode for bulk uploads — clear only if needed
    await message.answer(
        "📤 Send another `.json` file or use /cancel to stop.",
        parse_mode="Markdown",
    )


@router.message(UploadState.waiting_for_file)
async def upload_wrong_input(message: Message) -> None:
    """Prompt the user to send a valid .json file."""
    if message.text and message.text.startswith("/cancel"):
        from aiogram.fsm.context import FSMContext
        # handled by cancel handler below
        return
    await message.answer("⚠️ Please send a `.json` file, or /cancel to abort.")


@router.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext) -> None:
    """Cancel current FSM state."""
    current = await state.get_state()
    if current:
        await state.clear()
        await message.answer("❎ Operation cancelled.")
    else:
        await message.answer("Nothing to cancel.")
