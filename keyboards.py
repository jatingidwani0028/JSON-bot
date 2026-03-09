"""
Reusable Telegram inline keyboard builders.
"""

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from database.models import Folder


def folder_list_keyboard(folders: list[Folder]) -> InlineKeyboardMarkup:
    """Build a keyboard listing all folders."""
    builder = InlineKeyboardBuilder()
    for folder in folders:
        builder.button(
            text=f"📁 {folder.folder_name}",
            callback_data=f"folder_select:{folder.folder_name}",
        )
    builder.adjust(1)
    return builder.as_markup()


def folder_actions_keyboard(folder_name: str) -> InlineKeyboardMarkup:
    """Build action menu for a specific folder."""
    builder = InlineKeyboardBuilder()
    actions = [
        ("📤 Upload JSON",    f"action:upload:{folder_name}"),
        ("📥 Get JSON",       f"action:get:{folder_name}"),
        ("📊 Statistics",     f"action:stats:{folder_name}"),
        ("🔄 Unused JSONs",   f"action:unused:{folder_name}"),
        ("⚡ Next Unused",    f"action:next_unused:{folder_name}"),
        ("🔍 Preview JSON",   f"action:preview:{folder_name}"),
        ("🗜️ Backup Folder",  f"action:backup:{folder_name}"),
        ("🔙 Back",           "action:back"),
    ]
    for text, cb in actions:
        builder.button(text=text, callback_data=cb)
    builder.adjust(2)
    return builder.as_markup()


def back_keyboard() -> InlineKeyboardMarkup:
    """Single back button."""
    builder = InlineKeyboardBuilder()
    builder.button(text="🔙 Back to Folders", callback_data="action:back")
    return builder.as_markup()


def confirm_keyboard(action: str, folder_name: str, number: int) -> InlineKeyboardMarkup:
    """Confirm / Cancel keyboard."""
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Confirm", callback_data=f"confirm:{action}:{folder_name}:{number}")
    builder.button(text="❌ Cancel",  callback_data=f"folder_select:{folder_name}")
    builder.adjust(2)
    return builder.as_markup()
