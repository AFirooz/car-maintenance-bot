"""The guard that stops repeated rejected logins locking the Subaru account."""

from __future__ import annotations

import auth_guard

USER = "owner@example.com"
PASSWORD = "correct-horse"


def test_a_fresh_install_is_not_blocked(session):
    assert auth_guard.blocked(session, USER, PASSWORD) is False


def test_blocks_after_three_rejected_logins(session):
    for _ in range(auth_guard.MAX_AUTH_FAILURES - 1):
        auth_guard.record_failure(session, USER, PASSWORD)
    assert auth_guard.blocked(session, USER, PASSWORD) is False

    auth_guard.record_failure(session, USER, PASSWORD)
    assert auth_guard.blocked(session, USER, PASSWORD) is True


def test_a_successful_login_clears_the_count(session):
    for _ in range(auth_guard.MAX_AUTH_FAILURES):
        auth_guard.record_failure(session, USER, PASSWORD)

    auth_guard.record_success(session, USER, PASSWORD)

    assert auth_guard.blocked(session, USER, PASSWORD) is False


def test_changing_the_password_clears_the_block(session):
    for _ in range(auth_guard.MAX_AUTH_FAILURES):
        auth_guard.record_failure(session, USER, PASSWORD)
    assert auth_guard.blocked(session, USER, PASSWORD) is True

    assert auth_guard.blocked(session, USER, "a-different-password") is False


def test_changing_the_username_clears_the_block(session):
    for _ in range(auth_guard.MAX_AUTH_FAILURES):
        auth_guard.record_failure(session, USER, PASSWORD)

    assert auth_guard.blocked(session, "someone-else@example.com", PASSWORD) is False


def test_the_block_survives_the_process_exiting(session_factory):
    with session_factory() as first:
        for _ in range(auth_guard.MAX_AUTH_FAILURES):
            auth_guard.record_failure(first, USER, PASSWORD)

    with session_factory() as second:
        assert auth_guard.blocked(second, USER, PASSWORD) is True


def test_credentials_are_never_stored(session):
    import db

    auth_guard.record_failure(session, USER, PASSWORD)

    stored = db.get_state(session, "subaru_auth_fingerprint", "")
    assert stored
    assert USER not in stored
    assert PASSWORD not in stored
