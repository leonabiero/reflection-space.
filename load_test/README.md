# Load Testing Toolkit — Confirmation Test A

This folder contains the tools for **Confirmation Test A**: finding
out how Reflection Space behaves when many social workers use it at
the same time, doing a realistic mix of things (not everyone doing
the exact same single action at once — that was already tested
separately).

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

## Files in this folder

- `_bootstrap.py` — quietly connects these scripts to the real app's
  code and your `.env` secrets. You never need to open this.
- `common.py` — shared helpers (timing, fake Claude responses, the
  results tracker). You never need to open this.
- `confirmation_test_a.py` — the test itself. This is the one you run.
- `cleanup_synthetic_data.py` — deletes all `LOADTEST_` test data.
- `requirements.txt` — the extra packages this folder needs.
- `.env.example` — template for your secret keys (copy to `.env`).
- `.env` — your real secret keys (you create this; never shared, never uploaded to GitHub).
