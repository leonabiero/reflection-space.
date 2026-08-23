"""
A small, dependency-free concurrency harness.

It does one job: run a given Python function many times, concurrently,
from many threads (simulating many practitioners clicking at once), and
honestly report what happened -- how long each call took, how many
succeeded, how many failed, and why.

This does NOT talk to any real network service by itself. Whether a
given run is "safe" (no real DB/AI/Qdrant credits used) depends entirely
on what the scenario function it's given actually does -- see
load_test/scenarios.py, which is written to only ever call this
application's real code against the fakes in load_test/fakes.py.
"""

from __future__ import annotations

import statistics
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field


@dataclass
class CallResult:
    success: bool
    duration_ms: float
    error: str | None = None
    detail: dict | None = None


@dataclass
class LoadTestReport:
    scenario_name: str
    num_users: int
    calls_per_user: int
    total_calls: int
    wall_clock_seconds: float
    results: list = field(default_factory=list)

    @property
    def successes(self):
        return [r for r in self.results if r.success]

    @property
    def failures(self):
        return [r for r in self.results if not r.success]

    def _percentile(self, values, pct):
        if not values:
            return 0.0
        values = sorted(values)
        k = (len(values) - 1) * (pct / 100.0)
        f = int(k)
        c = min(f + 1, len(values) - 1)
        if f == c:
            return values[f]
        return values[f] + (values[c] - values[f]) * (k - f)

    def summary(self) -> dict:
        durations = [r.duration_ms for r in self.results]
        error_counts: dict[str, int] = {}
        for r in self.failures:
            key = r.error or "unknown error"
            error_counts[key] = error_counts.get(key, 0) + 1

        return {
            "scenario": self.scenario_name,
            "concurrent_users": self.num_users,
            "calls_per_user": self.calls_per_user,
            "total_calls": self.total_calls,
            "wall_clock_seconds": round(self.wall_clock_seconds, 3),
            "throughput_calls_per_sec": (
                round(self.total_calls / self.wall_clock_seconds, 2)
                if self.wall_clock_seconds > 0 else 0.0
            ),
            "successes": len(self.successes),
            "failures": len(self.failures),
            "success_rate_pct": (
                round(100.0 * len(self.successes) / self.total_calls, 1)
                if self.total_calls else 0.0
            ),
            "latency_ms": {
                "min": round(min(durations), 1) if durations else 0.0,
                "mean": round(statistics.fmean(durations), 1) if durations else 0.0,
                "p50": round(self._percentile(durations, 50), 1),
                "p95": round(self._percentile(durations, 95), 1),
                "p99": round(self._percentile(durations, 99), 1),
                "max": round(max(durations), 1) if durations else 0.0,
            },
            "errors_by_type": error_counts,
        }

    def print_report(self):
        s = self.summary()
        print(f"\n=== Load test: {s['scenario']} ===")
        print(f"Concurrent virtual users : {s['concurrent_users']}")
        print(f"Calls per user           : {s['calls_per_user']}")
        print(f"Total calls              : {s['total_calls']}")
        print(f"Wall-clock time          : {s['wall_clock_seconds']}s")
        print(f"Throughput               : {s['throughput_calls_per_sec']} calls/sec")
        print(f"Successes / Failures     : {s['successes']} / {s['failures']} "
              f"({s['success_rate_pct']}% success)")
        lat = s["latency_ms"]
        print(f"Latency ms (min/mean/p50/p95/p99/max): "
              f"{lat['min']}/{lat['mean']}/{lat['p50']}/{lat['p95']}/{lat['p99']}/{lat['max']}")
        if s["errors_by_type"]:
            print("Errors observed:")
            for err, count in sorted(s["errors_by_type"].items(), key=lambda kv: -kv[1]):
                print(f"  - {count}x {err}")


def run_load_test(
    scenario_fn,
    scenario_name: str,
    num_users: int,
    calls_per_user: int = 1,
    ramp_up_seconds: float = 0.0,
) -> LoadTestReport:
    """
    Run `scenario_fn(call_index)` concurrently, simulating `num_users`
    virtual practitioners, each making `calls_per_user` calls.

    `scenario_fn` must be a zero-or-one-argument callable that performs
    ONE unit of realistic work (e.g. "acquire a DB connection and run a
    typical query", or "generate one reflection") and either returns
    normally (counted as success) or raises (counted as failure, with
    the exception's message recorded).

    `ramp_up_seconds`, if given, staggers virtual-user start times
    evenly across that window instead of firing all of them at the
    exact same instant -- closer to how real traffic actually arrives,
    while still reaching full concurrency well within the run.
    """
    total_calls = num_users * calls_per_user
    results: list[CallResult] = []
    results_lock = threading.Lock()

    def _one_call(call_index: int):
        started = time.monotonic()
        try:
            scenario_fn(call_index)
            duration_ms = (time.monotonic() - started) * 1000.0
            result = CallResult(success=True, duration_ms=duration_ms)
        except Exception as exc:  # noqa: BLE001 -- intentionally broad: we want every failure counted
            duration_ms = (time.monotonic() - started) * 1000.0
            result = CallResult(
                success=False,
                duration_ms=duration_ms,
                error=f"{type(exc).__name__}: {exc}",
            )
        with results_lock:
            results.append(result)

    def _one_user(user_index: int):
        if ramp_up_seconds:
            time.sleep(ramp_up_seconds * user_index / max(1, num_users))
        for c in range(calls_per_user):
            _one_call(user_index * calls_per_user + c)

    wall_started = time.monotonic()
    with ThreadPoolExecutor(max_workers=num_users) as executor:
        futures = [executor.submit(_one_user, u) for u in range(num_users)]
        for f in as_completed(futures):
            f.result()  # re-raise any bug in the harness itself (not the scenario)
    wall_clock_seconds = time.monotonic() - wall_started

    return LoadTestReport(
        scenario_name=scenario_name,
        num_users=num_users,
        calls_per_user=calls_per_user,
        total_calls=total_calls,
        wall_clock_seconds=wall_clock_seconds,
        results=results,
    )
