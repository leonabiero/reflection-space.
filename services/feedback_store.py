import psycopg2
from datetime import datetime, timezone
from config import DATABASE_URL

# --- Schema-hardening pass (audit Issue 1 / Issue 2) --------------------
#
# Audit Issue 1: `submitted_at` used to be stored as plain TEXT
# (datetime.now().isoformat() strings) -- no timezone info, only
# string-based comparisons, no real date arithmetic in SQL. It is now
# a TIMESTAMPTZ column, populated via _now_utc() (timezone-aware UTC)
# instead of the old naive isoformat() string.
#
# Audit Issue 2: no indexes existed beyond the implicit primary key,
# despite get_all_feedback() sorting on submitted_at. That column is
# now indexed (see idx_feedback_submitted_at below).
#
# The TIMESTAMPTZ migration runs once per process (guarded by the
# module-level _schema_migrated flag) since ALTER COLUMN TYPE is not a
# cheap no-op the way ADD COLUMN IF NOT EXISTS is. Every value read
# back from `submitted_at` is normalized back to an ISO-8601 string via
# _iso()/_iso_row() before being returned, so this migration stays
# entirely contained to this module -- no caller outside
# services/feedback_store.py needs to change.

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
    One-time-per-process migration: convert feedback.submitted_at from
    TEXT to TIMESTAMPTZ, if it isn't already. Safe to call more than
    once (checks information_schema first), but deliberately only ever
    invoked once per process via the _schema_migrated guard in
    _get_conn(), since ALTER COLUMN TYPE rewrites the column and is not
    a cheap operation to repeat on every call.
    """
    with conn.cursor() as c:
        c.execute("""
            SELECT data_type FROM information_schema.columns
            WHERE table_name = 'feedback' AND column_name = 'submitted_at'
        """)
        row = c.fetchone()
        current_type = row[0] if row else None

        if current_type != "timestamp with time zone":
            c.execute("""
                ALTER TABLE feedback
                ALTER COLUMN submitted_at TYPE TIMESTAMPTZ
                USING NULLIF(submitted_at, '')::timestamptz
            """)
    conn.commit()


def _get_conn():
    global _schema_migrated

    conn = psycopg2.connect(DATABASE_URL)
    with conn.cursor() as c:
        c.execute("""
        CREATE TABLE IF NOT EXISTS feedback (
            id SERIAL PRIMARY KEY,
            draft_ids TEXT,
            rating INTEGER,
            comment TEXT,
            submitted_by TEXT,
            submitted_by_role TEXT,
            submitted_at TEXT
        )
        """)

        # Cheap, safe to run on every call -- same pattern as the
        # existing ADD COLUMN IF NOT EXISTS statements elsewhere in
        # this codebase (see services/draft_storage.py).
        c.execute("""
            CREATE INDEX IF NOT EXISTS idx_feedback_submitted_at
            ON feedback (submitted_at DESC)
        """)
    conn.commit()

    # ALTER COLUMN TYPE is NOT cheap to repeat -- only ever run this
    # once per process, guarded by the module-level flag.
    if not _schema_migrated:
        _ensure_timestamp_columns(conn)
        _schema_migrated = True

    return conn


def save_feedback(draft_ids, rating, comment, submitted_by="", submitted_by_role=""):
    conn = _get_conn()
    with conn.cursor() as c:
        c.execute("""
            INSERT INTO feedback (draft_ids, rating, comment, submitted_by, submitted_by_role, submitted_at)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (
            ",".join(str(d) for d in draft_ids),
            rating,
            comment,
            submitted_by,
            submitted_by_role,
            _now_utc(),
        ))
    conn.commit()
    conn.close()


def get_all_feedback():
    conn = _get_conn()
    with conn.cursor() as c:
        c.execute("""
            SELECT id, draft_ids, rating, comment, submitted_by, submitted_by_role, submitted_at
            FROM feedback ORDER BY submitted_at DESC
        """)
        rows = c.fetchall()
    conn.close()
    return [_iso_row(row, [6]) for row in rows]


def get_feedback_summary():
    """
    Sprint 10 (Research Metrics): aggregate usefulness-rating stats with
    no professional or case attribution -- just how useful the
    reflection process is rated, org-wide.

    Returns:
        {
            "count": int,                         # ratings submitted
            "average": float | None,               # None if count == 0
            "distribution": {1: n, 2: n, ..., 5: n},
            "comment_count": int,                  # how many left a comment
        }
    """
    conn = _get_conn()
    with conn.cursor() as c:
        c.execute("SELECT rating, comment FROM feedback")
        rows = c.fetchall()
    conn.close()

    distribution = {i: 0 for i in range(1, 6)}
    comment_count = 0
    ratings = []

    for rating, comment in rows:
        if rating in distribution:
            distribution[rating] += 1
        if rating is not None:
            ratings.append(rating)
        if comment and comment.strip():
            comment_count += 1

    average = (sum(ratings) / len(ratings)) if ratings else None

    return {
        "count": len(rows),
        "average": average,
        "distribution": distribution,
        "comment_count": comment_count,
    }