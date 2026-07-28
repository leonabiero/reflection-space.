import psycopg2
from config import DATABASE_URL
from services.db_time import now_utc, iso_row, get_logger
from services.db_migration import ensure_timestamptz_columns

logger = get_logger(__name__)

# --- Schema-hardening pass (audit Issue 1 / Issue 2) --------------------
#
# Audit Issue 1: `submitted_at` used to be stored as plain TEXT
# (datetime.now().isoformat() strings) -- no timezone info, only
# string-based comparisons, no real date arithmetic in SQL. It is now
# a TIMESTAMPTZ column, populated via now_utc() (timezone-aware UTC)
# instead of the old naive isoformat() string.
#
# Audit Issue 2: no indexes existed beyond the implicit primary key,
# despite get_all_feedback() sorting on submitted_at. That column is
# now indexed (see idx_feedback_submitted_at below).
#
# The TIMESTAMPTZ migration runs once per process, via the shared
# services.db_migration.ensure_timestamptz_columns() helper. Every
# value read back from `submitted_at` is normalized back to an
# ISO-8601 string via services.db_time.iso_row() before being
# returned, so this migration stays entirely contained to the database
# layer -- no caller outside services/feedback_store.py needs to
# change.
#
# Engineering-quality pass (see accompanying handoff notes)
# ---------------------------------------------------------------------
#   Change 1: connection always closed via try/finally.
#   Change 2: save_feedback() wraps its single INSERT with an explicit
#     commit/rollback pair.
#   Change 4: get_all_feedback() gains optional limit/offset
#     parameters, defaulting to limit=None (return everything, exactly
#     as before) so pages/case_history.py's existing
#     `get_all_feedback()` call is unaffected.
#   Change 5 / 6: local _now_utc/_iso/_iso_row and
#     _schema_migrated/_ensure_timestamp_columns are replaced by the
#     shared services.db_time / services.db_migration modules.
# ---------------------------------------------------------------------


def _get_conn():
    conn = psycopg2.connect(DATABASE_URL)
    try:
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

        ensure_timestamptz_columns(conn, "feedback", ["submitted_at"])
    except Exception:
        conn.close()
        raise

    return conn


def save_feedback(draft_ids, rating, comment, submitted_by="", submitted_by_role=""):
    conn = _get_conn()
    try:
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
                now_utc(),
            ))
        conn.commit()
    except Exception:
        conn.rollback()
        # Operational identifiers only -- never logs `comment`, which
        # is free-text a practitioner wrote and could contain
        # case-adjacent content (Change 7's "no sensitive case content
        # in logs" rule).
        logger.exception(
            "save_feedback FAILED: draft_ids=%r rating=%r submitted_by=%r",
            draft_ids, rating, submitted_by,
        )
        raise
    finally:
        conn.close()


def get_all_feedback(limit=None, offset=0):
    """
    Returns feedback records, most recently submitted first.

    Pagination (Change 4): `limit`/`offset` are optional and default to
    `limit=None` (no LIMIT clause -- every row is returned, exactly as
    before this change), so pages/case_history.py's existing call is
    unaffected. Pass an explicit `limit` to page through feedback.
    """
    conn = _get_conn()
    try:
        query = """
            SELECT id, draft_ids, rating, comment, submitted_by, submitted_by_role, submitted_at
            FROM feedback ORDER BY submitted_at DESC
        """
        params = []
        if limit is not None:
            query += " LIMIT %s OFFSET %s"
            params.extend([limit, offset])

        with conn.cursor() as c:
            c.execute(query, tuple(params))
            rows = c.fetchall()
    finally:
        conn.close()
    return [iso_row(row, [6]) for row in rows]


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

    This intentionally reads the WHOLE table (no pagination) -- it
    needs every row to compute an accurate average/distribution, so a
    `limit` parameter would silently make this function's numbers
    wrong. Not paginated on purpose.
    """
    conn = _get_conn()
    try:
        with conn.cursor() as c:
            c.execute("SELECT rating, comment FROM feedback")
            rows = c.fetchall()
    finally:
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