"""One-time Subaru two-factor device registration.

Subaru ties registration to SUBARU_DEVICE_ID, so keep that value stable forever;
changing it means doing this again.
"""

from __future__ import annotations

import asyncio
import sys

import aiohttp
import subarulink

from config import load_config


async def main() -> int:
    config = load_config()
    if not config.subaru_device_id:
        print("Set SUBARU_DEVICE_ID in .env first. Any stable integer works, e.g.")
        print(f"  SUBARU_DEVICE_ID=\"{int(__import__('time').time())}\"")
        return 1

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
        await controller.connect()

        if controller.device_registered:
            print("Already registered. Nothing to do.")
            print(f"Vehicles on this account: {', '.join(controller.get_vehicles())}")
            return 0

        methods = controller.contact_methods
        print("Where should Subaru send the code?")
        for key, value in methods.items():
            print(f"  {key}: {value}")
        choice = input("Contact method key: ").strip()
        if not await controller.request_auth_code(choice):
            print("Subaru refused to send a code.")
            return 1

        code = input("Enter the 6-digit code: ").strip()
        if not await controller.submit_auth_code(code):
            print("That code was not accepted.")
            return 1

        print("Registered. This device will not need 2FA again.")
        print(f"Vehicles on this account: {', '.join(controller.get_vehicles())}")
        return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
