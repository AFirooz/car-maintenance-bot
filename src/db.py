from __future__ import annotations

import json
from datetime import datetime

from sqlalchemy import create_engine, delete, select
from sqlalchemy.orm import Session, sessionmaker

from schema import AppState, Base, OdometerReading, PendingFlow, Reminder, ServiceEvent, Vehicle

# Odometer Readings kept per Vehicle. Small on purpose: the history exists only
# to resolve a Service Event supplied as a date with no odometer.
READING_HISTORY_LIMIT = 3

FLOW_EXPIRY_MINUTES = 30


def make_engine(db_path: str):
    engine = create_engine(f"sqlite:///{db_path}", future=True)
    Base.metadata.create_all(engine)
    return engine


def make_session_factory(db_path: str) -> sessionmaker[Session]:
    return sessionmaker(bind=make_engine(db_path), future=True)


# --- vehicles ---------------------------------------------------------------


def list_vehicles(session: Session) -> list[Vehicle]:
    return list(session.scalars(select(Vehicle).order_by(Vehicle.id)))


def seed_vehicles(session: Session, discovered) -> list[Vehicle]:
    """Insert any Vehicle on the account we have not seen before."""
    known = {v.vin for v in list_vehicles(session)}
    for item in discovered:
        if item.vin not in known:
            session.add(Vehicle(vin=item.vin, display_name=item.display_name))
    session.commit()
    return list_vehicles(session)


# --- odometer readings ------------------------------------------------------


def latest_reading(session: Session, vehicle_id: int) -> OdometerReading | None:
    return session.scalars(
        select(OdometerReading)
        .where(OdometerReading.vehicle_id == vehicle_id)
        .order_by(OdometerReading.reported_at.desc(), OdometerReading.id.desc())
        .limit(1)
    ).first()


def latest_miles(session: Session, vehicle_id: int) -> int | None:
    reading = latest_reading(session, vehicle_id)
    return reading.miles if reading else None


def odometer_map(session: Session) -> dict[int, int | None]:
    return {v.id: latest_miles(session, v.id) for v in list_vehicles(session)}


def record_reading(session: Session, vehicle_id: int, miles: int, reported_at: datetime) -> bool:
    """Append a reading if the value actually changed, then trim the history."""
    current = latest_reading(session, vehicle_id)
    if current is not None and current.miles == miles:
        return False
    session.add(OdometerReading(vehicle_id=vehicle_id, miles=miles, reported_at=reported_at.isoformat()))
    session.commit()
    _trim_readings(session, vehicle_id)
    return True


def _trim_readings(session: Session, vehicle_id: int) -> None:
    keep = session.scalars(
        select(OdometerReading.id)
        .where(OdometerReading.vehicle_id == vehicle_id)
        .order_by(OdometerReading.reported_at.desc(), OdometerReading.id.desc())
        .limit(READING_HISTORY_LIMIT)
    ).all()
    session.execute(
        delete(OdometerReading).where(
            OdometerReading.vehicle_id == vehicle_id,
            OdometerReading.id.not_in(keep),
        )
    )
    session.commit()


def reading_at_or_before(session: Session, vehicle_id: int, moment: datetime):
    """Newest reading taken at or before ``moment``, else the oldest one held."""
    newest = session.scalars(
        select(OdometerReading)
        .where(OdometerReading.vehicle_id == vehicle_id, OdometerReading.reported_at <= moment.isoformat())
        .order_by(OdometerReading.reported_at.desc(), OdometerReading.id.desc())
        .limit(1)
    ).first()
    if newest is not None:
        return newest, True
    oldest = session.scalars(
        select(OdometerReading)
        .where(OdometerReading.vehicle_id == vehicle_id)
        .order_by(OdometerReading.reported_at.asc(), OdometerReading.id.asc())
        .limit(1)
    ).first()
    return oldest, False


# --- reminders --------------------------------------------------------------


def list_reminders(session: Session) -> list[Reminder]:
    return list(session.scalars(select(Reminder).order_by(Reminder.vehicle_id, Reminder.id)))


def get_reminder(session: Session, reminder_id: int) -> Reminder | None:
    return session.get(Reminder, reminder_id)


def mark_notified(session: Session, reminder: Reminder, now: datetime) -> None:
    reminder.notified_at = now.isoformat()
    reminder.last_nag_at = None
    reminder.nag_count = 0
    session.commit()


def mark_nagged(session: Session, reminder: Reminder, now: datetime) -> None:
    reminder.last_nag_at = now.isoformat()
    reminder.nag_count += 1
    session.commit()


def record_service_event(session: Session, reminder: Reminder, odometer: int, performed_at: datetime) -> None:
    """Record the service and move the whole Baseline to that point.

    Both clocks reset together: the Baseline is one point, never two.
    """
    session.add(
        ServiceEvent(reminder_id=reminder.id, odometer=odometer, performed_at=performed_at.isoformat())
    )
    reminder.baseline_odometer = odometer
    reminder.baseline_at = performed_at.isoformat()
    reminder.notified_at = None
    reminder.last_nag_at = None
    reminder.nag_count = 0
    session.commit()


# --- pending flows ----------------------------------------------------------


def get_flow(session: Session, chat_id: int) -> PendingFlow | None:
    return session.scalars(select(PendingFlow).where(PendingFlow.chat_id == chat_id)).first()


def save_flow(session: Session, chat_id: int, command: str, step: str, answers: dict, now: datetime) -> None:
    flow = get_flow(session, chat_id)
    if flow is None:
        flow = PendingFlow(chat_id=chat_id, command=command, step=step)
        session.add(flow)
    flow.command = command
    flow.step = step
    flow.answers_json = json.dumps(answers)
    flow.touched_at = now.isoformat()
    session.commit()


def clear_flow(session: Session, chat_id: int) -> None:
    session.execute(delete(PendingFlow).where(PendingFlow.chat_id == chat_id))
    session.commit()


def flow_answers(flow: PendingFlow) -> dict:
    return json.loads(flow.answers_json)


def expire_stale_flows(session: Session, now: datetime) -> None:
    from datetime import timedelta

    cutoff = (now - timedelta(minutes=FLOW_EXPIRY_MINUTES)).isoformat()
    session.execute(delete(PendingFlow).where(PendingFlow.touched_at < cutoff))
    session.commit()


# --- app state --------------------------------------------------------------


def get_state(session: Session, key: str, default: str = "") -> str:
    row = session.get(AppState, key)
    return row.value if row else default


def set_state(session: Session, key: str, value: str) -> None:
    row = session.get(AppState, key)
    if row is None:
        session.add(AppState(key=key, value=value))
    else:
        row.value = value
    session.commit()
