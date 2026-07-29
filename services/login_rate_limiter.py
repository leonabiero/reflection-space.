"""
Login Lockout (brute-force guard)
=====================================

Security hardening pass -- "Login rate limiting" change.

BEFORE this change, the login form had no limit at all on failed
attempts: someone (or some automated script) could try password after
password against any username as fast as the app would respond, with
nothing to slow them down.

This module adds a small, DB-backed lockout: after
config.LOGIN_MAX_ATTEMPTS failed logins for the same username within
config.LOGIN_LOCKOUT_WINDOW_MINUTES, that username is temporarily
blocked from attempting another login for
config.LOGIN_LOCKOUT_DURATION_MINUTES. A correct password typed by the
real account holder is completely unaffected until/unless that many
wrong attempts have just happened.

Design, deliberately mirrors services/rate_limiter.py
----------------------------------------------------------
Same shape as the existing Reflection Rate Limiter: one small Postgres
table, one row per FAILED login attempt (successful logins are never
recorded here -- they just clear out that username's recent failures),
timestamped. No in-memory counters, so this works correctly even
though Streamlit may be running multiple independent sessions/threads,
and survives an app restart.

Locking by USERNAME (not by browser/session/IP)
--------------------------------------------------
Streamlit does not give the app a reliable way to identify the
person's real network address, so this locks by the username being
attempted rather than by IP. That's the right target anyway: the goal
is "stop someone from guessing this person's password," not "stop one
particular computer." A side effect worth knowing: several genuine
people mistyping the same shared/well-known username in a short window
will trigger the same lockout a real attacker would. Given this app's
scale (a small, named roster of professionals, not a public signup
system), that trade-off is intentional.

Fails OPEN, consistent with the rest of this codebase
-----------------------------------------------------------
Exactly like services/rate_limiter.py, if the database is unreachable
for any reason, checks here return "not locked out" rather than
blocking every login in the app. A lockout-tracking outage must never
be the reason nobody can sign in -- see services/qdrant_service.py,
services/embedding_service.py, services/rate_limiter.py for the same
graceful-degradation philosophy applied elsewhere in this app.
"""

from datetime import datetime, timedelta

import psycopg2

from config import (
    DATABASE_URL,
    LOGIN_MAX_ATTEMPTS,
    LOGIN_LOCKOUT_WINDOW_MINUTES,
    LOGIN_LOCKOUT_DURATION_MINUTES,
)
from services.db_time import get_logger

logger = get_logger(__name__)

CLEANUP_HOURS = 24


def _get_conn():
    conn = psycopg2.connect(DATABASE_URL)
    with conn.cursor() as c:
        c.execute("""
        CREATE TABLE IF NOT EXISTS login_failure_log (
            id SERIAL PRIMARY KEY,
            username TEXT,
            occurred_at TEXT
        )
        """)
    conn.commit()
    return conn


def is_locked_out(username: str):
    """
    Call this BEFORE checking a submitted password, i.e. as the very
    first thing that happens when the login button is pressed.

    Returns (locked_out, retry_after_seconds):
        locked_out         -- True if this username currently has
                               config.LOGIN_MAX_ATTEMPTS or more failed
                               attempts within the lockout window, and
                               must not be allowed to attempt a login
                               right now.
        retry_after_seconds -- if locked_out is True, how many seconds
                               remain until the lockout clears (based
                               on the most recent failed attempt).
                               0 if not locked out.

    Fails OPEN (returns locked_out=False) if the database is
    unreachable -- see module docstring.
    """
    if not username:
        return False, 0

    try:
        conn = _get_conn()
        try:
            with conn.cursor() as c:
                now = datetime.now()
                window_start = (now - timedelta(minutes=LOGIN_LOCKOUT_WINDOW_MINUTES)).isoformat()

                c.execute(
                    "SELECT occurred_at FROM login_failure_log "
                    "WHERE username = %s AND occurred_at >= %s "
                    "ORDER BY occurred_at DESC",
                    (username, window_start),
                )
                rows = c.fetchall()

            if len(rows) < LOGIN_MAX_ATTEMPTS:
                return False, 0

            most_recent = datetime.fromisoformat(rows[0][0])
            lockout_ends = most_recent + timedelta(minutes=LOGIN_LOCKOUT_DURATION_MINUTES)
            remaining = (lockout_ends - now).total_seconds()

            if remaining <= 0:
                return False, 0
            return True, int(remaining)
        finally:
            conn.close()
    except Exception:
        logger.exception("is_locked_out check failed; failing open")
        return False, 0


def record_failed_attempt(username: str):
    """
    Call this whenever a submitted username/password pair is rejected.
    Also opportunistically deletes stale rows (older than
    CLEANUP_HOURS) so this table never grows without bound.

    Best-effort: swallows its own errors so a logging failure can
    never itself crash the login page (the person just sees the
    normal "incorrect username or password" message either way).
    """
    if not username:
        return

    try:
        conn = _get_conn()
        try:
            with conn.cursor() as c:
                now = datetime.now()
                cleanup_cutoff = (now - timedelta(hours=CLEANUP_HOURS)).isoformat()
                c.execute(
                    "DELETE FROM login_failure_log WHERE occurred_at < %s",
                    (cleanup_cutoff,),
                )
                c.execute(
                    "INSERT INTO login_failure_log (username, occurred_at) VALUES (%s, %s)",
                    (username, now.isoformat()),
                )
            conn.commit()
        finally:
            conn.close()
    except Exception:
        logger.exception("record_failed_attempt failed (non-fatal)")


def clear_failed_attempts(username: str):
    """
    Call this right after a SUCCESSFUL login, so a person who mistyped
    their password a couple of times before getting it right doesn't
    stay partway toward a lockout indefinitely.

    Best-effort, same reasoning as record_failed_attempt() above.
    """
    if not username:
        return

    try:
        conn = _get_conn()
        try:
            with conn.cursor() as c:
                c.execute(
                    "DELETE FROM login_failure_log WHERE username = %s",
                    (username,),
                )
            conn.commit()
        finally:
            conn.close()
    except Exception:
        logger.exception("clear_failed_attempts failed (non-fatal)")