from __future__ import annotations

from loguru import logger
from telegram import Bot
from telegram.error import TimedOut

import db
from ports import InboundMessage

OFFSET_KEY = "telegram_offset"


class TelegramChat:
    """Reads and writes the owner's Telegram chat, remembering its own offset."""

    def __init__(self, bot: Bot, chat_id: int, session):
        self._bot = bot
        self._chat_id = chat_id
        self._session = session

    async def updates(self) -> list[InboundMessage]:
        offset = int(db.get_state(self._session, OFFSET_KEY, "0") or 0)
        try:
            updates = await self._bot.get_updates(offset=offset or None, timeout=10)
        except TimedOut:
            return []
        except Exception as error:
            logger.error(f"Telegram polling failed: {error}")
            return []

        messages: list[InboundMessage] = []
        for update in updates:
            db.set_state(self._session, OFFSET_KEY, str(update.update_id + 1))
            message = update.message or update.edited_message
            if message is None or not message.text or message.from_user is None:
                continue
            messages.append(InboundMessage(user_id=message.from_user.id, text=message.text))
        return messages

    async def send(self, text: str) -> None:
        await self._bot.send_message(chat_id=self._chat_id, text=text)
