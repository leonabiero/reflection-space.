import psycopg2
from datetime import datetime, timezone
from config import DATABASE_URL

# Central audit trail: WHO did WHAT action, on WHICH case, WHEN.
# Distinct from visit_log.py (which only tracks page visits/navigation)
# — this tracks actual data-changing actions: create, edit, submit,
# delete, restore, purge. Referenced case content is NOT stored here,
# only identifying metadata (case_ref, doc_type) — so that even a
# permanently deleted case still leaves a truthful record that
# something happened, without keeping the sensitive content itself.

# ---------------------------------------------------------------------
# Schema hardening pass (audit findings "Issue 1" and "Issue 2")
# ---------------------------------------------------------------------
# Issue 1: occurred_at was a plain TEXT column holding
# datetime.now().isoformat() strings -- no timezone info, string-only
# comparisons. It is now TIMESTAMPTZ.
#
# Issue 2: this module had no index beyond the implicit primary-key
# index. get_audit_log()'s ORDER BY occurred_at DESC now has one.
#
# Same design choice as services/draft_storage.py (see that file's
# module docstring for the full reasoning): TIMESTAMPTZ columns return
# native datetime objects from psycopg2, but every caller of
# get_audit_log() (currently pages/case_history.py isn't shown reading
# it directly, but any future admin page rendering this list will do
# string slicing like occurred_at[:16], matching the pattern used
# everywhere else in this app) expects a string. get_audit_log()
# converts back to the same ISO-8601 string shape it always returned,
# so nothing outside this file needs to change.
# ---------------------------------------------------------------------

# Process-level guard so the one-time TIMESTAMPTZ column migration only
# runs once per running process, not on every _get_conn() call.
_schema_migrated = False


def _now_utc():
    """Single source of truth for 'now' as a timezone-aware UTC
    datetime, replacing the old datetime.now().isoformat() pattern."""
    return datetime.now(timezone.utc)


def _iso(value):
    """Normalize a value read back from occurred_at (now TIMESTAMPTZ)
    into the same ISO-8601 string shape this module has always
    returned to its callers."""
    if value is None:
        return None
    if isinstance(value, str):
        return value
    return value.isoformat()


def _iso_row(row, date_indexes):
    """Apply _iso() to specific positions in a fetched row tuple,
    leaving every other value untouched."""
    row = list(row)
    for i in date_indexes:
        row[i] = _iso(row[i])
    return tuple(row)


def _ensure_timestamp_columns(conn):
    """
    One-time-per-process migration: convert occurred_at from TEXT to
    TIMESTAMPTZ.

    Idempotent two ways: guarded by the module-level _schema_migrated
    flag (only runs once per process), and also checks
    information_schema before altering, so it's safe across process
    restarts too (a column already converted on a previous deploy is
    left alone, avoiding a needless full-table rewrite on every app
    start).

    NULLIF(occurred_at, '') guards against an empty-string value ever
    being cast -- every existing value here was written by
    datetime.now().isoformat(), so this is a cheap, harmless safety
    net rather than an expected case.
    """
    with conn.cursor() as c:
        c.execute("""
            SELECT column_name, data_type FROM information_schema.columns
            WHERE table_name = 'audit_log' AND column_name = 'occurred_at'
        """)
        row = c.fetchone()
        current_type = row[1] if row else None
        if current_type != "timestamp with time zone":
            c.execute("""
                ALTER TABLE audit_log
                ALTER COLUMN occurred_at TYPE TIMESTAMPTZ
                USING NULLIF(occurred_at, '')::timestamptz
            """)
    conn.commit()


def _get_conn():
    global _schema_migrated
    conn = psycopg2.connect(DATABASE_URL)
    with conn.cursor() as c:
        c.execute("""
        CREATE TABLE IF NOT EXISTS audit_log (
            id SERIAL PRIMARY KEY,
            action TEXT,
            draft_id INTEGER,
            case_ref TEXT,
            doc_type TEXT,
            actor_name TEXT,
            actor_role TEXT,
            details TEXT,
            occurred_at TEXT
        )
        """)
        # get_audit_log()'s ORDER BY occurred_at DESC currently scans
        # and sorts the entire table every time it's called (there is
        # also no LIMIT on that query -- flagged separately as a
        # pagination gap, out of scope for this schema-only pass, but
        # worth fixing alongside this).
        c.execute("CREATE INDEX IF NOT EXISTS idx_audit_log_occurred_at ON audit_log (occurred_at DESC)")
    conn.commit()

    if not _schema_migrated:
        _ensure_timestamp_columns(conn)
        _schema_migrated = True

    return conn


def log_action(action, draft_id, case_ref, doc_type, actor_name="", actor_role="", details=""):
    """
    action: one of "created", "submitted", "deleted", "restored", "purged"
    """
    conn = _get_conn()
    with conn.cursor() as c:
        c.execute("""
            INSERT INTO audit_log (action, draft_id, case_ref, doc_type, actor_name, actor_role, details, occurred_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            action, draft_id, case_ref, doc_type,
            actor_name, actor_role, details,
            _now_utc(),
        ))
    conn.commit()
    conn.close()


def get_audit_log():
    conn = _get_conn()
    with conn.cursor() as c:
        c.execute("""
            SELECT id, action, draft_id, case_ref, doc_type, actor_name, actor_role, details, occurred_at
            FROM audit_log ORDER BY occurred_at DESC
        """)
        rows = c.fetchall()
    conn.close()
    return [_iso_row(row, [8]) for row in rows]