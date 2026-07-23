import psycopg2
from datetime import datetime, timedelta
from config import DATABASE_URL
from services.audit_log import log_action
from services.qdrant_service import upsert_document, delete_document

DELETION_WINDOW_HOURS = 48


def _get_conn():
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
    conn.commit()
    return conn


def init_db():
    conn = _get_conn()
    conn.close()


def save_draft(case_ref, doc_type, language, content, created_by="", created_by_role=""):
    conn = _get_conn()
    with conn.cursor() as c:
        c.execute("""
            INSERT INTO drafts (case_ref, doc_type, language, content, created_at, status, created_by, created_by_role, was_edited)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (case_ref, doc_type, language, content, datetime.now().isoformat(), "draft", created_by, created_by_role, False))
        new_id = c.fetchone()[0]
    conn.commit()
    conn.close()
    log_action("created", new_id, case_ref, doc_type, created_by, created_by_role)


def get_drafts():
    conn = _get_conn()
    with conn.cursor() as c:
        c.execute("""
            SELECT id, case_ref, doc_type, content, created_at, created_by, created_by_role
            FROM drafts WHERE status='draft'
            ORDER BY id
        """)
        rows = c.fetchall()
    conn.close()
    return rows


def get_draft_by_id(draft_id):
    conn = _get_conn()
    with conn.cursor() as c:
        c.execute("SELECT * FROM drafts WHERE id=%s", (draft_id,))
        row = c.fetchone()
    conn.close()
    return row


def finalize_draft(draft_id, edited_content):
    conn = _get_conn()
    with conn.cursor() as c:
        c.execute("""
            SELECT content, case_ref, doc_type, created_by, created_by_role, language
            FROM drafts WHERE id=%s
        """, (draft_id,))
        row = c.fetchone()
        if row:
            current_content, case_ref, doc_type, created_by, created_by_role, language = row
        else:
            current_content, case_ref, doc_type, created_by, created_by_role, language = ("", "", "", "", "", "")
        now = datetime.now().isoformat()

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
    created_at = created_row[0] if created_row else ""

    upsert_document(
        draft_id, case_ref, doc_type,
        content=edited_content,
        language=language,
        created_at=created_at,
        completed_at=now,
        created_by_role=created_by_role,
        was_edited=edited_flag,
    )


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
    return rows


def get_completed_draft_count(since_iso=None):
    """
    Sprint 10 (Research Metrics): how many documents have been
    completed, org-wide, WITHOUT pulling document content (or any
    other row data) into memory the way get_completed_drafts() does --
    this is a plain COUNT(*), nothing else.
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
    return rows


def delete_pending_draft(draft_id, deleted_by="", deleted_by_role=""):
    """
    Permanently deletes a still-pending draft (status='draft' -- not yet
    reflected on or submitted), with no restore window. This is distinct
    from soft_delete_draft() below, which is for completed cases and
    goes through the 48-hour GDPR erasure window instead.

    Callers are responsible for authorization (this should only be
    reachable by the draft's own creator or an admin) -- this function
    itself does not check who is calling.

    If the row is missing or is no longer in 'draft' status (e.g. it was
    already submitted in another tab), this is a no-op rather than a
    forced delete, so it can't accidentally remove a completed case.

    A pending (never-completed) draft is never indexed in Qdrant in the
    first place -- indexing only happens at finalize_draft() -- so no
    Qdrant cleanup is needed here.
    """
    conn = _get_conn()
    with conn.cursor() as c:
        c.execute("SELECT status, case_ref, doc_type FROM drafts WHERE id=%s", (draft_id,))
        row = c.fetchone()
        if not row:
            conn.close()
            return
        status, case_ref, doc_type = row
        if status != "draft":
            conn.close()
            return
        c.execute("DELETE FROM draft_history WHERE draft_id=%s", (draft_id,))
        c.execute("DELETE FROM drafts WHERE id=%s", (draft_id,))
    conn.commit()
    conn.close()
    log_action(
        "purged", draft_id, case_ref, doc_type, deleted_by, deleted_by_role,
        details="deleted while pending",
    )


# --- Deletion / restore / purge (GDPR right to erasure) ---

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
        now = datetime.now().isoformat()
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
    return rows


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
    cutoff = (datetime.now() - timedelta(hours=DELETION_WINDOW_HOURS)).isoformat()
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