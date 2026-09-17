from __future__ import annotations

from datetime import datetime

import db
from conftest import VIN
from helpers import create_reminder, say, tick


async def test_recording_a_service_moves_the_baseline_to_now(session, chat, odometer, clock):
    await create_reminder(session, chat, odometer, clock, mileage="5000")
    odometer.miles[VIN] = 45_000
    await tick(session, chat, odometer, clock)

    await say(session, chat, odometer, clock, "/done 1 -", "yes")

    reminder = db.list_reminders(session)[0]
    assert reminder.baseline_odometer == 45_000
    assert datetime.fromisoformat(reminder.baseline_at) == clock.now()
    assert reminder.notified_at is None


async def test_a_service_can_be_recorded_when_the_reminder_is_not_due(
    session, chat, odometer, clock
):
    await create_reminder(session, chat, odometer, clock, mileage="5000")
    odometer.miles[VIN] = 42_000
    await tick(session, chat, odometer, clock)

    await say(session, chat, odometer, clock, "/done 1 -", "yes")

    assert db.list_reminders(session)[0].baseline_odometer == 42_000


async def test_both_clocks_reset_together(session, chat, odometer, clock):
    await create_reminder(session, chat, odometer, clock, mileage="5000", months="6")
    odometer.miles[VIN] = 45_000
    await tick(session, chat, odometer, clock)
    chat.clear()

    clock.set(datetime(2026, 3, 10, 12, 0))
    await say(session, chat, odometer, clock, "/done 1 -", "yes")
    chat.clear()

    # Six months from the original baseline (2026-01-10) would have been due by
    # now; measured from the service event (2026-03-10) it is not.
    clock.set(datetime(2026, 7, 10, 12, 0))
    await tick(session, chat, odometer, clock)
    assert [m for m in chat.sent if " is due" in m] == []


async def test_an_odometer_alone_is_recorded_at_the_current_moment(
    session, chat, odometer, clock
):
    await create_reminder(session, chat, odometer, clock, mileage="5000")

    await say(session, chat, odometer, clock, "/done 1 41800", "yes")

    reminder = db.list_reminders(session)[0]
    assert reminder.baseline_odometer == 41_800
    assert datetime.fromisoformat(reminder.baseline_at) == clock.now()


async def test_a_date_alone_uses_the_newest_reading_at_or_before_it(
    session, chat, odometer, clock
):
    await create_reminder(session, chat, odometer, clock, mileage="5000")
    odometer.miles[VIN] = 43_000
    odometer.reported_at = datetime(2026, 2, 1, 9, 0)
    await tick(session, chat, odometer, clock)

    await say(session, chat, odometer, clock, "/done 1 2026-03-01", "yes")

    reminder = db.list_reminders(session)[0]
    assert reminder.baseline_odometer == 43_000
    assert datetime.fromisoformat(reminder.baseline_at) == datetime(2026, 3, 1)


async def test_a_date_older_than_every_reading_falls_back_and_says_so(
    session, chat, odometer, clock
):
    await create_reminder(session, chat, odometer, clock, mileage="5000")

    await say(session, chat, odometer, clock, "/done 1 2020-01-01")

    assert "oldest one I have" in chat.last


async def test_the_full_baseline_is_shown_before_it_is_applied(session, chat, odometer, clock):
    await create_reminder(session, chat, odometer, clock, mileage="5000")

    await say(session, chat, odometer, clock, "/done 1 41800")

    assert "41,800 mi" in chat.last
    assert db.list_reminders(session)[0].baseline_odometer == 40_000

    await say(session, chat, odometer, clock, "yes")
    assert db.list_reminders(session)[0].baseline_odometer == 41_800


async def test_declining_the_confirmation_changes_nothing(session, chat, odometer, clock):
    await create_reminder(session, chat, odometer, clock, mileage="5000")

    await say(session, chat, odometer, clock, "/done 1 41800", "no")

    assert db.list_reminders(session)[0].baseline_odometer == 40_000


async def test_done_with_no_arguments_offers_a_numbered_list(session, chat, odometer, clock):
    await create_reminder(session, chat, odometer, clock, name="Oil change")
    await create_reminder(session, chat, odometer, clock, name="Tire rotation")

    await say(session, chat, odometer, clock, "/done")

    assert "1. Oil change" in chat.last
    assert "2. Tire rotation" in chat.last

    await say(session, chat, odometer, clock, "2", "-", "yes")
    assert db.list_reminders(session)[1].baseline_odometer == 40_000
