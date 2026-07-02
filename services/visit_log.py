import sqlite3
from datetime import datetime
import os

DB_PATH = "storage/drafts.db"


def _get_conn():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
    CREATE TABLE IF NOT EXISTS visits (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        page TEXT,
        language TEXT,
        visited_at TEXT
    )
    """)
    return conn


def log_visit(page: str, language: str = ""):
    conn = _get_conn()
    conn.execute(
        "INSERT INTO visits (page, language, visited_at) VALUES (?, ?, ?)",
        (page, language, datetime.now().isoformat()),
    )
    conn.commit()
    conn.close()


def get_visits():
    conn = _get_conn()
    c = conn.cursor()
    c.execute("SELECT page, language, visited_at FROM visits ORDER BY visited_at DESC")
    rows = c.fetchall()
    conn.close()
    return rows


def clear_visits():
    conn = _get_conn()
    conn.execute("DELETE FROM visits")
    conn.commit()
    conn.close()