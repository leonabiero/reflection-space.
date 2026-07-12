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
        # Postgres supports "IF NOT EXISTS" directly on ADD COLUMN, so
        # this is safe to run every time without checking first.
        c.execute("ALTER TABLE drafts ADD COLUMN IF NOT EXISTS created_by TEXT")
        c.execute("ALTER TABLE drafts ADD COLUMN IF NOT EXISTS created_by_role TEXT")
    conn.commit()
    return conn


def init_db():
    conn = _get_conn()
    conn.close()


def save_draft(case_ref, doc_type, language, content, created_by="", created_by_role=""):
    conn = _get_conn()
    with conn.cursor() as c:
        c.execute("""
            INSERT INTO drafts (case_ref, doc_type, language, content, created_at, status, created_by, created_by_role)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (case_ref, doc_type, language, content, datetime.now().isoformat(), "draft", created_by, created_by_role))
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


def update_draft(draft_id, content):
    conn = _get_conn()
    with conn.cursor() as c:
        c.execute("UPDATE drafts SET content=%s WHERE id=%s", (content, draft_id))
    conn.commit()
    conn.close()


def mark_completed(draft_id):
    conn = _get_conn()
    with conn.cursor() as c:
        c.execute("UPDATE drafts SET status='completed' WHERE id=%s", (draft_id,))
    conn.commit()
    conn.close()