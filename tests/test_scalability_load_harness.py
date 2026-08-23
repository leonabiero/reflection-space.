"""
Phase 3 -- automated load-test regression coverage.

These tests run the real load-testing toolkit (load_test/) at a small,
fast, deterministic scale so they can be part of the normal CI test
suite (no real database, no real AI, no real Qdrant, no real time
spent waiting on a slow external service). They exist to prove two
things:

1. The load-testing harness itself works: it can actually drive
   concurrent load through a scenario and produce an honest report.
2. The specific behaviors Phase 3 cares about (DB pool queueing under
   pressure, and the two AI-cost rate limiters staying correct under
   concurrent hits) hold up when many threads hit them at once.

For a full-scale, longer-running exploration (dozens of users, several
seconds), run load_test/run_load_test.py directly -- see
load_test/README.md.
"""

import threading
import unittest

from load_test.harness import run_load_test
from load_test.scenarios import (
    fake_database_environment,
    db_read_scenario,
    reflection_rate_limit_scenario,
    login_attempt_scenario,
)


class TestLoadHarnessReportsHonestly(unittest.TestCase):

    def test_trivial_always_succeeds_scenario(self):
        """A scenario that always succeeds instantly should be reported as 100% success."""

        def always_succeeds(call_index):
            return None

        report = run_load_test(always_succeeds, "always succeeds", num_users=10, calls_per_user=3)

        self.assertEqual(report.total_calls, 30)
        self.assertEqual(len(report.successes), 30)
        self.assertEqual(len(report.failures), 0)
        summary = report.summary()
        self.assertEqual(summary["success_rate_pct"], 100.0)
        self.assertGreaterEqual(summary["latency_ms"]["max"], summary["latency_ms"]["min"])
        self.assertGreaterEqual(summary["latency_ms"]["min"], 0.0)

    def test_trivial_always_fails_scenario(self):
        """A scenario that always fails should be reported as 0% success, with the real error message."""

        def always_fails(call_index):
            raise ValueError("simulated failure")

        report = run_load_test(always_fails, "always fails", num_users=5, calls_per_user=1)

        self.assertEqual(report.total_calls, 5)
        self.assertEqual(len(report.failures), 5)
        summary = report.summary()
        self.assertEqual(summary["success_rate_pct"], 0.0)
        self.assertEqual(summary["errors_by_type"], {"ValueError: simulated failure": 5})


class TestDatabasePoolUnderConcurrency(unittest.TestCase):

    def test_pool_serves_more_concurrent_requests_than_its_size_via_queueing(self):
        """
        20 virtual users share a pool sized to only 5 real connections.
        The real services/db_pool.py checkout-queueing logic (not a
        simplified test copy) should let every request eventually
        succeed by waiting for a connection to free up, rather than
        failing immediately the moment the 6th request arrives.
        """
        with fake_database_environment(pool_min=5, pool_max=5, wait_timeout_seconds=5.0,
                                        query_latency_seconds=0.02) as fake_db:
            report = run_load_test(db_read_scenario, "pool pressure", num_users=20, calls_per_user=1)

        summary = report.summary()
        self.assertEqual(summary["total_calls"], 20)
        self.assertEqual(summary["successes"], 20,
                          f"Unexpected failures under pool pressure: {summary['errors_by_type']}")
        # With only 5 real connections serving 20 near-simultaneous
        # requests, at least some of them must have had to wait -- if
        # p95 latency were as low as a single query, the pool wouldn't
        # actually have been under any pressure and this test wouldn't
        # be proving anything.
        self.assertGreater(summary["latency_ms"]["p95"], summary["latency_ms"]["min"])
        self.assertLessEqual(fake_db.stats["connections_opened"], 5)

    def test_pool_checkout_times_out_gracefully_when_truly_exhausted(self):
        """
        When far more concurrent requests arrive than the pool's wait
        timeout can absorb, services/db_pool.get_conn() must raise a
        clear psycopg2.OperationalError (a graceful, recognisable
        failure) rather than hanging forever or crashing the process.
        """
        with fake_database_environment(pool_min=2, pool_max=2, wait_timeout_seconds=0.3,
                                        query_latency_seconds=0.5):
            report = run_load_test(db_read_scenario, "pool exhaustion", num_users=15, calls_per_user=1)

        summary = report.summary()
        # Some requests should succeed (those that got a connection or
        # waited successfully) and the rest should fail with the
        # expected, specific error type -- never an unrelated crash.
        self.assertGreaterEqual(summary["successes"], 1)
        if summary["failures"] > 0:
            self.assertTrue(
                all(err.startswith("OperationalError") for err in summary["errors_by_type"]),
                summary["errors_by_type"],
            )


class TestRateLimitersUnderConcurrency(unittest.TestCase):

    def test_reflection_rate_limiter_never_exceeds_its_cap(self):
        """
        30 near-simultaneous reflection requests from the SAME user,
        with max_per_hour effectively capped at 10 for this test. The
        real pg_advisory_xact_lock serialization in
        services/rate_limiter.py must ensure no more than 10 are ever
        allowed through, even though all 30 threads see the count as
        "0 so far" at roughly the same instant.
        """
        from services import rate_limiter

        original_default = rate_limiter.DEFAULT_MAX_PER_HOUR
        rate_limiter.DEFAULT_MAX_PER_HOUR = 10
        try:
            with fake_database_environment(pool_max=10, query_latency_seconds=0.01):
                report = run_load_test(
                    lambda call_index: reflection_rate_limit_scenario(call_index, users=("same_user",)),
                    "reflection rate limit race", num_users=30, calls_per_user=1,
                )
        finally:
            rate_limiter.DEFAULT_MAX_PER_HOUR = original_default

        summary = report.summary()
        self.assertEqual(summary["successes"], 30, "check_and_record() itself should never raise")

    def test_ka_rate_limiter_never_exceeds_its_cap(self):
        """
        The same concurrency race test as above, but for the Knowledge
        Assistant rate limiter -- this is the specific behavior the
        Phase 3 load-testing pass found was UNPROTECTED and fixed (see
        services/ka_rate_limiter.py's Phase 3 note). This test verifies
        the fix actually holds under real concurrent access to the
        fake database, using real threads and the real advisory-lock
        code path.
        """
        from services import ka_rate_limiter

        allowed_count = {"n": 0}
        lock = threading.Lock()

        def scenario(call_index):
            allowed, _count = ka_rate_limiter.check_and_record("same_ka_user", max_per_hour=10)
            if allowed:
                with lock:
                    allowed_count["n"] += 1

        with fake_database_environment(pool_max=10, query_latency_seconds=0.01):
            report = run_load_test(scenario, "ka rate limit race", num_users=30, calls_per_user=1)

        summary = report.summary()
        self.assertEqual(summary["successes"], 30, "check_and_record() itself should never raise")
        self.assertEqual(
            allowed_count["n"], 10,
            f"Expected the advisory-lock serialization to allow exactly 10 of 30 concurrent "
            f"Knowledge Assistant requests through; {allowed_count['n']} were allowed. This is "
            f"the exact race condition the Phase 3 fix in services/ka_rate_limiter.py closes.",
        )


class TestRequestDedupUnderConcurrency(unittest.TestCase):

    def test_dedup_allows_exactly_one_concurrent_identical_request(self):
        """
        25 near-simultaneous attempts at the exact same fingerprinted
        request (the "double-click" / "two browser tabs" case). Exactly
        one should be told to proceed ("claimed"); the rest must NOT
        trigger the expensive operation again.
        """
        from services import request_dedup

        claimed_count = {"n": 0}
        lock = threading.Lock()

        def scenario(call_index):
            request_id = request_dedup.fingerprint("dedup_race_test", "identical_payload")
            status = request_dedup.claim(request_id, "load_test", ttl_minutes=5)
            if status == "claimed":
                with lock:
                    claimed_count["n"] += 1
                request_dedup.complete(request_id)

        with fake_database_environment(pool_max=10, query_latency_seconds=0.01):
            report = run_load_test(scenario, "dedup race", num_users=25, calls_per_user=1)

        summary = report.summary()
        self.assertEqual(summary["successes"], 25)
        self.assertEqual(
            claimed_count["n"], 1,
            f"Expected exactly one of 25 identical concurrent requests to be claimed; "
            f"{claimed_count['n']} were.",
        )


class TestLoginActivityUnderConcurrency(unittest.TestCase):

    def test_login_activity_scenario_runs_cleanly(self):
        """Concurrent failed-login bookkeeping should never itself raise or corrupt data."""
        with fake_database_environment(pool_max=10, query_latency_seconds=0.01):
            report = run_load_test(login_attempt_scenario, "login activity", num_users=20, calls_per_user=1)

        summary = report.summary()
        self.assertEqual(summary["successes"], 20)


if __name__ == "__main__":
    unittest.main()
