"""
confirmation_test_a.py
=======================

WHAT THIS SCRIPT DOES (plain English)

It pretends to be several social workers using Reflection Space at
the same time, each one doing a realistic sequence of things a real
practitioner does during a session:

    1. Log in / show up as active           (touches the database)
    2. Open the dashboard                   (touches the database)
    3. Save a new reflective note as a draft (touches the database)
    4. -> this automatically starts the background "historical
          context prefetch" feature, exactly like it does for a real
          user (touches Gemini + Qdrant + the database)
    5. Check Case History                   (touches the database) -- most users
    6. Ask the Knowledge Assistant a question (FAKE/mocked -- $0 cost) -- some users
    7. Finalize (submit) the draft           (touches the database + Gemini + Qdrant,
                                               for real -- this is the step that had
                                               indexing failures before)
    8. Begin Reflection                      (checks the real prefetched-context
                                               cache, then a FAKE/mocked reflection
                                               generation -- $0 cost) -- users who
                                               finalized

Every fake user's case is tagged "LOADTEST_..." so it can never be
confused with a real social worker's case, and so it can be safely
and completely deleted afterwards.

Reflection generation and Knowledge Assistant questions are FAKED
(no real Claude call) on purpose, to keep this test at zero Anthropic
cost -- Claude's own ability to handle concurrent requests was already
proven separately (up to 50 at once, 100% success). Everything else
in this test is 100% real: it really writes to your real database,
really calls Gemini to create embeddings, and really writes to your
real Qdrant search index.

HOW TO RUN IT

    python load_test/confirmation_test_a.py --users 10

Start with --users 10 (the default). Look at the results. Only once
that looks healthy, try --users 25, then 50, then 100, then 200 --
one step at a time. Do not jump straight to a big number.

Full list of options:

    --users N          how many simulated social workers run at once (default 10)
    --pause-min X       shortest realistic pause between a user's actions, in seconds (default 0.5)
    --pause-max X       longest realistic pause between a user's actions, in seconds (default 2.0)
    --timeout X         give up on any single action after this many seconds (default 30)
    --no-cleanup        skip the automatic cleanup at the end (so you can inspect the test data yourself)

WHAT HAPPENS AT THE END

A results table prints in your terminal, and unless you passed
--no-cleanup, every LOADTEST_ record this run created is automatically
deleted (from the database AND from Qdrant) before the script exits.
"""

import argparse
import random
import sys
import time
import concurrent.futures

import _bootstrap  # noqa: F401  (sets up imports + loads .env -- must run first)

from services.draft_storage import (
    update_user_activity,
    save_draft,
    get_completed_drafts,
    finalize_draft,
)
from services.context_prefetch import trigger_prefetch, get_cached_context

import common


# Pass/warning/fail boundaries, in seconds, based on each action's
# AVERAGE response time across all simulated users at this load level.
# These are starting points based on what "normal" looked like in
# earlier testing -- treat the first 10-user run as the real baseline,
# and revisit these numbers with Leon once real numbers are in.
THRESHOLDS = {
    "login_presence":        {"pass": 1.0, "warn": 3.0},
    "dashboard":              {"pass": 2.0, "warn": 5.0},
    "save_draft":              {"pass": 2.5, "warn": 6.0},
    "case_history":            {"pass": 3.0, "warn": 8.0},
    "knowledge_assistant_ask": {"pass": 1.0, "warn": 2.0},  # mocked -- should always be fast
    "finalize_draft":          {"pass": 5.0, "warn": 12.0},  # includes real Gemini + Qdrant write
    "begin_reflection":        {"pass": 2.0, "warn": 5.0},
}


def simulate_one_user(user_index, run_id, pause_range, timeout, metrics):
    """
    Runs one simulated social worker's session, start to finish.
    Every real step is timed and safety-wrapped with a timeout.
    """
    user_name = common.synthetic_user_name(user_index, run_id)
    user_role = "Social Worker"
    case_ref = common.synthetic_case_ref(user_index, run_id)
    content = common.random_note_text()

    def pause():
        time.sleep(random.uniform(*pause_range))

    # 1. Login / presence
    r = common.timed_with_timeout(
        update_user_activity, user_name, user_role, timeout=timeout,
    )
    metrics.record("login_presence", r["elapsed"], r["success"], r["timed_out"], r["error"])
    pause()

    # 2. Dashboard (a lightweight real read -- how many completed
    # documents exist recently; stands in for the dashboard's own
    # database read without needing a browser)
    r = common.timed_with_timeout(
        get_completed_drafts, limit=10, timeout=timeout,
    )
    metrics.record("dashboard", r["elapsed"], r["success"], r["timed_out"], r["error"])
    pause()

    # 3. Save a new draft (real DB write)
    r = common.timed_with_timeout(
        save_draft, case_ref, "LOADTEST_DOC_TYPE", "Español", content, user_name, user_role,
        timeout=timeout,
    )
    metrics.record("save_draft", r["elapsed"], r["success"], r["timed_out"], r["error"])
    draft_id = r["result"] if r["success"] else None
    if draft_id is None:
        # Can't continue this user's session without a draft id.
        return

    # 4. Kick off the real background historical-context prefetch,
    # exactly as pages/documentation.py does after a real save. This
    # doesn't block the user (or this script) -- it runs on its own
    # background thread, same as in the real app.
    trigger_prefetch(draft_id, case_ref, content)
    pause()

    # 5. Case History -- most users check this, not all
    if random.random() < 0.7:
        r = common.timed_with_timeout(
            get_completed_drafts, limit=20, timeout=timeout,
        )
        metrics.record("case_history", r["elapsed"], r["success"], r["timed_out"], r["error"])
        pause()

    # 6. Knowledge Assistant -- a smaller fraction of users, mocked/$0 cost
    if random.random() < 0.3:
        r = common.timed_with_timeout(
            common.mock_knowledge_assistant_ask, "Pregunta de prueba de carga", timeout=timeout,
        )
        metrics.record("knowledge_assistant_ask", r["elapsed"], r["success"], r["timed_out"], r["error"])
        pause()

    # 7. Finalize (submit) the draft -- most users finish their note.
    # This is REAL: it writes to Postgres, then really calls Gemini to
    # embed the text and really writes the vector into Qdrant. This is
    # the exact step that produced the earlier open finding (859
    # indexing failures), so it matters that this stays real here.
    if random.random() < 0.7:
        r = common.timed_with_timeout(
            finalize_draft, draft_id, content, user_name, timeout=timeout,
        )
        metrics.record("finalize_draft", r["elapsed"], r["success"], r["timed_out"], r["error"])
        pause()

        # 8. Begin Reflection -- checks the real prefetch cache (was it
        # ready in time?), then a fake/mocked reflection generation.
        r = common.timed_with_timeout(
            get_cached_context, draft_id, timeout=timeout,
        )
        prefetch_hit = bool(r["result"]) if r["success"] else False
        common.mock_generate_reflection(content)
        metrics.record("begin_reflection", r["elapsed"], r["success"], r["timed_out"], r["error"])
        metrics.record(
            "prefetch_cache_hit" if prefetch_hit else "prefetch_cache_miss",
            0.0, True, False, "",
        )


def main():
    parser = argparse.ArgumentParser(description="Confirmation Test A -- realistic mixed load")
    parser.add_argument("--users", type=int, default=10)
    parser.add_argument("--pause-min", type=float, default=0.5)
    parser.add_argument("--pause-max", type=float, default=2.0)
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument("--no-cleanup", action="store_true")
    args = parser.parse_args()

    run_id = common.new_run_id()
    print(f"\nStarting Confirmation Test A")
    print(f"  Simulated concurrent users: {args.users}")
    print(f"  Run tag (for this batch of fake data): LOADTEST_{run_id}")
    print(f"  Per-action timeout: {args.timeout}s\n")

    metrics = common.Metrics()
    start = time.monotonic()

    with concurrent.futures.ThreadPoolExecutor(max_workers=args.users) as pool:
        futures = [
            pool.submit(
                simulate_one_user, i, run_id,
                (args.pause_min, args.pause_max), args.timeout, metrics,
            )
            for i in range(args.users)
        ]
        for f in concurrent.futures.as_completed(futures):
            # Surface any unexpected crash in a single user's session
            # rather than letting it disappear silently.
            exc = f.exception()
            if exc is not None:
                print(f"  WARNING: a simulated user session crashed unexpectedly: {exc}")

    total_elapsed = time.monotonic() - start
    print(f"\nAll {args.users} simulated user sessions finished in {total_elapsed:.1f}s (wall clock).")

    metrics.print_summary(thresholds=THRESHOLDS)

    if args.no_cleanup:
        print(
            f"--no-cleanup was set: this run's LOADTEST_{run_id} data was left in place.\n"
            f"Run this when you're done inspecting it:\n"
            f"    python load_test/cleanup_synthetic_data.py\n"
        )
    else:
        print("Cleaning up this run's synthetic data now...\n")
        import cleanup_synthetic_data
        cleanup_synthetic_data.run_cleanup(run_id_filter=run_id)


if __name__ == "__main__":
    main()
