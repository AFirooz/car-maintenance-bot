from __future__ import annotations

from datetime import datetime

from sqlalchemy import ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def _now_local_iso() -> str:
    return datetime.now().isoformat()


class Base(DeclarativeBase):
    pass


class Vehicle(Base):
    __tablename__ = "vehicles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    vin: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String, nullable=False)


class OdometerReading(Base):
    """Miles reported by a Vehicle, with the moment the Vehicle itself reported it."""

    __tablename__ = "odometer_readings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    vehicle_id: Mapped[int] = mapped_column(ForeignKey("vehicles.id", ondelete="CASCADE"), nullable=False)
    miles: Mapped[int] = mapped_column(Integer, nullable=False)
    reported_at: Mapped[str] = mapped_column(String, nullable=False)


class Reminder(Base):
    """A named service, recurring on a Mileage Interval, a Time Interval, or both."""

    __tablename__ = "reminders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    vehicle_id: Mapped[int] = mapped_column(ForeignKey("vehicles.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    mileage_interval: Mapped[int | None] = mapped_column(Integer, nullable=True)
    time_interval_months: Mapped[int | None] = mapped_column(Integer, nullable=True)
    nag_interval_days: Mapped[int] = mapped_column(Integer, nullable=False)

    # Baseline: the single point this Reminder measures its next occurrence from.
    baseline_odometer: Mapped[int] = mapped_column(Integer, nullable=False)
    baseline_at: Mapped[str] = mapped_column(String, nullable=False)

    # Current Due episode. notified_at is None while the Reminder is not Due.
    notified_at: Mapped[str | None] = mapped_column(String, nullable=True)
    last_nag_at: Mapped[str | None] = mapped_column(String, nullable=True)
    nag_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class ServiceEvent(Base):
    """The owner's record that a Reminder's service was performed."""

    __tablename__ = "service_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    reminder_id: Mapped[int] = mapped_column(ForeignKey("reminders.id", ondelete="CASCADE"), nullable=False)
    odometer: Mapped[int] = mapped_column(Integer, nullable=False)
    performed_at: Mapped[str] = mapped_column(String, nullable=False)


class PendingFlow(Base):
    """A half-finished interactive conversation, resumable across process exits."""

    __tablename__ = "pending_flows"
    __table_args__ = (UniqueConstraint("chat_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    chat_id: Mapped[int] = mapped_column(Integer, nullable=False)
    command: Mapped[str] = mapped_column(String, nullable=False)
    step: Mapped[str] = mapped_column(String, nullable=False)
    answers_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    touched_at: Mapped[str] = mapped_column(String, nullable=False, default=_now_local_iso)


class AppState(Base):
    __tablename__ = "app_state"

    key: Mapped[str] = mapped_column(String, primary_key=True)
    value: Mapped[str] = mapped_column(Text, nullable=False)
