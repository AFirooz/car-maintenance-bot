from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Config:
    telegram_token: str
    owner_id: int
    db_path: str
    subaru_username: str
    subaru_password: str
    subaru_pin: str
    subaru_device_id: int
    subaru_device_name: str
    subaru_country: str

    def missing(self) -> list[str]:
        required = {
            "TELEGRAM_BOT_TOKEN": self.telegram_token,
            "ALLOWED_USER_ID": self.owner_id,
            "SUBARU_USERNAME": self.subaru_username,
            "SUBARU_PASSWORD": self.subaru_password,
            "SUBARU_DEVICE_ID": self.subaru_device_id,
        }
        return [name for name, value in required.items() if not value]


def load_config() -> Config:
    return Config(
        telegram_token=os.getenv("TELEGRAM_BOT_TOKEN", ""),
        owner_id=int(os.getenv("ALLOWED_USER_ID", "0") or 0),
        db_path=os.getenv("BOT_DB_PATH", "data/car_bot.db"),
        subaru_username=os.getenv("SUBARU_USERNAME", ""),
        subaru_password=os.getenv("SUBARU_PASSWORD", ""),
        subaru_pin=os.getenv("SUBARU_PIN", ""),
        subaru_device_id=int(os.getenv("SUBARU_DEVICE_ID", "0") or 0),
        subaru_device_name=os.getenv("SUBARU_DEVICE_NAME", "car-maintenance-bot"),
        subaru_country=os.getenv("SUBARU_COUNTRY", "USA"),
    )
