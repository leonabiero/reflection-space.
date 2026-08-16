"""
Diagnose the one-time Wave-1 login/presence delay.

This is an OBSERVATION-ONLY diagnostic. It does not change the pool,
application behavior, or database configuration.

Question being tested:
    Is the ~18-second Wave-1 `login_presence` result actually caused by
    database pool initialization, or does update_user_activity() itself
    remain slow after the pool is already initialized?

Why this script exists:
    Confirmation Test A times `update_user_activity()` as `login_presence`.
    On a fresh process, that first call also triggers db_pool._get_pool(),
    which creates DB_POOL_MIN_CONN physical connections. With the current
    pre-warm setting, that is the first database-touching operation in the
    load-test process. Therefore the original metric combines two different
    things:

        pool creation + login_presence SQL work

    This script separates them without changing either one.

Run from the repository root:

    python load_test/diagnose_wave1_login.py

It performs four measurements:

    1. Import/bootstrap time (before any database access).
    2. Pool creation time, explicitly calling the internal _get_pool().
    3. First login_presence after the pool is already warm.
    4. Second login_presence, to confirm normal warm behavior.

Interpretation:

    - If pool creation is ~18s and both login_presence calls are fast:
        the 18s is NOT a login problem. It is the cold pool startup cost.

    - If pool creation is small but login_presence is ~18s:
        the delay is inside update_user_activity() or its database path.

    - If pool creation and login_presence are both unexpectedly slow:
        the measurements tell us exactly which layers need the next test.

No real application user is touched. The username is tagged LOADTEST_ and
is removed at the end if the insert succeeds.
"""

import time

import _bootstrap  # noqa: F401 -- loads load_test/.env before app imports

from services import db_pool
from services.draft_storage import update_user_activity


def timed(label, fn):
    start = time.monotonic()
    result = fn()
    elapsed = time.monotonic() - start
    print(f"  {label:<42} {elapsed:8.3f}s")
    return result, elapsed


def main():
    print("\nWave-1 login_presence diagnostic")
    print("=" * 72)
    print("Observation only -- no pool/config/application changes are made.\n")

    # The process starts with db_pool._pool == None. Calling this directly
    # isolates the exact cost that the first real database operation would
    # otherwise hide inside update_user_activity().
    _, pool_seconds = timed(
        "1. pool creation (_get_pool)",
        db_pool._get_pool,
    )

    test_user = f"LOADTEST_DIAG_{int(time.time())}"
    test_role = "Social Worker"

    _, login1_seconds = timed(
        "2. login_presence (first, pool warm)",
        lambda: update_user_activity(test_user, test_role),
    )

    _, login2_seconds = timed(
        "3. login_presence (second, pool warm)",
        lambda: update_user_activity(test_user, test_role),
    )

    # Remove only the synthetic diagnostic row. Use the same pooled DB path;
    # this is deliberately tiny and does not touch any production records.
    def cleanup():
        conn = db_pool.get_conn()
        try:
            with conn.cursor() as c:
                c.execute("DELETE FROM user_activity WHERE user_name=%s", (test_user,))
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    _, cleanup_seconds = timed("4. diagnostic cleanup", cleanup)

    print("\n" + "=" * 72)
    print("INTERPRETATION")
    print("=" * 72)
    print(f"  Pool creation:                 {pool_seconds:8.3f}s")
    print(f"  First warm login_presence:     {login1_seconds:8.3f}s")
    print(f"  Second warm login_presence:    {login2_seconds:8.3f}s")
    print(f"  Diagnostic cleanup:             {cleanup_seconds:8.3f}s")

    if pool_seconds >= 10 and login1_seconds < 3 and login2_seconds < 3:
        print("\n  CONCLUSION: the Wave-1 delay is pool initialization, not login_presence.")
        print("  Do NOT modify the pool based on the old login metric.")
    elif pool_seconds < 5 and login1_seconds >= 10:
        print("\n  CONCLUSION: pool initialization does NOT explain the delay.")
        print("  Investigate update_user_activity() / its database path next.")
    else:
        print("\n  CONCLUSION: mixed/ambiguous result; use the four timings above to choose the next test.")

    print("\nThe existing confirmation test should continue to be used for concurrency.")
    print("This script only separates the cold-start component from the login action.\n")


if __name__ == "__main__":
    main()
