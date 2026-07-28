"""
Shared PostgreSQL Connection Pool
====================================

Production-hardening pass (see accompanying handoff notes -- "Change 9:
Connection pooling").

Every storage module in services/ (draft_storage.py, feedback_store.py,
presence.py, settings_store.py, audit_log.py, reflection_log.py,
exploration_log.py) previously called `psycopg2.connect(DATABASE_URL)`
directly inside its own `_get_conn()`, once per read or write. That
means every single call to save_draft(), get_drafts(), touch(),
log_action(), etc. opened a brand-new TCP connection and ran a fresh
TLS handshake against Postgres, then tore it down again a few
milliseconds later. Under concurrent users (Streamlit runs each active
session on its own script-run thread within the same process) this
multiplies connection-setup overhead directly with traffic, and risks
exhausting whatever connection limit the Postgres plan allows (Neon's
free/pilot tiers cap total concurrent connections in the low tens).

This module replaces that pattern with a single, shared, thread-safe
connection pool (psycopg2.pool.ThreadedConnectionPool), created once
per process and reused for the life of the process -- exactly the
shape recommended for a Streamlit deployment, where one long-lived
Python process serves many concurrent user sessions on separate
threads (as opposed to one-process-per-request web frameworks, where a
pool is less critical).

Drop-in compatibility
------------------------
Every one of the modules above was written around the pattern:

    conn = _get_conn()
    try:
        ...
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

Rather than rewrite every call site in every module to use
`pool.getconn()` / `pool.putconn()` explicitly, `get_conn()` below
returns a thin proxy (_PooledConnection) whose `.close()` method
returns the underlying connection to the pool instead of physically
closing it. `conn.cursor()`, `conn.commit()`, `conn.rollback()`, and
every other attribute access pass straight through to the real
psycopg2 connection via `__getattr__`. This means each module's own
`_get_conn()` only needed to change from
`psycopg2.connect(DATABASE_URL)` to `db_pool.get_conn()` -- nothing
else in any calling function needed to change.

Stale-connection resilience
-------------------------------
A connection sitting idle in the pool can be silently dropped by the
server side or a network intermediary (for example, Neon's
autosuspend/compute-scale-to-zero behavior, or any idle-connection
timeout on a proxy in between) without the pool knowing. Handing back
a dead connection would surface as a confusing failure on whatever
statement the caller runs first. `get_conn()` runs a cheap liveness
check (`SELECT 1`) before handing a pooled connection back out and
transparently discards + replaces it if that check fails, so callers
never have to know or care that pooling is happening underneath them.
"""

import threading

import psycopg2
from psycopg2 import pool as pg_pool

from config import DATABASE_URL, DB_POOL_MIN_CONN, DB_POOL_MAX_CONN
from services.db_time import get_logger

logger = get_logger(__name__)

_pool = None
_pool_lock = threading.Lock()


def _get_pool():
    """Lazily create the process-wide pool on first use (double-checked
    locking so concurrent Streamlit session threads never race to
    create two pools)."""
    global _pool
    if _pool is None:
        with _pool_lock:
            if _pool is None:
                _pool = pg_pool.ThreadedConnectionPool(
                    DB_POOL_MIN_CONN, DB_POOL_MAX_CONN, DATABASE_URL
                )
                logger.info(
                    "PostgreSQL connection pool created (min=%d, max=%d)",
                    DB_POOL_MIN_CONN, DB_POOL_MAX_CONN,
                )
    return _pool


class _PooledConnection:
    """
    Proxy around a pooled psycopg2 connection. See module docstring
    ("Drop-in compatibility") for why this exists: it lets every
    existing `conn = _get_conn(); ...; conn.close()` call site in
    services/ keep working unmodified, with `.close()` now returning
    the connection to the shared pool instead of closing it.
    """

    __slots__ = ("_conn", "_returned")

    def __init__(self, conn):
        object.__setattr__(self, "_conn", conn)
        object.__setattr__(self, "_returned", False)

    def __getattr__(self, name):
        return getattr(object.__getattribute__(self, "_conn"), name)

    def close(self):
        if object.__getattribute__(self, "_returned"):
            return
        object.__setattr__(self, "_returned", True)
        conn = object.__getattribute__(self, "_conn")
        try:
            _get_pool().putconn(conn)
        except Exception:
            # The pool itself is unusable for this connection (e.g. it
            # was already closed underneath us) -- fall back to a
            # direct close so we at least don't leak the socket.
            logger.exception("Failed to return connection to pool; closing it directly")
            try:
                conn.close()
            except Exception:
                pass


def _is_alive(conn):
    try:
        with conn.cursor() as c:
            c.execute("SELECT 1")
            c.fetchone()
        return True
    except Exception:
        return False


def get_conn():
    """
    Acquire a connection from the shared pool. Used exactly like
    `psycopg2.connect(DATABASE_URL)` was used before: callers run
    `conn.cursor()` / `conn.commit()` / `conn.rollback()` as normal,
    and MUST still call `conn.close()` when finished -- that now
    returns the connection to the pool rather than physically closing
    it, so the try/finally pattern already used throughout services/
    is unchanged.
    """
    pool = _get_pool()
    raw_conn = pool.getconn()

    if raw_conn.closed or not _is_alive(raw_conn):
        try:
            pool.putconn(raw_conn, close=True)
        except Exception:
            try:
                raw_conn.close()
            except Exception:
                pass
        raw_conn = pool.getconn()

    return _PooledConnection(raw_conn)


def closeall():
    """
    Close every connection currently held by the pool. Not used in
    normal request handling -- provided for clean shutdown in tooling
    (e.g. a management script or test suite) that wants to release
    every open connection explicitly.
    """
    global _pool
    with _pool_lock:
        if _pool is not None:
            _pool.closeall()
            _pool = None
            logger.info("PostgreSQL connection pool closed")