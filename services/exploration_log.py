import psycopg2
from datetime import datetime, timezone
from config import DATABASE_URL

# Reflection Exploration Log
# ============================
#
# Sprint 7: durable record of WHICH reflective themes a professional
# chose to explore (clicked "Explore" and exchanged at least one
# message about), and how many turns that exploration ran to.
#
# Deliberately does NOT store the conversation content itself. Session
# state already holds the live conversation for as long as the practitioner
# is working on it (see rdi/reflection_session.py); once that session
# ends, the conversation text is gone -- only the fact that this theme
# was explored, by whom, on which case, and how deeply, survives here.
#
# This follows the same minimization pattern already used by
# services/audit_log.py (which records that a case was deleted, never
# the case content). It exists specifically to give Sprint 8
# (Professional Growth Dashboard) and Sprint 9 (Team Learning Dashboard)
# real, durable data to read from -- without ever putting case dialogue
# at rest in a place a dashboard could accidentally surface it.
#
# --- Schema-hardening pass (audit Issue 1 / Issue 2) ------------------
#
# Audit Issue 1: `explored_at` used to be stored as plain TEXT
# (datetime.now().isoformat() strings) -- no timezone info, only
# string-based comparisons, no real date arithmetic in SQL. It is now
# a TIMESTAMPTZ column, populated via _now_utc() (timezone-aware UTC)
# instead of the old naive isoformat() string.
#
# Audit Issue 2: no indexes existed beyond the implicit primary key,
# despite get_personal_exploration_history() filtering on explored_by
# and sorting on explored_at, and get_aggregated_theme_counts()
# filtering on explored_at. Both are now indexed (see
# idx_reflection_explorations_explored_by_at and
# idx_reflection_explorations_explored_at below).
#
# The TIMESTAMPTZ migration runs once per process (guarded by the
# module-level _schema_migrated flag) since ALTER COLUMN TYPE is not a
# cheap no-op the way ADD COLUMN IF NOT EXISTS is. Every value read
# back from `explored_at` is normalized back to an ISO-8601 string via
# _iso()/_iso_row() before being returned, so this migration stays
# entirely contained to this module -- no caller outside
# services/exploration_log.py needs to change.

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
    One-time-per-process migration: convert reflection_explorations.explored_at
    from TEXT to TIMESTAMPTZ, if it isn't already. Safe to call more than
    once (checks information_schema first), but deliberately only ever
    invoked once per process via the _schema_migrated guard in
    _get_conn(), since ALTER COLUMN TYPE rewrites the column and is not
    a cheap operation to repeat on every call.
    """
    with conn.cursor() as c:
        c.execute("""
            SELECT data_type FROM information_schema.columns
            WHERE table_name = 'reflection_explorations' AND column_name = 'explored_at'
        """)
        row = c.fetchone()
        current_type = row[0] if row else None

        if current_type != "timestamp with time zone":
            c.execute("""
                ALTER TABLE reflection_explorations
                ALTER COLUMN explored_at TYPE TIMESTAMPTZ
                USING NULLIF(explored_at, '')::timestamptz
            """)
    conn.commit()


def _get_conn():
    global _schema_migrated

    conn = psycopg2.connect(DATABASE_URL)
    with conn.cursor() as c:
        c.execute("""
        CREATE TABLE IF NOT EXISTS reflection_explorations (
            id SERIAL PRIMARY KEY,
            case_ref TEXT,
            trigger TEXT,
            turn_count INTEGER,
            explored_by TEXT,
            explored_by_role TEXT,
            explored_at TEXT
        )
        """)

        # Cheap, safe to run on every call -- same pattern as the
        # existing ADD COLUMN IF NOT EXISTS statements elsewhere in
        # this codebase (see services/draft_storage.py).
        c.execute("""
            CREATE INDEX IF NOT EXISTS idx_reflection_explorations_explored_by_at
            ON reflection_explorations (explored_by, explored_at DESC)
        """)
        c.execute("""
            CREATE INDEX IF NOT EXISTS idx_reflection_explorations_explored_at
            ON reflection_explorations (explored_at)
        """)
    conn.commit()

    # ALTER COLUMN TYPE is NOT cheap to repeat -- only ever run this
    # once per process, guarded by the module-level flag.
    if not _schema_migrated:
        _ensure_timestamp_columns(conn)
        _schema_migrated = True

    return conn


def log_exploration(case_ref, trigger, turn_count, explored_by="", explored_by_role=""):
    """
    Record one theme being explored within one reflection session.

    `trigger` is one of the 8 dimension keys already used everywhere
    else (see rdi.reflection_objects.ReflectiveOpportunity.trigger /
    services.reflection_log.THEME_KEYS), so this can be joined against
    the same theme vocabulary the Learning page already uses.

    `turn_count` is how many messages the professional sent in this
    opportunity's conversation before the session ended -- a simple
    depth signal, not a quality or competence measure. Call sites should
    skip calling this for opportunities with turn_count == 0 (never
    explored), so this table only ever contains genuine explorations.
    """
    conn = _get_conn()
    with conn.cursor() as c:
        c.execute("""
            INSERT INTO reflection_explorations
                (case_ref, trigger, turn_count, explored_by, explored_by_role, explored_at)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (
            case_ref, trigger, turn_count,
            explored_by, explored_by_role,
            _now_utc(),
        ))
    conn.commit()
    conn.close()


def get_personal_exploration_history(professional_name, limit=50):
    """
    All explorations logged by ONE named professional, most recent
    first. Used by the Professional Growth Dashboard (Sprint 8), which
    is scoped to a single practitioner looking at their own history --
    never used to compare across professionals.
    """
    conn = _get_conn()
    with conn.cursor() as c:
        c.execute("""
            SELECT case_ref, trigger, turn_count, explored_at
            FROM reflection_explorations
            WHERE explored_by = %s
            ORDER BY explored_at DESC
            LIMIT %s
        """, (professional_name, limit))
        rows = c.fetchall()
    conn.close()
    return [_iso_row(row, [3]) for row in rows]


def get_aggregated_theme_counts(since_iso=None):
    """
    Theme -> total exploration count, aggregated across ALL
    professionals and cases, with no identifying information attached.
    Used by the Team Learning Dashboard (Sprint 9), which per the
    product requirements must never expose an individual professional,
    an individual case, or any one person's reflection history --
    only this kind of organisation-wide, anonymous tally.

    `since_iso`, if given, restricts to explorations at or after that
    ISO timestamp (e.g. "last 6 months"). Returns a plain dict.
    """
    conn = _get_conn()
    with conn.cursor() as c:
        if since_iso:
            c.execute("""
                SELECT trigger, COUNT(*) FROM reflection_explorations
                WHERE explored_at >= %s
                GROUP BY trigger
            """, (since_iso,))
        else:
            c.execute("""
                SELECT trigger, COUNT(*) FROM reflection_explorations
                GROUP BY trigger
            """)
        rows = c.fetchall()
    conn.close()
    return {trigger: count for trigger, count in rows}