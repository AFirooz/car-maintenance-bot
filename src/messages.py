"""User-facing text. Uses the CONTEXT.md vocabulary throughout."""

from __future__ import annotations

from datetime import datetime

from reminders import MAX_NAGS, days_remaining, due_date, due_odometer, due_reason, miles_remaining
from schema import Reminder, Vehicle


def _miles(value: int) -> str:
    return f"{value:,} mi"


def due_text(
    reminder: Reminder,
    vehicle: Vehicle,
    reason: str,
    current_odometer: int | None,
    now: datetime,
    is_nag: bool,
    nag_number: int,
) -> str:
    head = f"{reminder.name} is due" if not is_nag else f"Still due: {reminder.name}"
    lines = [f"{head} - {vehicle.display_name}", f"Due by {reason}."]

    target_odometer = due_odometer(reminder)
    if target_odometer is not None:
        if current_odometer is None:
            lines.append(f"Due at {_miles(target_odometer)}; no odometer reading available.")
        else:
            over = current_odometer - target_odometer
            past = f"{_miles(over)} past" if over >= 0 else f"{_miles(-over)} to go"
            lines.append(f"Odometer {_miles(current_odometer)}, due at {_miles(target_odometer)} ({past}).")

    target_date = due_date(reminder)
    if target_date is not None:
        left = days_remaining(reminder, now)
        past = f"{-left} days past" if left <= 0 else f"in {left} days"
        lines.append(f"Due {target_date:%Y-%m-%d} ({past}).")

    if is_nag:
        lines.append(f"Nag {nag_number} of {MAX_NAGS}.")
        if nag_number >= MAX_NAGS:
            lines.append("This is the last one; I'll stay quiet until you send /done.")
    lines.append("Send /done when it's been taken care of.")
    return "\n".join(lines)


def reminder_line(index: int, reminder: Reminder, current_odometer: int | None, now: datetime) -> str:
    parts = []
    miles = miles_remaining(reminder, current_odometer)
    if miles is not None:
        parts.append(f"{_miles(miles)} left" if miles >= 0 else f"{_miles(-miles)} over")
    elif reminder.mileage_interval is not None:
        parts.append("no odometer reading")
    days = days_remaining(reminder, now)
    if days is not None:
        parts.append(f"{days} days left" if days >= 0 else f"{-days} days over")
    status = " DUE -" if due_reason(reminder, current_odometer, now) else ""
    return f"{index}.{status} {reminder.name} - {', '.join(parts)}"


def list_text(
    vehicles: list[Vehicle],
    reminders: list[Reminder],
    odometers: dict[int, int | None],
    now: datetime,
) -> str:
    if not reminders:
        return "No reminders yet. Send /add to create one."
    by_vehicle = {v.id: v for v in vehicles}
    show_vehicle = len(vehicles) > 1
    lines: list[str] = []
    current_vehicle = None
    for index, reminder in enumerate(reminders, start=1):
        if show_vehicle and reminder.vehicle_id != current_vehicle:
            current_vehicle = reminder.vehicle_id
            vehicle = by_vehicle.get(current_vehicle)
            lines.append(f"\n{vehicle.display_name if vehicle else 'Unknown vehicle'}:")
        lines.append(reminder_line(index, reminder, odometers.get(reminder.vehicle_id), now))
    return "\n".join(lines).strip()


def baseline_text(reminder_name: str, odometer: int, moment: datetime) -> str:
    return f"{reminder_name} now measured from {_miles(odometer)} on {moment:%Y-%m-%d}"
