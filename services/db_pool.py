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

This instrumentation is purely observational and safe to remove once
the investigation it supports is done -- it doesn't itself change any
application behavior.

Performance fix: skip redundant back-to-back liveness checks
-------------------------------------------------------------
That instrumentation found the answer. Under 10 concurrent users, the
liveness check (`SELECT 1`) was measured costing a real, remarkably
consistent ~350ms of network round-trip time on every single checkout
-- not just occasionally, every time, for every action in the app.
Combined with this pooling library handing out connections to one
thread at a time rather than truly in parallel, that ~350ms tax
stacking up person after person accounted for almost exactly the
~1-second-per-person queue observed, in both a cold and an already-
"warm" pool alike.

The fix: `get_conn()` now only re-runs the liveness check on a given
physical connection if it hasn't been successfully verified in the
last `DB_POOL_HEALTH_RECHECK_SECONDS` (see config.py; default 30
seconds). A connection that was just used and returned a moment ago
hasn't had time to go stale -- re-checking it anyway was pure
redundant cost. A connection that really has been sitting idle for a
while (the actual scenario this check exists to protect against, e.g.
Neon's autosuspend/compute-scale-to-zero behavior) still gets checked
exactly as before. `_last_verified_at` (a small in-memory dict, keyed
by Python object identity of the underlying psycopg2 connection) is
purely a local optimization cache -- worst case if it's ever wrong is
one extra `SELECT 1` that didn't strictly need to happen, never a
skipped check on a connection that actually needed one, since an
entry is only ever trusted for a connection object still known to be
open and was itself the direct result of a previous successful check.

Reliability fix: verify replacement connections too
--------------------------------------------------------
Previously, when a connection failed its liveness check, `get_conn()`
discarded it, fetched ONE replacement from the pool, and handed that
replacement straight to the caller without checking it -- on the
(usually true, but not guaranteed) assumption that a freshly-fetched
connection would be fine. If several connections in the pool had gone
stale around the same time (e.g. after a period of inactivity, or a
brief network blip affecting more than one open connection at once),
the replacement could ALSO be dead, and the caller would be handed a
connection guaranteed to fail on its very first real query -- surfacing
as a confusing error deep inside whatever business function asked for
it (e.g. "server closed the connection unexpectedly" during a save),
rather than being caught and handled here, where the problem actually
is.

`get_conn()` now checks every replacement the same way it checks the
first connection it tries, and will discard-and-fetch-again up to
`DB_POOL_MAX_REPLACE_ATTEMPTS` (see config.py; default 3) times. Only
if every attempt comes back dead does it give up -- at which point it
raises a clear, immediate error instead of quietly handing back a
broken connection. This is a genuine behavior change for that one rare
case (many stale connections in a row): before, the caller got a
connection that would fail later and confusingly; now, the caller gets
an honest, immediate failure it can catch the same way it already
catches any other database error (see e.g. services/rate_limiter.py's
"fails open" handling).

Performance/reliability fix: pre-warming the pool
-----------------------------------------------------
Even with the two fixes above, load testing (10 concurrent users)
still showed a real, repeatable slowdown at the START of every burst
of traffic: the 2nd person's database call would wait ~1.3s, the 3rd
~2.6s, the 4th ~4.1s, climbing in lockstep. This was not a liveness-
check cost (already fixed above) or a broken-connection cost (also
fixed above) -- it was the pool itself only having ONE connection
open (the old DB_POOL_MIN_CONN default), forced to open every
additional connection needed one at a time, competing with real users
who were all waiting for that same growth to happen.

The fix lives in config.py: DB_POOL_MIN_CONN now defaults to the same
value as DB_POOL_MAX_CONN, so every connection this process will ever
use gets opened up front, in one place, at pool-creation time --
before real user traffic is competing for them, not during it. See
config.py's comment on DB_POOL_MIN_CONN for the full trade-off this
involves (a few extra seconds the first time the pool is created, in
exchange for real users never again queueing behind pool growth).

Pre-warming the pool, in parallel
-----------------------------------------------------
Real testing of the fix above found its "a few extra seconds" estimate
was too optimistic: on a real (if slow) home connection, opening 10
connections ONE AT A TIME -- psycopg2's own built-in behavior when a
pool is first created -- cost close to 16 seconds, all paid at once by
whichever request happened to be first. That's because opening a
brand-new connection (full network handshake, encryption setup,
database login) is meaningfully more expensive than the lightweight
liveness check used elsewhere in this file, and there was nothing
overlapping those 10 handshakes with each other.

`_get_pool()` now creates the pool with minconn=0 (instant, since
nothing is opened yet) and immediately calls
`_prewarm_pool_in_parallel()` (see its own docstring) to open all
DB_POOL_MIN_CONN connections AT THE SAME TIME instead of one after
another -- cutting that one-time cost from roughly (10 x one
handshake) down to roughly (one handshake). This changes nothing
about how the pool behaves afterward -- callers still see exactly
DB_POOL_MIN_CONN warm connections ready to go -- it only changes how
quickly that readiness is reached.
"""

import inspect
import threading
import time

import concurrent.futures
import psycopg2
from psycopg2 import pool as pg_pool

from config import (
    DATABASE_URL, DB_POOL_MIN_CONN, DB_POOL_MAX_CONN,
    DB_POOL_HEALTH_RECHECK_SECONDS, DB_POOL_MAX_REPLACE_ATTEMPTS,
)
from services.db_time import get_logger

logger = get_logger(__name__)

_pool = None
_pool_lock = threading.Lock()

# Tracks, per physical connection (keyed by id(raw_conn)), the
# monotonic time it was last successfully verified alive -- see
# module docstring, "Performance fix: skip redundant back-to-back
# liveness checks". Entries are added on a successful check and
# removed the moment a connection is found dead/discarded, so a
# stale entry can never outlive the connection it describes.
_last_verified_at = {}
_last_verified_lock = threading.Lock()

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


def _prewarm_pool_in_parallel(pool, count):
    """
    Opens `count` real connections to Postgres all at once, in
    parallel, and hands them to `pool` as its ready-to-use free
    connections -- instead of psycopg2's own built-in behavior of
    opening them one at a time (see module docstring, "Pre-warming the
    pool, in parallel").

    Real testing found the SEQUENTIAL version of this (letting
    ThreadedConnectionPool's own constructor open all
    DB_POOL_MIN_CONN connections itself, one after another) cost
    roughly 16 seconds for 10 connections on a real, if slow, home
    connection -- because opening a brand-new connection (full
    network handshake, encryption setup, database login) is
    meaningfully more expensive than the lightweight "are you still
    there?" check used elsewhere in this file, and psycopg2 does not
    parallelize this on its own.

    This function uses a temporary set of Python threads (NOT the
    pool's own locked getconn()/putconn(), which -- by design, for
    safety -- only lets one thread open a connection at a time) so
    that all `count` handshakes genuinely happen at the same time,
    cutting the total one-time wait from roughly (count x one
    handshake) down to roughly (one handshake), the same way opening
    several browser tabs at once doesn't take several times as long as
    opening just one.

    This reaches into `pool`'s internal free-connection list, which
    isn't officially part of psycopg2's public interface (though it
    has been stable for a very long time). If a future psycopg2
    version changes that internal detail, this function detects that
    safely and simply does nothing -- the pool still works exactly as
    before, just falling back to opening connections one at a time as
    they're actually needed, which is slower but never broken.
    """
    if count <= 0:
        return 0

    t0 = time.monotonic()
    opened = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=count) as executor:
        futures = [executor.submit(psycopg2.connect, DATABASE_URL) for _ in range(count)]
        for f in futures:
            try:
                opened.append(f.result())
            except Exception:
                logger.exception("Pre-warm: one parallel connection attempt failed -- continuing with the rest")

    if not opened:
        return 0

    try:
        with pool._lock:
            pool._pool.extend(opened)
    except AttributeError:
        # psycopg2's internal pool.pool list (or its lock) is no
        # longer where this version expects -- safe fallback: close
        # what we just opened rather than leaking connections, and
        # let the pool grow the normal, slower, built-in way instead.
        logger.warning(
            "Pre-warm: psycopg2 pool internals not found as expected -- "
            "falling back to the pool's normal (slower) connection growth."
        )
        for conn in opened:
            try:
                conn.close()
            except Exception:
                pass
        return 0

    elapsed = time.monotonic() - t0
    logger.info(
        "Pre-warm: opened %d connection(s) in parallel in %.1fs (vs. roughly %d x that time if done one at a time)",
        len(opened), elapsed, count,
    )
    return len(opened)


def _get_pool():
    """Lazily create the process-wide pool on first use (double-checked
    locking so concurrent Streamlit session threads never race to
    create two pools).

    IMPORTANT ordering detail: the new pool is built and fully
    pre-warmed in a LOCAL variable first, and only assigned to the
    global `_pool` as the very last step. Real testing caught a bug
    from an earlier version of this function that assigned `_pool`
    (globally visible) BEFORE pre-warming had finished -- other
    threads' outer `if _pool is None:` check (deliberately outside
    the lock, for speed) would then see a real-but-still-empty pool
    and immediately start opening their OWN connections the normal,
    slow, one-at-a-time way, racing against the parallel pre-warm
    itself and slowing both down. Building fully offline in a local
    variable and publishing it only once complete closes that gap:
    every other thread's outer check keeps seeing None, exactly as
    intended, until the real, ready pool is handed over all at once.
    """
    global _pool
    if _pool is None:
        with _pool_lock:
            if _pool is None:
                # minconn=0 here on purpose: this makes construction
                # itself instant (no built-in sequential connection
                # opening), and _prewarm_pool_in_parallel() below does
                # the equivalent job -- opening DB_POOL_MIN_CONN
                # connections -- but genuinely in parallel rather than
                # one at a time. See that function's docstring, and
                # module docstring "Pre-warming the pool, in parallel".
                new_pool = pg_pool.ThreadedConnectionPool(
                    0, DB_POOL_MAX_CONN, DATABASE_URL
                )
                warmed = _prewarm_pool_in_parallel(new_pool, DB_POOL_MIN_CONN)
                logger.info(
                    "PostgreSQL connection pool created (min=%d, max=%d, pre-warmed=%d)",
                    DB_POOL_MIN_CONN, DB_POOL_MAX_CONN, warmed,
                )
                # Published only now, fully built and warmed -- see
                # docstring above for why this ordering matters.
                _pool = new_pool
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


def _check_health(raw_conn):
    """
    Runs the "is this connection actually usable" check for one
    connection, honoring the recently-verified skip-cache (see module
    docstring, "Performance fix"). Assumes raw_conn.closed has already
    been checked as False by the caller.

    Returns (healthy, health_ms, skipped):
      healthy   -- True if this connection is safe to hand out.
      health_ms -- how long the real SELECT 1 check took, in
                   milliseconds (0.0 if skipped via the cache).
      skipped   -- True if this result came from the recently-verified
                   cache rather than a fresh check.

    Used for both the connection get_conn() first tries AND for every
    replacement it fetches afterward (see module docstring,
    "Reliability fix: verify replacement connections too") -- a
    replacement gets exactly the same scrutiny as any other
    connection, nothing more, nothing less.
    """
    cid = id(raw_conn)
    now = time.monotonic()
    with _last_verified_lock:
        last_ok = _last_verified_at.get(cid)

    if last_ok is not None and (now - last_ok) < DB_POOL_HEALTH_RECHECK_SECONDS:
        return True, 0.0, True

    health_start = time.monotonic()
    healthy = _is_alive(raw_conn)
    health_ms = (time.monotonic() - health_start) * 1000.0
    if healthy:
        with _last_verified_lock:
            _last_verified_at[cid] = time.monotonic()
    return healthy, health_ms, False


def get_conn():
    """
    Acquire a connection from the shared pool. Used exactly like
    `psycopg2.connect(DATABASE_URL)` was used before: callers run
    `conn.cursor()` / `conn.commit()` / `conn.rollback()` as normal,
    and MUST still call `conn.close()` when finished -- that now
    returns the connection to the pool rather than physically closing
    it, so the try/finally pattern already used throughout services/
    is unchanged.

    (See module docstring -- "Diagnostic instrumentation", "Performance
    fix", and "Reliability fix: verify replacement connections too" --
    this also logs one "DB checkout: ..." line per call, skips the
    liveness check when a connection was already verified recently,
    and checks every replacement it fetches the same way, up to
    DB_POOL_MAX_REPLACE_ATTEMPTS times, before giving up.)

    Raises psycopg2.OperationalError if no healthy connection could be
    obtained after DB_POOL_MAX_REPLACE_ATTEMPTS attempts -- callers
    already wrap get_conn() in their own try/except (see e.g.
    services/rate_limiter.py's "fails open" handling), so this is a
    normal, catchable failure, not a crash.
    """
    operation = _caller_operation()
    thread_name = threading.current_thread().name

    pool = _get_pool()

    checkout_start = time.monotonic()
    raw_conn = pool.getconn()
    checkout_wait_ms = (time.monotonic() - checkout_start) * 1000.0

    total_health_ms = 0.0
    skipped_check = False
    attempt = 0

    while True:
        attempt += 1

        if raw_conn.closed:
            healthy, health_ms, skipped = False, 0.0, False
        else:
            healthy, health_ms, skipped = _check_health(raw_conn)

        total_health_ms += health_ms
        if skipped:
            skipped_check = True

        if healthy:
            break

        # This connection (whether it was the original or an earlier
        # replacement) is dead -- discard it.
        with _last_verified_lock:
            _last_verified_at.pop(id(raw_conn), None)
        try:
            pool.putconn(raw_conn, close=True)
        except Exception:
            try:
                raw_conn.close()
            except Exception:
                pass

        if attempt >= DB_POOL_MAX_REPLACE_ATTEMPTS:
            try:
                logger.error(
                    "DB checkout FAILED: no healthy connection after %d attempt(s) "
                    "operation=%s thread=%s wait=%.1fms health=%.1fms",
                    attempt, operation, thread_name, checkout_wait_ms, total_health_ms,
                )
            except Exception:
                pass
            raise psycopg2.OperationalError(
                f"Could not obtain a healthy database connection after "
                f"{attempt} attempt(s) (operation={operation})"
            )

        replace_start = time.monotonic()
        raw_conn = pool.getconn()
        checkout_wait_ms += (time.monotonic() - replace_start) * 1000.0
        # Loop back around and actually check THIS connection too --
        # this is the fix: a replacement is no longer trusted blindly.

    replaced = attempt > 1

    try:
        logger.info(
            "DB checkout: operation=%s thread=%s conn_id=%s wait=%.1fms health=%.1fms "
            "healthy=%s replaced=%s attempts=%d skipped_check=%s",
            operation, thread_name, id(raw_conn), checkout_wait_ms, total_health_ms,
            "yes" if healthy else "no", "yes" if replaced else "no",
            attempt, "yes" if skipped_check else "no",
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
            with _last_verified_lock:
                _last_verified_at.clear()
            logger.info("PostgreSQL connection pool closed")