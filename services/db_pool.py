"""Shared PostgreSQL connection pool.

The application uses one process-wide psycopg2 ThreadedConnectionPool.
Connections are reused, health-checked periodically, and returned by the
existing ``conn.close()`` call sites.

psycopg2 raises PoolError immediately when every connection is checked out.
This module adds bounded condition-variable waiting so short bursts above the
pool size wait for a returned connection instead of failing immediately.

Checkout tracing is intentionally detailed so load tests can distinguish:

- total time spent waiting for a connection
- individual checkout attempts
- replacement-connection waits
- the configured timeout/deadline
- whether a request exceeded the configured total wait budget
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

DB_POOL_WAIT_TIMEOUT_SECONDS = float(
    os.getenv("DB_POOL_WAIT_TIMEOUT_SECONDS", "5")
)

_pool = None
_pool_lock = threading.Lock()
_pool_available = threading.Condition(threading.Lock())

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
            "Pre-warm: psycopg2 pool internals changed; "
            "falling back to normal growth"
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
                    0,
                    DB_POOL_MAX_CONN,
                    DATABASE_URL,
                )

                new_pool.minconn = DB_POOL_MIN_CONN

                warmed = _prewarm_pool_in_parallel(
                    new_pool,
                    DB_POOL_MIN_CONN,
                )

                logger.info(
                    "PostgreSQL connection pool created "
                    "(min=%d, max=%d, pre-warmed=%d)",
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


def _checkout_with_wait(
    pool,
    timeout_seconds,
    operation="unknown",
    deadline=None,
):
    """Get a connection using one absolute total wait deadline.

    ``deadline`` is created by the outer checkout operation and is reused for
    every replacement attempt. This is important: replacing an unhealthy
    connection must never restart the configured wait budget.

    The deadline applies to time spent waiting for pool capacity. Health-check
    and query execution time are outside this pool-capacity wait budget.
    """
    started = time.monotonic()

    if deadline is None:
        deadline = started + timeout_seconds

    wait_cycles = 0

    logger.debug(
        "DB checkout START: operation=%s timeout=%.3fs "
        "deadline_in=%.1fms",
        operation,
        timeout_seconds,
        max(0.0, deadline - started) * 1000.0,
    )

    while True:
        now = time.monotonic()
        remaining = deadline - now

        if remaining <= 0:
            elapsed_ms = (now - started) * 1000.0

            logger.warning(
                "DB checkout DEADLINE EXCEEDED: "
                "operation=%s elapsed=%.1fms timeout=%.3fs "
                "wait_cycles=%d deadline_remaining=0.0ms",
                operation,
                elapsed_ms,
                timeout_seconds,
                wait_cycles,
            )

            raise TimeoutError(
                "Timed out waiting %.1fs for a database connection"
                % timeout_seconds
            )

        try:
            raw_conn = pool.getconn()

            elapsed_ms = (time.monotonic() - started) * 1000.0

            logger.debug(
                "DB checkout ACQUIRED: "
                "operation=%s elapsed=%.1fms timeout=%.3fs "
                "wait_cycles=%d conn_id=%s",
                operation,
                elapsed_ms,
                timeout_seconds,
                wait_cycles,
                id(raw_conn),
            )

            return raw_conn, elapsed_ms

        except pg_pool.PoolError:
            now = time.monotonic()
            remaining = deadline - now

            if remaining <= 0:
                elapsed_ms = (now - started) * 1000.0

                logger.warning(
                    "DB checkout TIMEOUT BEFORE WAIT: "
                    "operation=%s elapsed=%.1fms timeout=%.3fs "
                    "wait_cycles=%d deadline_remaining=0.0ms",
                    operation,
                    elapsed_ms,
                    timeout_seconds,
                    wait_cycles,
                )

                raise TimeoutError(
                    "Timed out waiting %.1fs for a database connection"
                    % timeout_seconds
                )

            wait_cycles += 1

            logger.debug(
                "DB checkout WAIT: "
                "operation=%s elapsed=%.1fms remaining=%.1fms "
                "timeout=%.3fs wait_cycle=%d",
                operation,
                (now - started) * 1000.0,
                remaining * 1000.0,
                timeout_seconds,
                wait_cycles,
            )

            with _pool_available:
                # Re-check while holding the condition lock so a return
                # cannot be missed between the failed checkout and wait().
                try:
                    raw_conn = pool.getconn()

                    elapsed_ms = (time.monotonic() - started) * 1000.0

                    logger.debug(
                        "DB checkout ACQUIRED AFTER LOCK RECHECK: "
                        "operation=%s elapsed=%.1fms remaining=%.1fms "
                        "wait_cycles=%d conn_id=%s",
                        operation,
                        elapsed_ms,
                        max(
                            0.0,
                            deadline - time.monotonic(),
                        )
                        * 1000.0,
                        wait_cycles,
                        id(raw_conn),
                    )

                    return raw_conn, elapsed_ms

                except pg_pool.PoolError:
                    wait_started = time.monotonic()

                    _pool_available.wait(
                        timeout=max(0.0, deadline - wait_started)
                    )

                    wake_now = time.monotonic()

                    wait_elapsed_ms = (
                        wake_now - wait_started
                    ) * 1000.0

                    total_elapsed_ms = (
                        wake_now - started
                    ) * 1000.0

                    remaining_after_wait_ms = max(
                        0.0,
                        deadline - wake_now,
                    ) * 1000.0

                    logger.debug(
                        "DB checkout WOKE: "
                        "operation=%s wait_cycle=%d "
                        "condition_wait=%.1fms total_elapsed=%.1fms "
                        "deadline_remaining=%.1fms",
                        operation,
                        wait_cycles,
                        wait_elapsed_ms,
                        total_elapsed_ms,
                        remaining_after_wait_ms,
                    )


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

    def __init__(
        self,
        conn,
        operation="unknown",
        thread_name="unknown",
        conn_id=0,
    ):
        object.__setattr__(self, "_conn", conn)
        object.__setattr__(self, "_returned", False)
        object.__setattr__(self, "_operation", operation)
        object.__setattr__(self, "_thread_name", thread_name)
        object.__setattr__(self, "_conn_id", conn_id)
        object.__setattr__(
            self,
            "_checkout_finished_at",
            time.monotonic(),
        )

    def __getattr__(self, name):
        return getattr(
            object.__getattribute__(self, "_conn"),
            name,
        )

    def close(self):
        if object.__getattribute__(self, "_returned"):
            return

        object.__setattr__(self, "_returned", True)

        conn = object.__getattribute__(self, "_conn")

        try:
            hold_ms = (
                time.monotonic()
                - object.__getattribute__(
                    self,
                    "_checkout_finished_at",
                )
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
    """Acquire a healthy pooled connection.

    One absolute deadline is created for the complete pool-capacity checkout.
    If the first connection is unhealthy and must be replaced, the
    replacement uses the remaining time from that same deadline rather than
    receiving a fresh timeout budget.

    Detailed tracing records direct acquisition, waiting, replacement,
    remaining deadline, and final timeout behaviour.
    """
    operation = _caller_operation()
    thread_name = threading.current_thread().name

    pool = _get_pool()
    raw_conn = None

    checkout_started = time.monotonic()

    # IMPORTANT:
    # This deadline belongs to the whole get_conn() checkout operation.
    # It must not be recreated for replacement connections.
    checkout_deadline = (
        checkout_started + DB_POOL_WAIT_TIMEOUT_SECONDS
    )

    total_queue_wait_ms = 0.0

    try:
        raw_conn, queue_wait_ms = _checkout_with_wait(
            pool,
            DB_POOL_WAIT_TIMEOUT_SECONDS,
            operation=operation,
            deadline=checkout_deadline,
        )

        total_queue_wait_ms += queue_wait_ms

    except TimeoutError as exc:
        elapsed_ms = (
            time.monotonic() - checkout_started
        ) * 1000.0

        logger.error(
            "DB checkout TIMEOUT: "
            "operation=%s thread=%s queue_wait=%.1fms "
            "timeout=%.1fs total_elapsed=%.1fms",
            operation,
            thread_name,
            elapsed_ms,
            DB_POOL_WAIT_TIMEOUT_SECONDS,
            elapsed_ms,
        )

        raise psycopg2.OperationalError(str(exc)) from exc

    total_health_ms = 0.0
    skipped_check = False
    attempts = 0

    try:
        while True:
            attempts += 1

            if raw_conn.closed:
                healthy, health_ms, skipped = (
                    False,
                    0.0,
                    False,
                )
            else:
                healthy, health_ms, skipped = _check_health(
                    raw_conn
                )

            total_health_ms += health_ms
            skipped_check = skipped_check or skipped

            logger.debug(
                "DB checkout HEALTH RESULT: "
                "operation=%s attempt=%d conn_id=%s "
                "healthy=%s health=%.1fms "
                "queue_wait=%.1fms",
                operation,
                attempts,
                id(raw_conn),
                "yes" if healthy else "no",
                health_ms,
                total_queue_wait_ms,
            )

            if healthy:
                break

            logger.warning(
                "DB checkout REPLACING UNHEALTHY CONNECTION: "
                "operation=%s attempt=%d conn_id=%s "
                "queue_wait=%.1fms",
                operation,
                attempts,
                id(raw_conn),
                total_queue_wait_ms,
            )

            _discard_connection(pool, raw_conn)
            raw_conn = None

            if attempts >= DB_POOL_MAX_REPLACE_ATTEMPTS:
                logger.error(
                    "DB checkout FAILED: no healthy connection after "
                    "%d attempt(s) operation=%s queue_wait=%.1fms "
                    "health=%.1fms",
                    attempts,
                    operation,
                    total_queue_wait_ms,
                    total_health_ms,
                )

                raise psycopg2.OperationalError(
                    "Could not obtain a healthy database connection "
                    "after "
                    f"{attempts} attempt(s) "
                    f"(operation={operation})"
                )

            remaining_before_replacement = (
                checkout_deadline - time.monotonic()
            )

            if remaining_before_replacement <= 0:
                elapsed_ms = (
                    time.monotonic() - checkout_started
                ) * 1000.0

                logger.warning(
                    "DB checkout DEADLINE EXCEEDED BEFORE REPLACEMENT: "
                    "operation=%s attempt=%d elapsed=%.1fms "
                    "timeout=%.3fs queue_wait=%.1fms",
                    operation,
                    attempts,
                    elapsed_ms,
                    DB_POOL_WAIT_TIMEOUT_SECONDS,
                    total_queue_wait_ms,
                )

                raise psycopg2.OperationalError(
                    "Timed out waiting for a replacement database "
                    "connection after "
                    f"{elapsed_ms / 1000.0:.1f}s "
                    f"(operation={operation})"
                )

            replacement_started = time.monotonic()

            raw_conn, replacement_wait_ms = _checkout_with_wait(
                pool,
                DB_POOL_WAIT_TIMEOUT_SECONDS,
                operation=(
                    f"{operation}:replacement_attempt_{attempts + 1}"
                ),
                deadline=checkout_deadline,
            )

            replacement_elapsed_ms = (
                time.monotonic() - replacement_started
            ) * 1000.0

            total_queue_wait_ms += replacement_wait_ms

            logger.debug(
                "DB checkout REPLACEMENT ACQUIRED: "
                "operation=%s attempt=%d conn_id=%s "
                "replacement_wait=%.1fms "
                "replacement_elapsed=%.1fms "
                "total_queue_wait=%.1fms "
                "deadline_remaining=%.1fms",
                operation,
                attempts + 1,
                id(raw_conn),
                replacement_wait_ms,
                replacement_elapsed_ms,
                total_queue_wait_ms,
                max(
                    0.0,
                    checkout_deadline - time.monotonic(),
                )
                * 1000.0,
            )

        total_checkout_ms = (
            time.monotonic() - checkout_started
        ) * 1000.0

        logger.info(
            "DB checkout: operation=%s thread=%s conn_id=%s "
            "queue_wait=%.1fms health=%.1fms healthy=yes "
            "replaced=%s attempts=%d skipped_check=%s "
            "total_checkout=%.1fms configured_wait_timeout=%.1fs "
            "deadline_remaining=%.1fms",
            operation,
            thread_name,
            id(raw_conn),
            total_queue_wait_ms,
            total_health_ms,
            "yes" if attempts > 1 else "no",
            attempts,
            "yes" if skipped_check else "no",
            total_checkout_ms,
            DB_POOL_WAIT_TIMEOUT_SECONDS,
            max(
                0.0,
                checkout_deadline - time.monotonic(),
            )
            * 1000.0,
        )

        return _PooledConnection(
            raw_conn,
            operation=operation,
            thread_name=thread_name,
            conn_id=id(raw_conn),
        )

    except Exception:
        if raw_conn is not None:
            try:
                if not getattr(raw_conn, "closed", True):
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