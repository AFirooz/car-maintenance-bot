"""Due and Nag rules. Pure: decides what should be said, sends nothing."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from dateutil.relativedelta import relativedelta

from schema import Reminder

MAX_NAGS = 4

DUE_BY_MILEAGE = "mileage"
DUE_BY_TIME = "time"
DUE_BY_BOTH = "mileage and time"


@dataclass(frozen=True)
class Notification:
    reminder: Reminder
    is_nag: bool
    reason: str
    nag_number: int = 0


def due_odometer(reminder: Reminder) -> int | None:
    """The odometer value at which this Reminder becomes Due."""
    if reminder.mileage_interval is None:
        return None
    return reminder.baseline_odometer + reminder.mileage_interval


def due_date(reminder: Reminder) -> datetime | None:
    """The moment at which this Reminder becomes Due.

    Calendar months, clamped to the last day of the target month by
    ``relativedelta`` when the day does not exist.
    """
    if reminder.time_interval_months is None:
        return None
    baseline = datetime.fromisoformat(reminder.baseline_at)
    return baseline + relativedelta(months=reminder.time_interval_months)


def miles_remaining(reminder: Reminder, current_odometer: int | None) -> int | None:
    target = due_odometer(reminder)
    if target is None or current_odometer is None:
        return None
    return target - current_odometer


def days_remaining(reminder: Reminder, now: datetime) -> int | None:
    target = due_date(reminder)
    if target is None:
        return None
    return (target - now).days


def due_reason(reminder: Reminder, current_odometer: int | None, now: datetime) -> str | None:
    """Why this Reminder is Due right now, or None if it is not."""
    by_mileage = False
    target_odometer = due_odometer(reminder)
    if target_odometer is not None and current_odometer is not None:
        by_mileage = current_odometer >= target_odometer

    by_time = False
    target_date = due_date(reminder)
    if target_date is not None:
        by_time = now >= target_date

    if by_mileage and by_time:
        return DUE_BY_BOTH
    if by_mileage:
        return DUE_BY_MILEAGE
    if by_time:
        return DUE_BY_TIME
    return None


def declared_reason(reminder: Reminder) -> str:
    """The dimensions this Reminder actually has, for when the live one is unknowable."""
    if reminder.mileage_interval is not None and reminder.time_interval_months is not None:
        return DUE_BY_BOTH
    if reminder.mileage_interval is not None:
        return DUE_BY_MILEAGE
    return DUE_BY_TIME


def _nag_is_owed(reminder: Reminder, now: datetime) -> bool:
    if reminder.nag_count >= MAX_NAGS:
        return False
    since = reminder.last_nag_at or reminder.notified_at
    if since is None:
        return False
    return now >= datetime.fromisoformat(since) + timedelta(days=reminder.nag_interval_days)


def evaluate(
    reminders: list[Reminder],
    odometers: dict[int, int | None],
    now: datetime,
) -> list[Notification]:
    """Decide which Reminders need telling about.

    ``odometers`` maps vehicle id to its latest known miles, or None when no
    reading has ever been taken. A missing odometer never stops a Time Interval
    from being evaluated.
    """
    notifications: list[Notification] = []
    for reminder in reminders:
        current = odometers.get(reminder.vehicle_id)
        if reminder.notified_at is None:
            reason = due_reason(reminder, current, now)
            if reason is not None:
                notifications.append(Notification(reminder=reminder, is_nag=False, reason=reason))
        elif _nag_is_owed(reminder, now):
            reason = due_reason(reminder, current, now) or declared_reason(reminder)
            notifications.append(
                Notification(
                    reminder=reminder,
                    is_nag=True,
                    reason=reason,
                    nag_number=reminder.nag_count + 1,
                )
            )
    return notifications
