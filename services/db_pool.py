"""Shared PostgreSQL connection pool.

The application uses one process-wide psycopg2 ThreadedConnectionPool.
Connections are reused, health-checked periodically, and returned by the
existing ``conn.close()`` call sites.

Important concurrency behavior:
    psycopg2's ThreadedConnectionPool raises PoolError immediately when all
    connections are checked out. This module adds a small, bounded wait queue
    around checkout so short bursts above the pool size wait for a connection
    instead of failing immediately. The queue timeout is configurable with
    DB_POOL_WAIT_TIMEOUT_SECONDS and defaults to 5 seconds.
"""

import concurrent.futures
import inspect
import os
import threading
import time

import psycopg2
from psycopg2 import pool as pg_pool

from config import (
    DATABASE_URL,
    DB_POOL_MIN_CONN,
    DB_POOL_MAX_CONN,
    DB_POOL_HEALTH_RECHECK_SECONDS,
    DB_POOL_MAX_REPLACE_ATTEMPTS,
)
from services.db_time import get_logger

logger = get_logger(__name__)

# A short, bounded queue is safer than retrying in a tight loop and is enough
# for the observed ~0.4-0.5s connection hold times. Override with an
# environment variable if deployment testing shows a different requirement.
DB_POOL_WAIT_TIMEOUT_SECONDS = float(
    os.getenv("DB_POOL_WAIT_TIMEOUT_SECONDS", "5")
)

_pool = None
_pool_lock = threading.Lock()
_pool_available = threading.Condition(threading.Lock())

# Physical connection id -> monotonic time of its last successful health check.
_last_verified_at = {}
_last_verified_lock = threading.Lock()

_TRIVIAL_WRAPPER_NAMES = {"_get_conn", "get_conn"}


def _caller_operation():
    """Return the business function that requested a connection, for logging."""
    try:
        frame = inspect.currentframe().f_back
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


def _prewarm_pool_in_parallel(pool, count):
    """Open the configured warm connections concurrently."""
    if count <= 0:
        return 0

    started = time.monotonic()
    opened = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=count) as executor:
        futures = [
            executor.submit(psycopg2.connect, DATABASE_URL)
            for _ in range(count)
        ]
        for future in futures:
            try:
                opened.append(future.result())
            except Exception:
                logger.exception(
                    "Pre-warm: one parallel connection attempt failed"
                )

    if not opened:
        return 0

    try:
        with pool._lock:
            pool._pool.extend(opened)
    except AttributeError:
        logger.warning(
            "Pre-warm: psycopg2 pool internals changed; falling back to normal growth"
        )
        for conn in opened:
            try:
                conn.close()
            except Exception:
                pass
        return 0

    logger.info(
        "Pre-warm: opened %d connection(s) in %.1fs",
        len(opened),
        time.monotonic() - started,
    )
    return len(opened)


def _get_pool():
    """Lazily create and fully pre-warm the process-wide pool."""
    global _pool
    if _pool is None:
        with _pool_lock:
            if _pool is None:
                new_pool = pg_pool.ThreadedConnectionPool(
                    0, DB_POOL_MAX_CONN, DATABASE_URL
                )
                # psycopg2 also uses minconn when deciding whether returned
                # connections should remain in the idle pool.
                new_pool.minconn = DB_POOL_MIN_CONN
                warmed = _prewarm_pool_in_parallel(
                    new_pool, DB_POOL_MIN_CONN
                )
                logger.info(
                    "PostgreSQL connection pool created (min=%d, max=%d, pre-warmed=%d)",
                    DB_POOL_MIN_CONN,
                    DB_POOL_MAX_CONN,
                    warmed,
                )
                _pool = new_pool
    return _pool


def _is_alive(conn):
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        return True
    except Exception:
        return False


def _check_health(raw_conn):
    """Return (healthy, health_ms, skipped) for one physical connection."""
    cid = id(raw_conn)
    now = time.monotonic()
    with _last_verified_lock:
        last_ok = _last_verified_at.get(cid)

    if last_ok is not None and (
        now - last_ok < DB_POOL_HEALTH_RECHECK_SECONDS
    ):
        return True, 0.0, True

    started = time.monotonic()
    healthy = _is_alive(raw_conn)
    health_ms = (time.monotonic() - started) * 1000.0

    if healthy:
        with _last_verified_lock:
            _last_verified_at[cid] = time.monotonic()

    return healthy, health_ms, False


def _discard_connection(pool, raw_conn):
    with _last_verified_lock:
        _last_verified_at.pop(id(raw_conn), None)
    try:
        pool.putconn(raw_conn, close=True)
    except Exception:
        try:
            raw_conn.close()
        except Exception:
            pass


def _checkout_with_wait(pool, timeout_seconds):
    """Get a connection, waiting for a returned connection when the pool is full.

    psycopg2 raises PoolError immediately when every connection is checked out.
    We convert that into bounded condition-variable waiting. A connection
    return calls notify_all(), so waiting callers wake as soon as capacity is
    available instead of polling or sleeping in a retry loop.
    """
    started = time.monotonic()
    deadline = started + timeout_seconds
    queue_wait_ms = 0.0

    while True:
        try:
            raw_conn = pool.getconn()
            queue_wait_ms = (time.monotonic() - started) * 1000.0
            return raw_conn, queue_wait_ms
        except pg_pool.PoolError:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                queue_wait_ms = (time.monotonic() - started) * 1000.0
                raise TimeoutError(
                    "Timed out waiting %.1fs for a database connection"
                    % timeout_seconds
                )

            with _pool_available:
                # Re-check immediately after acquiring the condition lock.
                try:
                    raw_conn = pool.getconn()
                    queue_wait_ms = (time.monotonic() - started) * 1000.0
                    return raw_conn, queue_wait_ms
                except pg_pool.PoolError:
                    _pool_available.wait(timeout=remaining)


def _return_to_pool(pool, raw_conn):
    """Return a connection and wake callers waiting for pool capacity."""
    try:
        pool.putconn(raw_conn)
    finally:
        with _pool_available:
            _pool_available.notify_all()


class _PooledConnection:
    """Compatibility proxy whose close() returns the connection to the pool."""

    __slots__ = (
        "_conn",
        "_returned",
        "_operation",
        "_thread_name",
        "_conn_id",
        "_checkout_finished_at",
    )

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
            hold_ms = (
                time.monotonic()
                - object.__getattribute__(self, "_checkout_finished_at")
            ) * 1000.0
            logger.info(
                "DB return: operation=%s thread=%s conn_id=%s hold=%.1fms",
                object.__getattribute__(self, "_operation"),
                object.__getattribute__(self, "_thread_name"),
                object.__getattribute__(self, "_conn_id"),
                hold_ms,
            )
        except Exception:
            pass

        try:
            _return_to_pool(_get_pool(), conn)
        except Exception:
            logger.exception(
                "Failed to return connection to pool; closing it directly"
            )
            try:
                conn.close()
            except Exception:
                pass


def get_conn():
    """Acquire a healthy pooled connection, waiting up to the configured timeout."""
    operation = _caller_operation()
    thread_name = threading.current_thread().name
    pool = _get_pool()

    checkout_started = time.monotonic()
    try:
        raw_conn, queue_wait_ms = _checkout_with_wait(
            pool, DB_POOL_WAIT_TIMEOUT_SECONDS
        )
    except TimeoutError as exc:
        logger.error(
            "DB checkout TIMEOUT: operation=%s thread=%s queue_wait=%.1fms timeout=%.1fs",
            operation,
            thread_name,
            (time.monotonic() - checkout_started) * 1000.0,
            DB_POOL_WAIT_TIMEOUT_SECONDS,
        )
        raise psycopg2.OperationalError(str(exc)) from exc

    total_health_ms = 0.0
    skipped_check = False
    attempts = 0

    try:
        while True:
            attempts += 1

            if raw_conn.closed:
                healthy, health_ms, skipped = False, 0.0, False
            else:
                healthy, health_ms, skipped = _check_health(raw_conn)

            total_health_ms += health_ms
            skipped_check = skipped_check or skipped

            if healthy:
                break

            _discard_connection(pool, raw_conn)

            if attempts >= DB_POOL_MAX_REPLACE_ATTEMPTS:
                logger.error(
                    "DB checkout FAILED: no healthy connection after %d attempt(s) "
                    "operation=%s queue_wait=%.1fms health=%.1fms",
                    attempts,
                    operation,
                    queue_wait_ms,
                    total_health_ms,
                )
                raise psycopg2.OperationalError(
                    "Could not obtain a healthy database connection after "
                    f"{attempts} attempt(s) (operation={operation})"
                )

            replacement_started = time.monotonic()
            try:
                replacement, replacement_wait_ms = _checkout_with_wait(
                    pool, DB_POOL_WAIT_TIMEOUT_SECONDS
                )
                queue_wait_ms += replacement_wait_ms
                raw_conn = replacement
            except TimeoutError as exc:
                raise psycopg2.OperationalError(str(exc)) from exc

        logger.info(
            "DB checkout: operation=%s thread=%s conn_id=%s queue_wait=%.1fms "
            "health=%.1fms healthy=yes replaced=%s attempts=%d skipped_check=%s",
            operation,
            thread_name,
            id(raw_conn),
            queue_wait_ms,
            total_health_ms,
            "yes" if attempts > 1 else "no",
            attempts,
            "yes" if skipped_check else "no",
        )
        return _PooledConnection(
            raw_conn,
            operation=operation,
            thread_name=thread_name,
            conn_id=id(raw_conn),
        )
    except Exception:
        # If health validation itself fails after we acquired a live-looking
        # connection, make sure the physical connection is not leaked.
        try:
            if raw_conn is not None and not getattr(raw_conn, "closed", True):
                _return_to_pool(pool, raw_conn)
        except Exception:
            pass
        raise


def closeall():
    """Close every connection currently held by the pool."""
    global _pool
    with _pool_lock:
        if _pool is not None:
            _pool.closeall()
            _pool = None
            with _last_verified_lock:
                _last_verified_at.clear()
            with _pool_available:
                _pool_available.notify_all()
            logger.info("PostgreSQL connection pool closed")
