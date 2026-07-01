import sqlite3
from datetime import datetime
import os
DB_PATH = "storage/drafts.db"
def init_db():
    os.makedirs("storage", exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
    CREATE TABLE IF NOT EXISTS drafts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        case_ref TEXT,
        doc_type TEXT,
        language TEXT,
        content TEXT,
        created_at TEXT,
        status TEXT
    )
    """)
    conn.commit()
    conn.close()
def save_draft(case_ref, doc_type, language, content):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        INSERT INTO drafts (case_ref, doc_type, language, content, created_at, status)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (case_ref, doc_type, language, content, datetime.now().isoformat(), "draft"))
    conn.commit()
    conn.close()
def get_drafts():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, case_ref, doc_type, content, created_at FROM drafts WHERE status='draft'")
    rows = c.fetchall()
    conn.close()
    return rows
def get_draft_by_id(draft_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT * FROM drafts WHERE id=?", (draft_id,))
    row = c.fetchone()
    conn.close()
    return row
def update_draft(draft_id, content):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE drafts SET content=? WHERE id=?", (content, draft_id))
    conn.commit()
    conn.close()
def mark_completed(draft_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE drafts SET status='completed' WHERE id=?", (draft_id,))
    conn.commit()
    conn.close()