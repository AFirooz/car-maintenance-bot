from __future__ import annotations

from datetime import datetime

import db
from conftest import VIN
from helpers import create_reminder, say, tick


async def test_creates_a_mileage_only_reminder_anchored_to_the_current_odometer(
    session, chat, odometer, clock
):
    await create_reminder(session, chat, odometer, clock, mileage="5000", months="-")

    reminder = db.list_reminders(session)[0]
    assert reminder.name == "Oil change"
    assert reminder.mileage_interval == 5000
    assert reminder.time_interval_months is None
    assert reminder.baseline_odometer == 40_000


async def test_creates_a_time_only_reminder(session, chat, odometer, clock):
    await create_reminder(session, chat, odometer, clock, mileage="-", months="6")

    reminder = db.list_reminders(session)[0]
    assert reminder.mileage_interval is None
    assert reminder.time_interval_months == 6


async def test_creates_a_reminder_with_both_intervals(session, chat, odometer, clock):
    await create_reminder(session, chat, odometer, clock, mileage="5000", months="6")

    reminder = db.list_reminders(session)[0]
    assert reminder.mileage_interval == 5000
    assert reminder.time_interval_months == 6


async def test_refuses_a_reminder_with_neither_interval(session, chat, odometer, clock):
    await say(session, chat, odometer, clock, "/add")
    await say(session, chat, odometer, clock, "Oil change", "-", "-")

    assert "at least one interval" in chat.last
    assert db.list_reminders(session) == []


async def test_accepts_a_stated_last_service_as_the_baseline(session, chat, odometer, clock):
    await create_reminder(session, chat, odometer, clock, last="38000 2025-11-01")

    reminder = db.list_reminders(session)[0]
    assert reminder.baseline_odometer == 38_000
    assert datetime.fromisoformat(reminder.baseline_at) == datetime(2025, 11, 1)


async def test_declining_the_summary_saves_nothing(session, chat, odometer, clock):
    await say(session, chat, odometer, clock, "/add")
    await say(session, chat, odometer, clock, "Oil change", "5000", "-", "7", "-", "no")

    assert db.list_reminders(session) == []


async def test_asks_which_vehicle_only_when_there_is_more_than_one(
    session, chat, two_car_odometer, clock
):
    await say(session, chat, two_car_odometer, clock, "/add")

    assert "Which vehicle?" in chat.last
    assert "Outback" in chat.last and "Forester" in chat.last

    await say(session, chat, two_car_odometer, clock, "2", "Tire rotation", "6000", "-", "7", "-", "yes")
    reminder = db.list_reminders(session)[0]
    forester = [v for v in db.list_vehicles(session) if v.display_name == "Forester"][0]
    assert reminder.vehicle_id == forester.id


async def test_creation_fails_clearly_when_the_odometer_cannot_be_read(session, chat, clock):
    from conftest import FakeOdometer

    blind = FakeOdometer(miles={VIN: None}, reported_at=clock.now(), names={VIN: "Outback"})
    await say(session, chat, blind, clock, "/add")
    await say(session, chat, blind, clock, "Oil change", "5000", "-", "7", "-")

    assert "couldn't read the odometer" in chat.last
    assert db.list_reminders(session) == []


async def test_a_half_finished_flow_survives_the_process_exiting(
    session_factory, chat, odometer, clock
):
    with session_factory() as first:
        await say(first, chat, odometer, clock, "/add")
        await say(first, chat, odometer, clock, "Oil change")

    # A completely separate session, as a later scheduled run would have.
    with session_factory() as second:
        await say(second, chat, odometer, clock, "5000", "-", "7", "-", "yes")
        assert db.list_reminders(second)[0].name == "Oil change"


async def test_a_flow_left_alone_for_half_an_hour_is_abandoned(session, chat, odometer, clock):
    await say(session, chat, odometer, clock, "/add")
    await say(session, chat, odometer, clock, "Oil change")
    clock.advance(minutes=31)

    await say(session, chat, odometer, clock, "5000")

    assert db.get_flow(session, 4242) is None
    assert "Commands:" in chat.last


async def test_a_baseline_of_now_reads_a_fresh_odometer_rather_than_stored_history(
    session, chat, odometer, clock
):
    await create_reminder(session, chat, odometer, clock, name="Oil change")

    # The car has moved since the last scheduled run stored a reading.
    odometer.miles[VIN] = 41_000
    await say(session, chat, odometer, clock, "/add")
    await say(session, chat, odometer, clock, "Tire rotation", "6000", "-", "7", "-", "yes")

    assert db.list_reminders(session)[1].baseline_odometer == 41_000


async def test_creation_fails_rather_than_anchoring_to_a_stale_reading(
    session, chat, odometer, clock
):
    await create_reminder(session, chat, odometer, clock, name="Oil change")

    odometer.raises = True
    await say(session, chat, odometer, clock, "/add")
    await say(session, chat, odometer, clock, "Tire rotation", "6000", "-", "7", "-")

    assert "couldn't read the odometer" in chat.last
    assert len(db.list_reminders(session)) == 1


async def test_a_stated_odometer_gets_past_an_unreachable_subaru(
    session, chat, odometer, clock
):
    odometer.raises = True

    await say(session, chat, odometer, clock, "/add")
    await say(session, chat, odometer, clock, "Tire rotation", "6000", "-", "7", "38000", "yes")

    assert db.list_reminders(session)[0].baseline_odometer == 38_000
