from __future__ import annotations

import db
from conftest import VIN
from helpers import create_reminder, say, tick


def _nags(chat) -> list[str]:
    return [m for m in chat.sent if m.startswith("Still due")]


async def _make_it_due(session, chat, odometer, clock):
    await create_reminder(session, chat, odometer, clock, mileage="5000", nag="7")
    odometer.miles[VIN] = 45_000
    await tick(session, chat, odometer, clock)
    chat.clear()


async def test_does_not_nag_before_the_nag_interval_has_passed(session, chat, odometer, clock):
    await _make_it_due(session, chat, odometer, clock)

    clock.advance(days=6)
    await tick(session, chat, odometer, clock)

    assert _nags(chat) == []


async def test_nags_once_the_nag_interval_has_passed(session, chat, odometer, clock):
    await _make_it_due(session, chat, odometer, clock)

    clock.advance(days=7)
    await tick(session, chat, odometer, clock)

    assert len(_nags(chat)) == 1
    assert "Nag 1 of 4" in chat.last


async def test_falls_silent_after_four_nags(session, chat, odometer, clock):
    await _make_it_due(session, chat, odometer, clock)

    for _ in range(8):
        clock.advance(days=7)
        await tick(session, chat, odometer, clock)

    assert len(_nags(chat)) == 4
    reminder = db.list_reminders(session)[0]
    assert reminder.nag_count == 4


async def test_more_miles_do_not_restart_nagging_on_the_same_outstanding_service(
    session, chat, odometer, clock
):
    await _make_it_due(session, chat, odometer, clock)
    for _ in range(4):
        clock.advance(days=7)
        await tick(session, chat, odometer, clock)
    chat.clear()

    odometer.miles[VIN] = 50_000
    clock.advance(days=30)
    await tick(session, chat, odometer, clock)

    assert chat.sent == []


async def test_recording_the_service_gives_the_next_episode_its_full_four_nags(
    session, chat, odometer, clock
):
    await _make_it_due(session, chat, odometer, clock)
    clock.advance(days=7)
    await tick(session, chat, odometer, clock)

    await say(session, chat, odometer, clock, "/done 1 -", "yes")
    reminder = db.list_reminders(session)[0]
    assert reminder.nag_count == 0
    assert reminder.notified_at is None

    odometer.miles[VIN] = 50_000
    await tick(session, chat, odometer, clock)
    chat.clear()
    for _ in range(8):
        clock.advance(days=7)
        await tick(session, chat, odometer, clock)

    assert len(_nags(chat)) == 4
