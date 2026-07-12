import psycopg2
from datetime import datetime
from config import DATABASE_URL


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
        # FR-028: track whether a note was changed at the point of
        # completing a reflection, without storing a duplicate copy
        # unless something actually changed.
        c.execute("ALTER TABLE drafts ADD COLUMN IF NOT EXISTS was_edited BOOLEAN DEFAULT FALSE")

        # History table: only ever receives a row when a draft's
        # content is actually changed during the submit step. Stores
        # the version that existed BEFORE the edit, so nothing is lost.
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
        """, (case_ref, doc_type, language, content, datetime.now().isoformat(), "draft", created_by, created_by_role, False))
    conn.commit()
    conn.close()


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
    """
    Called once per draft when a reflection is submitted. Compares the
    new text against what's currently stored:
      - If unchanged: just marks the draft completed, was_edited stays False.
      - If changed: archives the OLD content into draft_history first,
        then updates the draft with the new content and sets was_edited=True.
    This replaces the old update_draft()/mark_completed() pair with a
    single, safer operation that can't accidentally destroy the
    original without a record of it.
    """
    conn = _get_conn()
    with conn.cursor() as c:
        c.execute("SELECT content FROM drafts WHERE id=%s", (draft_id,))
        row = c.fetchone()
        current_content = row[0] if row else ""

        if edited_content.strip() != (current_content or "").strip():
            c.execute("""
                INSERT INTO draft_history (draft_id, content, saved_at)
                VALUES (%s, %s, %s)
            """, (draft_id, current_content, datetime.now().isoformat()))
            c.execute("""
                UPDATE drafts SET content=%s, status='completed', was_edited=TRUE
                WHERE id=%s
            """, (edited_content, draft_id))
        else:
            c.execute("""
                UPDATE drafts SET status='completed'
                WHERE id=%s
            """, (draft_id,))
    conn.commit()
    conn.close()


def get_completed_drafts():
    conn = _get_conn()
    with conn.cursor() as c:
        c.execute("""
            SELECT id, case_ref, doc_type, content, created_at, created_by, created_by_role, was_edited
            FROM drafts WHERE status='completed'
            ORDER BY id DESC
        """)
        rows = c.fetchall()
    conn.close()
    return rows


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