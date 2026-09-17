from __future__ import annotations

from bot import run_once
from conftest import OWNER_ID


async def tick(session, chat, odometer, clock):
    """One scheduled run."""
    await run_once(session, chat, odometer, clock, OWNER_ID)


async def say(session, chat, odometer, clock, *texts: str):
    """Send messages one at a time, each in its own run."""
    for text in texts:
        chat.receive(text)
        await tick(session, chat, odometer, clock)


async def create_reminder(
    session,
    chat,
    odometer,
    clock,
    name: str = "Oil change",
    mileage: str = "5000",
    months: str = "-",
    nag: str = "7",
    last: str = "-",
):
    await say(session, chat, odometer, clock, "/add")
    await say(session, chat, odometer, clock, name, mileage, months, nag, last, "yes")
    chat.clear()
