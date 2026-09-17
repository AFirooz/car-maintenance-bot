from __future__ import annotations

import db
from conftest import VIN
from helpers import create_reminder, say, tick


async def test_listing_shows_miles_and_days_remaining(session, chat, odometer, clock):
    await create_reminder(session, chat, odometer, clock, mileage="5000", months="6")

    await say(session, chat, odometer, clock, "/list")

    assert "Oil change" in chat.last
    assert "5,000 mi left" in chat.last
    assert "days left" in chat.last


async def test_listing_marks_what_is_due(session, chat, odometer, clock):
    await create_reminder(session, chat, odometer, clock, mileage="5000")
    odometer.miles[VIN] = 45_000
    await tick(session, chat, odometer, clock)
    chat.clear()

    await say(session, chat, odometer, clock, "/list")

    assert "DUE" in chat.last


async def test_listing_groups_by_vehicle_when_there_is_more_than_one(
    session, chat, two_car_odometer, clock
):
    await say(session, chat, two_car_odometer, clock, "/add")
    await say(session, chat, two_car_odometer, clock, "1", "Oil change", "5000", "-", "7", "-", "yes")
    await say(session, chat, two_car_odometer, clock, "/add")
    await say(session, chat, two_car_odometer, clock, "2", "Brake fluid", "-", "24", "7", "-", "yes")
    chat.clear()

    await say(session, chat, two_car_odometer, clock, "/list")

    assert "Outback:" in chat.last
    assert "Forester:" in chat.last


async def test_listing_with_nothing_yet_says_so(session, chat, odometer, clock):
    await say(session, chat, odometer, clock, "/list")

    assert "No reminders yet" in chat.last


async def test_deleting_asks_first_then_removes(session, chat, odometer, clock):
    await create_reminder(session, chat, odometer, clock, name="Oil change")

    await say(session, chat, odometer, clock, "/delete 1")
    assert "Delete Oil change?" in chat.last
    assert len(db.list_reminders(session)) == 1

    await say(session, chat, odometer, clock, "yes")
    assert db.list_reminders(session) == []


async def test_declining_a_delete_keeps_the_reminder(session, chat, odometer, clock):
    await create_reminder(session, chat, odometer, clock)

    await say(session, chat, odometer, clock, "/delete 1", "no")

    assert len(db.list_reminders(session)) == 1


async def test_an_out_of_range_choice_is_rejected(session, chat, odometer, clock):
    await create_reminder(session, chat, odometer, clock)

    await say(session, chat, odometer, clock, "/delete 7")

    assert "between 1 and 1" in chat.last


async def test_cancel_abandons_whatever_was_in_progress(session, chat, odometer, clock):
    await say(session, chat, odometer, clock, "/add")
    await say(session, chat, odometer, clock, "Oil change")

    await say(session, chat, odometer, clock, "/cancel")

    assert db.get_flow(session, 4242) is None
    assert "Dropped it." in chat.last


async def test_renaming_a_vehicle_changes_what_messages_call_it(
    session, chat, odometer, clock
):
    await create_reminder(session, chat, odometer, clock, mileage="5000")

    await say(session, chat, odometer, clock, "/rename", "Blue wagon")
    assert db.list_vehicles(session)[0].display_name == "Blue wagon"

    odometer.miles[VIN] = 45_000
    await tick(session, chat, odometer, clock)
    assert "Blue wagon" in chat.last


async def test_renaming_asks_which_vehicle_when_there_are_several(
    session, chat, two_car_odometer, clock
):
    await tick(session, chat, two_car_odometer, clock)

    await say(session, chat, two_car_odometer, clock, "/rename")
    assert "Which vehicle should I rename?" in chat.last

    await say(session, chat, two_car_odometer, clock, "2", "Little one")
    assert [v.display_name for v in db.list_vehicles(session)] == ["Outback", "Little one"]
