"""
check_db_connectivity.py
=========================

WHAT THIS SCRIPT DOES (plain English)

This is the simplest possible test: it tries to connect to your real
database, one single time, with nobody else and nothing else going
on, and times how long that takes. Then it does that 5 times in a row
(one at a time, not simultaneously) so a single lucky/unlucky moment
doesn't mislead us.

This exists to answer ONE question on its own, with no other moving
parts involved: "Right now, on this internet connection, can my
computer reach the database quickly and reliably?"

It does NOT touch Gemini, Qdrant, or any simulated users. It does not
create or change any data. It is completely safe to run at any time.

HOW TO RUN IT

    python load_test/check_db_connectivity.py

WHAT TO LOOK FOR

- If all 5 attempts finish in under 1-2 seconds each: your current
  connection to the database is healthy right now.
- If attempts are slow (several seconds) or time out: your current
  network connection to the database is the likely explanation for
  what we saw in the last test run -- not a problem with the app
  itself.
"""

import time
import psycopg2

import _bootstrap  # noqa: F401
from config import DATABASE_URL


def one_attempt(attempt_number):
    start = time.monotonic()
    try:
        conn = psycopg2.connect(DATABASE_URL, connect_timeout=10)
        with conn.cursor() as c:
            c.execute("SELECT 1")
            c.fetchone()
        conn.close()
        elapsed = time.monotonic() - start
        print(f"  Attempt {attempt_number}: OK -- {elapsed:.2f} seconds")
        return elapsed, True
    except Exception as e:
        elapsed = time.monotonic() - start
        print(f"  Attempt {attempt_number}: FAILED after {elapsed:.2f} seconds -- {e}")
        return elapsed, False


def main():
    print("\nChecking your connection to the real database (5 one-at-a-time attempts)...\n")
    results = []
    for i in range(1, 6):
        elapsed, ok = one_attempt(i)
        results.append((elapsed, ok))
        time.sleep(0.5)

    successes = [e for e, ok in results if ok]
    print("\n" + "=" * 60)
    print(f"Successful attempts: {len(successes)} / 5")
    if successes:
        print(f"Fastest: {min(successes):.2f}s   Slowest: {max(successes):.2f}s   "
              f"Average: {sum(successes)/len(successes):.2f}s")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
