"""
Main entry point for the Telegram JSON Manager Bot.
Designed for Render's free tier — runs an aiohttp health-check web server
alongside the Telegram polling loop so Render never kills the process.

Run with:
    python bot.py
  or from the repo root:
    python telegram_json_manager/bot.py

Environment variables (set these in Render's dashboard):
    BOT_TOKEN   — your Telegram bot token
    PORT        — port to bind the web server (Render sets this automatically)
"""

import asyncio
import logging
import os
import sys
from pathlib import Path

# ── Path fix ──────────────────────────────────────────────────────────────────
# Ensure the directory containing bot.py (telegram_json_manager/) is always
# on sys.path.  Render runs "python telegram_json_manager/bot.py" from the
# repo root, so Python's default path would be the repo root — not the package
# directory — causing "No module named 'database.database'" etc.
_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from aiohttp import web
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

# ── Health-check web server ───────────────────────────────────────────────────

async def handle_health(request: web.Request) -> web.Response:
    """GET / — simple liveness probe for Render."""
    return web.Response(text="OK", status=200)


async def run_web_server() -> None:
    """Start a minimal aiohttp server on the PORT Render assigns."""
    port = int(os.environ.get("PORT", 8080))
    app = web.Application()
    app.router.add_get("/", handle_health)
    app.router.add_get("/health", handle_health)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host="0.0.0.0", port=port)
    await site.start()
    logger.info("Health-check server listening on port %d", port)


# ── Telegram bot ──────────────────────────────────────────────────────────────

async def on_startup(bot: Bot) -> None:
    """Called when the Telegram bot starts."""
    await init_db()
    me = await bot.get_me()
    logger.info("Bot started: @%s (id=%s)", me.username, me.id)


async def on_shutdown(bot: Bot) -> None:
    """Called when the Telegram bot shuts down."""
    logger.info("Bot shutting down...")
    await bot.session.close()


async def run_bot() -> None:
    """Initialise and start Telegram long-polling."""
    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN),
    )
    dp = Dispatcher(storage=MemoryStorage())

    # Middlewares
    dp.message.middleware(LoggingMiddleware())

    # Routers (order matters — more specific first)
    dp.include_router(start_router)
    dp.include_router(folder_router)
    dp.include_router(upload_router)
    dp.include_router(fetch_router)
    dp.include_router(stats_router)

    # Lifecycle hooks
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    logger.info("Starting Telegram polling...")
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())


# ── Entry point ───────────────────────────────────────────────────────────────

async def main() -> None:
    setup_logging()

    if BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        logger.error(
            "BOT_TOKEN is not set. "
            "Add it to config.py or set the BOT_TOKEN environment variable."
        )
        return

    # Run the web server and the Telegram bot concurrently.
    # The web server keeps Render happy; the bot handles Telegram updates.
    await asyncio.gather(
        run_web_server(),
        run_bot(),
    )


if __name__ == "__main__":
    asyncio.run(main())
