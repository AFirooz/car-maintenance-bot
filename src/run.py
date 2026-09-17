"""launchd entry point.

One pass of the real work, then an idle window so an interactive flow can be
finished in one sitting. Per ADR 0001 this is not a daemon: launchd decides when
work happens.
"""

from __future__ import annotations

import asyncio
import sys
from datetime import datetime, timedelta
from pathlib import Path

from loguru import logger
from telegram import Bot

import db
from bot import drain_updates, run_once
from config import load_config
from ports import SystemClock
import auth_guard
from subaru import subaru_source
from telegram_chat import TelegramChat

IDLE_WINDOW_MINUTES = 30
POLL_SECONDS = 3


async def _idle_window(session, chat, odometer, clock, owner_id: int) -> None:
    """Stay available while the owner is mid-conversation."""
    deadline = datetime.now() + timedelta(minutes=IDLE_WINDOW_MINUTES)
    while datetime.now() < deadline:
        handled = await drain_updates(session, chat, odometer, clock, owner_id)
        if handled:
            deadline = datetime.now() + timedelta(minutes=IDLE_WINDOW_MINUTES)
        await asyncio.sleep(POLL_SECONDS)
    logger.info("Idle window closed.")


async def main() -> int:
    config = load_config()
    missing = config.missing()
    if missing:
        logger.error(f"Missing configuration: {', '.join(missing)}. Check your .env file.")
        return 1

    Path(config.db_path).parent.mkdir(parents=True, exist_ok=True)
    session_factory = db.make_session_factory(config.db_path)
    clock = SystemClock()

    with session_factory() as session:
        try:
            async with subaru_source(config, session) as odometer:
                bot = Bot(token=config.telegram_token)
                chat = TelegramChat(bot, config.owner_id, session)
                await run_once(session, chat, odometer, clock, config.owner_id)
                await _idle_window(session, chat, odometer, clock, config.owner_id)
        except auth_guard.CredentialsRefused as error:
            logger.error(str(error))
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
