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

Diagnostic instrumentation (observation-only, temporary)
-------------------------------------------------------
Added to help answer one specific open question from load testing:
under 10 concurrent simulated users, even a "warm" pool (all 10
connections already open and healthy from an earlier wave) still shows
roughly 10 seconds of delay on simple actions like logging in -- and
nothing in this file's existing logic fully explains why. This adds
two log lines per connection checkout/return cycle, timing exactly
where the time goes:

  - "DB checkout: ..." -- logged the moment a connection is handed
    out. Reports how long pool.getconn() itself took (wait), how long
    the SELECT 1 liveness check took (health), whether the connection
    was healthy, and whether it had to be discarded and replaced.
  - "DB return: ..." -- logged the moment a connection is handed back
    (conn.close()). Reports how long the caller actually held it
    (hold) before returning it.

Both lines include which line of application code asked for the
connection (best-effort, read from the Python call stack -- see
_caller_operation() below) and which thread it ran on, plus a shared
conn_id so a checkout line and its matching return line can be paired
up by eye in the terminal output.

This is purely observational: every existing behavior (pool size,
when a new connection gets created, the SELECT 1 check itself, when a
connection is considered healthy, how replacement works, how/when
connections are returned) is completely unchanged. The only new thing
happening is timing and logging around behavior that was already
there. Safe to remove once the investigation it supports is done.
"""

import inspect
import threading
import time

import psycopg2
from psycopg2 import pool as pg_pool

from config import DATABASE_URL, DB_POOL_MIN_CONN, DB_POOL_MAX_CONN
from services.db_time import get_logger

logger = get_logger(__name__)

_pool = None
_pool_lock = threading.Lock()

# Function names used, identically, by every services/*.py module's own
# tiny local `_get_conn()` wrapper around this file's get_conn(). Purely
# diagnostic: _caller_operation() below skips past these so the logged
# "operation" is the actual business function (e.g. "save_draft"), not
# this same wrapper name repeated for every single checkout.
_TRIVIAL_WRAPPER_NAMES = {"_get_conn", "get_conn"}


def _caller_operation():
    """
    Best-effort, log-only: walks a few frames up the call stack from
    get_conn() to find the name of the function that actually asked
    for a connection, so diagnostic log lines can say e.g.
    "operation=save_draft" instead of just "operation=_get_conn"
    (every services/ module names its own wrapper _get_conn, so that
    name alone isn't useful).

    This only reads the call stack -- it doesn't change what runs or
    what get_conn() returns. It can never raise: any failure to
    determine a name falls back to "unknown", the same as if this
    function didn't exist.
    """
    try:
        frame = inspect.currentframe().f_back  # get_conn()'s own frame
        for _ in range(5):
            frame = frame.f_back
            if frame is None:
                return "unknown"
            name = frame.f_code.co_name
            if name not in _TRIVIAL_WRAPPER_NAMES:
                return name
        return "unknown"
    except Exception:
        return "unknown"


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

    The extra fields (_operation, _thread_name, _conn_id,
    _checkout_finished_at) are purely for the diagnostic "DB return"
    log line in close() -- see module docstring, "Diagnostic
    instrumentation". They don't change how this class behaves for
    callers.
    """

    __slots__ = ("_conn", "_returned", "_operation", "_thread_name", "_conn_id", "_checkout_finished_at")

    def __init__(self, conn, operation="unknown", thread_name="unknown", conn_id=0):
        object.__setattr__(self, "_conn", conn)
        object.__setattr__(self, "_returned", False)
        object.__setattr__(self, "_operation", operation)
        object.__setattr__(self, "_thread_name", thread_name)
        object.__setattr__(self, "_conn_id", conn_id)
        object.__setattr__(self, "_checkout_finished_at", time.monotonic())

    def __getattr__(self, name):
        return getattr(object.__getattribute__(self, "_conn"), name)

    def close(self):
        if object.__getattribute__(self, "_returned"):
            return
        object.__setattr__(self, "_returned", True)
        conn = object.__getattribute__(self, "_conn")

        try:
            hold_ms = (time.monotonic() - object.__getattribute__(self, "_checkout_finished_at")) * 1000.0
            logger.info(
                "DB return: operation=%s thread=%s conn_id=%s hold=%.1fms",
                object.__getattribute__(self, "_operation"),
                object.__getattribute__(self, "_thread_name"),
                object.__getattribute__(self, "_conn_id"),
                hold_ms,
            )
        except Exception:
            pass  # diagnostic logging must never block returning the connection

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

    (See module docstring, "Diagnostic instrumentation" -- this also
    logs one "DB checkout: ..." line per call, timing where the time
    goes. That logging is purely observational and does not change
    any of the behavior described above.)
    """
    operation = _caller_operation()
    thread_name = threading.current_thread().name

    pool = _get_pool()

    checkout_start = time.monotonic()
    raw_conn = pool.getconn()
    checkout_wait_ms = (time.monotonic() - checkout_start) * 1000.0

    health_ms = 0.0
    replaced = False

    if raw_conn.closed:
        healthy = False
    else:
        health_start = time.monotonic()
        healthy = _is_alive(raw_conn)
        health_ms = (time.monotonic() - health_start) * 1000.0

    if not healthy:
        replaced = True
        try:
            pool.putconn(raw_conn, close=True)
        except Exception:
            try:
                raw_conn.close()
            except Exception:
                pass
        replace_start = time.monotonic()
        raw_conn = pool.getconn()
        checkout_wait_ms += (time.monotonic() - replace_start) * 1000.0

    try:
        logger.info(
            "DB checkout: operation=%s thread=%s conn_id=%s wait=%.1fms health=%.1fms healthy=%s replaced=%s",
            operation, thread_name, id(raw_conn), checkout_wait_ms, health_ms,
            "yes" if healthy else "no", "yes" if replaced else "no",
        )
    except Exception:
        pass  # diagnostic logging must never block handing back a connection

    return _PooledConnection(raw_conn, operation=operation, thread_name=thread_name, conn_id=id(raw_conn))


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