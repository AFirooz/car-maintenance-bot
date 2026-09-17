"""The three collaborators the run entry point is parameterised by.

Tests supply fakes for all of them; the database is real SQLite either way.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol


@dataclass(frozen=True)
class Reading:
    """An Odometer Reading as reported by the Vehicle itself."""

    miles: int
    reported_at: datetime


@dataclass(frozen=True)
class DiscoveredVehicle:
    vin: str
    display_name: str


@dataclass(frozen=True)
class InboundMessage:
    user_id: int
    text: str


class OdometerSource(Protocol):
    async def vehicles(self) -> list[DiscoveredVehicle]: ...

    async def reading(self, vin: str) -> Reading | None:
        """Return the Vehicle's latest cached reading, or None if unavailable."""
        ...


class ChatTransport(Protocol):
    async def updates(self) -> list[InboundMessage]: ...

    async def send(self, text: str) -> None: ...


class Clock(Protocol):
    def now(self) -> datetime:
        """Local wall-clock time, naive."""
        ...


class SystemClock:
    def now(self) -> datetime:
        return datetime.now()
