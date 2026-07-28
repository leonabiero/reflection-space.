import psycopg2
from datetime import datetime, timedelta
from config import DATABASE_URL

# Reflection Rate Limiter
# ==========================
#
# Cost-safety guard, added after a project risk review. This does NOT
# protect against server overload (Streamlit/Postgres handle this
# pilot's volume easily) -- it protects against RUNAWAY CLAUDE API
# COST: each reflection triggers 8 parallel Claude calls (see
# rdi/orchestrator.py) plus automatic retries. Without a cap, a UI bug,
# a double-click, or an unusually heavy user could trigger far more of
# these than intended, with no automatic brake.
#
# Design, deliberately simple
# -------------------------------
# One small Postgres table, one row per reflection actually generated
# (not per attempt/click), timestamped. Checking the limit is just
# "how many rows for this user in the last N minutes" -- no separate
# scheduler, no in-memory counters that would reset on every server
# restart or be inconsistent across multiple app instances.
#
# This is intentionally a GENEROUS limit, meant to catch bugs and
# runaway loops -- not to restrict normal practitioner use. Real usage
# (per the app's own docstrings elsewhere) is roughly 70-100
# reflections/month ACROSS THE WHOLE ORGANISATION, i.e. a small
# fraction of one per person per day. DEFAULT_MAX_PER_HOUR is set well
# above any realistic legitimate use.
#
# This module only tracks WHEN a reflection was generated and BY WHOM
# (their display name) -- no case data, no document content, nothing
# sensitive. Rows older than 24 hours are cleaned up automatically
# whenever the limit is checked, so this table never grows large.

DEFAULT_MAX_PER_HOUR = 20
WINDOW_MINUTES = 60
CLEANUP_HOURS = 24


def _get_conn():
    conn = psycopg2.connect(DATABASE_URL)
    with conn.cursor() as c:
        c.execute("""
        CREATE TABLE IF NOT EXISTS reflection_rate_log (
            id SERIAL PRIMARY KEY,
            user_name TEXT,
            occurred_at TEXT
        )
        """)
    conn.commit()
    return conn


def check_and_record(user_name, max_per_hour=DEFAULT_MAX_PER_HOUR):
    """
    Call this ONCE, right before generating a reflection (i.e. right
    before rdi.orchestrator.run_reflection() is called).

    Returns (allowed, current_count):
        allowed       -- True if this reflection is permitted to
                          proceed, False if the user has already hit
                          the hourly limit.
        current_count -- how many reflections this user has generated
                          in the current rolling 60-minute window,
                          INCLUDING this one if allowed is True (so the
                          caller can show "18 of 20" type messaging if
                          it ever wants to).

    If allowed is True, this function ALSO records the new reflection
    immediately (so the count is accurate for the very next call) --
    callers should only call this right before actually generating,
    never speculatively.

    Fails OPEN (returns allowed=True) if the database is unreachable
    for any reason -- a rate-limiter outage must never be the reason a
    practitioner can't do their work. This mirrors the same
    graceful-degradation philosophy already used throughout this
    codebase (see services/qdrant_service.py, services/embedding_service.py).
    """
    if not user_name:
        # No identified user to attribute this to -- don't block, but
        # don't track it either.
        return True, 0

    try:
        conn = _get_conn()
        with conn.cursor() as c:
            now = datetime.now()
            window_start = (now - timedelta(minutes=WINDOW_MINUTES)).isoformat()
            cleanup_cutoff = (now - timedelta(hours=CLEANUP_HOURS)).isoformat()

            # Best-effort housekeeping: remove old rows so this table
            # never grows without bound. Safe to run on every check --
            # cheap at this volume (a handful of rows per hour, org-wide).
            c.execute("DELETE FROM reflection_rate_log WHERE occurred_at < %s", (cleanup_cutoff,))

            c.execute(
                "SELECT COUNT(*) FROM reflection_rate_log WHERE user_name = %s AND occurred_at >= %s",
                (user_name, window_start),
            )
            (count,) = c.fetchone()

            if count >= max_per_hour:
                conn.commit()
                conn.close()
                return False, count

            c.execute(
                "INSERT INTO reflection_rate_log (user_name, occurred_at) VALUES (%s, %s)",
                (user_name, now.isoformat()),
            )
        conn.commit()
        conn.close()
        return True, count + 1
    except Exception:
        # Fail open -- see docstring above.
        return True, 0