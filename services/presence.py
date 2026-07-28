"""
Team Presence
===============

Sprint 12. Lets a Supervisor/Programme Manager see, at a glance, which
Social Workers are currently active in the app -- "Team Presence" on
the Learning page.

Design, deliberately kept simple
------------------------------------
There is no background scheduler and no websocket/session-list
infrastructure in this Streamlit Cloud deployment (see
services/rag_logging.py's docstring for the same kind of hosting
constraint). Instead, this reuses the exact same lightweight pattern
already used by services/settings_store.py: a tiny Postgres table with
one row per person, upserted on every touch.

touch(name, role) is called once per page load from
services.identity.init_identity() for EVERY authenticated person (not
only Social Workers) -- so the "last_seen" timestamp simply advances
naturally as people use the app; there is no separate heartbeat
process to run or maintain. The Team Presence panel then filters down
to role == "Social Worker" at read time (see get_active_social_workers
below), since that's the audience product requirements ask for --
Supervisors/Managers/Admins are never listed there themselves.

What is (and is NOT) tracked
---------------------------------
Only: display name, role, last_seen timestamp. No case data, no
document content, no passwords, nothing else -- this table has no way
to hold sensitive information even by mistake, since it only has three
columns.

Status classification (used by the Learning page's Team Presence
panel):
    - "active"    : last_seen within PRESENCE_ACTIVE_WINDOW_MINUTES (default 5)
    - "recent"    : last_seen within PRESENCE_RECENT_WINDOW_MINUTES (default 15)
    - "offline"   : older than that, or no last_seen at all

Nobody is ever shown as indefinitely "online" just because they logged
in once -- status is always recomputed from the actual last_seen
timestamp at read time, not from a login/logout flag.

--- Schema hardening (audit Issue 1 / Issue 2) -----------------------------

Issue 1: `last_seen` was stored as plain TEXT
(datetime.now().isoformat() strings) -- no timezone info, string-only
comparisons, no real date arithmetic in SQL. It is now a proper
TIMESTAMPTZ column. touch() now writes a timezone-aware UTC datetime
object (via now_utc()) instead of a plain isoformat() string.

Issue 2: this table had no index beyond its implicit primary key,
despite get_active_social_workers() filtering on professional_role AND
ordering by last_seen DESC. A composite index on
(professional_role, last_seen DESC) is now created for exactly that
access pattern.

Data-flow note: get_active_social_workers() converts the TIMESTAMPTZ
value back into the same ISO-8601 string shape via iso() before it is
ever handed to _classify() or returned to callers -- so _classify()
below is unchanged and, as before, only ever receives a plain string,
never a raw datetime object.

--- Engineering-quality pass (see accompanying handoff notes) --------------

Change 1: connection always closed via try/finally.
Change 2: touch() wraps its single UPSERT with an explicit
  commit/rollback pair.
Change 5 / 6: local _now_utc/_iso/_iso_row and
  _schema_migrated/_ensure_timestamp_columns are replaced by the
  shared services.db_time / services.db_migration modules.
Change 7: touch() previously had no failure handling of its own at
  all (its caller, services.identity._touch_presence(), wraps it in a
  bare try/except that silently discards any error). touch() itself
  now logs before its exception propagates, so a presence failure is
  at least visible in the operational log even though the page-level
  behavior (never block a page load over a presence hiccup) is
  unchanged.
Change 8: ACTIVE_WINDOW_MINUTES / RECENT_WINDOW_MINUTES are now
  PRESENCE_ACTIVE_WINDOW_MINUTES / PRESENCE_RECENT_WINDOW_MINUTES,
  imported from config.py instead of being defined locally in this
  module -- see config.py for the rationale. Values are unchanged
  (5 / 15 minutes) unless overridden via environment variable.
"""

import psycopg2
from datetime import datetime, timedelta, timezone
from config import DATABASE_URL, PRESENCE_ACTIVE_WINDOW_MINUTES, PRESENCE_RECENT_WINDOW_MINUTES
from services.db_time import now_utc, iso, iso_row, get_logger
from services.db_migration import ensure_timestamptz_columns

logger = get_logger(__name__)

# Kept as local aliases so the rest of this module (and _classify()'s
# reasoning below) reads exactly as it always did -- only the
# definition site moved to config.py (Change 8).
ACTIVE_WINDOW_MINUTES = PRESENCE_ACTIVE_WINDOW_MINUTES
RECENT_WINDOW_MINUTES = PRESENCE_RECENT_WINDOW_MINUTES


def _get_conn():
    conn = psycopg2.connect(DATABASE_URL)
    try:
        with conn.cursor() as c:
            c.execute("""
            CREATE TABLE IF NOT EXISTS user_presence (
                professional_name TEXT PRIMARY KEY,
                professional_role TEXT,
                last_seen TEXT
            )
            """)
            # Issue 2: composite index to support
            # get_active_social_workers()'s
            # `WHERE professional_role = %s ORDER BY last_seen DESC`.
            # Cheap to run every call, same as the ADD COLUMN IF NOT EXISTS
            # pattern already used elsewhere in this codebase.
            c.execute("""
            CREATE INDEX IF NOT EXISTS idx_user_presence_role_last_seen
            ON user_presence (professional_role, last_seen DESC)
            """)
        conn.commit()

        ensure_timestamptz_columns(conn, "user_presence", ["last_seen"])
    except Exception:
        conn.close()
        raise

    return conn


def touch(name, role):
    """Record that `name` (with `role`) is active right now. Called on
    every authenticated page load. Best-effort -- callers
    (services.identity.init_identity) already wrap this in a
    try/except, since a presence hiccup must never block a page from
    loading. This function now logs the failure (Change 7) before
    re-raising, so the hiccup is at least visible operationally
    instead of vanishing silently."""
    if not name:
        return
    conn = _get_conn()
    try:
        with conn.cursor() as c:
            c.execute("""
                INSERT INTO user_presence (professional_name, professional_role, last_seen)
                VALUES (%s, %s, %s)
                ON CONFLICT (professional_name)
                DO UPDATE SET professional_role = EXCLUDED.professional_role,
                              last_seen = EXCLUDED.last_seen
            """, (name, role, now_utc()))
        conn.commit()
    except Exception:
        conn.rollback()
        logger.warning("touch (presence heartbeat) FAILED for name=%r role=%r", name, role, exc_info=True)
        raise
    finally:
        conn.close()


def _classify(last_seen_iso):
    if not last_seen_iso:
        return "offline"
    try:
        last_seen = datetime.fromisoformat(last_seen_iso)
    except Exception:
        return "offline"
    # NOTE (schema hardening / Issue 1 follow-on): last_seen_iso now
    # comes from a TIMESTAMPTZ column, so fromisoformat() returns a
    # timezone-AWARE datetime (it includes a UTC offset). Comparing
    # that against the old datetime.now() (timezone-naive) raises
    # "can't subtract offset-naive and offset-aware datetimes". Using
    # datetime.now(timezone.utc) here keeps both sides aware -- this is
    # the one necessary deviation from "no change needed inside
    # _classify()", required to avoid a runtime crash rather than to
    # change behavior.
    delta_minutes = (datetime.now(timezone.utc) - last_seen).total_seconds() / 60.0
    if delta_minutes <= ACTIVE_WINDOW_MINUTES:
        return "active"
    if delta_minutes <= RECENT_WINDOW_MINUTES:
        return "recent"
    return "offline"


def get_active_social_workers():
    """
    Returns a list of dicts, most-recently-active first:
        {"name": str, "status": "active"|"recent"|"offline",
         "last_seen": str (ISO timestamp), "minutes_ago": float}

    Scoped to role == "Social Worker" only, per the product requirement
    that Team Presence shows practitioners, not other
    Supervisors/Managers/Admins who happen to also be logged in.

    "offline" rows are included (not filtered out) so a caller can
    choose to hide them, or show a fuller picture -- see
    pages/learning.py, which shows only active+recent by default.
    """
    conn = _get_conn()
    try:
        with conn.cursor() as c:
            c.execute("""
                SELECT professional_name, last_seen FROM user_presence
                WHERE professional_role = %s
                ORDER BY last_seen DESC
            """, ("Social Worker",))
            rows = c.fetchall()
    finally:
        conn.close()

    # last_seen is now TIMESTAMPTZ (index 1 in each row) -- normalize
    # back to the same ISO-8601 string shape this module has always
    # handed to callers and to _classify() below, before any further
    # processing.
    rows = [iso_row(row, [1]) for row in rows]

    results = []
    # See the note inside _classify() above: last_seen_iso now parses
    # as a timezone-AWARE datetime (TIMESTAMPTZ column), so `now` here
    # must be timezone-aware too, or this subtraction raises a
    # TypeError.
    now = datetime.now(timezone.utc)
    for name, last_seen_iso in rows:
        status = _classify(last_seen_iso)
        minutes_ago = None
        if last_seen_iso:
            try:
                minutes_ago = (now - datetime.fromisoformat(last_seen_iso)).total_seconds() / 60.0
            except Exception:
                minutes_ago = None
        results.append({
            "name": name,
            "status": status,
            "last_seen": last_seen_iso or "",
            "minutes_ago": minutes_ago,
        })
    return results