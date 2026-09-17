"""Stops repeated Subaru logins with credentials already known to be rejected.

Subaru locks an account after enough failures, so a wrong password in .env must
not turn into an unbounded retry loop across setup runs and daily launchd runs.
The guard keys on a hash of the credentials, never the credentials themselves,
so editing .env clears it automatically.
"""

from __future__ import annotations

import hashlib

from sqlalchemy.orm import Session

import db

MAX_AUTH_FAILURES = 3

_COUNT_KEY = "subaru_auth_failures"
_FINGERPRINT_KEY = "subaru_auth_fingerprint"


class CredentialsRefused(RuntimeError):
    """Raised instead of attempting a login that has already failed too often."""


def _fingerprint(username: str, password: str) -> str:
    return hashlib.sha256(f"{username}:{password}".encode()).hexdigest()[:16]


def _sync_fingerprint(session: Session, username: str, password: str) -> None:
    """Reset the count whenever the credentials themselves change."""
    current = _fingerprint(username, password)
    if db.get_state(session, _FINGERPRINT_KEY, "") != current:
        db.set_state(session, _FINGERPRINT_KEY, current)
        db.set_state(session, _COUNT_KEY, "0")


def failures(session: Session, username: str, password: str) -> int:
    _sync_fingerprint(session, username, password)
    return int(db.get_state(session, _COUNT_KEY, "0") or 0)


def blocked(session: Session, username: str, password: str) -> bool:
    return failures(session, username, password) >= MAX_AUTH_FAILURES


def record_failure(session: Session, username: str, password: str) -> int:
    _sync_fingerprint(session, username, password)
    count = int(db.get_state(session, _COUNT_KEY, "0") or 0) + 1
    db.set_state(session, _COUNT_KEY, str(count))
    return count


def record_success(session: Session, username: str, password: str) -> None:
    _sync_fingerprint(session, username, password)
    db.set_state(session, _COUNT_KEY, "0")


def refusal_message(count: int) -> str:
    return (
        f"Refusing to try again: {count} logins with these exact credentials have "
        "already been rejected, and Subaru locks accounts after repeated failures.\n"
        "Sign in at https://www.subaru.com/owners.html to check them, then edit "
        "SUBARU_USERNAME or SUBARU_PASSWORD in .env. The counter clears itself as "
        "soon as either value changes."
    )
