import psycopg2
from datetime import datetime
from config import DATABASE_URL


def _get_conn():
    conn = psycopg2.connect(DATABASE_URL)
    with conn.cursor() as c:
        c.execute("""
        CREATE TABLE IF NOT EXISTS visits (
            id SERIAL PRIMARY KEY,
            page TEXT,
            language TEXT,
            visited_at TEXT
        )
        """)
    conn.commit()
    return conn


def log_visit(page: str, language: str = ""):
    conn = _get_conn()
    with conn.cursor() as c:
        c.execute(
            "INSERT INTO visits (page, language, visited_at) VALUES (%s, %s, %s)",
            (page, language, datetime.now().isoformat()),
        )
    conn.commit()
    conn.close()


def get_visits():
    conn = _get_conn()
    with conn.cursor() as c:
        c.execute("SELECT page, language, visited_at FROM visits ORDER BY visited_at DESC")
        rows = c.fetchall()
    conn.close()
    return rows


def clear_visits():
    conn = _get_conn()
    with conn.cursor() as c:
        c.execute("DELETE FROM visits")
    conn.commit()
    conn.close()