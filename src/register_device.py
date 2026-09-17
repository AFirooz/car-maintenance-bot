"""One-time Subaru two-factor device registration.

Subaru ties registration to SUBARU_DEVICE_ID, so keep that value stable forever;
changing it means doing this again.
"""

from __future__ import annotations

import asyncio
import sys

import aiohttp
import subarulink
from subarulink.exceptions import InvalidCredentials, SubaruException

import auth_guard
import db
from config import load_config


def _explain_rejection(code: str, config, count: int) -> None:
    """Subaru returns one generic code for every kind of login rejection."""
    print(f"Subaru rejected the login ({code}).")
    print()
    print("This code is generic: Subaru returns it for a wrong email, a wrong")
    print("password, and an account without connected services alike. Check, in order:")
    print()
    print(f"  1. SUBARU_USERNAME is the email you sign in to MySubaru with.")
    print(f"     Currently {len(config.subaru_username)} characters.")
    print("  2. SUBARU_PASSWORD matches that sign-in, with no stray spaces.")
    print("     Verify both at https://www.subaru.com/owners.html by signing in.")
    print("  3. The account has active MySubaru connected services (STARLINK) on")
    print("     at least one vehicle. An account with no enrolled vehicle is rejected.")
    print()
    remaining = auth_guard.MAX_AUTH_FAILURES - count
    if remaining > 0:
        print(f"I will attempt {remaining} more login(s) with these exact credentials,")
        print("then refuse, because Subaru locks accounts after repeated failures.")
    else:
        print("I will not try these credentials again until you change them in .env.")


async def main() -> int:
    config = load_config()
    if not config.subaru_device_id:
        print("Set SUBARU_DEVICE_ID in .env first. Any stable integer works, e.g.")
        print(f"  SUBARU_DEVICE_ID=\"{int(__import__('time').time())}\"")
        return 1

    session_factory = db.make_session_factory(config.db_path)
    with session_factory() as session:
        if auth_guard.blocked(session, config.subaru_username, config.subaru_password):
            count = auth_guard.failures(session, config.subaru_username, config.subaru_password)
            print(auth_guard.refusal_message(count))
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
        try:
            await controller.connect()
        except InvalidCredentials as error:
            with session_factory() as session:
                count = auth_guard.record_failure(
                    session, config.subaru_username, config.subaru_password
                )
            _explain_rejection(str(error), config, count)
            return 1
        except SubaruException as error:
            print(f"Subaru refused the connection: {error}")
            return 1

        with session_factory() as session:
            auth_guard.record_success(session, config.subaru_username, config.subaru_password)

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
