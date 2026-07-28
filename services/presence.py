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
    - "active"    : last_seen within ACTIVE_WINDOW_MINUTES (default 5)
    - "recent"    : last_seen within RECENT_WINDOW_MINUTES (default 15)
    - "offline"   : older than that, or no last_seen at all

Nobody is ever shown as indefinitely "online" just because they logged
in once -- status is always recomputed from the actual last_seen
timestamp at read time, not from a login/logout flag.

--- Schema hardening (audit Issue 1 / Issue 2) -----------------------------

Issue 1: `last_seen` was stored as plain TEXT
(datetime.now().isoformat() strings) -- no timezone info, string-only
comparisons, no real date arithmetic in SQL. It is now a proper
TIMESTAMPTZ column. touch() now writes a timezone-aware UTC datetime
object (via _now_utc()) instead of a plain isoformat() string.

Issue 2: this table had no index beyond its implicit primary key,
despite get_active_social_workers() filtering on professional_role AND
ordering by last_seen DESC. A composite index on
(professional_role, last_seen DESC) is now created for exactly that
access pattern.

Data-flow note: get_active_social_workers() converts the TIMESTAMPTZ
value back into the same ISO-8601 string shape via _iso() before it is
ever handed to _classify() or returned to callers -- so _classify()
below is unchanged and, as before, only ever receives a plain string,
never a raw datetime object.
"""

import psycopg2
from datetime import datetime, timedelta, timezone
from config import DATABASE_URL

ACTIVE_WINDOW_MINUTES = 5
RECENT_WINDOW_MINUTES = 15

# One-time-per-process guard for the TIMESTAMPTZ migration below -- an
# ALTER COLUMN TYPE is not a cheap no-op like ADD COLUMN IF NOT EXISTS,
# so it must only ever run once per process, not on every _get_conn()
# call.
_schema_migrated = False


def _now_utc():
    """Single source of truth for 'now' as a timezone-aware UTC
    datetime, replacing the old datetime.now().isoformat() pattern."""
    return datetime.now(timezone.utc)


def _iso(value):
    """Normalize a value read back from a TIMESTAMPTZ column into the
    same ISO-8601 string shape this module has always returned to its
    callers -- every downstream caller (pages/, rdi/) does string
    operations on these values (e.g. slicing), so this keeps the
    TIMESTAMPTZ migration self-contained to the database layer."""
    if value is None:
        return None
    if isinstance(value, str):
        return value
    return value.isoformat()


def _iso_row(row, date_indexes):
    """Apply _iso() to specific positions in a fetched row tuple."""
    row = list(row)
    for i in date_indexes:
        row[i] = _iso(row[i])
    return tuple(row)


def _ensure_timestamp_columns(conn):
    """
    One-time-per-process migration: convert `user_presence.last_seen`
    from TEXT to TIMESTAMPTZ, if it isn't already.

    Checks information_schema.columns for the column's current
    data_type first, and only runs the ALTER TABLE if it isn't already
    'timestamp with time zone' -- so this is safe to have called on
    every process start, even against a database that was already
    migrated by an earlier process/deploy.
    """
    with conn.cursor() as c:
        c.execute("""
            SELECT data_type FROM information_schema.columns
            WHERE table_name = 'user_presence' AND column_name = 'last_seen'
        """)
        row = c.fetchone()
        current_type = row[0] if row else None

        if current_type != "timestamp with time zone":
            c.execute("""
                ALTER TABLE user_presence
                ALTER COLUMN last_seen TYPE TIMESTAMPTZ
                USING NULLIF(last_seen, '')::timestamptz
            """)
    conn.commit()


def _get_conn():
    global _schema_migrated

    conn = psycopg2.connect(DATABASE_URL)
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

    # Issue 1: migrate last_seen TEXT -> TIMESTAMPTZ. Guarded by the
    # module-level flag so this only ever runs once per process, not on
    # every _get_conn() call.
    if not _schema_migrated:
        _ensure_timestamp_columns(conn)
        _schema_migrated = True

    return conn


def touch(name, role):
    """Record that `name` (with `role`) is active right now. Called on
    every authenticated page load. Best-effort -- callers
    (services.identity.init_identity) already wrap this in a
    try/except, since a presence hiccup must never block a page from
    loading."""
    if not name:
        return
    conn = _get_conn()
    with conn.cursor() as c:
        c.execute("""
            INSERT INTO user_presence (professional_name, professional_role, last_seen)
            VALUES (%s, %s, %s)
            ON CONFLICT (professional_name)
            DO UPDATE SET professional_role = EXCLUDED.professional_role,
                          last_seen = EXCLUDED.last_seen
        """, (name, role, _now_utc()))
    conn.commit()
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
    with conn.cursor() as c:
        c.execute("""
            SELECT professional_name, last_seen FROM user_presence
            WHERE professional_role = %s
            ORDER BY last_seen DESC
        """, ("Social Worker",))
        rows = c.fetchall()
    conn.close()

    # last_seen is now TIMESTAMPTZ (index 1 in each row) -- normalize
    # back to the same ISO-8601 string shape this module has always
    # handed to callers and to _classify() below, before any further
    # processing.
    rows = [_iso_row(row, [1]) for row in rows]

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