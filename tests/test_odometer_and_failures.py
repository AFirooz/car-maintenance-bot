from __future__ import annotations

from datetime import datetime

import db
from conftest import SECOND_VIN, VIN, FakeOdometer
from helpers import create_reminder, say, tick


def _readings(session, vehicle_id):
    from sqlalchemy import select

    return list(session.scalars(select(db.OdometerReading).where(db.OdometerReading.vehicle_id == vehicle_id)))


async def test_an_unchanged_reading_is_not_appended_again(session, chat, odometer, clock):
    await tick(session, chat, odometer, clock)
    await tick(session, chat, odometer, clock)
    await tick(session, chat, odometer, clock)

    vehicle = db.list_vehicles(session)[0]
    assert len(_readings(session, vehicle.id)) == 1


async def test_only_the_three_most_recent_readings_are_kept(session, chat, odometer, clock):
    for index, miles in enumerate([40_100, 40_200, 40_300, 40_400, 40_500]):
        odometer.miles[VIN] = miles
        odometer.reported_at = datetime(2026, 1, 10 + index, 12, 0)
        await tick(session, chat, odometer, clock)

    vehicle = db.list_vehicles(session)[0]
    assert sorted(r.miles for r in _readings(session, vehicle.id)) == [40_300, 40_400, 40_500]


async def test_one_failed_read_is_logged_and_otherwise_ignored(session, chat, odometer, clock):
    await tick(session, chat, odometer, clock)
    chat.clear()

    odometer.miles[VIN] = None
    await tick(session, chat, odometer, clock)

    assert chat.sent == []


async def test_two_consecutive_failed_reads_alert_the_owner(session, chat, odometer, clock):
    await tick(session, chat, odometer, clock)
    chat.clear()

    odometer.miles[VIN] = None
    await tick(session, chat, odometer, clock)
    await tick(session, chat, odometer, clock)

    assert len(chat.sent) == 1
    assert "haven't been able to read the odometer" in chat.sent[0]


async def test_a_successful_read_clears_the_failure_streak(session, chat, odometer, clock):
    odometer.miles[VIN] = None
    await tick(session, chat, odometer, clock)
    odometer.miles[VIN] = 41_000
    await tick(session, chat, odometer, clock)
    chat.clear()

    odometer.miles[VIN] = None
    await tick(session, chat, odometer, clock)

    assert chat.sent == []


async def test_an_exception_from_subaru_counts_as_a_failed_read(session, chat, clock):
    source = FakeOdometer(miles={VIN: 40_000}, reported_at=clock.now(), names={VIN: "Outback"})
    await tick(session, chat, source, clock)
    chat.clear()

    source.raises = True
    await tick(session, chat, source, clock)
    await tick(session, chat, source, clock)

    assert any("haven't been able to read the odometer" in m for m in chat.sent)


async def test_vehicles_are_discovered_from_the_account(session, chat, two_car_odometer, clock):
    await tick(session, chat, two_car_odometer, clock)

    names = [v.display_name for v in db.list_vehicles(session)]
    assert names == ["Outback", "Forester"]


async def test_reminders_track_their_own_vehicle(session, chat, two_car_odometer, clock):
    await say(session, chat, two_car_odometer, clock, "/add")
    await say(session, chat, two_car_odometer, clock, "1", "Oil change", "5000", "-", "7", "-", "yes")
    await say(session, chat, two_car_odometer, clock, "/add")
    await say(session, chat, two_car_odometer, clock, "2", "Oil change", "5000", "-", "7", "-", "yes")
    chat.clear()

    # Only the Forester passes its interval.
    two_car_odometer.miles[SECOND_VIN] = 17_000
    await tick(session, chat, two_car_odometer, clock)

    due = [m for m in chat.sent if " is due" in m]
    assert len(due) == 1
    assert "Forester" in due[0]


async def test_a_message_from_anyone_else_is_ignored(session, chat, odometer, clock):
    chat.receive("/add", user_id=9999)
    await tick(session, chat, odometer, clock)

    assert chat.sent == []
    assert db.get_flow(session, 4242) is None
