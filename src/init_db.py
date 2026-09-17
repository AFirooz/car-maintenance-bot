"""Create the database file and its tables. Safe to run repeatedly."""

from __future__ import annotations

from pathlib import Path

from loguru import logger

import db
from config import load_config

if __name__ == "__main__":
    config = load_config()
    Path(config.db_path).parent.mkdir(parents=True, exist_ok=True)
    db.make_engine(config.db_path)
    logger.info(f"Database ready at {config.db_path}")
