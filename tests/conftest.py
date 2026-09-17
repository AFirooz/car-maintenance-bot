from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

import pytest

import db
from ports import DiscoveredVehicle, InboundMessage, Reading

OWNER_ID = 4242
VIN = "JF2TESTVIN0000001"
SECOND_VIN = "JF2TESTVIN0000002"


class FakeClock:
    def __init__(self, start: datetime):
        self._now = start

    def now(self) -> datetime:
        return self._now

    def advance(self, **kwargs) -> None:
        self._now += timedelta(**kwargs)

    def set(self, moment: datetime) -> None:
        self._now = moment


class FakeChat:
    """Records what the owner would see, and queues what they type."""

    def __init__(self):
        self.inbox: list[InboundMessage] = []
        self.sent: list[str] = []

    def receive(self, text: str, user_id: int = OWNER_ID) -> None:
        self.inbox.append(InboundMessage(user_id=user_id, text=text))

    async def updates(self) -> list[InboundMessage]:
        pending, self.inbox = self.inbox, []
        return pending

    async def send(self, text: str) -> None:
        self.sent.append(text)

    @property
    def last(self) -> str:
        return self.sent[-1] if self.sent else ""

    def clear(self) -> None:
        self.sent = []


@dataclass
class FakeOdometer:
    """Scripted per VIN. A value of None means no reading is available."""

    miles: dict
    reported_at: datetime
    names: dict | None = None
    raises: bool = False

    async def vehicles(self) -> list[DiscoveredVehicle]:
        names = self.names or {vin: f"Car {i}" for i, vin in enumerate(self.miles, start=1)}
        return [DiscoveredVehicle(vin=vin, display_name=names[vin]) for vin in self.miles]

    async def reading(self, vin: str) -> Reading | None:
        if self.raises:
            raise RuntimeError("subaru is down")
        value = self.miles.get(vin)
        if value is None:
            return None
        return Reading(miles=value, reported_at=self.reported_at)


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock(datetime(2026, 1, 10, 12, 0))


@pytest.fixture
def chat() -> FakeChat:
    return FakeChat()


@pytest.fixture
def odometer(clock) -> FakeOdometer:
    return FakeOdometer(miles={VIN: 40_000}, reported_at=clock.now(), names={VIN: "Outback"})


@pytest.fixture
def two_car_odometer(clock) -> FakeOdometer:
    return FakeOdometer(
        miles={VIN: 40_000, SECOND_VIN: 12_000},
        reported_at=clock.now(),
        names={VIN: "Outback", SECOND_VIN: "Forester"},
    )


@pytest.fixture
def session_factory(tmp_path):
    return db.make_session_factory(str(tmp_path / "test.db"))


@pytest.fixture
def session(session_factory):
    with session_factory() as active:
        yield active
