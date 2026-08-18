"""
test_replacement_deadline.py -- Deliberately Breaking a Connection, On Purpose
================================================================================

WHAT THIS TEST IS FOR (plain English)

Every load test we've run so far -- Confirmation Test A, Phase 3
Scenario A -- finished from start to end without a single pooled
connection ever actually going bad. That's good news for those tests,
but it means one specific part of services/db_pool.py has NEVER
actually been exercised by any real test run: the part that notices a
connection has died, throws it away, and gets a replacement -- all
while making sure the replacement doesn't get a brand-new 5-second
budget of its own (it's supposed to share whatever time is left over
from the original request).

This script exists purely to force that exact situation to happen, on
purpose, so we can finally watch it and time it for real, instead of
reading the code and hoping it's right.

WHAT IT ACTUALLY DOES

  1. Warms up the connection pool (same as normal app startup).
  2. Deliberately kills a handful of pooled connections at the network
     level -- this is standing in for something that happens for real
     occasionally on its own (Neon recycling a connection, a brief
     network blip, a connection going idle too long).
  3. Puts those broken connections back in the pool, looking completely
     normal from the outside.
  4. Fires off several real, ordinary get_conn() calls at once. Some of
     them are very likely to be handed one of the broken connections.
     When that happens, the app's own code in services/db_pool.py has
     to notice it's broken, throw it away, and get a working one
     instead -- all within the same request's original time budget.
  5. Reports, for every one of those calls: how long it actually took,
     whether it succeeded, and whether it stayed within the configured
     time budget or blew past it.

This does NOT touch or modify services/db_pool.py in any way -- it only
calls the same get_conn() function any real page load in the app
already calls, and deliberately hands it some broken connections to
deal with.

WHAT A HEALTHY RESULT LOOKS LIKE

  - Every single checkout still succeeds. A broken connection should be
    completely invisible to the rest of the app -- it should just
    quietly end up with a working one instead.
  - No checkout takes dramatically longer than the configured budget
    (a little extra time for the health check that caught the problem,
    plus opening one fresh replacement connection, is normal and fine
    -- typically well under a second of overhead).
  - Your terminal shows real "DB checkout REPLACING UNHEALTHY
    CONNECTION" and "DB checkout REPLACEMENT ACQUIRED" lines while this
    runs (these are debug-level messages -- see the note below if you
    don't see them and want to).

WHAT AN UNHEALTHY RESULT LOOKS LIKE

  - Any checkout failing outright.
  - A checkout that took noticeably longer than the configured budget
    (for example, close to DOUBLE the budget) -- that would suggest a
    replacement checkout is getting its own fresh timeout instead of
    sharing what was left of the original one.

A NOTE ON SEEING THE DETAILED LOG LINES

By default, services/db_pool.py only prints its short one-line summary
for each checkout (INFO level). The more detailed "REPLACING UNHEALTHY
CONNECTION" / "REPLACEMENT ACQUIRED" lines exist in the code but are
only shown when logging is turned up to DEBUG level. This script turns
DEBUG-level logging on for services.db_pool automatically for the
duration of the run, so you should see them without doing anything
extra.

HOW TO RUN IT

    python load_test/test_replacement_deadline.py
    python load_test/test_replacement_deadline.py --poison 5 --concurrency 10
    python load_test/test_replacement_deadline.py --poison 15 --concurrency 20

This does not write any LOADTEST_ data to your database or Qdrant --
it only opens and closes raw database connections, so there is
nothing for you to clean up afterward.
"""

import argparse
import logging
import threading
import time

import _bootstrap  # noqa: F401  (sets up imports + loads .env -- must run first)

from services import db_pool


def _poison_connections(count):
    """
    Checks out `count` real connections from the real pool, kills their
    underlying network connection directly (standing in for an
    unexpected real-world disconnect), then returns them to the pool
    exactly the way a normal, healthy connection would be returned --
    so from the pool's point of view, nothing looks unusual yet.

    Returns the number of connections actually poisoned (this can be
    less than `count` if the pool doesn't have that many connections
    available to grab all at once).
    """
    grabbed = []
    for _ in range(count):
        try:
            grabbed.append(db_pool.get_conn())
        except Exception as e:  # noqa: BLE001
            print(f"    (could only grab {len(grabbed)} connection(s) to poison -- {e})")
            break

    for conn in grabbed:
        # `conn._conn` is the real psycopg2 connection underneath our
        # wrapper -- closing it directly simulates the connection
        # dying unexpectedly, the same way a real network blip or a
        # server-side recycle would.
        try:
            conn._conn.close()
        except Exception:
            pass

    for conn in grabbed:
        conn.close()  # returned to the pool -- looks completely normal from the outside

    return len(grabbed)


def _one_checkout(index, results, lock):
    started = time.monotonic()
    error = None
    try:
        conn = db_pool.get_conn()
        conn.close()
    except Exception as e:  # noqa: BLE001
        error = str(e)
    elapsed = time.monotonic() - started

    with lock:
        results.append({"index": index, "elapsed": elapsed, "error": error})


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--poison", type=int, default=5,
        help="How many pooled connections to deliberately break (default: 5)",
    )
    parser.add_argument(
        "--concurrency", type=int, default=10,
        help="How many real get_conn() calls to fire at once afterward (default: 10)",
    )
    args = parser.parse_args()

    # Turn on the detailed "REPLACING / REPLACEMENT" log lines for this
    # run only -- they're logged at DEBUG level in services/db_pool.py
    # and wouldn't show up otherwise.
    logging.getLogger("services.db_pool").setLevel(logging.DEBUG)

    print("\nStarting Replacement Deadline Test")
    print(f"  Configured DB checkout budget (DB_POOL_WAIT_TIMEOUT_SECONDS): "
          f"{db_pool.DB_POOL_WAIT_TIMEOUT_SECONDS:.1f}s")

    print("  Warming up the connection pool (same as normal app startup)...")
    warmup_conn = db_pool.get_conn()
    warmup_conn.close()

    print(f"  Deliberately breaking up to {args.poison} pooled connection(s) "
          f"at the network level...")
    poisoned_count = _poison_connections(args.poison)
    print(f"  Done -- {poisoned_count} connection(s) are now sitting in the "
          f"pool, silently broken.\n")

    print(f"  Firing {args.concurrency} real get_conn() calls at once "
          f"(some should land on a broken connection)...\n")

    results = []
    lock = threading.Lock()
    threads = [
        threading.Thread(target=_one_checkout, args=(i, results, lock))
        for i in range(args.concurrency)
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    results.sort(key=lambda r: r["index"])

    budget = db_pool.DB_POOL_WAIT_TIMEOUT_SECONDS
    slack_seconds = 1.0  # normal allowance for one extra health check + one fresh connect
    over_budget = [r for r in results if r["elapsed"] > budget + slack_seconds]
    failed = [r for r in results if r["error"] is not None]

    print("  ----- Results -----\n")
    for r in results:
        status = "OK" if r["error"] is None else f"FAILED ({r['error']})"
        flag = "  <-- OVER BUDGET" if r in over_budget else ""
        print(f"    checkout #{r['index']:<3} elapsed={r['elapsed']:.2f}s  {status}{flag}")

    print("\n  ----- Summary -----")
    print(f"    Connections deliberately broken:                  {poisoned_count}")
    print(f"    Total checkouts attempted:                        {len(results)}")
    print(f"    Succeeded:                                        {len(results) - len(failed)}")
    print(f"    Failed:                                           {len(failed)}")
    print(f"    Exceeded the {budget:.1f}s budget by more than {slack_seconds:.0f}s: {len(over_budget)}")

    print()
    if not failed and not over_budget:
        print(
            "  RESULT: every checkout succeeded and stayed within budget, even "
            "with broken connections sitting in the pool. This is the healthy "
            "outcome -- the replacement path works and correctly shares the "
            "original request's time budget instead of restarting it."
        )
    elif failed and not over_budget:
        print(
            "  RESULT: the timing held up (nothing ran dramatically over budget), "
            "but some checkouts still failed outright. The deadline logic itself "
            "looks fine here -- worth looking at why those specific checkouts "
            "failed (see their error message above)."
        )
    else:
        print(
            "  RESULT: at least one checkout ran well past the configured "
            f"budget ({budget:.1f}s). This suggests a replacement checkout may "
            "be getting a fresh timeout budget of its own, instead of sharing "
            "what was left of the original request's budget. This is worth a "
            "closer look at services/db_pool.py's replacement logic before "
            "trusting the deadline under real-world connection failures."
        )
    print()


if __name__ == "__main__":
    main()