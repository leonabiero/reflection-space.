from services.db_time import now_utc, iso_row, get_logger
from services.db_pool import get_conn as _acquire_pooled_conn

logger = get_logger(__name__)

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
# get_audit_log() expects a string. get_audit_log() converts back to
# the same ISO-8601 string shape it always returned, so nothing outside
# this file needs to change.
# ---------------------------------------------------------------------
#
# Engineering-quality pass (see accompanying handoff notes)
# ---------------------------------------------------------------------
#   Change 1: connection is always closed via try/finally.
#   Change 2: log_action() wraps its single INSERT with an explicit
#     commit/rollback pair.
#   Change 4: get_audit_log() gains optional limit/offset parameters,
#     defaulting to limit=None (return everything, exactly as before)
#     so it stays a drop-in replacement for any existing/future caller
#     that doesn't ask for pagination. There was previously no LIMIT
#     on this query at all -- flagged in the original schema-hardening
#     docstring as "a pagination gap" -- this closes that gap while
#     remaining fully backward compatible.
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


def log_action(action, draft_id, case_ref, doc_type, actor_name="", actor_role="", details=""):
    """
    action: one of "created", "submitted", "deleted", "restored", "purged"
    """
    conn = _get_conn()
    try:
        with conn.cursor() as c:
            c.execute("""
                INSERT INTO audit_log (action, draft_id, case_ref, doc_type, actor_name, actor_role, details, occurred_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                action, draft_id, case_ref, doc_type,
                actor_name, actor_role, details,
                now_utc(),
            ))
        conn.commit()
    except Exception:
        conn.rollback()
        # Deliberately does not include `details` in the log message --
        # it may echo document-adjacent free text (e.g. "edited" is
        # fine, but a future caller could pass something more
        # sensitive) -- only operational identifiers are logged, per
        # Change 7's "no sensitive case content in logs" rule.
        logger.exception(
            "log_action FAILED: action=%r draft_id=%r case_ref=%r doc_type=%r",
            action, draft_id, case_ref, doc_type,
        )
        raise
    finally:
        conn.close()


def get_audit_log(limit=None, offset=0):
    """
    Returns audit records, most recent first.

    Pagination (Change 4): `limit`/`offset` are optional and default to
    `limit=None` (no LIMIT clause -- every row is returned, exactly as
    before this change), so any existing caller that doesn't pass
    `limit` sees no behavior change. Pass an explicit `limit` (and
    optionally `offset`) to page through the audit trail.
    """
    conn = _get_conn()
    try:
        query = """
            SELECT id, action, draft_id, case_ref, doc_type, actor_name, actor_role, details, occurred_at
            FROM audit_log ORDER BY occurred_at DESC
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
    return [iso_row(row, [8]) for row in rows]