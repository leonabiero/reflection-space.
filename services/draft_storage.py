from datetime import timedelta
from config import DELETION_WINDOW_HOURS
from services.audit_log import log_action
from services.qdrant_service import upsert_document, delete_document
from services.db_time import now_utc, iso, iso_row, get_logger
from services.db_pool import get_conn as _acquire_pooled_conn
from services.db_schema import ensure_schema

logger = get_logger(__name__)

# ---------------------------------------------------------------------
# Schema hardening pass (audit findings "Issue 1" and "Issue 2")
# ---------------------------------------------------------------------
# Issue 1: created_at/completed_at/deleted_at (drafts), saved_at
# (draft_history), and last_seen (user_activity) were all plain TEXT
# columns holding datetime.now().isoformat() strings -- no timezone
# info, string-only comparisons, no real date arithmetic possible in
# SQL. They are now TIMESTAMPTZ.
#
# Issue 2: this module had zero indexes beyond each table's implicit
# primary-key index. Every filter/sort actually used by the functions
# below (status+created_by, status+case_ref, completed_at ordering,
# the deleted-status lookup, draft_history's draft_id lookup,
# last_seen ordering) now has one.
#
# Design choice worth knowing about: converting to TIMESTAMPTZ means
# psycopg2 returns a native datetime object on read, not a string.
# Every page in this app (case_history.py, learning.py,
# growth_dashboard.py, research_metrics_SERVICE.py, etc.) does string
# operations on these values (e.g. completed_at[:10]). Rather than
# touch every one of those files in this pass, every function below
# converts datetime values back to the exact same ISO-8601 string
# shape they always returned, right before returning -- see
# services.db_time.iso() / iso_row(). The database is now correct and
# indexable internally; nothing outside services/ needs to change
# because of this.
# ---------------------------------------------------------------------
#
# Engineering-quality pass (see accompanying handoff notes)
# ---------------------------------------------------------------------
# This revision applies the following, purely non-behavioral,
# production-hardening changes on top of everything above:
#
#   Change 1 (Connection management): every function that opens a
#   connection now guarantees it is closed via try/finally, even if an
#   exception is raised partway through -- previously a raised
#   exception between _get_conn() and conn.close() would leak the
#   connection.
#
#   Change 2 (Transaction safety): every multi-statement write
#   (save_draft, finalize_draft, delete_pending_draft,
#   soft_delete_draft, restore_draft, purge_expired_deletions) now
#   explicitly rolls back the transaction if any statement inside it
#   raises, so a partial write (e.g. draft_history insert succeeding
#   but the drafts UPDATE failing) can never be left committed.
#
#   Change 3 (Parameterized SQL): unchanged in substance -- every query
#   here already used %s placeholders for every value. Reviewed and
#   confirmed as part of this pass; nothing needed to change.
#
#   Change 4 (Pagination): get_completed_drafts() and
#   get_pending_deletions() gain optional `limit`/`offset` parameters.
#   Both default to `limit=None`, which preserves the EXACT previous
#   behavior (return every matching row) for every existing call site
#   in this codebase (pages/case_history.py, rdi/retrieval_service.py)
#   -- pagination only activates if a caller explicitly opts in by
#   passing `limit`.
#
#   Change 9 (Scalability -- filter in SQL, not Python): September
#   pilot hardening. get_completed_drafts() gains optional `case_ref`
#   and `date_filter` parameters so callers that only need one case's
#   documents (rdi/retrieval_service.py) or one date's documents
#   (pages/case_history.py) push that filter into the WHERE clause
#   instead of fetching every completed document org-wide and
#   discarding rows in Python. A new get_completed_draft_dates() does
#   the same for date-picker options (`SELECT DISTINCT
#   completed_at::date`) instead of loading full document content just
#   to compute a list of dates. Both default to no filter, so existing
#   unfiltered call sites (the admin re-indexing utility, the manager
#   case-history org-wide view) are unaffected. See
#   services/db_schema.py for the composite indexes added to support
#   these queries at pilot scale.
#
#   Change 5 / 6 (Centralized helpers): the local _now_utc/_iso/
#   _iso_row and _schema_migrated/_ensure_timestamp_columns
#   implementations are replaced by the shared
#   services.db_time / services.db_migration modules -- see those
#   modules' docstrings. Behavior is identical.
#
#   Change 7 (Logging): the previous local module-level "best effort"
#   comments are unchanged in intent, but this module now imports the
#   shared logger (services.db_time.get_logger) for use by call sites
#   that need to log a non-fatal issue, and re-raises rather than
#   silently swallowing on write-path failures (see Change 2).
#
#   Change 8 (Constants): DELETION_WINDOW_HOURS now lives in config.py
#   (imported above) instead of being defined locally in this module.
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


def init_db():
    """
    Kept for backward compatibility with any external caller that
    still imports draft_storage.init_db() directly. app.py now calls
    services.db_schema.ensure_schema() instead, which this delegates
    to.
    """
    ensure_schema()


def update_user_activity(user_name, user_role):
    if not user_name:
        return
    conn = _get_conn()
    try:
        with conn.cursor() as c:
            c.execute("""
                INSERT INTO user_activity (user_name, user_role, last_seen)
                VALUES (%s, %s, %s)
                ON CONFLICT (user_name) DO UPDATE
                SET user_role = EXCLUDED.user_role, last_seen = EXCLUDED.last_seen
            """, (user_name, user_role, now_utc()))
        conn.commit()
    except Exception:
        conn.rollback()
        logger.exception("update_user_activity FAILED for user_name=%r", user_name)
        raise
    finally:
        conn.close()


def get_active_users():
    conn = _get_conn()
    try:
        with conn.cursor() as c:
            c.execute("SELECT user_name, user_role, last_seen FROM user_activity ORDER BY last_seen DESC")
            rows = c.fetchall()
    finally:
        conn.close()
    return [iso_row(row, [2]) for row in rows]


def get_case_count(since_iso=None, service=None, doc_type=None):
    """
    Structured query for aggregation/counting.

    Note on since_iso: callers elsewhere in the app (e.g.
    services/research_metrics_SERVICE.py) build this as a naive,
    server-local ISO string via datetime.now() (not UTC-aware). Now
    that completed_at is TIMESTAMPTZ, Postgres will cast that string
    using the session's timezone setting when comparing. This is
    unchanged behavior from before this migration (it was a string
    comparison either way) and is flagged here as a known, pre-existing
    inconsistency to fix separately if exact timezone precision ever
    matters for this comparison -- not something this schema pass
    changes the correctness of.

    Every value below (since_iso, service, doc_type) is passed as a
    %s parameter, never interpolated into the query string -- see
    Change 3 in the module docstring.
    """
    conn = _get_conn()
    try:
        query = "SELECT COUNT(DISTINCT case_ref) FROM drafts WHERE status='completed'"
        params = []
        if since_iso:
            query += " AND completed_at >= %s"
            params.append(since_iso)
        # Note: 'service' is not a separate column yet, but we can search in case_ref
        # if it follows a pattern, or just return total for now.
        # The requirement mentions 'service' and 'age' which aren't explicit columns.
        # We will search case_ref for service names if provided.
        if service:
            query += " AND case_ref ILIKE %s"
            params.append(f"%{service}%")
        if doc_type:
            query += " AND doc_type = %s"
            params.append(doc_type)

        with conn.cursor() as c:
            c.execute(query, tuple(params))
            (count,) = c.fetchone()
    finally:
        conn.close()
    return count


def save_draft(case_ref, doc_type, language, content, created_by="", created_by_role=""):
    conn = _get_conn()
    try:
        with conn.cursor() as c:
            c.execute("""
                INSERT INTO drafts (case_ref, doc_type, language, content, created_at, status, created_by, created_by_role, was_edited)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (case_ref, doc_type, language, content, now_utc(), "draft", created_by, created_by_role, False))
            new_id = c.fetchone()[0]
        conn.commit()
    except Exception:
        conn.rollback()
        logger.exception("save_draft FAILED for case_ref=%r doc_type=%r", case_ref, doc_type)
        raise
    finally:
        conn.close()
    log_action("created", new_id, case_ref, doc_type, created_by, created_by_role)
    # Purely additive: every existing call site that ignored this
    # function's (previously None) return value is unaffected.
    return new_id


# ---------------------------------------------------------------------
# Ownership isolation (pending / unsubmitted drafts)
# ---------------------------------------------------------------------
#
# A "draft" (status='draft') is a professional's own private,
# in-progress work -- it has not yet been submitted/completed, and has
# never gone through the Reflection process. Per product requirements,
# these must be visible and editable ONLY by the professional who
# created them -- not by any other Social Worker, and not automatically
# by a Supervisor, Programme Manager, or System Administrator either.
# (This is deliberately different from completed/submitted documents,
# which Managers can already see via Case History -- that is an
# existing, intentional feature for finished work, not a bypass for
# still-private drafts.)
#
# get_drafts() now REQUIRES an owner_name and filters by it directly in
# SQL, so there is no code path that can return another professional's
# pending drafts by accident. finalize_draft() and
# delete_pending_draft() both re-verify created_by == the acting user's
# name before making any change, even if a caller somehow supplied a
# draft_id belonging to someone else (e.g. a stale/tampered widget
# key) -- this is enforced at the data layer, not just hidden by the
# UI.

def get_drafts(owner_name):
    """
    Returns only PENDING (status='draft') documents belonging to
    `owner_name`. This is the single source of truth for "my pending
    drafts" -- it deliberately does NOT return every practitioner's
    drafts, regardless of the caller's role. `owner_name` is required
    (not optional) so this can never accidentally be called unscoped.
    """
    if not owner_name:
        return []
    conn = _get_conn()
    try:
        with conn.cursor() as c:
            c.execute("""
                SELECT id, case_ref, doc_type, content, created_at, created_by, created_by_role
                FROM drafts WHERE status='draft' AND created_by=%s
                ORDER BY id
            """, (owner_name,))
            rows = c.fetchall()
    finally:
        conn.close()
    return [iso_row(row, [4]) for row in rows]


def get_draft_by_id(draft_id, owner_name=None):
    """
    Fetch one draft row by id. If `owner_name` is given, this returns
    None unless that draft was created by `owner_name` -- a defense-in-
    depth ownership check for any future call site, mirroring the same
    check already enforced inside finalize_draft() and
    delete_pending_draft(). If `owner_name` is omitted, behaves as
    before (used only by trusted, already-scoped internal callers).
    """
    conn = _get_conn()
    try:
        with conn.cursor() as c:
            c.execute("SELECT * FROM drafts WHERE id=%s", (draft_id,))
            row = c.fetchone()
    finally:
        conn.close()
    if row is None:
        return None
    # Column order: id(0), case_ref(1), doc_type(2), language(3),
    # content(4), created_at(5), status(6), created_by(7),
    # created_by_role(8), was_edited(9), completed_at(10), deleted_at(11),
    # status_before_delete(12), deleted_by(13), deleted_by_role(14).
    row = iso_row(row, [5, 10, 11])
    if owner_name is not None:
        created_by = row[7]
        if created_by != owner_name:
            return None
    return row


def finalize_draft(draft_id, edited_content, owner_name):
    """
    Submit/complete a pending draft. Only succeeds if the draft exists,
    is still in 'draft' status, AND was created by `owner_name` -- a
    professional can only submit their OWN pending work, never someone
    else's, regardless of role. Returns True on success, False if the
    draft doesn't exist, isn't pending, or isn't owned by `owner_name`
    (no changes are made in that case).

    Transaction safety (Change 2): the "insert into draft_history" +
    "update drafts" pair (when the content was edited) are two
    statements that must succeed together -- if the UPDATE were to fail
    after the history INSERT already went through, the draft would be
    left showing its NEW content with no matching "current" status
    change, and a phantom history row pointing at content that was
    never actually applied. Both statements now share one transaction
    that is rolled back as a unit on any failure.

    Data-integrity fix (Qdrant indexing failures were silent): this
    function's `return True` used to happen unconditionally after
    calling upsert_document(), without even looking at what it
    returned -- so a document could be marked 'completed' and shown
    normally everywhere in the app while permanently failing to become
    searchable, with zero trace of that anywhere the app itself
    surfaces. That PostgreSQL commit above stays exactly as it was
    (this function still always returns True once the record is safely
    saved -- a practitioner's submission must never be blocked or look
    like it failed just because search indexing had a hiccup). What
    changed is what happens after: the outcome of upsert_document() is
    now recorded on the row itself (`embedding_status`), and a real
    failure (not the expected/deliberate "Qdrant isn't configured"
    skip) is logged loudly via services/error_log.py, the same place
    every other error in this app shows up for a System Administrator
    -- see the "Document Indexing" panel on pages/system_administration.py,
    which reads `embedding_status` to show and retry failures.
    """
    if not owner_name:
        return False

    conn = _get_conn()
    try:
        with conn.cursor() as c:
            c.execute("""
                SELECT content, case_ref, doc_type, created_by, created_by_role, language, status
                FROM drafts WHERE id=%s
            """, (draft_id,))
            row = c.fetchone()
            if not row:
                return False

            current_content, case_ref, doc_type, created_by, created_by_role, language, status = row

            if status != "draft" or created_by != owner_name:
                # Either already submitted/deleted, or owned by someone
                # else -- refuse silently rather than acting on it.
                return False

            now = now_utc()

            if edited_content.strip() != (current_content or "").strip():
                c.execute("""
                    INSERT INTO draft_history (draft_id, content, saved_at)
                    VALUES (%s, %s, %s)
                """, (draft_id, current_content, now))
                c.execute("""
                    UPDATE drafts SET content=%s, status='completed', was_edited=TRUE, completed_at=%s
                    WHERE id=%s
                """, (edited_content, now, draft_id))
                edited_flag = True
            else:
                c.execute("""
                    UPDATE drafts SET status='completed', completed_at=%s
                    WHERE id=%s
                """, (now, draft_id))
                edited_flag = False
        conn.commit()
    except Exception:
        conn.rollback()
        logger.exception("finalize_draft FAILED for draft_id=%r owner_name=%r", draft_id, owner_name)
        raise
    finally:
        conn.close()

    log_action(
        "submitted", draft_id, case_ref, doc_type, created_by, created_by_role,
        details=("edited" if edited_flag else "not edited"),
    )

    # Hybrid RAG: index the now-completed document in Qdrant so future
    # reflections on this case can find it semantically. Best-effort --
    # see services/qdrant_service.py for why this never raises upward.
    # Fetch created_at separately rather than reusing the SELECT above,
    # since that row reflects pre-update state.
    conn2 = _get_conn()
    try:
        with conn2.cursor() as c2:
            c2.execute("SELECT created_at FROM drafts WHERE id=%s", (draft_id,))
            created_row = c2.fetchone()
    finally:
        conn2.close()
    created_at = iso(created_row[0]) if created_row else ""

    indexed_ok, reason = upsert_document(
        draft_id, case_ref, doc_type,
        content=edited_content,
        language=language,
        created_at=created_at,
        completed_at=iso(now),
        created_by_role=created_by_role,
        was_edited=edited_flag,
    )
    record_embedding_outcome(draft_id, case_ref, indexed_ok, reason)
    return True


def record_embedding_outcome(draft_id, case_ref, indexed_ok, reason):
    """
    Persist the result of an upsert_document() call onto the draft row,
    and -- for a genuine failure (as opposed to the expected "Qdrant
    isn't configured" skip) -- log it loudly via services/error_log.py
    so it's impossible to miss on the System Administration page.

    Shared by finalize_draft() (one document, right after completion)
    and pages/system_administration.py's "Retry failed only" and full
    backfill actions (many documents, run on demand by an admin) --
    kept in one place so all three paths always agree on what
    `embedding_status` means and how failures get reported.

    Never raises: this runs after the document is already safely saved
    and must not turn a successful save into a visible error for the
    person who just submitted it.
    """
    status = "indexed" if indexed_ok else ("not_applicable" if reason == "not_configured" else "failed")
    try:
        conn = _get_conn()
        try:
            with conn.cursor() as c:
                c.execute("UPDATE drafts SET embedding_status=%s WHERE id=%s", (status, draft_id))
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
    except Exception:
        logger.exception(
            "Failed to record embedding_status=%r for draft_id=%r (indexing outcome itself was %r)",
            status, draft_id, reason,
        )

    if status == "failed":
        try:
            from services.error_log import log_error
            log_error(
                page="reflection_space (document indexing)",
                error_type="EmbeddingIndexError",
                message=(
                    f"Document {draft_id} (case {case_ref!r}) was saved as 'completed' "
                    f"but failed to index in Qdrant, so it will not appear in Knowledge "
                    f"Assistant or Reflection Context's historical-document lookup until "
                    f"it is retried. Reason: {reason}"
                ),
                traceback_text="",
                traceback_unavailable_reason=(
                    "upsert_document() reports failures as a (success, reason) result "
                    "rather than raising, so there is no exception/traceback here."
                ),
                context={"draft_id": draft_id, "case_ref": case_ref, "reason": reason},
                severity="warning",
            )
        except Exception:
            logger.exception("Failed to log_error() for embedding failure on draft_id=%r", draft_id)


def get_completed_drafts(limit=None, offset=0, case_ref=None, date_filter=None):
    """
    Returns completed (status='completed') documents, most recently
    completed first.

    Scalability pass (production hardening, pre-September pilot):
    `case_ref` and `date_filter` are new, optional keyword-only-in-
    practice filters that push filtering into PostgreSQL instead of
    pulling every completed document (org-wide) into Python and
    filtering there. Both default to `None`, which preserves the EXACT
    previous behavior (every matching row, org-wide) for any call site
    that doesn't pass them.

    - `case_ref`: restrict to one case (`WHERE case_ref = %s`). Use
      this any time the caller only needs one case's documents --
      e.g. rdi/retrieval_service.py's retrieve_historical_context(),
      which used to fetch every completed document org-wide and then
      discard everything not matching the case in Python.
    - `date_filter`: restrict to documents completed on one calendar
      date (`WHERE completed_at::date = %s`, `date_filter` as an
      'YYYY-MM-DD' string). Use this instead of loading every
      completed document and filtering by date client-side --
      pages/case_history.py's per-date view now does this.

    Pagination (`limit`/`offset`) is unchanged and composes with the
    new filters (e.g. one case's documents, paginated).
    """
    conn = _get_conn()
    try:
        query = """
            SELECT id, case_ref, doc_type, content, created_at, created_by, created_by_role, was_edited, completed_at
            FROM drafts WHERE status='completed'
        """
        params = []
        if case_ref:
            query += " AND case_ref = %s"
            params.append(case_ref)
        if date_filter:
            query += " AND completed_at::date = %s"
            params.append(date_filter)

        query += " ORDER BY completed_at DESC"
        if limit is not None:
            query += " LIMIT %s OFFSET %s"
            params.extend([limit, offset])

        with conn.cursor() as c:
            c.execute(query, tuple(params))
            rows = c.fetchall()
    finally:
        conn.close()
    return [iso_row(row, [4, 8]) for row in rows]


def get_drafts_by_ids(draft_ids):
    """
    Returns completed (status='completed') documents matching the
    given list of draft ids, in no particular guaranteed order (callers
    that care about order should re-key by id, as
    rdi/retrieval_service.py's retrieve_global_context() does).

    Added for retrieve_global_context(), which looks up the handful
    (bounded by its own `limit`, a handful of documents) of documents
    Qdrant's cross-case semantic search matched, by id -- there is no
    case_ref to filter by there (matches can span any case, by
    design), so `case_ref` filtering doesn't apply. Fetching only the
    matched ids, instead of every completed document org-wide, is the
    same "filter in SQL, not Python" fix as get_completed_drafts()'s
    new `case_ref`/`date_filter` parameters, applied to an id lookup
    rather than an equality/date filter. Returns [] for an empty/None
    id list without touching the database.
    """
    if not draft_ids:
        return []
    conn = _get_conn()
    try:
        with conn.cursor() as c:
            c.execute("""
                SELECT id, case_ref, doc_type, content, created_at, created_by, created_by_role, was_edited, completed_at
                FROM drafts
                WHERE status='completed' AND id = ANY(%s)
            """, (list(draft_ids),))
            rows = c.fetchall()
    finally:
        conn.close()
    return [iso_row(row, [4, 8]) for row in rows]


def get_failed_embedding_drafts():
    """
    Returns every completed document whose embedding_status is
    'failed' -- i.e. it saved fine but a real attempt to index it in
    Qdrant did not succeed (as opposed to 'not_applicable', which
    means Qdrant wasn't configured at the time and nothing actually
    went wrong). Used by pages/system_administration.py's "Document
    Indexing" panel to show what needs attention and drive the
    "Retry failed only" action. Same row shape as get_completed_drafts()
    so it can reuse the same upsert_document() call pattern.
    """
    conn = _get_conn()
    try:
        with conn.cursor() as c:
            c.execute("""
                SELECT id, case_ref, doc_type, content, created_at, created_by, created_by_role, was_edited, completed_at
                FROM drafts
                WHERE status='completed' AND embedding_status='failed'
                ORDER BY completed_at DESC
            """)
            rows = c.fetchall()
    finally:
        conn.close()
    return [iso_row(row, [4, 8]) for row in rows]


def count_failed_embedding_drafts():
    """
    Cheap count-only version of get_failed_embedding_drafts(), for
    showing a badge/count on the admin page without fetching full
    document content when the panel is collapsed.
    """
    conn = _get_conn()
    try:
        with conn.cursor() as c:
            c.execute("SELECT COUNT(*) FROM drafts WHERE status='completed' AND embedding_status='failed'")
            (count,) = c.fetchone()
    finally:
        conn.close()
    return count


def get_completed_draft_dates():
    """
    Returns the distinct calendar dates (as 'YYYY-MM-DD' strings, most
    recent first) on which at least one document was completed,
    org-wide.

    Added for pages/case_history.py's date filter dropdown, which
    previously called get_completed_drafts() (fetching every completed
    document's full content, org-wide) purely to compute this list of
    dates in Python. This does the same aggregation in PostgreSQL --
    `SELECT DISTINCT completed_at::date` -- without ever pulling
    document content into the app.
    """
    conn = _get_conn()
    try:
        with conn.cursor() as c:
            c.execute("""
                SELECT DISTINCT completed_at::date AS d
                FROM drafts
                WHERE status='completed' AND completed_at IS NOT NULL
                ORDER BY d DESC
            """)
            rows = c.fetchall()
    finally:
        conn.close()
    return [row[0].isoformat() for row in rows]


def get_completed_draft_count(since_iso=None):
    """
    Sprint 10 (Research Metrics): how many documents have been
    completed, org-wide, WITHOUT pulling document content (or any
    other row data) into memory the way get_completed_drafts() does --
    this is a plain COUNT(*), nothing else.

    See get_case_count()'s docstring re: since_iso timezone-naivety --
    same caveat applies here.
    """
    conn = _get_conn()
    try:
        with conn.cursor() as c:
            if since_iso:
                c.execute("SELECT COUNT(*) FROM drafts WHERE status='completed' AND completed_at >= %s", (since_iso,))
            else:
                c.execute("SELECT COUNT(*) FROM drafts WHERE status='completed'")
            (count,) = c.fetchone()
    finally:
        conn.close()
    return count


def get_draft_history(draft_id):
    conn = _get_conn()
    try:
        with conn.cursor() as c:
            c.execute("""
                SELECT content, saved_at FROM draft_history
                WHERE draft_id=%s ORDER BY id
            """, (draft_id,))
            rows = c.fetchall()
    finally:
        conn.close()
    return [iso_row(row, [1]) for row in rows]


def delete_pending_draft(draft_id, deleted_by="", deleted_by_role=""):
    """
    Permanently deletes a still-pending draft (status='draft' -- not yet
    reflected on or submitted), with no restore window. This is distinct
    from soft_delete_draft() below, which is for completed cases and
    goes through the 48-hour GDPR erasure window instead.

    Ownership is enforced HERE, at the data layer -- not just by hiding
    the delete button in the UI. This only succeeds if the draft is
    still 'draft' status AND its created_by matches `deleted_by`
    exactly. A System Administrator (or any other role) can no longer
    delete another professional's still-pending draft through this
    function -- that bypass has been removed. If a genuine admin
    override is ever needed for a pending draft, it should be built as
    its own explicit, audited feature rather than reusing this
    function.

    Returns True if the draft was deleted, False if it didn't exist,
    was no longer pending, or wasn't owned by `deleted_by` (no changes
    are made in that case).

    Transaction safety (Change 2): the draft_history DELETE and the
    drafts DELETE must succeed together, or a foreign-key-orphaned
    history row (or a draft deleted without its history) could result.
    Both now share one transaction, rolled back together on failure.
    """
    if not deleted_by:
        return False

    conn = _get_conn()
    try:
        with conn.cursor() as c:
            c.execute("SELECT status, case_ref, doc_type, created_by FROM drafts WHERE id=%s", (draft_id,))
            row = c.fetchone()
            if not row:
                return False
            status, case_ref, doc_type, created_by = row
            if status != "draft" or created_by != deleted_by:
                return False
            c.execute("DELETE FROM draft_history WHERE draft_id=%s", (draft_id,))
            c.execute("DELETE FROM drafts WHERE id=%s", (draft_id,))
        conn.commit()
    except Exception:
        conn.rollback()
        logger.exception("delete_pending_draft FAILED for draft_id=%r deleted_by=%r", draft_id, deleted_by)
        raise
    finally:
        conn.close()

    log_action(
        "purged", draft_id, case_ref, doc_type, deleted_by, deleted_by_role,
        details="deleted while pending",
    )
    return True


# --- Deletion / restore / purge (GDPR right to erasure) ---
#
# Everything below this line operates on COMPLETED cases only (the
# case has already been submitted and gone through Reflection) and is
# part of the existing, intentional Case History / audit feature for
# supervisory and administrative roles (see pages/case_history.py).
# This is unrelated to the pending-draft ownership isolation above --
# a completed case is no longer anyone's private in-progress draft.

def soft_delete_draft(draft_id, deleted_by="", deleted_by_role=""):
    """
    Hides the case immediately (status becomes 'deleted', so it drops
    out of every normal view), while keeping the content for a short
    window in case this needs to be undone. Content is only truly
    removed by purge_expired_deletions().

    The Qdrant vector deliberately stays in place during this window
    (see services/qdrant_service.py:delete_document docstring) -- the
    case is already invisible everywhere a user could see it, and
    keeping the vector means restore_draft() doesn't need to re-embed
    anything.

    Transaction safety (Change 2): the single UPDATE below is already
    atomic on its own, but is still wrapped with an explicit
    commit/rollback pair (rather than the previous bare conn.commit())
    so a failure between execute() and commit() can never leave the
    connection in an ambiguous, uncommitted state that's silently
    closed without rollback.
    """
    conn = _get_conn()
    try:
        with conn.cursor() as c:
            c.execute("SELECT status, case_ref, doc_type FROM drafts WHERE id=%s", (draft_id,))
            row = c.fetchone()
            if not row:
                return
            previous_status, case_ref, doc_type = row
            now = now_utc()
            c.execute("""
                UPDATE drafts
                SET status='deleted', status_before_delete=%s, deleted_at=%s,
                    deleted_by=%s, deleted_by_role=%s
                WHERE id=%s
            """, (previous_status, now, deleted_by, deleted_by_role, draft_id))
        conn.commit()
    except Exception:
        conn.rollback()
        logger.exception("soft_delete_draft FAILED for draft_id=%r", draft_id)
        raise
    finally:
        conn.close()

    if not row:
        return
    log_action("deleted", draft_id, case_ref, doc_type, deleted_by, deleted_by_role)


def restore_draft(draft_id, restored_by="", restored_by_role=""):
    """Undo a soft delete, within the safety window."""
    conn = _get_conn()
    try:
        with conn.cursor() as c:
            c.execute("SELECT status_before_delete, case_ref, doc_type FROM drafts WHERE id=%s", (draft_id,))
            row = c.fetchone()
            if not row:
                return
            previous_status, case_ref, doc_type = row
            c.execute("""
                UPDATE drafts
                SET status=%s, status_before_delete=NULL, deleted_at=NULL,
                    deleted_by=NULL, deleted_by_role=NULL
                WHERE id=%s
            """, (previous_status or "draft", draft_id))
        conn.commit()
    except Exception:
        conn.rollback()
        logger.exception("restore_draft FAILED for draft_id=%r", draft_id)
        raise
    finally:
        conn.close()

    if not row:
        return
    log_action("restored", draft_id, case_ref, doc_type, restored_by, restored_by_role)


def get_pending_deletions(limit=None, offset=0):
    """
    Cases currently in the soft-deleted window, awaiting purge.

    Pagination (Change 4): `limit`/`offset` are optional, defaulting to
    `limit=None` (no LIMIT clause -- every matching row is returned,
    exactly as before this change), so the existing call site
    (pages/case_history.py) is unaffected. Pass an explicit `limit` to
    page through results.
    """
    conn = _get_conn()
    try:
        query = """
            SELECT id, case_ref, doc_type, deleted_at, deleted_by, deleted_by_role
            FROM drafts WHERE status='deleted'
            ORDER BY deleted_at DESC
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
    return [iso_row(row, [3]) for row in rows]


def purge_expired_deletions():
    """
    Permanently removes any case whose deletion window has passed.
    Call this at the top of any admin-facing page load — there's no
    background scheduler on this hosting setup, so the purge happens
    the next time someone actually uses the app after the window
    closes, rather than at an exact second.

    Also removes the corresponding Qdrant vector for each purged
    document (see services/qdrant_service.py:delete_document), so a
    permanently erased case leaves no retrievable trace in the semantic
    index either -- matching the same GDPR guarantee already made for
    Postgres content.

    DELETION_WINDOW_HOURS now comes from config.py (Change 8) rather
    than being defined as a local module constant.

    Transaction safety (Change 2): the per-draft draft_history DELETE +
    drafts DELETE pair, across potentially many expired drafts, all
    happen inside ONE transaction now -- either every expired case is
    purged from Postgres, or (on failure partway through) none of them
    are, and the whole batch is retried on the next run rather than
    leaving some cases purged and others not.
    """
    cutoff = now_utc() - timedelta(hours=DELETION_WINDOW_HOURS)
    conn = _get_conn()
    expired = []
    try:
        with conn.cursor() as c:
            c.execute("""
                SELECT id, case_ref, doc_type FROM drafts
                WHERE status='deleted' AND deleted_at < %s
            """, (cutoff,))
            expired = c.fetchall()

            # Batch delete instead of N+1 query pattern:
            # - Delete all draft history in one query
            # - Delete all drafts in one query
            if expired:
                expired_ids = [row[0] for row in expired]
                c.execute("DELETE FROM draft_history WHERE draft_id = ANY(%s)", (expired_ids,))
                c.execute("DELETE FROM drafts WHERE id = ANY(%s)", (expired_ids,))
        conn.commit()
    except Exception:
        conn.rollback()
        logger.exception("purge_expired_deletions FAILED (batch of %d expired case(s) rolled back)", len(expired))
        raise
    finally:
        conn.close()

    for draft_id, case_ref, doc_type in expired:
        delete_document(draft_id)
        log_action("purged", draft_id, case_ref, doc_type, "system", "system")
