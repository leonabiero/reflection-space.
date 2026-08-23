"""
Realistic concurrent-usage scenarios for Phase 3 load testing.

Every scenario function below calls this application's REAL code
(services/db_pool.py, services/rate_limiter.py,
services/ka_rate_limiter.py, services/request_dedup.py,
services/login_rate_limiter.py, rdi/orchestrator.py). Nothing here
re-implements or simplifies that logic -- the whole point is to find
out how the actual production code behaves under concurrency.

The two context managers below (`fake_database_environment` and
`fake_ai_environment`) are the ONLY place real infrastructure is
swapped out, and they only ever swap in the safe fakes from
load_test/fakes.py. Both restore everything they changed when the
`with` block exits, so running a load test can never leave the rest of
the test suite (or, if this were ever run outside a controlled
environment, the real app) in a different state than before.
"""

from __future__ import annotations

import threading
from contextlib import contextmanager
from datetime import datetime, timezone
from unittest.mock import patch

from load_test.fakes import FakeDatabase, FakeAnthropicMessages


@contextmanager
def fake_database_environment(pool_min=5, pool_max=20, wait_timeout_seconds=5.0,
                               query_latency_seconds=0.003):
    """
    Point services/db_pool.py at an in-memory FakeDatabase instead of a
    real PostgreSQL server, and optionally resize the pool for this run
    (e.g. a small pool_max to deliberately provoke queueing/contention
    at a manageable number of virtual users).

    Real, unmodified code being exercised: services/db_pool.py's
    ThreadedConnectionPool, pre-warming, health-checking, checkout
    queueing/timeout, and every services/*.py module that calls
    services.db_pool.get_conn().
    """
    import psycopg2
    from services import db_pool

    fake_db = FakeDatabase(query_latency_seconds=query_latency_seconds)

    original_pool = db_pool._pool
    original_min = db_pool.DB_POOL_MIN_CONN
    original_max = db_pool.DB_POOL_MAX_CONN
    original_wait = db_pool.DB_POOL_WAIT_TIMEOUT_SECONDS
    original_verified = dict(db_pool._last_verified_at)

    db_pool._pool = None
    db_pool.DB_POOL_MIN_CONN = pool_min
    db_pool.DB_POOL_MAX_CONN = pool_max
    db_pool.DB_POOL_WAIT_TIMEOUT_SECONDS = wait_timeout_seconds
    db_pool._last_verified_at.clear()

    with patch.object(psycopg2, "connect", lambda *a, **kw: fake_db.connect()):
        try:
            yield fake_db
        finally:
            # Return every connection this run opened so nothing is
            # left "checked out" for the next test/run.
            try:
                if db_pool._pool is not None:
                    db_pool._pool.closeall()
            except Exception:
                pass
            db_pool._pool = original_pool
            db_pool.DB_POOL_MIN_CONN = original_min
            db_pool.DB_POOL_MAX_CONN = original_max
            db_pool.DB_POOL_WAIT_TIMEOUT_SECONDS = original_wait
            db_pool._last_verified_at.clear()
            db_pool._last_verified_at.update(original_verified)


@contextmanager
def fake_ai_environment(latency_seconds=1.5, failure_rate=0.0, timeout_rate=0.0,
                         max_concurrent_reflections=None, queue_timeout_seconds=None):
    """
    Point services/reflection_service.py's Claude client at a fake that
    never makes a network call or spends a real API credit, and
    optionally resize rdi/orchestrator.py's concurrency semaphore /
    queue timeout for this run.

    Real, unmodified code being exercised: rdi/orchestrator.py's
    per-reflection concurrency semaphore, its 8-way parallel companion
    fan-out, and its per-companion retry logic.
    """
    from services import reflection_service
    from rdi import orchestrator

    fake_messages = FakeAnthropicMessages(
        latency_seconds=latency_seconds,
        failure_rate=failure_rate,
        timeout_rate=timeout_rate,
    )

    original_messages = reflection_service.client.messages
    original_semaphore = orchestrator._reflection_semaphore
    original_queue_timeout = orchestrator.CLAUDE_REFLECTION_QUEUE_TIMEOUT_SECONDS

    reflection_service.client.messages = fake_messages
    if max_concurrent_reflections is not None:
        orchestrator._reflection_semaphore = threading.Semaphore(max_concurrent_reflections)
    if queue_timeout_seconds is not None:
        orchestrator.CLAUDE_REFLECTION_QUEUE_TIMEOUT_SECONDS = queue_timeout_seconds

    try:
        yield fake_messages
    finally:
        reflection_service.client.messages = original_messages
        orchestrator._reflection_semaphore = original_semaphore
        orchestrator.CLAUDE_REFLECTION_QUEUE_TIMEOUT_SECONDS = original_queue_timeout


# ---------------------------------------------------------------------------
# Scenario functions -- one unit of realistic work each
# ---------------------------------------------------------------------------

def db_read_scenario(call_index: int):
    """One practitioner-triggered database round trip (real db_pool.get_conn())."""
    from services.db_pool import get_conn

    conn = get_conn()
    try:
        with conn.cursor() as c:
            c.execute("SELECT 1")
            c.fetchone()
    finally:
        conn.close()


def reflection_rate_limit_scenario(call_index: int, users=("wave_user_1", "wave_user_2", "wave_user_3")):
    """
    Many practitioners generating reflections at once, all funnelled
    through services.rate_limiter.check_and_record() -- the real
    per-user cost-safety cap, including its pg_advisory_xact_lock
    serialization.
    """
    from services import rate_limiter

    user_name = users[call_index % len(users)]
    rate_limiter.check_and_record(user_name, max_per_hour=rate_limiter.DEFAULT_MAX_PER_HOUR)


def ka_rate_limit_scenario(call_index: int, users=("wave_user_1", "wave_user_2", "wave_user_3")):
    """Same idea as above, for the Knowledge Assistant's rate limiter."""
    from services import ka_rate_limiter

    user_name = users[call_index % len(users)]
    ka_rate_limiter.check_and_record(user_name, max_per_hour=30)


def request_dedup_scenario(call_index: int, shared_fingerprint: bool = True):
    """
    Simulates the classic "double-click" / "two browser tabs" case:
    several near-simultaneous attempts at what should count as the SAME
    request. With shared_fingerprint=True every call in the run
    fingerprints identically, so a correct implementation should let
    exactly ONE of them proceed.
    """
    from services import request_dedup

    request_id = (
        request_dedup.fingerprint("load_test", "same_request")
        if shared_fingerprint
        else request_dedup.fingerprint("load_test", f"request_{call_index}")
    )
    status = request_dedup.claim(request_id, "load_test", ttl_minutes=5)
    if status == "claimed":
        request_dedup.complete(request_id)


def login_attempt_scenario(call_index: int, username="wave_login_user"):
    """Concurrent failed login attempts against the real lockout check."""
    from services import login_rate_limiter

    login_rate_limiter.is_locked_out(username)
    login_rate_limiter.record_failed_attempt(username)


def reflection_generation_scenario(call_index: int):
    """
    A full, realistic reflection generation: real semaphore, real 8-way
    companion fan-out, real retry logic -- only the Claude API call
    itself is faked (see fake_ai_environment).
    """
    from rdi.orchestrator import run_reflection

    sample_text = (
        "Practitioner case note used only for load testing: client "
        "reported feeling unheard during the last home visit."
    )
    result = run_reflection(sample_text, lang="English")
    if "error" in result:
        raise RuntimeError(result.get("friendly_message") or result.get("error"))
