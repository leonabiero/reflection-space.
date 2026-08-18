"""
phase3_concurrent_users.py
============================

WHAT THIS SCRIPT DOES (plain English)

This is "Phase 3" load testing: instead of a realistic MIX of actions
spread out over time (that's confirmation_test_a.py), this script asks
two sharper questions, each with a burst of users hitting the exact
same thing at the exact same instant:

  SCENARIO A -- "What happens to the database when a burst of
  practitioners all open a case / check history at once?"

  SCENARIO B -- "What happens to Claude reflection generation when a
  burst of practitioners all click Generate at once?"

Both scenarios use a `threading.Barrier`, which is a synchronization
gate: every simulated user gets ready, then WAITS at the gate, and the
gate only opens once every single one of them is ready -- so they
truly all start at the same instant, instead of trickling in one after
another the way a normal loop would. This is what makes it a genuine
"burst" test rather than a "steady trickle" test.

--------------------------------------------------------------------
SCENARIO A -- Database connection pool under concurrent reads
--------------------------------------------------------------------

Simulates N practitioners all pulling up their dashboard / opening a
case / asking the Knowledge Assistant a question, at the exact same
moment. Every one of the three actions below is 100% REAL -- nothing
is faked or skipped:

  1. get_completed_drafts()        -- Case History page load
  2. retrieve_historical_context() -- opening a case (a real Gemini
                                       query-embedding + a real Qdrant
                                       search)
  3. retrieve_global_context()     -- Knowledge Assistant search (same)

This deliberately makes small, real, cheap Gemini query-embedding
calls (embedding a short search phrase, not generating text) -- that
cost is expected and accepted. It makes ZERO Claude calls.

Before the burst starts, this script quietly creates a small, fixed
pool of fake ("LOADTEST_") cases with real completed, indexed
documents to read during the burst -- otherwise every user would be
searching an empty case with nothing to find, which wouldn't tell us
anything real. This setup happens ONCE, not once per concurrency
level, so the cost stays small and constant no matter how high the
sweep goes.

--------------------------------------------------------------------
SCENARIO B -- Claude reflection-generation concurrency limiter
--------------------------------------------------------------------

Your app gates every reflection generation through one shared "traffic
light" (a `threading.Semaphore` in rdi/orchestrator.py) so that, at
your pilot's scale, hundreds of practitioners clicking Generate at
once can never turn into hundreds x 8 simultaneous real Claude calls.
This scenario tests THAT traffic light for real, under a genuine burst
-- WITHOUT spending money on real Claude calls.

How that's possible: this script temporarily swaps out (and, when it's
done, puts back exactly as it was) only the one small function that
actually talks to Claude for a single reflection-dimension
(`generate_companion_reflection`, inside rdi/orchestrator.py). In its
place, for the duration of this test only, it substitutes a fake
stand-in that sleeps for a fraction of a second (to behave like a
quick real network call) and returns a small, valid fake answer --
never contacting Anthropic. This is called "monkeypatching": swapping
one function out at runtime, then swapping the real one back the
moment the test ends (even if the test crashes -- a `finally` block
guarantees the swap-back always happens).

Everything else -- the traffic-light semaphore itself, the real
8-way-parallel fan-out, the real retry logic, the real queue-timeout
behavior -- is the REAL, completely unmodified code from
rdi/orchestrator.py. This scenario is testing the traffic light, not
the fake answers behind it.

--------------------------------------------------------------------
SAFETY / COST GUARANTEES
--------------------------------------------------------------------

- Every fake case/document this script creates is tagged "LOADTEST_"
  (the same convention as confirmation_test_a.py), so it's always
  100% obvious which records are test data, and it's automatically
  deleted at the end unless you pass --no-cleanup.
- $0 in real Claude/Anthropic API calls, guaranteed -- Scenario A
  never touches Claude at all, and Scenario B never calls the real
  Claude-calling function during the test.
- Small, real Gemini query-embedding costs happen only in Scenario A
  (this is expected and accepted -- see above).

--------------------------------------------------------------------
HOW TO RUN IT
--------------------------------------------------------------------

Run both scenarios, with their default concurrency sweeps:

    python load_test/phase3_concurrent_users.py

Run just one scenario:

    python load_test/phase3_concurrent_users.py --scenario a
    python load_test/phase3_concurrent_users.py --scenario b

Customize the concurrency levels swept (comma-separated, no spaces):

    python load_test/phase3_concurrent_users.py --scenario a --levels-a 5,10,25
    python load_test/phase3_concurrent_users.py --scenario b --levels-b 10,20,40,80

Isolate the database pool from Gemini/Qdrant, re-testing just concurrency 50:

    python load_test/phase3_concurrent_users.py --scenario a --levels-a 50 --db-only

Keep the test data around afterwards, to inspect it yourself:

    python load_test/phase3_concurrent_users.py --no-cleanup

Full list of options:

    --scenario {a,b,both}   which scenario(s) to run (default: both)
    --levels-a N,N,N        concurrency levels to sweep for Scenario A
                            (default: 5,10,15,25,50)
    --levels-b N,N,N        concurrency levels to sweep for Scenario B
                            (default: 10,20,25,50)
    --seed-cases N          how many fake cases to pre-create for
                            Scenario A to read during the burst
                            (default: 8 -- shared across every
                            concurrency level, so setup cost doesn't
                            grow with the sweep)
    --timeout-a X           give up on any single Scenario A database
                            call after this many seconds (default: 30)
    --timeout-b X           give up on any single Scenario B reflection
                            request after this many seconds (default:
                            your app's CLAUDE_REFLECTION_QUEUE_TIMEOUT_
                            SECONDS setting, plus 30 seconds of slack)
    --no-cleanup            skip automatic cleanup at the end
    --db-only               Scenario A only: skip the two Gemini-calling
                            steps and only run the pure database read.
                            Isolates the database connection pool from
                            Gemini rate limits / Qdrant latency -- useful
                            for re-testing high concurrency cleanly.
                            Has no effect on Scenario B.

--------------------------------------------------------------------
WHAT HAPPENS AT THE END
--------------------------------------------------------------------

A results table prints for each concurrency level, in each scenario,
and (unless --no-cleanup was passed) every LOADTEST_ record this run
created is automatically deleted before the script exits.

One thing worth knowing: if Scenario B ever produces a "capacity
timeout" outcome (every slot on the traffic light was busy and none
freed up in time), that is a REAL outcome of REAL app code
(rdi/orchestrator.py logs it exactly like it would for a real
practitioner) -- so it's expected to show up as a real entry in your
app's own error/issue log after a high-concurrency Scenario B run.
That's not a bug in this test; it's the exact behavior a real traffic
spike would produce, which is the whole point of testing it.
"""

import argparse
import random
import statistics
import threading
import time

import _bootstrap  # noqa: F401  (sets up imports + loads .env -- must run first)

import config
from services.draft_storage import get_completed_drafts, save_draft, finalize_draft
from services.qdrant_service import is_available as qdrant_available
from rdi.retrieval_service import retrieve_historical_context, retrieve_global_context
import rdi.orchestrator as orchestrator_module

import common


# =====================================================================
# Small, self-contained results tracker for this script.
#
# This is deliberately separate from common.py's Metrics class:
# common.Metrics only knows about "success / failure / timeout", but
# the two scenarios here each need their OWN, more specific set of
# outcome buckets (e.g. "pool_exhausted" for Scenario A, "partial_
# success" / "capacity_timeout" for Scenario B), broken down PER
# concurrency level. Nothing in common.py is changed by this file.
# =====================================================================

class OutcomeTracker:
    """
    Records one outcome per action per concurrency level, then prints
    a plain-English table. Thread-safe (many simulated users record
    results at the same moment, from different threads).
    """

    def __init__(self, outcome_labels):
        self._lock = threading.Lock()
        self._entries = []  # [{level, action, outcome, elapsed}, ...]
        self._outcome_labels = outcome_labels  # fixed display order

    def record(self, level, action, outcome, elapsed):
        with self._lock:
            self._entries.append({
                "level": level, "action": action,
                "outcome": outcome, "elapsed": elapsed,
            })

    def print_level_summary(self, level):
        with self._lock:
            entries = [e for e in self._entries if e["level"] == level]

        actions = sorted(set(e["action"] for e in entries))
        print(f"\n  ----- Results at concurrency = {level} -----")
        for action in actions:
            action_entries = [e for e in entries if e["action"] == action]
            times = [e["elapsed"] for e in action_entries]
            print(f"\n    {action}  ({len(action_entries)} attempt(s))")

            counts = {label: 0 for label in self._outcome_labels}
            for e in action_entries:
                counts[e["outcome"]] = counts.get(e["outcome"], 0) + 1
            counts_str = "  |  ".join(f"{label}: {counts.get(label, 0)}" for label in self._outcome_labels)
            print(f"      Outcomes -- {counts_str}")

            if times:
                times_sorted = sorted(times)
                p95_index = max(0, int(len(times_sorted) * 0.95) - 1)
                print(
                    f"      Time (seconds) -- avg: {statistics.mean(times):.2f}  "
                    f"median: {statistics.median(times):.2f}  "
                    f"p95: {times_sorted[p95_index]:.2f}  "
                    f"min: {min(times):.2f}  max: {max(times):.2f}"
                )

    def print_overall_summary(self, scenario_name):
        with self._lock:
            entries = list(self._entries)
        print(f"\n{'=' * 78}")
        print(f"{scenario_name} -- OVERALL SUMMARY (every concurrency level combined)")
        print("=" * 78)
        levels = sorted(set(e["level"] for e in entries))
        for level in levels:
            level_entries = [e for e in entries if e["level"] == level]
            counts = {label: 0 for label in self._outcome_labels}
            for e in level_entries:
                counts[e["outcome"]] = counts.get(e["outcome"], 0) + 1
            counts_str = "  |  ".join(f"{label}: {counts.get(label, 0)}" for label in self._outcome_labels)
            print(f"  concurrency={level:<4}  {counts_str}")
        print("=" * 78 + "\n")


def _classify_db_outcome(r):
    """
    Turns a common.timed_with_timeout() result into one of Scenario
    A's four outcome buckets: success / pool_exhausted / timeout /
    error.
    """
    if r["success"]:
        return "success"
    if r["timed_out"]:
        return "timeout"
    error_text = (r["error"] or "").lower()
    # psycopg2's connection pool raises an error whose message contains
    # exactly this phrase when every pooled connection is already
    # checked out (see services/db_pool.py). A connection that
    # repeatedly fails its own health check and gives up
    # (DB_POOL_MAX_REPLACE_ATTEMPTS exhausted) is the same underlying
    # "the pool is under too much pressure" story, so it's grouped
    # here too rather than under the generic "error" bucket.
    if "pool exhausted" in error_text or "could not obtain a healthy database connection" in error_text:
        return "pool_exhausted"
    return "error"


# =====================================================================
# SCENARIO A -- Database connection pool under concurrent reads
# =====================================================================

SCENARIO_A_OUTCOMES = ["success", "pool_exhausted", "timeout", "error"]

# A handful of different topics, so the fake documents aren't all
# word-for-word identical -- gives the real Gemini/Qdrant semantic
# search something meaningful to actually compare, instead of
# searching N copies of the exact same sentence.
_SEED_TOPICS = [
    "seguimiento de vivienda y estabilidad familiar",
    "escolarización y absentismo",
    "salud mental y apoyo emocional",
    "situación económica y ayudas sociales",
    "coordinación con servicios de salud",
    "dinámica familiar y red de apoyo",
    "seguimiento de menores en el hogar",
    "acceso a recursos comunitarios",
]


def seed_scenario_a_cases(num_cases, run_id, timeout):
    """
    Creates `num_cases` fake, LOADTEST_-tagged cases, each with one
    real, finalized (completed + really embedded + really indexed in
    Qdrant) document, so Scenario A's burst of readers has real data
    to find. Runs ONCE, before any concurrency level is tested, so
    this setup cost never grows with the sweep.

    Returns a list of dicts: [{"case_ref": ..., "content": ...}, ...]
    """
    print(f"\nSetting up {num_cases} fake case(s) for Scenario A to read (one-time, real Gemini + Qdrant writes)...")
    seeded = []
    for i in range(num_cases):
        case_ref = common.synthetic_case_ref(i, run_id)
        topic = _SEED_TOPICS[i % len(_SEED_TOPICS)]
        content = common.random_note_text() + f" Tema de esta nota de prueba: {topic}."
        user_name = common.synthetic_user_name(i, run_id)

        draft_id = save_draft(case_ref, "LOADTEST_DOC_TYPE", "Español", content, user_name, "Social Worker")
        r = common.timed_with_timeout(finalize_draft, draft_id, content, user_name, timeout=timeout)
        if not r["success"]:
            print(f"  WARNING: could not finalize seed case {i}: {r['error']}")
            continue

        seeded.append({"case_ref": case_ref, "content": content, "topic": topic})
        print(f"  seeded case {i + 1}/{num_cases}: {case_ref}")

    if not seeded:
        print("  WARNING: no seed cases were successfully created -- Scenario A's reads will find nothing.")
    return seeded


def run_scenario_a_burst(level, seeded_cases, timeout, tracker, db_only=False):
    """
    Launches `level` simulated user sessions that all start at the
    EXACT same instant (via threading.Barrier).

    Normally each session makes 3 real, read-only calls a
    practitioner's normal usage already makes. When `db_only` is True,
    steps 2 and 3 (the ones that call out to Gemini for a query
    embedding) are skipped entirely, so this burst becomes a PURE
    database-connection-pool test -- no Gemini call, no Gemini rate
    limit, no Qdrant call, nothing but services/db_pool.py and Neon.
    This isolates the database pool's behaviour from any noise caused
    by Gemini quota limits or Qdrant latency, which is useful at high
    concurrency where those two things can otherwise make it hard to
    tell what's actually causing a slow or failed request.
    """
    barrier = threading.Barrier(level)
    global_query_text = "¿Qué se ha observado sobre vivienda y bienestar familiar?"

    def one_session(session_index):
        case = seeded_cases[session_index % len(seeded_cases)]

        # All `level` threads wait here -- the barrier only releases
        # everyone at once, once every single one has arrived. This is
        # what makes it a genuine simultaneous burst.
        barrier.wait()

        # 1. Case History page load -- pure database read, no Gemini/Qdrant.
        r = common.timed_with_timeout(get_completed_drafts, limit=20, timeout=timeout)
        tracker.record(level, "get_completed_drafts (Case History)", _classify_db_outcome(r), r["elapsed"])

        if db_only:
            # Skip the two RAG calls below entirely -- they're the only
            # ones that touch Gemini. Everything else about the burst
            # (barrier, timing, outcome classification) stays identical
            # so results are directly comparable to a normal run.
            return

        # 2. Opening a case -- real Gemini query embedding + real Qdrant search
        r = common.timed_with_timeout(
            retrieve_historical_context, case["case_ref"],
            exclude_ids=set(), limit=4, query_text=case["content"],
            timeout=timeout,
        )
        tracker.record(level, "retrieve_historical_context (open a case)", _classify_db_outcome(r), r["elapsed"])

        # 3. Knowledge Assistant search -- real Gemini query embedding + real Qdrant search
        if qdrant_available():
            r = common.timed_with_timeout(
                retrieve_global_context, global_query_text,
                exclude_ids=set(), limit=4,
                timeout=timeout,
            )
            tracker.record(level, "retrieve_global_context (Knowledge Assistant)", _classify_db_outcome(r), r["elapsed"])

    threads = [threading.Thread(target=one_session, args=(i,)) for i in range(level)]
    start = time.monotonic()
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    elapsed = time.monotonic() - start
    print(f"  concurrency={level}: all {level} simulated sessions finished in {elapsed:.1f}s (wall clock)")


def run_scenario_a(levels, seed_cases, timeout, run_id, db_only=False):
    print("\n" + "=" * 78)
    print("SCENARIO A -- Database connection pool under concurrent reads")
    if db_only:
        print("           (DB-ONLY MODE -- Gemini/Qdrant calls are skipped)")
    print("=" * 78)
    print(f"  Sweeping concurrency levels: {levels}")
    print(f"  Your app's DB_POOL_MAX_CONN setting: {config.DB_POOL_MAX_CONN} "
          f"(the ceiling this test is checking against)")

    if db_only:
        print(
            "  DB-ONLY MODE: only the pure database read (get_completed_drafts) "
            "runs in this burst. The two calls that go out to Gemini "
            "(retrieve_historical_context, retrieve_global_context) are "
            "skipped entirely, so nothing here can be slowed down or failed "
            "by a Gemini rate limit or a Qdrant search -- whatever this run "
            "shows is 100% about services/db_pool.py and Neon."
        )
    elif not qdrant_available():
        print(
            "  NOTE: Qdrant isn't configured in this environment -- the "
            "'Knowledge Assistant' (retrieve_global_context) call will be "
            "skipped, but the other two real calls still run normally."
        )

    seeded_cases = seed_scenario_a_cases(seed_cases, run_id, timeout)
    if not seeded_cases:
        print("Aborting Scenario A: no seed data to read.")
        return None

    tracker = OutcomeTracker(SCENARIO_A_OUTCOMES)
    for level in levels:
        print(f"\n--- Scenario A: concurrency = {level} ---")
        run_scenario_a_burst(level, seeded_cases, timeout, tracker, db_only=db_only)
        tracker.print_level_summary(level)

    tracker.print_overall_summary("SCENARIO A")
    return tracker


# =====================================================================
# SCENARIO B -- Claude reflection-generation concurrency limiter
# =====================================================================

SCENARIO_B_OUTCOMES = ["success", "partial_success", "capacity_timeout", "complete_failure"]


def fake_generate_companion_reflection(companion, safe_text, lang="Español"):
    """
    Fast, in-memory stand-in for services.reflection_service.
    generate_companion_reflection() -- the ONE function that actually
    calls Claude. Sleeps a fraction of a second to behave like a real,
    quick network call, then returns a small, valid, always-successful
    fake answer. NEVER contacts Anthropic -- $0 cost.

    Matches the exact same return shape the real function returns on
    success, so the real, unmodified retry logic, semaphore, and
    fan-out code in rdi/orchestrator.py behave exactly as they would
    for a real (successful) Claude response.
    """
    time.sleep(random.uniform(0.05, 0.3))
    return {
        "observation": f"[LOADTEST fake observation for {companion.get('label', 'companion')}]",
        "questions": ["[LOADTEST fake reflective question]"],
    }


def run_scenario_b_burst(level, timeout, tracker):
    """
    Launches `level` simulated "click Generate" requests that all
    start at the EXACT same instant (via threading.Barrier), each
    making a real call into the real, unmodified run_reflection() --
    with only the Claude-calling function swapped for the fake
    stand-in above.
    """
    barrier = threading.Barrier(level)
    text = common.random_note_text() + " (Scenario B synthetic reflection request.)"

    def one_session(session_index):
        barrier.wait()
        r = common.timed_with_timeout(
            orchestrator_module.run_reflection, text,
            lang="Español", context_description="LOADTEST synthetic case",
            timeout=timeout,
        )
        outcome = _classify_reflection_outcome(r)
        tracker.record(level, "run_reflection", outcome, r["elapsed"])

    threads = [threading.Thread(target=one_session, args=(i,)) for i in range(level)]
    start = time.monotonic()
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    elapsed = time.monotonic() - start
    print(f"  concurrency={level}: all {level} simulated requests finished in {elapsed:.1f}s (wall clock)")


def _classify_reflection_outcome(r):
    """
    Turns a common.timed_with_timeout() result wrapping a
    run_reflection() call into one of Scenario B's four outcome
    buckets: success / partial_success / capacity_timeout /
    complete_failure.
    """
    if r["timed_out"]:
        # The TEST harness gave up waiting -- the real request may
        # still be stuck queued behind the semaphore. This is grouped
        # with complete_failure since, from the practitioner's point
        # of view, no reflection appeared in a reasonable time either way.
        return "complete_failure"
    if not r["success"]:
        # An unexpected Python exception escaped run_reflection()
        # itself (should not normally happen -- run_reflection()
        # catches its own failures and returns a result dict instead).
        return "complete_failure"

    result = r["result"] or {}
    if "error" in result:
        # run_reflection() returns this shape for BOTH a capacity/
        # queue-timeout (friendly_message is set) and a genuine
        # Complete Failure (friendly_message is None) -- see
        # rdi/orchestrator.py's run_reflection() docstring.
        if result.get("friendly_message"):
            return "capacity_timeout"
        return "complete_failure"

    if result.get("failed_count", 0) > 0:
        return "partial_success"

    return "success"


def run_scenario_b(levels, timeout):
    print("\n" + "=" * 78)
    print("SCENARIO B -- Claude reflection-generation concurrency limiter")
    print("=" * 78)
    print(f"  Sweeping concurrency levels: {levels}")
    print(f"  Your app's CLAUDE_MAX_CONCURRENT_REFLECTIONS setting: {config.CLAUDE_MAX_CONCURRENT_REFLECTIONS}")
    print(f"  Your app's CLAUDE_REFLECTION_QUEUE_TIMEOUT_SECONDS setting: {config.CLAUDE_REFLECTION_QUEUE_TIMEOUT_SECONDS}")
    print("  Swapping in the fake (zero-cost) Claude-calling stand-in for the duration of this test...")

    original_fn = orchestrator_module.generate_companion_reflection
    orchestrator_module.generate_companion_reflection = fake_generate_companion_reflection
    tracker = OutcomeTracker(SCENARIO_B_OUTCOMES)
    try:
        for level in levels:
            print(f"\n--- Scenario B: concurrency = {level} ---")
            run_scenario_b_burst(level, timeout, tracker)
            tracker.print_level_summary(level)
    finally:
        # Guaranteed to run even if a level crashes or the test is
        # interrupted -- the real Claude-calling function is always
        # restored, so nothing about your real app is left modified.
        orchestrator_module.generate_companion_reflection = original_fn
        print("\n  Restored the real Claude-calling function -- no trace of the fake stand-in remains.")

    tracker.print_overall_summary("SCENARIO B")
    return tracker


# =====================================================================
# Entry point
# =====================================================================

def _parse_levels(s):
    return [int(x.strip()) for x in s.split(",") if x.strip()]


def main():
    parser = argparse.ArgumentParser(description="Phase 3 -- concurrent-user burst testing")
    parser.add_argument("--scenario", choices=["a", "b", "both"], default="both")
    parser.add_argument("--levels-a", type=str, default="5,10,15,25,50")
    parser.add_argument("--levels-b", type=str, default="10,20,25,50")
    parser.add_argument("--seed-cases", type=int, default=8)
    parser.add_argument("--timeout-a", type=float, default=30.0)
    parser.add_argument(
        "--timeout-b", type=float, default=None,
        help="default: your app's CLAUDE_REFLECTION_QUEUE_TIMEOUT_SECONDS + 30s of slack",
    )
    parser.add_argument("--no-cleanup", action="store_true")
    parser.add_argument(
        "--db-only", action="store_true",
        help=(
            "Scenario A only: skip the two Gemini-calling steps "
            "(retrieve_historical_context, retrieve_global_context) and "
            "only run the pure database read. Isolates the database "
            "connection pool's behaviour from Gemini rate limits / Qdrant "
            "latency -- useful for re-testing high concurrency (e.g. 50) "
            "without that noise. Has no effect on Scenario B."
        ),
    )
    args = parser.parse_args()

    timeout_b = args.timeout_b
    if timeout_b is None:
        timeout_b = config.CLAUDE_REFLECTION_QUEUE_TIMEOUT_SECONDS + 30.0

    run_id = common.new_run_id()
    print("\nStarting Phase 3 -- Concurrent User Burst Testing")
    print(f"  Run tag (for this batch of fake data): LOADTEST_{run_id}")
    print(f"  Scenario(s) to run: {args.scenario}")

    ran_a = False
    if args.scenario in ("a", "both"):
        run_scenario_a(
            _parse_levels(args.levels_a), args.seed_cases, args.timeout_a, run_id,
            db_only=args.db_only,
        )
        ran_a = True

    if args.scenario in ("b", "both"):
        run_scenario_b(_parse_levels(args.levels_b), timeout_b)

    if args.no_cleanup:
        print(
            f"\n--no-cleanup was set: this run's LOADTEST_{run_id} data was left in place.\n"
            f"Run this when you're done inspecting it:\n"
            f"    python load_test/cleanup_synthetic_data.py\n"
        )
    elif ran_a:
        # Scenario B never writes anything to the database or Qdrant
        # (run_reflection() itself has no database/Qdrant calls in its
        # own right -- only Scenario A's seed cases need cleanup).
        print("Cleaning up this run's synthetic data now...\n")
        import cleanup_synthetic_data
        cleanup_synthetic_data.run_cleanup(run_id_filter=run_id)
    else:
        print("\nNothing to clean up (Scenario B was run alone; it never writes to the database).")


if __name__ == "__main__":
    main()