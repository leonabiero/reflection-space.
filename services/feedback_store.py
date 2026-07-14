import psycopg2
from datetime import datetime
from config import DATABASE_URL


def _get_conn():
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
    conn.commit()
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
            datetime.now().isoformat(),
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
    return rows