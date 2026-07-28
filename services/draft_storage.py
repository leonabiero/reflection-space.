import psycopg2
from datetime import datetime, timedelta, timezone
from config import DATABASE_URL
from services.audit_log import log_action
from services.qdrant_service import upsert_document, delete_document

DELETION_WINDOW_HOURS = 48

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
# shape they always returned, right before returning -- see _iso() /
# _iso_row(). The database is now correct and indexable internally;
# nothing outside services/ needs to change because of this.
# ---------------------------------------------------------------------

# Process-level guard so the one-time TIMESTAMPTZ column migration
# only runs once per running process, not on every _get_conn() call --
# _get_conn() is called on nearly every function in this module, and
# ALTER COLUMN TYPE is not a cheap no-op to repeat, unlike
# "ADD COLUMN IF NOT EXISTS" / "CREATE INDEX IF NOT EXISTS".
_schema_migrated = False


def _now_utc():
    """Single source of truth for 'now' as a timezone-aware UTC
    datetime, replacing the old datetime.now().isoformat() pattern.
    Passing a real datetime object (instead of a pre-formatted string)
    lets psycopg2 store it natively in a TIMESTAMPTZ column, with no
    ambiguity about which timezone it represents."""
    return datetime.now(timezone.utc)


def _iso(value):
    """Normalize a value read back from a TIMESTAMPTZ column into the
    same ISO-8601 string shape this module has always returned to its
    callers. See the module docstring above for why this exists."""
    if value is None:
        return None
    if isinstance(value, str):
        return value
    return value.isoformat()


def _iso_row(row, date_indexes):
    """Apply _iso() to specific positions in a fetched row tuple,
    leaving every other value untouched. Rows from psycopg2 are plain
    tuples (immutable), so this returns a new tuple."""
    row = list(row)
    for i in date_indexes:
        row[i] = _iso(row[i])
    return tuple(row)


def _ensure_timestamp_columns(conn):
    """
    One-time-per-process migration: convert every TEXT-based date
    column in this module's tables to TIMESTAMPTZ.

    Idempotent two ways:
      1. Guarded by the module-level _schema_migrated flag (see
         above), so this only runs once per process.
      2. Also checks information_schema itself before altering any
         column, so it's safe across process restarts too -- a column
         already converted on a previous deploy is left alone,
         avoiding a needless full-table rewrite every time the app
         starts.

    NULLIF(col, '') guards against an empty-string value ever being
    cast (every existing value here was written by
    datetime.now().isoformat() or left NULL, so this is a cheap,
    harmless safety net rather than an expected case).
    """
    targets = {
        "drafts": ["created_at", "completed_at", "deleted_at"],
        "draft_history": ["saved_at"],
        "user_activity": ["last_seen"],
    }

    with conn.cursor() as c:
        for table, columns in targets.items():
            c.execute("""
                SELECT column_name, data_type FROM information_schema.columns
                WHERE table_name = %s AND column_name = ANY(%s)
            """, (table, columns))
            current_types = dict(c.fetchall())

            for col in columns:
                if current_types.get(col) == "timestamp with time zone":
                    continue
                c.execute(f"""
                    ALTER TABLE {table}
                    ALTER COLUMN {col} TYPE TIMESTAMPTZ
                    USING NULLIF({col}, '')::timestamptz
                """)
    conn.commit()


def _get_conn():
    global _schema_migrated
    conn = psycopg2.connect(DATABASE_URL)
    with conn.cursor() as c:
        c.execute("""
        CREATE TABLE IF NOT EXISTS drafts (
            id SERIAL PRIMARY KEY,
            case_ref TEXT,
            doc_type TEXT,
            language TEXT,
            content TEXT,
            created_at TEXT,
            status TEXT,
            created_by TEXT,
            created_by_role TEXT
        )
        """)
        c.execute("ALTER TABLE drafts ADD COLUMN IF NOT EXISTS created_by TEXT")
        c.execute("ALTER TABLE drafts ADD COLUMN IF NOT EXISTS created_by_role TEXT")
        c.execute("ALTER TABLE drafts ADD COLUMN IF NOT EXISTS was_edited BOOLEAN DEFAULT FALSE")
        c.execute("ALTER TABLE drafts ADD COLUMN IF NOT EXISTS completed_at TEXT")
        # GDPR right-to-erasure support: soft-delete first, so an admin
        # has a short window to restore a case in case of a mistake,
        # before it is permanently purged.
        c.execute("ALTER TABLE drafts ADD COLUMN IF NOT EXISTS deleted_at TEXT")
        c.execute("ALTER TABLE drafts ADD COLUMN IF NOT EXISTS status_before_delete TEXT")
        c.execute("ALTER TABLE drafts ADD COLUMN IF NOT EXISTS deleted_by TEXT")
        c.execute("ALTER TABLE drafts ADD COLUMN IF NOT EXISTS deleted_by_role TEXT")

        c.execute("""
        CREATE TABLE IF NOT EXISTS draft_history (
            id SERIAL PRIMARY KEY,
            draft_id INTEGER REFERENCES drafts(id),
            content TEXT,
            saved_at TEXT
        )
        """)
        c.execute("""
        CREATE TABLE IF NOT EXISTS user_activity (
            user_name TEXT PRIMARY KEY,
            user_role TEXT,
            last_seen TEXT
        )
        """)

        # --- Indexes (audit "Issue 2") ------------------------------------
        # Cheap, idempotent metadata checks -- safe to run on every
        # connection, exactly like the ADD COLUMN IF NOT EXISTS calls
        # above. Each one maps directly to a WHERE/ORDER BY already used
        # by a function in this module:
        #   - get_drafts(): WHERE status='draft' AND created_by=%s
        c.execute("CREATE INDEX IF NOT EXISTS idx_drafts_status_created_by ON drafts (status, created_by)")
        #   - historical-context / case-scoped lookups filter completed
        #     drafts by case_ref (rdi/retrieval_service.py reads
        #     get_completed_drafts() then filters in Python today; this
        #     index is what a future case_ref-scoped SQL query would need,
        #     and costs nothing to have now)
        c.execute("CREATE INDEX IF NOT EXISTS idx_drafts_status_case_ref ON drafts (status, case_ref)")
        #   - get_completed_drafts(): ORDER BY completed_at DESC
        c.execute("CREATE INDEX IF NOT EXISTS idx_drafts_completed_at ON drafts (completed_at DESC)")
        #   - get_pending_deletions() / purge_expired_deletions():
        #     WHERE status='deleted'
        c.execute("CREATE INDEX IF NOT EXISTS idx_drafts_deleted_status ON drafts (status) WHERE status = 'deleted'")
        #   - get_draft_history(): WHERE draft_id=%s
        c.execute("CREATE INDEX IF NOT EXISTS idx_draft_history_draft_id ON draft_history (draft_id)")
        #   - get_active_users(): ORDER BY last_seen DESC
        c.execute("CREATE INDEX IF NOT EXISTS idx_user_activity_last_seen ON user_activity (last_seen DESC)")
    conn.commit()

    if not _schema_migrated:
        _ensure_timestamp_columns(conn)
        _schema_migrated = True

    return conn


def init_db():
    conn = _get_conn()
    conn.close()


def update_user_activity(user_name, user_role):
    if not user_name:
        return
    conn = _get_conn()
    with conn.cursor() as c:
        c.execute("""
            INSERT INTO user_activity (user_name, user_role, last_seen)
            VALUES (%s, %s, %s)
            ON CONFLICT (user_name) DO UPDATE
            SET user_role = EXCLUDED.user_role, last_seen = EXCLUDED.last_seen
        """, (user_name, user_role, _now_utc()))
    conn.commit()
    conn.close()


def get_active_users():
    conn = _get_conn()
    with conn.cursor() as c:
        c.execute("SELECT user_name, user_role, last_seen FROM user_activity ORDER BY last_seen DESC")
        rows = c.fetchall()
    conn.close()
    return [_iso_row(row, [2]) for row in rows]


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
    """
    conn = _get_conn()
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
    conn.close()
    return count


def save_draft(case_ref, doc_type, language, content, created_by="", created_by_role=""):
    conn = _get_conn()
    with conn.cursor() as c:
        c.execute("""
            INSERT INTO drafts (case_ref, doc_type, language, content, created_at, status, created_by, created_by_role, was_edited)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (case_ref, doc_type, language, content, _now_utc(), "draft", created_by, created_by_role, False))
        new_id = c.fetchone()[0]
    conn.commit()
    conn.close()
    log_action("created", new_id, case_ref, doc_type, created_by, created_by_role)


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
    with conn.cursor() as c:
        c.execute("""
            SELECT id, case_ref, doc_type, content, created_at, created_by, created_by_role
            FROM drafts WHERE status='draft' AND created_by=%s
            ORDER BY id
        """, (owner_name,))
        rows = c.fetchall()
    conn.close()
    return [_iso_row(row, [4]) for row in rows]


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
    with conn.cursor() as c:
        c.execute("SELECT * FROM drafts WHERE id=%s", (draft_id,))
        row = c.fetchone()
    conn.close()
    if row is None:
        return None
    # Column order: id(0), case_ref(1), doc_type(2), language(3),
    # content(4), created_at(5), status(6), created_by(7),
    # created_by_role(8), was_edited(9), completed_at(10), deleted_at(11),
    # status_before_delete(12), deleted_by(13), deleted_by_role(14).
    row = _iso_row(row, [5, 10, 11])
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
    """
    if not owner_name:
        return False

    conn = _get_conn()
    with conn.cursor() as c:
        c.execute("""
            SELECT content, case_ref, doc_type, created_by, created_by_role, language, status
            FROM drafts WHERE id=%s
        """, (draft_id,))
        row = c.fetchone()
        if not row:
            conn.close()
            return False

        current_content, case_ref, doc_type, created_by, created_by_role, language, status = row

        if status != "draft" or created_by != owner_name:
            # Either already submitted/deleted, or owned by someone
            # else -- refuse silently rather than acting on it.
            conn.close()
            return False

        now = _now_utc()

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
    with conn2.cursor() as c2:
        c2.execute("SELECT created_at FROM drafts WHERE id=%s", (draft_id,))
        created_row = c2.fetchone()
    conn2.close()
    created_at = _iso(created_row[0]) if created_row else ""

    upsert_document(
        draft_id, case_ref, doc_type,
        content=edited_content,
        language=language,
        created_at=created_at,
        completed_at=_iso(now),
        created_by_role=created_by_role,
        was_edited=edited_flag,
    )
    return True


def get_completed_drafts():
    conn = _get_conn()
    with conn.cursor() as c:
        c.execute("""
            SELECT id, case_ref, doc_type, content, created_at, created_by, created_by_role, was_edited, completed_at
            FROM drafts WHERE status='completed'
            ORDER BY completed_at DESC
        """)
        rows = c.fetchall()
    conn.close()
    return [_iso_row(row, [4, 8]) for row in rows]


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
    with conn.cursor() as c:
        if since_iso:
            c.execute("SELECT COUNT(*) FROM drafts WHERE status='completed' AND completed_at >= %s", (since_iso,))
        else:
            c.execute("SELECT COUNT(*) FROM drafts WHERE status='completed'")
        (count,) = c.fetchone()
    conn.close()
    return count


def get_draft_history(draft_id):
    conn = _get_conn()
    with conn.cursor() as c:
        c.execute("""
            SELECT content, saved_at FROM draft_history
            WHERE draft_id=%s ORDER BY id
        """, (draft_id,))
        rows = c.fetchall()
    conn.close()
    return [_iso_row(row, [1]) for row in rows]


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
    """
    if not deleted_by:
        return False

    conn = _get_conn()
    with conn.cursor() as c:
        c.execute("SELECT status, case_ref, doc_type, created_by FROM drafts WHERE id=%s", (draft_id,))
        row = c.fetchone()
        if not row:
            conn.close()
            return False
        status, case_ref, doc_type, created_by = row
        if status != "draft" or created_by != deleted_by:
            conn.close()
            return False
        c.execute("DELETE FROM draft_history WHERE draft_id=%s", (draft_id,))
        c.execute("DELETE FROM drafts WHERE id=%s", (draft_id,))
    conn.commit()
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
    """
    conn = _get_conn()
    with conn.cursor() as c:
        c.execute("SELECT status, case_ref, doc_type FROM drafts WHERE id=%s", (draft_id,))
        row = c.fetchone()
        if not row:
            conn.close()
            return
        previous_status, case_ref, doc_type = row
        now = _now_utc()
        c.execute("""
            UPDATE drafts
            SET status='deleted', status_before_delete=%s, deleted_at=%s,
                deleted_by=%s, deleted_by_role=%s
            WHERE id=%s
        """, (previous_status, now, deleted_by, deleted_by_role, draft_id))
    conn.commit()
    conn.close()
    log_action("deleted", draft_id, case_ref, doc_type, deleted_by, deleted_by_role)


def restore_draft(draft_id, restored_by="", restored_by_role=""):
    """Undo a soft delete, within the safety window."""
    conn = _get_conn()
    with conn.cursor() as c:
        c.execute("SELECT status_before_delete, case_ref, doc_type FROM drafts WHERE id=%s", (draft_id,))
        row = c.fetchone()
        if not row:
            conn.close()
            return
        previous_status, case_ref, doc_type = row
        c.execute("""
            UPDATE drafts
            SET status=%s, status_before_delete=NULL, deleted_at=NULL,
                deleted_by=NULL, deleted_by_role=NULL
            WHERE id=%s
        """, (previous_status or "draft", draft_id))
    conn.commit()
    conn.close()
    log_action("restored", draft_id, case_ref, doc_type, restored_by, restored_by_role)


def get_pending_deletions():
    """Cases currently in the soft-deleted window, awaiting purge."""
    conn = _get_conn()
    with conn.cursor() as c:
        c.execute("""
            SELECT id, case_ref, doc_type, deleted_at, deleted_by, deleted_by_role
            FROM drafts WHERE status='deleted'
            ORDER BY deleted_at DESC
        """)
        rows = c.fetchall()
    conn.close()
    return [_iso_row(row, [3]) for row in rows]


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
    """
    cutoff = _now_utc() - timedelta(hours=DELETION_WINDOW_HOURS)
    conn = _get_conn()
    with conn.cursor() as c:
        c.execute("""
            SELECT id, case_ref, doc_type FROM drafts
            WHERE status='deleted' AND deleted_at < %s
        """, (cutoff,))
        expired = c.fetchall()

        for draft_id, case_ref, doc_type in expired:
            c.execute("DELETE FROM draft_history WHERE draft_id=%s", (draft_id,))
            c.execute("DELETE FROM drafts WHERE id=%s", (draft_id,))
    conn.commit()
    conn.close()

    for draft_id, case_ref, doc_type in expired:
        delete_document(draft_id)
        log_action("purged", draft_id, case_ref, doc_type, "system", "system")