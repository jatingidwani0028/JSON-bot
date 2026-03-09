"""
Main entry point for the Telegram JSON Manager Bot.

Run with:
    python bot.py
"""

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from config import BOT_TOKEN
from database.database import init_db
from utils.logger import setup_logging
from utils.middlewares import LoggingMiddleware

# Import all routers
from handlers.start import router as start_router
from handlers.folder_handler import router as folder_router
from handlers.upload_handler import router as upload_router
from handlers.json_fetch_handler import router as fetch_router
from handlers.stats_handler import router as stats_router

logger = logging.getLogger(__name__)


async def on_startup(bot: Bot) -> None:
    """Called when the bot starts."""
    await init_db()
    me = await bot.get_me()
    logger.info("Bot started: @%s (id=%s)", me.username, me.id)


async def on_shutdown(bot: Bot) -> None:
    """Called when the bot shuts down."""
    logger.info("Bot shutting down...")
    await bot.session.close()


async def main() -> None:
    setup_logging()

    if BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        logger.error(
            "Please set your BOT_TOKEN in config.py or via the BOT_TOKEN environment variable."
        )
        return

    # Initialize bot and dispatcher
    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN),
    )
    dp = Dispatcher(storage=MemoryStorage())

    # Register middlewares
    dp.message.middleware(LoggingMiddleware())

    # Register routers (order matters — more specific first)
    dp.include_router(start_router)
    dp.include_router(folder_router)
    dp.include_router(upload_router)
    dp.include_router(fetch_router)
    dp.include_router(stats_router)

    # Lifecycle hooks
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    logger.info("Starting polling...")
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())


if __name__ == "__main__":
    asyncio.run(main())
