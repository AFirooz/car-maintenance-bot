"""The run entry point: the single seam the whole app is tested through.

``run_once`` is parameterised by an odometer source, a chat transport and a
clock. The database is always real.
"""

from __future__ import annotations

from datetime import datetime
from functools import partial

from loguru import logger
from sqlalchemy.orm import Session

import db
import flows
import messages
from ports import ChatTransport, Clock, OdometerSource
from reminders import evaluate

# Consecutive failed odometer reads before the owner is told something is wrong.
CONSECUTIVE_FAILURE_ALERT = 2


async def run_once(
    session: Session,
    chat: ChatTransport,
    odometer: OdometerSource,
    clock: Clock,
    owner_id: int,
) -> None:
    await _ensure_vehicles(session, odometer)
    await drain_updates(session, chat, odometer, clock, owner_id)
    await _refresh_odometers(session, chat, odometer)
    await _notify(session, chat, clock)


async def _ensure_vehicles(session: Session, odometer: OdometerSource) -> None:
    """Seed any Vehicle on the account we don't know about yet, every run."""
    try:
        discovered = await odometer.vehicles()
    except Exception as error:
        logger.error(f"Could not discover vehicles: {error}")
        return
    known_before = len(db.list_vehicles(session))
    vehicles = db.seed_vehicles(session, discovered)
    if len(vehicles) > known_before:
        logger.info(f"Seeded {len(vehicles) - known_before} new vehicle(s)")


async def drain_updates(
    session: Session,
    chat: ChatTransport,
    odometer: OdometerSource,
    clock: Clock,
    owner_id: int,
) -> int:
    """Handle every pending message from the owner. Returns how many were handled."""
    try:
        updates = await chat.updates()
    except Exception as error:
        logger.error(f"Could not read messages: {error}")
        return 0

    handled = 0
    for message in updates:
        if message.user_id != owner_id:
            logger.warning(f"Ignoring message from user {message.user_id}")
            continue
        await flows.handle_message(
            session, owner_id, message.text, clock.now(), chat.send, partial(safe_reading, odometer)
        )
        handled += 1
    return handled


async def safe_reading(odometer: OdometerSource, vin: str):
    try:
        return await odometer.reading(vin)
    except Exception as error:
        logger.warning(f"Odometer read failed for {vin}: {error}")
        return None


async def _refresh_odometers(session: Session, chat: ChatTransport, odometer: OdometerSource) -> None:
    for vehicle in db.list_vehicles(session):
        key = f"fetch_failures:{vehicle.vin}"
        reading = await safe_reading(odometer, vehicle.vin)
        if reading is None:
            failures = int(db.get_state(session, key, "0")) + 1
            db.set_state(session, key, str(failures))
            logger.warning(f"No odometer reading for {vehicle.display_name} ({failures} in a row)")
            if failures == CONSECUTIVE_FAILURE_ALERT:
                await chat.send(
                    f"I haven't been able to read the odometer for {vehicle.display_name} "
                    f"{failures} runs in a row. Time-based reminders still work."
                )
            continue
        db.set_state(session, key, "0")
        if db.record_reading(session, vehicle.id, reading.miles, reading.reported_at):
            logger.info(f"{vehicle.display_name} odometer {reading.miles}")


async def _notify(session: Session, chat: ChatTransport, clock: Clock) -> None:
    now: datetime = clock.now()
    odometers = db.odometer_map(session)
    vehicles = {v.id: v for v in db.list_vehicles(session)}
    for notification in evaluate(db.list_reminders(session), odometers, now):
        reminder = notification.reminder
        vehicle = vehicles.get(reminder.vehicle_id)
        if vehicle is None:
            continue
        await chat.send(
            messages.due_text(
                reminder,
                vehicle,
                notification.reason,
                odometers.get(reminder.vehicle_id),
                now,
                notification.is_nag,
                notification.nag_number,
            )
        )
        if notification.is_nag:
            db.mark_nagged(session, reminder, now)
        else:
            db.mark_notified(session, reminder, now)
