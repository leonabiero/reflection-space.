import psycopg2
from config import DATABASE_URL


def _get_conn():
    conn = psycopg2.connect(DATABASE_URL)
    with conn.cursor() as c:
        c.execute("""
        CREATE TABLE IF NOT EXISTS app_settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
        """)
    conn.commit()
    return conn


def get_setting(key, default=None):
    conn = _get_conn()
    with conn.cursor() as c:
        c.execute("SELECT value FROM app_settings WHERE key=%s", (key,))
        row = c.fetchone()
    conn.close()
    return row[0] if row else default


def set_setting(key, value):
    conn = _get_conn()
    with conn.cursor() as c:
        c.execute("""
            INSERT INTO app_settings (key, value) VALUES (%s, %s)
            ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value
        """, (key, value))
    conn.commit()
    conn.close()