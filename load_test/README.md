# Load Testing Toolkit

This folder contains two different load tests. They answer two
different questions, so it's worth knowing which one you're running:

- **Confirmation Test A** (`confirmation_test_a.py`) — a realistic
  MIX of things, spread out over time: how does the app behave when
  many social workers are all using it, doing different things, at
  once?
- **Phase 3 — Concurrent User Burst Testing**
  (`phase3_concurrent_users.py`) — a sharp BURST of the exact same
  action, all at the exact same instant: what happens the moment many
  practitioners all click the same button together?

## Confirmation Test A

Finds out how Reflection Space behaves when many social workers use
it at the same time, doing a realistic mix of things (not everyone
doing the exact same single action at once — that's what Phase 3,
below, checks instead).

## What it actually does

It starts several "fake social workers" at once, in your terminal.
Each fake user logs in, checks the dashboard, saves a note, sometimes
checks Case History, sometimes asks the Knowledge Assistant a
question, usually finalizes (submits) their note, and then begins a
reflection (a real, live historical-context lookup).

**Important, so there are no surprises:** generating a full reflection
and asking the Knowledge Assistant are **faked** in this test (no real
call to Claude, $0 cost) — because Claude's ability to handle many
requests at once was already proven separately. Everything else in
this test is **real**: it really writes to your real database, and it
really calls Gemini and Qdrant to index the note, exactly like a real
submission does.

Every fake case is tagged `LOADTEST_...` so it can never be mistaken
for a real case, and it's automatically cleaned up (deleted) at the
end of every run.

## One-time setup

1. Copy `.env.example` in this folder, and rename the copy to `.env`
2. Open `.env` in Notepad and fill in the same database, Gemini, and
   Qdrant values your real app already uses
3. In your terminal, from your repo folder, run:

   ```
   pip install -r load_test/requirements.txt --break-system-packages
   ```

## Running the test

Start small. Do not skip ahead to a big number.

```
python load_test/confirmation_test_a.py --users 10
```

Watch the results table it prints at the end. If that looks healthy
(mostly PASS, no FAIL), move up one step at a time:

```
python load_test/confirmation_test_a.py --users 25
python load_test/confirmation_test_a.py --users 50
python load_test/confirmation_test_a.py --users 100
python load_test/confirmation_test_a.py --users 200
```

After each run, send me the results table (just copy-paste everything
your terminal printed) and I'll tell you what it means and whether
it's safe to move to the next level.

## If you want to look at the test data before it's deleted

Add `--no-cleanup` to any run, e.g.:

```
python load_test/confirmation_test_a.py --users 10 --no-cleanup
```

Then, whenever you're ready to delete it, run:

```
python load_test/cleanup_synthetic_data.py
```

## If something goes wrong mid-test

It's safe to just close the terminal window (Ctrl+C, or close it
outright). Nothing gets left in a broken state — but any fake data
that run already created won't have been cleaned up yet. Just run:

```
python load_test/cleanup_synthetic_data.py
```

afterwards to remove it.

## Phase 3 — Concurrent User Burst Testing

Tests two specific "everyone at once" moments directly, using a real
synchronization gate (`threading.Barrier`) so every simulated user
truly starts at the same instant, not one after another:

- **Scenario A**: a burst of practitioners all pulling up Case
  History / opening a case / asking the Knowledge Assistant, at once
  — checks how the database connection pool holds up. 100% real
  database, Gemini, and Qdrant calls.
- **Scenario B**: a burst of practitioners all clicking "Generate
  reflection" at once — checks the traffic-light limiter that caps
  how many reflections can be generating at the same time. The one
  function that actually calls Claude is temporarily swapped for a
  free, instant fake answer (and always swapped back before the
  script exits) — **$0 Claude/Anthropic cost**, but everything else
  (the limiter itself, the real retry logic, the real parallel
  fan-out) is the real, unmodified app code.

Run both scenarios, with their default concurrency sweeps:

```
python load_test/phase3_concurrent_users.py
```

Run just one:

```
python load_test/phase3_concurrent_users.py --scenario a
python load_test/phase3_concurrent_users.py --scenario b
```

Full usage details (custom concurrency levels, timeouts, etc.) are in
the comment block at the top of `phase3_concurrent_users.py` itself.

Same safety net as Confirmation Test A applies here too: every fake
case is tagged `LOADTEST_...` and automatically cleaned up at the end
unless you pass `--no-cleanup`.

### Isolating the database pool from Gemini/Qdrant (`--db-only`)

Scenario A normally makes 3 real calls per simulated user, and 2 of
those 3 go out to Gemini. At high concurrency (e.g. 50 users at once),
that can mean up to 100 Gemini calls landing in the same few seconds
-- enough to trip Gemini's free-tier rate limit on its own, which then
makes it hard to tell whether a slow or failed result was caused by
your database pool or by Gemini being temporarily unavailable.

Add `--db-only` to strip Scenario A down to just the one pure database
read (no Gemini, no Qdrant, no rate-limit risk at all):

```
python load_test/phase3_concurrent_users.py --scenario a --levels-a 50 --db-only
```

Everything else about the test (the synchronized burst, the timing,
the results table) stays identical, so this is directly comparable to
a normal run -- it just removes Gemini/Qdrant as a possible source of
noise.

## Staggered arrivals — is the burst-test ceiling realistic? (`phase3_staggered_arrivals.py`)

The burst test above (`phase3_concurrent_users.py`, Scenario A) found
a real ceiling at concurrency 30-40: every run capped out at exactly
20 successes (your `DB_POOL_MAX_CONN` setting), with the rest failing
around the 5-second budget. That test is deliberately the harshest
possible case — every simulated user starts at the *exact same
instant*, which isn't quite how real practitioners open the app, even
during a busy moment.

`phase3_staggered_arrivals.py` re-runs the same reads, at the same
concurrency levels, but spreads each level's simulated users' start
times out over a window (5 seconds by default) instead of firing them
all at once. Everything else — the seed data, the database calls, the
results table — is identical and directly comparable to the burst
test's numbers.

Run it at the same levels that showed failures in the burst test:

```
python load_test/phase3_staggered_arrivals.py --levels 30,35,40
```

Try a more relaxed, 10-second arrival window:

```
python load_test/phase3_staggered_arrivals.py --levels 30,35,40 --window 10
```

This defaults to the same db-only mode as the comparable burst-test
run (so Gemini's rate limit can't muddy the comparison). Full option
list is in the comment block at the top of the file itself.

**How to read it:** compare each concurrency level's success/error
counts here against the same level from the burst test. If failures
drop or disappear once arrivals are spread out, that confirms the
ceiling was really about the artificial "everyone in the same
nanosecond" burst shape, not a real capacity problem. If the same
failure rate still shows up, that points to a genuine capacity limit
worth addressing before opening this up to more pilot users.

## A note on Gemini's free-tier rate limit

If your Gemini API key is on the free tier, it's limited to 100
embedding calls per minute. A high-concurrency Scenario A run (without
`--db-only`) or a large Confirmation Test B run can get close to or
exceed that limit on its own, causing embedding calls to fail with a
`429 RESOURCE_EXHAUSTED` error -- nothing to do with your database
pool, but it can look like a failure in the same results table. If you
see that error in your terminal output, it's worth waiting a minute or
two before re-running, or using `--db-only` (Scenario A) to sidestep
Gemini entirely.

## Testing what happens when a pooled connection actually breaks

`test_replacement_deadline.py` is a separate, narrower test. Every
other test in this folder has always run start-to-finish without a
single pooled connection ever actually going bad -- which is good news
for those tests, but it also means the part of `services/db_pool.py`
that notices a broken connection, throws it away, and gets a working
replacement (while making sure that replacement doesn't get a brand
new time budget of its own) has never actually been exercised by a
real test run.

This script deliberately breaks a handful of pooled connections on
purpose, then fires off several real requests at once so some of them
are forced to discover the break and go through the replacement code
path for real -- and reports whether the whole thing still finished
within the configured time budget.

```
python load_test/test_replacement_deadline.py
python load_test/test_replacement_deadline.py --poison 5 --concurrency 10
```

Full explanation of what it does and how to read the result is in the
comment block at the top of the file itself. This test doesn't write
any `LOADTEST_` data anywhere, so there's nothing to clean up
afterward.

## Files in this folder

- `_bootstrap.py` — quietly connects these scripts to the real app's
  code and your `.env` secrets. You never need to open this.
- `common.py` — shared helpers (timing, fake Claude responses, the
  results tracker). You never need to open this.
- `confirmation_test_a.py` — the realistic-mix test.
- `phase3_concurrent_users.py` — the burst-of-simultaneous-users test
  (Scenario A supports `--db-only` to isolate the database pool from
  Gemini/Qdrant — see above).
- `phase3_staggered_arrivals.py` — the same reads as Scenario A above,
  but with simulated users' start times spread out over a window
  instead of all firing at once — checks whether the burst test's
  ceiling is a realistic concern or an artifact of the "everyone at
  the same instant" test shape (see above).
- `confirmation_test_b.py` — tests whether documents submitted at the
  exact same instant all actually finish being indexed for search.
- `test_replacement_deadline.py` — deliberately breaks pooled
  connections to test the "replace a broken connection" path in
  `services/db_pool.py` (see above).
- `cleanup_synthetic_data.py` — deletes all `LOADTEST_` test data.
- `requirements.txt` — the extra packages this folder needs.
- `.env.example` — template for your secret keys (copy to `.env`).
- `.env` — your real secret keys (you create this; never shared, never uploaded to GitHub).