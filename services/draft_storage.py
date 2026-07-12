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
        c.execute("ALTER TABLE drafts ADD COLUMN IF NOT EXISTS was_edited BOOLEAN DEFAULT FALSE")
        # When a reflection was actually completed/submitted — separate
        # from created_at (when the draft was first written), so Case
        # History can filter by "which day was this worked on" correctly.
        c.execute("ALTER TABLE drafts ADD COLUMN IF NOT EXISTS completed_at TEXT")

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
    conn = _get_conn()
    with conn.cursor() as c:
        c.execute("SELECT content FROM drafts WHERE id=%s", (draft_id,))
        row = c.fetchone()
        current_content = row[0] if row else ""
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
        else:
            c.execute("""
                UPDATE drafts SET status='completed', completed_at=%s
                WHERE id=%s
            """, (now, draft_id))
    conn.commit()
    conn.close()


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