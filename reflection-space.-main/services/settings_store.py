from services.db_time import get_logger
from services.db_pool import get_conn as _acquire_pooled_conn

logger = get_logger(__name__)

# Engineering-quality pass (see accompanying handoff notes)
# ---------------------------------------------------------------------
# Change 1 (Connection management): both functions below now guarantee
# their connection is closed via try/finally, even if an exception is
# raised partway through -- previously a raised exception between
# _get_conn() and conn.close() would leak the connection.
#
# Change 2 (Transaction safety): set_setting()'s single INSERT ...
# ON CONFLICT statement is already atomic on its own, but is now
# wrapped with an explicit commit/rollback pair (rather than a bare
# conn.commit()) so a failure between execute() and commit() can never
# leave the connection in an ambiguous, uncommitted state that's
# silently closed without rollback.
#
# This module has no TEXT timestamp columns, so Changes 5/6 (shared
# time/migration helpers) do not apply here.
# ---------------------------------------------------------------------


def _get_conn():
    """
    Acquire a pooled connection (services/db_pool.py). Schema
    creation used to happen here, on every call -- it is now
    centralized in services/db_schema.py:ensure_schema(), called once
    at application startup (see app.py), so this is now just a pool
    checkout.
    """
    return _acquire_pooled_conn()


def get_setting(key, default=None):
    conn = _get_conn()
    try:
        with conn.cursor() as c:
            c.execute("SELECT value FROM app_settings WHERE key=%s", (key,))
            row = c.fetchone()
    finally:
        conn.close()
    return row[0] if row else default


def set_setting(key, value):
    conn = _get_conn()
    try:
        with conn.cursor() as c:
            c.execute("""
                INSERT INTO app_settings (key, value) VALUES (%s, %s)
                ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value
            """, (key, value))
        conn.commit()
    except Exception:
        conn.rollback()
        logger.exception("set_setting FAILED for key=%r", key)
        raise
    finally:
        conn.close()