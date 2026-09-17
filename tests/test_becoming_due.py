from __future__ import annotations

from datetime import datetime

import db
from conftest import VIN
from helpers import create_reminder, tick


def _due_messages(chat) -> list[str]:
    """Initial Due notifications only, not Nags."""
    return [m for m in chat.sent if " is due" in m]


async def test_nothing_is_said_before_the_mileage_interval_is_reached(
    session, chat, odometer, clock
):
    await create_reminder(session, chat, odometer, clock, mileage="5000")

    odometer.miles[VIN] = 44_999
    await tick(session, chat, odometer, clock)

    assert _due_messages(chat) == []


async def test_notifies_once_the_mileage_interval_is_reached(session, chat, odometer, clock):
    await create_reminder(session, chat, odometer, clock, mileage="5000")

    odometer.miles[VIN] = 45_000
    await tick(session, chat, odometer, clock)

    assert "Oil change is due" in chat.last
    assert "mileage" in chat.last


async def test_notifies_once_the_time_interval_is_reached(session, chat, odometer, clock):
    await create_reminder(session, chat, odometer, clock, mileage="-", months="6")

    clock.set(datetime(2026, 7, 10, 12, 0))
    await tick(session, chat, odometer, clock)

    assert "Oil change is due" in chat.last
    assert "time" in chat.last


async def test_a_reminder_with_both_intervals_fires_on_whichever_comes_first(
    session, chat, odometer, clock
):
    await create_reminder(session, chat, odometer, clock, mileage="5000", months="6")

    odometer.miles[VIN] = 45_000
    await tick(session, chat, odometer, clock)

    assert len(_due_messages(chat)) == 1
    assert "mileage" in chat.last


async def test_crossing_the_second_threshold_does_not_notify_again(
    session, chat, odometer, clock
):
    await create_reminder(session, chat, odometer, clock, mileage="5000", months="6")
    odometer.miles[VIN] = 45_000
    await tick(session, chat, odometer, clock)
    chat.clear()

    clock.set(datetime(2026, 7, 10, 12, 0))
    await tick(session, chat, odometer, clock)

    assert _due_messages(chat) == []


async def test_running_several_times_the_same_day_says_it_once(session, chat, odometer, clock):
    await create_reminder(session, chat, odometer, clock, mileage="5000")
    odometer.miles[VIN] = 45_000

    await tick(session, chat, odometer, clock)
    await tick(session, chat, odometer, clock)
    await tick(session, chat, odometer, clock)

    assert len(_due_messages(chat)) == 1


async def test_a_month_end_baseline_clamps_to_the_last_day_of_the_target_month(
    session, chat, odometer, clock
):
    clock.set(datetime(2026, 8, 31, 12, 0))
    await create_reminder(session, chat, odometer, clock, mileage="-", months="6")

    clock.set(datetime(2027, 2, 27, 12, 0))
    await tick(session, chat, odometer, clock)
    assert _due_messages(chat) == []

    clock.set(datetime(2027, 2, 28, 13, 0))
    await tick(session, chat, odometer, clock)
    assert "Oil change is due" in chat.last


async def test_time_reminders_still_fire_while_the_odometer_is_unavailable(
    session, chat, odometer, clock
):
    await create_reminder(session, chat, odometer, clock, mileage="5000", months="6")
    odometer.miles[VIN] = None
    chat.clear()

    clock.set(datetime(2026, 7, 10, 12, 0))
    await tick(session, chat, odometer, clock)

    assert "Oil change is due" in chat.last
