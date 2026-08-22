from services.db_time import now_utc, iso_row, get_logger
from services.db_pool import get_conn as _acquire_pooled_conn
from services import request_dedup
from config import REQUEST_DEDUP_TTL_MINUTES

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
# The TIMESTAMPTZ migration runs once per process, at startup, via
# services.db_schema.ensure_schema() (which calls the shared
# services.db_migration.ensure_timestamptz_columns() helper -- see
# that module's docstring). Every value read back from `submitted_at`
# is normalized back to an ISO-8601 string via services.db_time.iso_row()
# before being returned, so this migration stays entirely contained to
# the database layer -- no caller outside services/feedback_store.py
# needs to change.
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
    """
    Acquire a pooled connection (services/db_pool.py). Schema
    creation/migration used to happen here, on every call -- it is now
    centralized in services/db_schema.py:ensure_schema(), called once
    at application startup (see app.py), so this is now just a pool
    checkout.
    """
    return _acquire_pooled_conn()


def save_feedback(draft_ids, rating, comment, submitted_by="", submitted_by_role=""):
    """
    Reliability-hardening pass (September pilot): guarded against a
    double click or a Streamlit rerun submitting the exact same
    feedback twice. "Exact same" here means the same person, for the
    same batch of drafts, with the same rating and comment -- a
    genuinely different rating/comment (the person changed their mind
    and resubmitted) is treated as a NEW, real submission, not a
    duplicate. See services/request_dedup.py for the full design;
    this is deliberately DATABASE-level protection (not a UI lock),
    per the September pilot reliability audit's guidance for this
    operation. Silently does nothing on a detected duplicate -- there
    is no AI cost here to protect, only avoiding a skewed feedback
    count on future dashboards.
    """
    request_id = request_dedup.fingerprint(
        "feedback", submitted_by, ",".join(str(d) for d in draft_ids), rating, comment,
    )
    claim_status = request_dedup.claim(request_id, "feedback", ttl_minutes=REQUEST_DEDUP_TTL_MINUTES)
    if claim_status != "claimed":
        logger.info("save_feedback: duplicate submission ignored (submitted_by=%r)", submitted_by)
        return

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
        request_dedup.complete(request_id)
    except Exception:
        conn.rollback()
        # A genuine retry of the SAME feedback (not a duplicate -- the
        # first attempt never actually succeeded) must not be blocked.
        request_dedup.release(request_id)
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

    Phase 3 (scalability): this used to read every row of the WHOLE
    table -- rating AND the full comment text -- into Python just to
    add numbers up. That got slower and heavier with every feedback
    submission ever made, forever, with no ceiling. It now asks
    PostgreSQL to do the counting/averaging directly (an aggregate
    query), so this function's cost stays flat no matter how much
    feedback has accumulated, and the (potentially long) comment text
    is never pulled across the wire at all -- only whether each comment
    is non-empty. The four returned numbers are computed exactly the
    same way as before (same rounding, same treatment of NULL ratings
    and blank/whitespace-only comments), so every existing caller sees
    identical results, just computed far more cheaply.
    """
    conn = _get_conn()
    try:
        with conn.cursor() as c:
            c.execute("""
                SELECT
                    COUNT(*) AS total_count,
                    AVG(rating) FILTER (WHERE rating IS NOT NULL) AS avg_rating,
                    COUNT(*) FILTER (
                        WHERE comment IS NOT NULL AND TRIM(comment) <> ''
                    ) AS comment_count
                FROM feedback
            """)
            total_count, avg_rating, comment_count = c.fetchone()

            c.execute("""
                SELECT rating, COUNT(*)
                FROM feedback
                WHERE rating BETWEEN 1 AND 5
                GROUP BY rating
            """)
            distribution_rows = c.fetchall()
    finally:
        conn.close()

    distribution = {i: 0 for i in range(1, 6)}
    for rating, count in distribution_rows:
        distribution[rating] = count

    average = float(avg_rating) if avg_rating is not None else None

    return {
        "count": total_count,
        "average": average,
        "distribution": distribution,
        "comment_count": comment_count,
    }