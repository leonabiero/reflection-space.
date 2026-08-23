"""
Safe, in-memory stand-ins for PostgreSQL and the Claude API.

WHY THIS FILE EXISTS
---------------------
Phase 3's load/performance testing is meant to answer "what happens when
many legitimate practitioners use Reflection Space at the same time?"
without spending real money on the Claude/Gemini APIs, without touching
a real Postgres database, and without needing production credentials.

The trick used throughout this package is NOT to re-implement the
application's logic in a simplified test copy. It is to run the REAL
application code (services/db_pool.py, services/rate_limiter.py,
services/ka_rate_limiter.py, services/request_dedup.py,
services/login_rate_limiter.py, rdi/orchestrator.py, ...) completely
unmodified, and only swap out the two things that would otherwise cost
money or require infrastructure we don't have here:

  1. psycopg2.connect(...) -- swapped for FakeConnection, an in-memory
     object that behaves enough like a real PostgreSQL connection
     (cursor(), execute(), fetchone()/fetchall(), commit(), rollback(),
     close(), .closed) for every SQL statement this codebase actually
     issues (see _QUERIES below -- this list was built by reading each
     services/*.py module's real queries, not guessed).

  2. services.reflection_service.client.messages.create(...) -- swapped
     for a fake that returns a realistically-shaped response after a
     configurable simulated delay, so rdi/orchestrator.py's real
     concurrency control (the semaphore, the 8-way thread pool, retries)
     runs exactly as it would in production, just without a real network
     call.

Because psycopg2.pool.ThreadedConnectionPool itself is NOT replaced --
only the psycopg2.connect() calls it makes internally -- pool sizing,
checkout queueing, and exhaustion behavior in services/db_pool.py are
all real, unmodified behavior being measured, not simulated.

CRITICAL SAFETY NOTE: nothing in this file ever imports or calls the
real `psycopg2.connect`, the real `anthropic` client's network methods,
or any real Qdrant client. It is impossible for this module to reach a
production service, spend API credits, or touch production data.
"""

import hashlib
import threading
import time
from datetime import datetime, timezone


# ---------------------------------------------------------------------------
# Fake PostgreSQL
# ---------------------------------------------------------------------------

class FakeDatabase:
    """
    One in-memory "database": a handful of tables (plain lists of dict
    rows) plus a registry of PostgreSQL advisory locks. Every
    FakeConnection created against the same FakeDatabase instance shares
    this state, exactly like every real psycopg2 connection in the pool
    shares the same underlying Postgres database.

    `query_latency_seconds` adds a small artificial delay to every
    execute() call, standing in for real network + query round-trip
    time, so latency numbers produced by the load test mean something
    instead of being instant no-ops. Defaults to a modest 3ms, tunable
    per load-test run.
    """

    def __init__(self, query_latency_seconds: float = 0.003):
        self.query_latency_seconds = query_latency_seconds
        self._lock = threading.Lock()
        self.tables = {
            "reflection_rate_log": [],
            "ka_rate_log": [],
            "login_failure_log": [],
            "idempotent_requests": [],  # unique on request_id
        }
        # PostgreSQL advisory transaction locks (pg_advisory_xact_lock):
        # keyed by the integer lock id, held until the owning
        # transaction commits or rolls back.
        self._advisory_locks: dict[int, threading.Lock] = {}
        self._advisory_locks_guard = threading.Lock()

        # Simple counters so a load test run can report exactly how
        # much read/write traffic it generated.
        self.stats = {"queries_executed": 0, "connections_opened": 0}

    def _advisory_lock_for(self, key: int) -> threading.Lock:
        with self._advisory_locks_guard:
            lock = self._advisory_locks.get(key)
            if lock is None:
                lock = threading.Lock()
                self._advisory_locks[key] = lock
            return lock

    def connect(self):
        self.stats["connections_opened"] += 1
        return FakeConnection(self)


def _hash_lock_key(value) -> int:
    """
    Stand-in for PostgreSQL's hashtextextended(text, 0): only needs to
    be a stable integer for the same input, since it's only ever used
    as a dict key here.
    """
    return int(hashlib.sha256(str(value).encode("utf-8")).hexdigest(), 16) % (2**31)


def _norm(sql: str) -> str:
    return " ".join(sql.split()).upper()


class FakeCursor:
    """
    Understands exactly the SQL statements actually issued by this
    codebase's rate limiters, request-dedup module, and health check --
    see each services/*.py module for the real query this mirrors.
    Anything unrecognised raises AssertionError loudly rather than
    silently doing nothing, so a future code change that adds a new
    query is caught by a failing load test instead of producing
    meaningless results.
    """

    def __init__(self, conn: "FakeConnection"):
        self.conn = conn
        self.db = conn.db
        self._result = None
        self.rowcount = 0

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def execute(self, sql, params=None):
        if self.db.query_latency_seconds:
            time.sleep(self.db.query_latency_seconds)

        self.db.stats["queries_executed"] += 1
        params = params or ()
        normalized = _norm(sql)
        self._result = None
        self.rowcount = 0

        if normalized == "SELECT 1":
            self._result = ("one", (1,))
            return

        if normalized.startswith("SELECT PG_ADVISORY_XACT_LOCK"):
            key = _hash_lock_key(params[0])
            lock = self.db._advisory_lock_for(key)
            lock.acquire()  # blocks -- real serialization, real waiting
            self.conn._held_advisory_locks.append(lock)
            self._result = ("one", (None,))
            return

        for table_name in self.db.tables:
            handled = self._maybe_handle_table_query(table_name, normalized, params)
            if handled:
                return

        raise AssertionError(f"FakeCursor does not recognise this query: {sql}")

    # -- generic per-table handlers -----------------------------------

    def _maybe_handle_table_query(self, table_name, normalized, params):
        table_key = table_name.upper()
        rows = self.db.tables[table_name]

        if normalized.startswith(f"DELETE FROM {table_key} WHERE"):
            cutoff = params[0]
            time_col = "occurred_at" if "occurred_at" in _row_columns(table_name) else "created_at"
            with self.db._lock:
                self.db.tables[table_name] = [
                    r for r in rows if _as_dt(r[time_col]) >= _as_dt(cutoff)
                ]
            return True

        if normalized.startswith(f"SELECT OCCURRED_AT FROM {table_key} WHERE") and "ORDER BY" in normalized:
            username, window_start = params
            with self.db._lock:
                matches = [
                    r for r in rows
                    if r["username"] == username and _as_dt(r["occurred_at"]) >= _as_dt(window_start)
                ]
            matches.sort(key=lambda r: _as_dt(r["occurred_at"]), reverse=True)
            self._result = ("many", [(r["occurred_at"],) for r in matches])
            return True

        if normalized.startswith(f"SELECT COUNT(*) FROM {table_key} WHERE"):
            user_col = "user_name" if table_name != "login_failure_log" else "username"
            user_name, window_start = params
            with self.db._lock:
                count = sum(
                    1 for r in self.db.tables[table_name]
                    if r[user_col] == user_name and _as_dt(r["occurred_at"]) >= _as_dt(window_start)
                )
            self._result = ("one", (count,))
            return True

        if normalized.startswith(f"INSERT INTO {table_key} (") and table_name != "idempotent_requests":
            cols = _insert_columns(table_name)
            with self.db._lock:
                self.db.tables[table_name].append(dict(zip(cols, params)))
            self.rowcount = 1
            return True

        if table_name == "idempotent_requests":
            return self._handle_idempotent_requests(normalized, params)

        return False

    def _handle_idempotent_requests(self, normalized, params):
        rows = self.db.tables["idempotent_requests"]

        if normalized.startswith("INSERT INTO IDEMPOTENT_REQUESTS"):
            request_id, kind, created_at = params
            with self.db._lock:
                if any(r["request_id"] == request_id for r in rows):
                    self.rowcount = 0  # ON CONFLICT (request_id) DO NOTHING
                else:
                    rows.append({
                        "request_id": request_id,
                        "kind": kind,
                        "status": "in_progress",
                        "created_at": created_at,
                        "completed_at": None,
                    })
                    self.rowcount = 1
            return True

        if normalized.startswith("SELECT STATUS FROM IDEMPOTENT_REQUESTS"):
            (request_id,) = params
            with self.db._lock:
                match = next((r for r in rows if r["request_id"] == request_id), None)
            self._result = ("one", (match["status"],) if match else None)
            return True

        if normalized.startswith("UPDATE IDEMPOTENT_REQUESTS SET STATUS = 'COMPLETED'"):
            completed_at, request_id = params
            with self.db._lock:
                for r in rows:
                    if r["request_id"] == request_id:
                        r["status"] = "completed"
                        r["completed_at"] = completed_at
            return True

        if normalized.startswith("DELETE FROM IDEMPOTENT_REQUESTS WHERE REQUEST_ID"):
            (request_id,) = params
            with self.db._lock:
                self.db.tables["idempotent_requests"] = [
                    r for r in rows if r["request_id"] != request_id
                ]
            return True

        if normalized.startswith("DELETE FROM IDEMPOTENT_REQUESTS WHERE CREATED_AT"):
            cutoff = params[0]
            with self.db._lock:
                self.db.tables["idempotent_requests"] = [
                    r for r in rows if _as_dt(r["created_at"]) >= _as_dt(cutoff)
                ]
            return True

        return False

    def fetchone(self):
        kind, value = self._result
        assert kind == "one"
        return value

    def fetchall(self):
        kind, value = self._result
        assert kind == "many"
        return value


def _row_columns(table_name):
    return {
        "reflection_rate_log": ("user_name", "occurred_at"),
        "ka_rate_log": ("user_name", "occurred_at"),
        "login_failure_log": ("username", "occurred_at"),
    }.get(table_name, ())


def _insert_columns(table_name):
    return _row_columns(table_name)


def _as_dt(value):
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    return datetime.fromisoformat(str(value))


class _FakeConnectionInfo:
    """
    psycopg2.pool.AbstractConnectionPool._putconn (real, unmodified code)
    checks conn.info.transaction_status to decide whether a returned
    connection is safe to reuse as-is. Our fake connections always
    finish a transaction via commit()/rollback() (mirrored in
    FakeConnection.commit/rollback below), so they are always idle by
    the time they're returned to the pool.
    """

    @property
    def transaction_status(self):
        import psycopg2.extensions as _ext
        return _ext.TRANSACTION_STATUS_IDLE


class FakeConnection:
    """Stand-in for a single psycopg2 connection, backed by a FakeDatabase."""

    def __init__(self, db: FakeDatabase):
        self.db = db
        self.closed = 0
        self.info = _FakeConnectionInfo()
        self._held_advisory_locks = []

    def cursor(self):
        return FakeCursor(self)

    def commit(self):
        self._release_advisory_locks()

    def rollback(self):
        self._release_advisory_locks()

    def _release_advisory_locks(self):
        for lock in self._held_advisory_locks:
            if lock.locked():
                lock.release()
        self._held_advisory_locks = []

    def close(self):
        # Real advisory-transaction locks release automatically at the
        # end of a session even without an explicit commit/rollback --
        # mirror that so a bug elsewhere can never deadlock the fake DB.
        self._release_advisory_locks()
        self.closed = 1


# ---------------------------------------------------------------------------
# Fake Claude client
# ---------------------------------------------------------------------------

class _FakeTextBlock:
    def __init__(self, text):
        self.type = "text"
        self.text = text


class _FakeMessage:
    def __init__(self, text, stop_reason="end_turn"):
        self.content = [_FakeTextBlock(text)]
        self.stop_reason = stop_reason


class FakeAnthropicMessages:
    """
    Drop-in replacement for `client.messages` used by
    services/reflection_service.py. Never makes a network call and
    never spends a real API credit.

    latency_seconds: simulated per-call response time (a real companion
    call in production typically takes a few seconds; default here is
    deliberately configurable so a load test can explore both "AI is
    fast today" and "AI is slow/degraded" conditions -- see Area 1's
    "external dependency degradation" requirement).

    failure_rate: fraction (0.0-1.0) of calls that raise an exception
    instead of responding, to exercise rdi/orchestrator.py's real
    per-companion retry logic under load.
    """

    def __init__(self, latency_seconds=1.5, failure_rate=0.0, timeout_rate=0.0):
        self.latency_seconds = latency_seconds
        self.failure_rate = failure_rate
        self.timeout_rate = timeout_rate
        self._call_count = 0
        self._lock = threading.Lock()

    def create(self, **kwargs):
        with self._lock:
            self._call_count += 1
            n = self._call_count

        time.sleep(self.latency_seconds)

        # Deterministic pseudo-randomness (based on call order) so a
        # given load-test run is reproducible rather than flaky.
        if self.timeout_rate and (n % max(1, round(1 / self.timeout_rate))) == 0:
            raise TimeoutError("Simulated Claude API timeout (load test)")

        if self.failure_rate and (n % max(1, round(1 / self.failure_rate))) == 0:
            raise Exception("Simulated Claude API error (load test)")

        return _FakeMessage(
            '{"observation": "Simulated observation for load testing.", '
            '"questions": ["Simulated reflective question?"]}'
        )
