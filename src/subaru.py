"""The only module that imports subarulink.

Reads Subaru's server-side cache with ``fetch()``. ``update()`` is never called:
it wakes the vehicle, and the library documents a 12V battery drain risk.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import datetime

import aiohttp
import subarulink
import subarulink.const as sc
from loguru import logger
from subarulink.exceptions import InvalidCredentials

import auth_guard
from config import Config
from ports import DiscoveredVehicle, Reading


class DeviceNotRegistered(RuntimeError):
    pass


class SubaruOdometer:
    def __init__(self, controller: subarulink.Controller):
        self._controller = controller

    async def vehicles(self) -> list[DiscoveredVehicle]:
        found = []
        for vin in self._controller.get_vehicles():
            data = await self._controller.get_data(vin)
            name = data.get("vehicle_name") or data.get("model_name") or vin[-6:]
            found.append(DiscoveredVehicle(vin=vin, display_name=str(name)))
        return found

    async def reading(self, vin: str) -> Reading | None:
        await self._controller.fetch(vin)
        data = await self._controller.get_data(vin)
        status = data.get(sc.VEHICLE_STATUS) or {}

        miles = status.get(sc.ODOMETER)
        if miles is sc.BAD_ODOMETER or miles is None:
            logger.warning(f"No odometer value in cached data for {vin}")
            return None

        reported_at = status.get(sc.TIMESTAMP)
        if isinstance(reported_at, datetime):
            # The vehicle reports tz-aware; the rest of the project is local naive.
            reported_at = reported_at.astimezone().replace(tzinfo=None)
        else:
            logger.warning(f"No vehicle timestamp for {vin}; recording the poll time instead")
            reported_at = datetime.now()

        return Reading(miles=int(miles), reported_at=reported_at)


@asynccontextmanager
async def subaru_source(config: Config, session):
    if auth_guard.blocked(session, config.subaru_username, config.subaru_password):
        count = auth_guard.failures(session, config.subaru_username, config.subaru_password)
        raise auth_guard.CredentialsRefused(auth_guard.refusal_message(count))

    async with aiohttp.ClientSession() as websession:
        controller = subarulink.Controller(
            websession,
            config.subaru_username,
            config.subaru_password,
            config.subaru_device_id,
            config.subaru_pin,
            config.subaru_device_name,
            country=config.subaru_country,
        )
        try:
            await controller.connect()
        except InvalidCredentials:
            count = auth_guard.record_failure(
                session, config.subaru_username, config.subaru_password
            )
            logger.error(f"Subaru rejected the login ({count} in a row).")
            raise

        auth_guard.record_success(session, config.subaru_username, config.subaru_password)
        if not controller.device_registered:
            raise DeviceNotRegistered(
                "This device is not registered with Subaru. Run: uv run src/register_device.py"
            )
        yield SubaruOdometer(controller)
