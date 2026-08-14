"""
common.py
=========

Shared building blocks used by every test in this folder. Plain-
English summary of what's in here:

- SYNTHETIC_PREFIX: every fake case/user this toolkit ever creates is
  named starting with "LOADTEST_" so it's always 100% obvious which
  records are test data, and cleanup_synthetic_data.py knows exactly
  what it's allowed to delete.

- timed_with_timeout(): runs one action (e.g. "save a draft"), times
  how long it takes, and gives up after a set number of seconds if it
  never finishes -- so one stuck action can't freeze the whole test
  forever. (This is the same safety wrapper used in the earlier data-
  volume testing, after we found a real call could hang with no
  timeout of its own.)

- mock_generate_reflection() / mock_knowledge_assistant_ask(): stand-
  ins for the two actions that would otherwise cost real money by
  calling Claude. They return instantly with a small fake response,
  so this test measures how the REST of the app behaves under load
  without spending anything on the AI itself.

- Metrics: a simple results tracker. Every action in the test calls
  metrics.record(...) once it's done, and at the end
  metrics.print_summary() prints a clear table of what happened.
"""

import concurrent.futures
import statistics
import time
import threading
import random
import string

SYNTHETIC_PREFIX = "LOADTEST_"
SYNTHETIC_USER_PREFIX = "LoadTestUser_"


def synthetic_case_ref(user_index: int, run_id: str) -> str:
    """A fake case reference, unmistakably tagged as test data."""
    return f"{SYNTHETIC_PREFIX}{run_id}_case{user_index}"


def synthetic_user_name(user_index: int, run_id: str) -> str:
    """A fake practitioner name, unmistakably tagged as test data."""
    return f"{SYNTHETIC_USER_PREFIX}{run_id}_{user_index}"


def new_run_id() -> str:
    """
    A short random tag identifying this particular test run, so if
    you run the test twice in a row without cleaning up in between,
    the two runs' fake data never gets mixed up.
    """
    return "".join(random.choices(string.ascii_lowercase + string.digits, k=6))


def random_note_text() -> str:
    """
    Realistic-length filler text for a fake reflective note -- long
    enough to behave like a real entry (for embedding/indexing), but
    obviously placeholder content.
    """
    filler = (
        "Nota de práctica reflexiva generada automáticamente para pruebas "
        "de carga (LOADTEST). Este contenido es ficticio y no corresponde "
        "a ninguna persona real. Se utiliza únicamente para verificar el "
        "comportamiento del sistema bajo actividad simultánea."
    )
    return filler


# ---------------------------------------------------------------------
# Timeout-protected timing wrapper
# ---------------------------------------------------------------------

def timed_with_timeout(fn, *args, timeout=30, **kwargs):
    """
    Runs fn(*args, **kwargs) on a background thread, with a hard time
    limit.

    Returns a dict:
        {
            "elapsed": seconds (float) -- how long it actually took,
            "result": whatever fn returned (None if it failed/timed out),
            "success": True/False,
            "timed_out": True/False,
            "error": the error message, or "" if it succeeded,
        }

    Why: some of the real functions we're calling (anything touching
    Gemini) were found, in earlier testing, to occasionally hang with
    no time limit of their own. This wrapper guarantees the test
    itself never gets stuck, even if one single call does.
    """
    result_box = {"result": None, "error": None}

    def _runner():
        try:
            result_box["result"] = fn(*args, **kwargs)
        except Exception as e:
            result_box["error"] = str(e)

    start = time.monotonic()
    thread = threading.Thread(target=_runner, daemon=True)
    thread.start()
    thread.join(timeout=timeout)
    elapsed = time.monotonic() - start

    if thread.is_alive():
        # Still running after the timeout -- we give up waiting for it,
        # but note that the underlying action may still finish in the
        # background eventually; we just stop timing/counting on it.
        return {
            "elapsed": elapsed,
            "result": None,
            "success": False,
            "timed_out": True,
            "error": f"Timed out after {timeout}s (no response in time)",
        }

    if result_box["error"] is not None:
        return {
            "elapsed": elapsed,
            "result": None,
            "success": False,
            "timed_out": False,
            "error": result_box["error"],
        }

    return {
        "elapsed": elapsed,
        "result": result_box["result"],
        "success": True,
        "timed_out": False,
        "error": "",
    }


# ---------------------------------------------------------------------
# Mocked (fake, $0 cost) stand-ins for the two Claude-calling actions
# ---------------------------------------------------------------------

def mock_generate_reflection(_text, lang="Español"):
    """
    Stands in for rdi/orchestrator.py's real reflection generation
    (which makes 8 real Claude calls per reflection). Sleeps briefly
    to behave like a real, fast network call, then returns a small
    fake result. Never calls Claude -- $0 cost.
    """
    time.sleep(random.uniform(0.05, 0.2))
    return {"mocked": True, "companions_generated": 8, "language": lang}


def mock_knowledge_assistant_ask(_question, lang="Español"):
    """
    Stands in for services/knowledge_assistant.py's real ask()
    (which makes one real Claude call). Same idea as above -- $0 cost.
    """
    time.sleep(random.uniform(0.05, 0.2))
    return {
        "answer": "[MOCKED RESPONSE -- no real Claude call made during this test]",
        "confidence": "strong",
        "limitations": "",
        "evidence": [],
        "evidence_count": 0,
    }


# ---------------------------------------------------------------------
# Results tracking
# ---------------------------------------------------------------------

class Metrics:
    """
    Collects one entry per action performed during the test, then
    produces a clear plain-English summary at the end.

    Thread-safe: many simulated users record results at the same time
    from different threads.
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._entries = []  # list of dicts

    def record(self, action, elapsed, success, timed_out=False, error=""):
        with self._lock:
            self._entries.append({
                "action": action,
                "elapsed": elapsed,
                "success": success,
                "timed_out": timed_out,
                "error": error,
            })

    def all_entries(self):
        with self._lock:
            return list(self._entries)

    def summary_by_action(self):
        """
        Returns {action_name: {count, successes, failures, timeouts,
        avg, median, p95, min, max}}
        """
        by_action = {}
        for e in self.all_entries():
            by_action.setdefault(e["action"], []).append(e)

        out = {}
        for action, entries in by_action.items():
            times = [e["elapsed"] for e in entries]
            successes = sum(1 for e in entries if e["success"])
            timeouts = sum(1 for e in entries if e["timed_out"])
            failures = len(entries) - successes
            times_sorted = sorted(times)
            p95_index = max(0, int(len(times_sorted) * 0.95) - 1)
            out[action] = {
                "count": len(entries),
                "successes": successes,
                "failures": failures,
                "timeouts": timeouts,
                "avg": statistics.mean(times) if times else 0.0,
                "median": statistics.median(times) if times else 0.0,
                "p95": times_sorted[p95_index] if times_sorted else 0.0,
                "min": min(times) if times else 0.0,
                "max": max(times) if times else 0.0,
            }
        return out

    def print_summary(self, thresholds=None):
        """
        Prints a plain-English table. `thresholds` is an optional dict
        like {"save_draft": {"pass": 3.0, "warn": 8.0}} giving, per
        action, the boundary (in seconds, based on the action's
        AVERAGE time) between PASS / WARNING / FAIL. Any action not
        listed in thresholds is shown with no verdict.
        """
        thresholds = thresholds or {}
        summary = self.summary_by_action()
        print("\n" + "=" * 78)
        print("RESULTS SUMMARY")
        print("=" * 78)
        for action, s in sorted(summary.items()):
            verdict = "(no threshold set)"
            if action in thresholds:
                t = thresholds[action]
                if s["failures"] > 0 or s["avg"] > t["warn"]:
                    verdict = "FAIL"
                elif s["avg"] > t["pass"]:
                    verdict = "WARNING"
                else:
                    verdict = "PASS"
            print(f"\n  Action: {action}")
            print(f"    Attempts: {s['count']}  |  Succeeded: {s['successes']}  |  "
                  f"Failed: {s['failures']}  |  Timed out: {s['timeouts']}")
            print(f"    Time (seconds) -- avg: {s['avg']:.2f}  median: {s['median']:.2f}  "
                  f"p95: {s['p95']:.2f}  min: {s['min']:.2f}  max: {s['max']:.2f}")
            print(f"    Verdict: {verdict}")

            # Show up to 3 example error messages so a failure pattern
            # is visible at a glance without reading the raw log.
            errors = [e["error"] for e in self.all_entries()
                      if e["action"] == action and e["error"]]
            if errors:
                print(f"    Example error(s): {errors[:3]}")
        print("\n" + "=" * 78 + "\n")
