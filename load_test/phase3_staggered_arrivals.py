"""
phase3_staggered_arrivals.py
=============================

WHAT THIS SCRIPT DOES (plain English)

phase3_concurrent_users.py (Scenario A) tests the harshest possible
case: every simulated practitioner opens the app at the EXACT same
instant (using a `threading.Barrier`, a gate that only opens once
everyone is lined up). That test found a real ceiling at concurrency
30-40, caused by Python's own thread-scheduling running out of
headroom when dozens of threads all start in the same nanosecond --
not by anything wrong in services/db_pool.py or in Neon itself.

This script asks a more realistic follow-up question: does that same
ceiling still show up if the same number of practitioners arrive
spread out over a few seconds instead of all at once -- which is how
people actually open an app in real life, even during a busy moment?

Instead of a Barrier, each simulated user is given its own small
starting delay, spread evenly (with a little random jitter) across a
configurable arrival window (default: 5 seconds). So for example, at
concurrency 40 with a 5-second window, the 40 simulated users don't
all start at 0.0s -- they start at roughly 0.0s, 0.13s, 0.25s, 0.38s,
and so on, up to about 5.0s, each with a bit of randomness added so
they're not perfectly evenly spaced either.

Everything else about the test is identical to Scenario A in
phase3_concurrent_users.py, and it reuses that file's own tested
building blocks directly (the seed-case setup, the outcome
classification, and the results table) rather than duplicating them,
so the two tests' numbers are directly comparable.

Each simulated user session does the same real, read-only action(s) a
practitioner's normal usage already makes:

  1. get_completed_drafts()        -- Case History page load (always)
  2. retrieve_historical_context() -- opening a case (skipped in
                                       --db-only mode)
  3. retrieve_global_context()     -- Knowledge Assistant search
                                       (skipped in --db-only mode)

--------------------------------------------------------------------
WHY THIS DEFAULTS TO --db-only MODE
--------------------------------------------------------------------

The last burst test at concurrency 30/35/40 was run with --db-only so
that a Gemini free-tier rate limit couldn't muddy the results. To keep
this new test's numbers directly comparable to that one, this script
also defaults to db-only mode. Pass --with-ai-calls if you want the
full 3-step version instead (only worth doing once your Gemini quota
allows it).

--------------------------------------------------------------------
SAFETY / COST GUARANTEES
--------------------------------------------------------------------

- Every fake case/document this script creates is tagged "LOADTEST_",
  the same convention as every other script in this folder, and is
  automatically deleted at the end unless you pass --no-cleanup.
- $0 in real Claude/Anthropic API calls -- this script never touches
  Claude at all.
- In db-only mode (the default): $0 in Gemini calls either, since the
  two Gemini-calling steps are skipped entirely.
- In --with-ai-calls mode: small, real Gemini query-embedding costs,
  same as Scenario A in phase3_concurrent_users.py.

--------------------------------------------------------------------
HOW TO RUN IT
--------------------------------------------------------------------

Match the exact levels from the last burst test, staggered over the
default 5-second window:

    python load_test/phase3_staggered_arrivals.py --levels 30,35,40

Try a wider, more relaxed arrival window (users trickle in over 10
seconds instead of 5):

    python load_test/phase3_staggered_arrivals.py --levels 30,35,40 --window 10

Full list of options:

    --levels N,N,N       concurrency levels to sweep (default: 30,35,40
                          -- the same levels that showed failures in
                          the burst test, for a direct comparison)
    --window X            spread each level's arrivals evenly (plus a
                          little random jitter) across this many
                          seconds (default: 5.0)
    --seed-cases N        how many fake cases to pre-create for the
                          test to read (default: 8, shared across
                          every concurrency level)
    --timeout X           give up on any single database call after
                          this many seconds (default: 30)
    --with-ai-calls       run the full 3-step version (adds the two
                          Gemini-calling steps back in) instead of the
                          default db-only mode
    --no-cleanup          skip automatic cleanup at the end

--------------------------------------------------------------------
HOW TO READ THE RESULTS
--------------------------------------------------------------------

Compare each concurrency level's success/error counts here against
the SAME level's counts from the burst test
(phase3_concurrent_users.py --scenario a --levels-a 30,35,40 --db-only):

  - If the failure count drops a lot (or disappears) once arrivals are
    staggered, that confirms the earlier ceiling was really about the
    artificial "everyone in the same nanosecond" burst shape, not a
    genuine capacity problem your pilot needs to worry about.
  - If the same ~60% failure rate still shows up even when arrivals
    are spread out, that would mean there's a real capacity limit here
    worth addressing before opening this up to more pilot users --
    and would be an important, separate thing to dig into next.
"""

import argparse
import random
import threading
import time

import _bootstrap  # noqa: F401  (sets up imports + loads .env -- must run first)

import config
from services.draft_storage import get_completed_drafts
from services.qdrant_service import is_available as qdrant_available
from rdi.retrieval_service import retrieve_historical_context, retrieve_global_context

import common
from phase3_concurrent_users import (
    OutcomeTracker,
    SCENARIO_A_OUTCOMES,
    _classify_db_outcome,
    seed_scenario_a_cases,
)


def run_staggered_burst(level, seeded_cases, timeout, tracker, window, db_only=True):
    """
    Launches `level` simulated user sessions whose start times are
    spread evenly (with a little random jitter) across `window`
    seconds, instead of all starting at the exact same instant.
    """
    global_query_text = "¿Qué se ha observado sobre vivienda y bienestar familiar?"

    # Evenly-spaced base offsets across the window, each nudged by a
    # small random amount so arrivals aren't perfectly metronomic --
    # closer to how real people actually trickle in.
    if level > 1:
        step = window / level
    else:
        step = 0.0
    offsets = [(i * step) + random.uniform(0, step) for i in range(level)]

    def one_session(session_index, delay):
        case = seeded_cases[session_index % len(seeded_cases)]
        time.sleep(delay)

        # 1. Case History page load -- pure database read, no Gemini/Qdrant.
        r = common.timed_with_timeout(get_completed_drafts, limit=20, timeout=timeout)
        tracker.record(level, "get_completed_drafts (Case History)", _classify_db_outcome(r), r["elapsed"])

        if db_only:
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

    threads = [threading.Thread(target=one_session, args=(i, offsets[i])) for i in range(level)]
    start = time.monotonic()
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    elapsed = time.monotonic() - start
    print(
        f"  concurrency={level} (arrivals staggered over {window:.1f}s): "
        f"all {level} simulated sessions finished in {elapsed:.1f}s (wall clock)"
    )


def run_staggered_test(levels, seed_cases, timeout, run_id, window, db_only=True):
    print("\n" + "=" * 78)
    print("STAGGERED ARRIVAL TEST -- Database connection pool, realistic pacing")
    if db_only:
        print("           (DB-ONLY MODE -- Gemini/Qdrant calls are skipped)")
    print("=" * 78)
    print(f"  Sweeping concurrency levels: {levels}")
    print(f"  Arrival window: {window:.1f}s (each level's users start at staggered times within this window)")
    print(f"  Your app's DB_POOL_MAX_CONN setting: {config.DB_POOL_MAX_CONN} "
          f"(the ceiling the earlier burst test hit)")

    if db_only:
        print(
            "  DB-ONLY MODE: only the pure database read (get_completed_drafts) "
            "runs in this test, matching how the last burst test at the same "
            "levels was run, so the two results are directly comparable."
        )
    elif not qdrant_available():
        print(
            "  NOTE: Qdrant isn't configured in this environment -- the "
            "'Knowledge Assistant' (retrieve_global_context) call will be "
            "skipped, but the other two real calls still run normally."
        )

    seeded_cases = seed_scenario_a_cases(seed_cases, run_id, timeout)
    if not seeded_cases:
        print("Aborting staggered arrival test: no seed data to read.")
        return None

    tracker = OutcomeTracker(SCENARIO_A_OUTCOMES)
    for level in levels:
        print(f"\n--- Staggered arrival test: concurrency = {level} ---")
        run_staggered_burst(level, seeded_cases, timeout, tracker, window, db_only=db_only)
        tracker.print_level_summary(level)

    tracker.print_overall_summary("STAGGERED ARRIVAL TEST")
    return tracker


# =====================================================================
# Entry point
# =====================================================================

def _parse_levels(s):
    return [int(x.strip()) for x in s.split(",") if x.strip()]


def main():
    parser = argparse.ArgumentParser(
        description="Staggered-arrival version of Scenario A -- same reads, spread-out start times"
    )
    parser.add_argument("--levels", type=str, default="30,35,40")
    parser.add_argument("--window", type=float, default=5.0)
    parser.add_argument("--seed-cases", type=int, default=8)
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument(
        "--with-ai-calls", action="store_true",
        help="Run the full 3-step version (adds the two Gemini-calling steps back in) "
             "instead of the default db-only mode.",
    )
    parser.add_argument("--no-cleanup", action="store_true")
    args = parser.parse_args()

    run_id = common.new_run_id()
    print("\nStarting Staggered Arrival Test")
    print(f"  Run tag (for this batch of fake data): LOADTEST_{run_id}")

    run_staggered_test(
        _parse_levels(args.levels), args.seed_cases, args.timeout, run_id,
        args.window, db_only=not args.with_ai_calls,
    )

    if args.no_cleanup:
        print(
            f"\n--no-cleanup was set: this run's LOADTEST_{run_id} data was left in place.\n"
            f"Run this when you're done inspecting it:\n"
            f"    python load_test/cleanup_synthetic_data.py\n"
        )
    else:
        print("Cleaning up this run's synthetic data now...\n")
        import cleanup_synthetic_data
        cleanup_synthetic_data.run_cleanup(run_id_filter=run_id)


if __name__ == "__main__":
    main()