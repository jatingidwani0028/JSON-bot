"""
Aiogram middlewares — logging, rate limiting helpers.
"""

import logging
import time
from typing import Any, Awaitable, Callable, Dict
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message

logger = logging.getLogger(__name__)


class LoggingMiddleware(BaseMiddleware):
    """Log every incoming message with user info."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        if isinstance(event, Message) and event.text:
            logger.info(
                "MSG from user_id=%s | text=%s",
                event.from_user.id if event.from_user else "?",
                event.text[:80],
            )
        return await handler(event, data)


def admin_required(user_id: int) -> bool:
    """Check if a user_id is in ADMIN_IDS."""
    from config import ADMIN_IDS
    return user_id in ADMIN_IDS
