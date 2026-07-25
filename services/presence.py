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
"""

import psycopg2
from datetime import datetime, timedelta
from config import DATABASE_URL

ACTIVE_WINDOW_MINUTES = 5
RECENT_WINDOW_MINUTES = 15


def _get_conn():
    conn = psycopg2.connect(DATABASE_URL)
    with conn.cursor() as c:
        c.execute("""
        CREATE TABLE IF NOT EXISTS user_presence (
            professional_name TEXT PRIMARY KEY,
            professional_role TEXT,
            last_seen TEXT
        )
        """)
    conn.commit()
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
        """, (name, role, datetime.now().isoformat()))
    conn.commit()
    conn.close()


def _classify(last_seen_iso):
    if not last_seen_iso:
        return "offline"
    try:
        last_seen = datetime.fromisoformat(last_seen_iso)
    except Exception:
        return "offline"
    delta_minutes = (datetime.now() - last_seen).total_seconds() / 60.0
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

    results = []
    now = datetime.now()
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