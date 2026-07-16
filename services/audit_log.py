import psycopg2
from datetime import datetime
from config import DATABASE_URL

# Central audit trail: WHO did WHAT action, on WHICH case, WHEN.
# Distinct from visit_log.py (which only tracks page visits/navigation)
# — this tracks actual data-changing actions: create, edit, submit,
# delete, restore, purge. Referenced case content is NOT stored here,
# only identifying metadata (case_ref, doc_type) — so that even a
# permanently deleted case still leaves a truthful record that
# something happened, without keeping the sensitive content itself.


def _get_conn():
    conn = psycopg2.connect(DATABASE_URL)
    with conn.cursor() as c:
        c.execute("""
        CREATE TABLE IF NOT EXISTS audit_log (
            id SERIAL PRIMARY KEY,
            action TEXT,
            draft_id INTEGER,
            case_ref TEXT,
            doc_type TEXT,
            actor_name TEXT,
            actor_role TEXT,
            details TEXT,
            occurred_at TEXT
        )
        """)
    conn.commit()
    return conn


def log_action(action, draft_id, case_ref, doc_type, actor_name="", actor_role="", details=""):
    """
    action: one of "created", "submitted", "deleted", "restored", "purged"
    """
    conn = _get_conn()
    with conn.cursor() as c:
        c.execute("""
            INSERT INTO audit_log (action, draft_id, case_ref, doc_type, actor_name, actor_role, details, occurred_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            action, draft_id, case_ref, doc_type,
            actor_name, actor_role, details,
            datetime.now().isoformat(),
        ))
    conn.commit()
    conn.close()


def get_audit_log():
    conn = _get_conn()
    with conn.cursor() as c:
        c.execute("""
            SELECT id, action, draft_id, case_ref, doc_type, actor_name, actor_role, details, occurred_at
            FROM audit_log ORDER BY occurred_at DESC
        """)
        rows = c.fetchall()
    conn.close()
    return rows