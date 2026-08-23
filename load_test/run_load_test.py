"""
Run a Phase 3 load test from the command line.

SAFE TO RUN ANYTIME: this never contacts a real database, the real
Claude API, or real Qdrant, and never touches production data or
credits -- see load_test/fakes.py for exactly what is faked.

Examples
--------
Simulate 50 practitioners hitting the database pool at once, with the
pool deliberately sized down to 20 (the real production default) so
queueing/contention is visible:

    python -m load_test.run_load_test --scenario db-read --users 50

Simulate 30 practitioners generating reflections at once (real 8-way
companion fan-out, real concurrency semaphore, fake ~1.5s Claude calls):

    python -m load_test.run_load_test --scenario reflection-generation \\
        --users 30 --max-concurrent-reflections 20 --ai-latency-ms 1500

Run every scenario at a moderate scale, one after another:

    python -m load_test.run_load_test --scenario all --users 30
"""

from __future__ import annotations

import argparse
import os

os.environ.setdefault("DATABASE_URL", "postgresql://fake:fake@localhost/fake")
os.environ.setdefault("ANTHROPIC_API_KEY", "sk-fake-for-load-test")
os.environ.setdefault("GEMINI_API_KEY", "fake-for-load-test")
os.environ.setdefault("QDRANT_URL", "http://localhost:6333")
os.environ.setdefault("QDRANT_API_KEY", "fake")

from load_test.harness import run_load_test
from load_test.scenarios import (
    fake_database_environment,
    fake_ai_environment,
    db_read_scenario,
    reflection_rate_limit_scenario,
    ka_rate_limit_scenario,
    request_dedup_scenario,
    login_attempt_scenario,
    reflection_generation_scenario,
)


def run_db_read(args):
    with fake_database_environment(pool_min=args.pool_max, pool_max=args.pool_max,
                                    wait_timeout_seconds=args.pool_wait_timeout,
                                    query_latency_seconds=args.query_latency_ms / 1000.0) as fake_db:
        report = run_load_test(db_read_scenario, "Database pool -- concurrent reads",
                                num_users=args.users, calls_per_user=args.calls_per_user)
        report.print_report()
        print(f"Fake-DB queries executed: {fake_db.stats['queries_executed']}, "
              f"physical connections opened: {fake_db.stats['connections_opened']} "
              f"(pool size was {args.pool_max})")
    return report


def run_reflection_rate_limit(args):
    with fake_database_environment(pool_max=args.pool_max, query_latency_seconds=args.query_latency_ms / 1000.0):
        report = run_load_test(reflection_rate_limit_scenario,
                                "Reflection rate limiter -- concurrent same-user hits",
                                num_users=args.users, calls_per_user=args.calls_per_user)
        report.print_report()
    return report


def run_ka_rate_limit(args):
    with fake_database_environment(pool_max=args.pool_max, query_latency_seconds=args.query_latency_ms / 1000.0):
        report = run_load_test(ka_rate_limit_scenario,
                                "Knowledge Assistant rate limiter -- concurrent same-user hits",
                                num_users=args.users, calls_per_user=args.calls_per_user)
        report.print_report()
    return report


def run_request_dedup(args):
    with fake_database_environment(pool_max=args.pool_max, query_latency_seconds=args.query_latency_ms / 1000.0):
        report = run_load_test(request_dedup_scenario,
                                "Request deduplication -- simultaneous identical requests",
                                num_users=args.users, calls_per_user=args.calls_per_user)
        report.print_report()
    return report


def run_login(args):
    with fake_database_environment(pool_max=args.pool_max, query_latency_seconds=args.query_latency_ms / 1000.0):
        report = run_load_test(login_attempt_scenario,
                                "Login activity -- concurrent failed attempts",
                                num_users=args.users, calls_per_user=args.calls_per_user)
        report.print_report()
    return report


def run_reflection_generation(args):
    with fake_database_environment(pool_max=args.pool_max, query_latency_seconds=args.query_latency_ms / 1000.0), \
         fake_ai_environment(latency_seconds=args.ai_latency_ms / 1000.0,
                              failure_rate=args.ai_failure_rate,
                              timeout_rate=args.ai_timeout_rate,
                              max_concurrent_reflections=args.max_concurrent_reflections,
                              queue_timeout_seconds=args.queue_timeout_seconds):
        report = run_load_test(reflection_generation_scenario,
                                "Reflection generation -- concurrent full reflections (AI calls faked)",
                                num_users=args.users, calls_per_user=args.calls_per_user)
        report.print_report()
    return report


SCENARIOS = {
    "db-read": run_db_read,
    "reflection-rate": run_reflection_rate_limit,
    "ka-rate": run_ka_rate_limit,
    "dedup": run_request_dedup,
    "login": run_login,
    "reflection-generation": run_reflection_generation,
}


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--scenario", choices=[*SCENARIOS.keys(), "all"], default="all")
    parser.add_argument("--users", type=int, default=30, help="Concurrent virtual practitioners")
    parser.add_argument("--calls-per-user", type=int, default=1)
    parser.add_argument("--pool-max", type=int, default=20, help="Fake DB pool size (production default: 20)")
    parser.add_argument("--pool-wait-timeout", type=float, default=5.0)
    parser.add_argument("--query-latency-ms", type=float, default=3.0,
                         help="Simulated per-query DB round-trip time")
    parser.add_argument("--ai-latency-ms", type=float, default=1500.0,
                         help="Simulated Claude API response time per companion call")
    parser.add_argument("--ai-failure-rate", type=float, default=0.0)
    parser.add_argument("--ai-timeout-rate", type=float, default=0.0)
    parser.add_argument("--max-concurrent-reflections", type=int, default=None,
                         help="Overrides CLAUDE_MAX_CONCURRENT_REFLECTIONS for this run "
                              "(production default: 20)")
    parser.add_argument("--queue-timeout-seconds", type=float, default=None)
    args = parser.parse_args()

    if args.scenario == "all":
        for name, fn in SCENARIOS.items():
            fn(args)
    else:
        SCENARIOS[args.scenario](args)


if __name__ == "__main__":
    main()
