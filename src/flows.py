"""Interactive command flows.

Every step is persisted to the database before the reply is sent, so a
half-finished conversation survives the process exiting between scheduled runs.
"""

from __future__ import annotations

import re
from datetime import datetime

from sqlalchemy.orm import Session

import db
import messages
from reminders import due_date, due_odometer
from schema import Reminder

DEFAULT_NAG_DAYS = 7
SKIP = {"-", "skip", "none", "no", "n/a"}
NOW_WORDS = {"-", "now", "today"}
YES = {"y", "yes", "ok", "confirm"}
DROPPED = "Dropped it."

_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

HELP = (
    "Commands:\n"
    "/add - create a reminder\n"
    "/list - show reminders\n"
    "/done - record that a service was performed\n"
    "/delete - remove a reminder\n"
    "/rename - rename a vehicle\n"
    "/cancel - abandon what we were doing"
)


class FlowError(Exception):
    """Something the owner typed can't be used; the step is re-asked."""


# --- parsing ----------------------------------------------------------------


def parse_when(text: str) -> tuple[int | None, datetime | None]:
    """Read an odometer, a date, or both from free text.

    A ``YYYY-MM-DD`` token is a date; a bare number is an odometer.
    """
    odometer: int | None = None
    moment: datetime | None = None
    for token in text.split():
        if _DATE_RE.match(token):
            moment = datetime.fromisoformat(token)
        elif token.isdigit():
            odometer = int(token)
        else:
            raise FlowError(f"I couldn't read '{token}' as a date (YYYY-MM-DD) or an odometer.")
    return odometer, moment


def _positive_int(text: str, label: str) -> int:
    if not text.isdigit() or int(text) <= 0:
        raise FlowError(f"{label} needs to be a whole number greater than zero.")
    return int(text)


def _choice_index(text: str, count: int) -> int:
    if not text.isdigit() or not (1 <= int(text) <= count):
        raise FlowError(f"Send a number between 1 and {count}.")
    return int(text) - 1


# --- baseline resolution ----------------------------------------------------


async def _resolve_baseline(
    session: Session,
    vehicle_id: int,
    odometer: int | None,
    moment: datetime | None,
    now: datetime,
    fetch_reading,
) -> tuple[int, datetime, str | None]:
    """Work out the half of the Baseline the owner didn't supply.

    ``moment`` of None means "right now", which is the only case worth spending a
    live odometer read on; a stated date is answered from stored history.
    """
    note: str | None = None
    wants_now = moment is None
    if moment is None:
        moment = now
    if odometer is not None:
        return odometer, moment, note

    if wants_now:
        vehicle = session.get(db.Vehicle, vehicle_id)
        fetched = await fetch_reading(vehicle.vin) if vehicle else None
        if fetched is not None:
            return fetched.miles, moment, None
        raise FlowError(
            "I couldn't read the odometer from Subaru, so I have no baseline for this. "
            "Send the odometer value and I'll use that."
        )

    reading, exact = db.reading_at_or_before(session, vehicle_id, moment)
    if reading is None:
        raise FlowError(
            "I have no odometer readings yet, so I can't work out the mileage for that date. "
            "Send the odometer value as well."
        )
    if not exact:
        note = (
            "I had no reading from on or before that date, "
            f"so I used the oldest one I have ({reading.miles:,} mi)."
        )
    return reading.miles, moment, note


# --- entry point ------------------------------------------------------------


async def handle_message(
    session: Session,
    chat_id: int,
    text: str,
    now: datetime,
    send,
    fetch_reading,
) -> None:
    db.expire_stale_flows(session, now)
    text = text.strip()

    if text.startswith("/"):
        command, _, rest = text.partition(" ")
        command = command.lower()
        rest = rest.strip()
        if command == "/cancel":
            db.clear_flow(session, chat_id)
            await send(DROPPED)
            return
        db.clear_flow(session, chat_id)
        try:
            if command == "/add":
                await _add_start(session, chat_id, now, send)
            elif command == "/list":
                await _list(session, now, send)
            elif command == "/done":
                await _done_start(session, chat_id, rest, now, send, fetch_reading)
            elif command == "/delete":
                await _delete_start(session, chat_id, rest, now, send)
            elif command == "/rename":
                await _rename_start(session, chat_id, rest, now, send)
            else:
                await send(HELP)
        except FlowError as error:
            await send(str(error))
        return

    flow = db.get_flow(session, chat_id)
    if flow is None:
        await send(HELP)
        return
    try:
        await _advance(session, chat_id, flow, text, now, send, fetch_reading)
    except FlowError as error:
        await send(str(error))


async def _advance(session, chat_id, flow, text, now, send, fetch_reading) -> None:
    answers = db.flow_answers(flow)
    if flow.command == "/add":
        await _add_step(session, chat_id, flow.step, answers, text, now, send, fetch_reading)
    elif flow.command == "/done":
        await _done_step(session, chat_id, flow.step, answers, text, now, send, fetch_reading)
    elif flow.command == "/delete":
        await _delete_step(session, chat_id, flow.step, answers, text, now, send)
    elif flow.command == "/rename":
        await _rename_step(session, chat_id, flow.step, answers, text, now, send)


# --- /list ------------------------------------------------------------------


async def _list(session: Session, now: datetime, send) -> None:
    await send(
        messages.list_text(
            db.list_vehicles(session),
            db.list_reminders(session),
            db.odometer_map(session),
            now,
        )
    )


def _numbered_reminders(session: Session) -> tuple[list[Reminder], str]:
    reminders = db.list_reminders(session)
    if not reminders:
        raise FlowError("You have no reminders yet. Send /add to create one.")
    lines = [f"{i}. {r.name}" for i, r in enumerate(reminders, start=1)]
    return reminders, "\n".join(lines)


# --- /add -------------------------------------------------------------------


async def _add_start(session: Session, chat_id: int, now: datetime, send) -> None:
    vehicles = db.list_vehicles(session)
    if not vehicles:
        raise FlowError("I don't know about any vehicles yet. Run setup first.")
    if len(vehicles) == 1:
        db.save_flow(session, chat_id, "/add", "name", {"vehicle_id": vehicles[0].id}, now)
        await send("What's the service called?")
        return
    listing = "\n".join(f"{i}. {v.display_name}" for i, v in enumerate(vehicles, start=1))
    db.save_flow(session, chat_id, "/add", "vehicle", {}, now)
    await send(f"Which vehicle?\n{listing}")


async def _add_step(session, chat_id, step, answers, text, now, send, fetch_reading) -> None:
    if step == "vehicle":
        vehicles = db.list_vehicles(session)
        answers["vehicle_id"] = vehicles[_choice_index(text, len(vehicles))].id
        db.save_flow(session, chat_id, "/add", "name", answers, now)
        await send("What's the service called?")

    elif step == "name":
        if not text:
            raise FlowError("Give it a name, like 'Oil change'.")
        answers["name"] = text
        db.save_flow(session, chat_id, "/add", "mileage", answers, now)
        await send("Mileage interval, in miles? Send - to skip.")

    elif step == "mileage":
        answers["mileage_interval"] = None if text.lower() in SKIP else _positive_int(text, "Mileage interval")
        db.save_flow(session, chat_id, "/add", "months", answers, now)
        await send("Time interval, in months? Send - to skip.")

    elif step == "months":
        months = None if text.lower() in SKIP else _positive_int(text, "Time interval")
        if months is None and answers.get("mileage_interval") is None:
            db.save_flow(session, chat_id, "/add", "mileage", answers, now)
            raise FlowError(
                "A reminder needs at least one interval. Mileage interval, in miles? Send - to skip."
            )
        answers["time_interval_months"] = months
        db.save_flow(session, chat_id, "/add", "nag", answers, now)
        await send(f"How often should I nag you once it's due, in days? Send - for {DEFAULT_NAG_DAYS}.")

    elif step == "nag":
        answers["nag_interval_days"] = (
            DEFAULT_NAG_DAYS if text.lower() in SKIP else _positive_int(text, "Nag interval")
        )
        db.save_flow(session, chat_id, "/add", "last", answers, now)
        await send(
            "When was it last done? Send - for right now at the current odometer, "
            "or a date (YYYY-MM-DD), or an odometer, or both."
        )

    elif step == "last":
        odometer, moment = (None, None) if text.lower() in NOW_WORDS else parse_when(text)
        odometer, moment, note = await _resolve_baseline(
            session, answers["vehicle_id"], odometer, moment, now, fetch_reading
        )
        answers["baseline_odometer"] = odometer
        answers["baseline_at"] = moment.isoformat()
        db.save_flow(session, chat_id, "/add", "confirm", answers, now)
        await send(_add_summary(session, answers, note))

    elif step == "confirm":
        if text.lower() not in YES:
            db.clear_flow(session, chat_id)
            await send(DROPPED)
            return
        reminder = Reminder(
            vehicle_id=answers["vehicle_id"],
            name=answers["name"],
            mileage_interval=answers["mileage_interval"],
            time_interval_months=answers["time_interval_months"],
            nag_interval_days=answers["nag_interval_days"],
            baseline_odometer=answers["baseline_odometer"],
            baseline_at=answers["baseline_at"],
        )
        session.add(reminder)
        session.commit()
        db.clear_flow(session, chat_id)
        await send(f"Saved: {reminder.name}.")


def _add_summary(session: Session, answers: dict, note: str | None) -> str:
    vehicle = session.get(db.Vehicle, answers["vehicle_id"])
    lines = [
        "Check this over:",
        f"Service: {answers['name']}",
        f"Vehicle: {vehicle.display_name if vehicle else '?'}",
    ]
    if answers["mileage_interval"] is not None:
        lines.append(f"Mileage interval: every {answers['mileage_interval']:,} mi")
    if answers["time_interval_months"] is not None:
        lines.append(f"Time interval: every {answers['time_interval_months']} months")
    lines.append(f"Nag interval: every {answers['nag_interval_days']} days")
    baseline_at = datetime.fromisoformat(answers["baseline_at"])
    lines.append(
        f"Measuring from: {answers['baseline_odometer']:,} mi on {baseline_at:%Y-%m-%d}"
    )

    probe = Reminder(
        mileage_interval=answers["mileage_interval"],
        time_interval_months=answers["time_interval_months"],
        baseline_odometer=answers["baseline_odometer"],
        baseline_at=answers["baseline_at"],
    )
    next_odometer = due_odometer(probe)
    if next_odometer is not None:
        lines.append(f"Next due at: {next_odometer:,} mi")
    next_date = due_date(probe)
    if next_date is not None:
        lines.append(f"Next due on: {next_date:%Y-%m-%d}")
    if note:
        lines.append(note)
    lines.append("Send yes to save, anything else to drop it.")
    return "\n".join(lines)


# --- /done ------------------------------------------------------------------


async def _done_start(session, chat_id, rest, now, send, fetch_reading) -> None:
    reminders, listing = _numbered_reminders(session)
    if not rest:
        db.save_flow(session, chat_id, "/done", "pick", {}, now)
        await send(f"Which one did you do?\n{listing}")
        return
    index, _, when = rest.partition(" ")
    reminder = reminders[_choice_index(index, len(reminders))]
    answers = {"reminder_id": reminder.id}
    if not when.strip():
        db.save_flow(session, chat_id, "/done", "when", answers, now)
        await send(_when_prompt(reminder.name))
        return
    await _done_when(session, chat_id, answers, when.strip(), now, send, fetch_reading)


def _when_prompt(name: str) -> str:
    return (
        f"When was {name} done? Send - for right now at the current odometer, "
        "or a date (YYYY-MM-DD), or an odometer, or both."
    )


async def _done_step(session, chat_id, step, answers, text, now, send, fetch_reading) -> None:
    if step == "pick":
        reminders, _ = _numbered_reminders(session)
        reminder = reminders[_choice_index(text, len(reminders))]
        answers["reminder_id"] = reminder.id
        db.save_flow(session, chat_id, "/done", "when", answers, now)
        await send(_when_prompt(reminder.name))

    elif step == "when":
        await _done_when(session, chat_id, answers, text, now, send, fetch_reading)

    elif step == "confirm":
        reminder = db.get_reminder(session, answers["reminder_id"])
        if reminder is None:
            db.clear_flow(session, chat_id)
            raise FlowError("That reminder is gone.")
        if text.lower() not in YES:
            db.clear_flow(session, chat_id)
            await send(DROPPED)
            return
        moment = datetime.fromisoformat(answers["performed_at"])
        db.record_service_event(session, reminder, answers["odometer"], moment)
        db.clear_flow(session, chat_id)
        await send(messages.baseline_text(reminder.name, answers["odometer"], moment) + ".")


async def _done_when(session, chat_id, answers, text, now, send, fetch_reading) -> None:
    reminder = db.get_reminder(session, answers["reminder_id"])
    if reminder is None:
        db.clear_flow(session, chat_id)
        raise FlowError("That reminder is gone.")
    odometer, moment = (None, None) if text.lower() in NOW_WORDS else parse_when(text)
    odometer, moment, note = await _resolve_baseline(
        session, reminder.vehicle_id, odometer, moment, now, fetch_reading
    )
    answers["odometer"] = odometer
    answers["performed_at"] = moment.isoformat()
    db.save_flow(session, chat_id, "/done", "confirm", answers, now)
    lines = [messages.baseline_text(reminder.name, odometer, moment) + "."]
    if note:
        lines.append(note)
    lines.append("Send yes to confirm, anything else to drop it.")
    await send("\n".join(lines))


# --- /delete ----------------------------------------------------------------


async def _delete_start(session, chat_id, rest, now, send) -> None:
    reminders, listing = _numbered_reminders(session)
    if not rest:
        db.save_flow(session, chat_id, "/delete", "pick", {}, now)
        await send(f"Which one should I remove?\n{listing}")
        return
    reminder = reminders[_choice_index(rest, len(reminders))]
    db.save_flow(session, chat_id, "/delete", "confirm", {"reminder_id": reminder.id}, now)
    await send(f"Delete {reminder.name}? Send yes to confirm.")


async def _delete_step(session, chat_id, step, answers, text, now, send) -> None:
    if step == "pick":
        reminders, _ = _numbered_reminders(session)
        reminder = reminders[_choice_index(text, len(reminders))]
        db.save_flow(session, chat_id, "/delete", "confirm", {"reminder_id": reminder.id}, now)
        await send(f"Delete {reminder.name}? Send yes to confirm.")

    elif step == "confirm":
        reminder = db.get_reminder(session, answers["reminder_id"])
        db.clear_flow(session, chat_id)
        if reminder is None:
            raise FlowError("That reminder is gone.")
        if text.lower() not in YES:
            await send(DROPPED)
            return
        name = reminder.name
        session.delete(reminder)
        session.commit()
        await send(f"Deleted {name}.")


# --- /rename ----------------------------------------------------------------


async def _rename_start(session, chat_id, rest, now, send) -> None:
    vehicles = db.list_vehicles(session)
    if not vehicles:
        raise FlowError("I don't know about any vehicles yet. Run setup first.")
    if len(vehicles) == 1:
        db.save_flow(session, chat_id, "/rename", "name", {"vehicle_id": vehicles[0].id}, now)
        await send(f"What should I call {vehicles[0].display_name}?")
        return
    listing = "\n".join(f"{i}. {v.display_name}" for i, v in enumerate(vehicles, start=1))
    db.save_flow(session, chat_id, "/rename", "pick", {}, now)
    await send(f"Which vehicle should I rename?\n{listing}")


async def _rename_step(session, chat_id, step, answers, text, now, send) -> None:
    vehicles = db.list_vehicles(session)
    if step == "pick":
        vehicle = vehicles[_choice_index(text, len(vehicles))]
        db.save_flow(session, chat_id, "/rename", "name", {"vehicle_id": vehicle.id}, now)
        await send(f"What should I call {vehicle.display_name}?")

    elif step == "name":
        if not text:
            raise FlowError("Give it a name, like 'Outback'.")
        vehicle = session.get(db.Vehicle, answers["vehicle_id"])
        db.clear_flow(session, chat_id)
        if vehicle is None:
            raise FlowError("That vehicle is gone.")
        vehicle.display_name = text
        session.commit()
        await send(f"Renamed to {text}.")
