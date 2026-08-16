"""
confirmation_test_b.py -- Embedding Reliability Under Concurrent Submission
============================================================================

WHAT THIS TEST IS FOR (plain English)

When a social worker finishes writing a note, the app doesn't just
save the text -- it also sends it to Google's Gemini service to be
turned into a search "fingerprint" (an embedding), which then gets
stored in Qdrant, the search database. That fingerprint is what makes
the Knowledge Assistant and historical case search actually work
later. A document that saves fine but fails this step is invisible
to search forever, with nothing visibly wrong about it in the normal
app screens (this is the same class of problem the "859 embedding
failures" finding was about).

Confirmation Test A (confirmation_test_a.py) already tests many
practitioners using the app at once, including some real finalize
calls -- but its users are spread out over a whole session (login,
browse, save, maybe finalize), so their finalize_draft() calls don't
all land at the exact same instant.

THIS test is narrower and more deliberate: it makes N synthetic
practitioners submit (finalize) a completed document at the EXACT
SAME MOMENT, over and over at increasing group sizes, and checks
afterward -- for every single one of those documents -- whether its
embedding actually succeeded, failed, or was skipped. This is the
one specific gap flagged after reviewing Phase 2 (data volume, one
document at a time) and Phase 3 (concurrent reads + a fully-mocked
Claude scenario): neither of those tests concurrent embedding WRITES.

WHAT IT COSTS

Every finalize_draft() call in this test is REAL -- it makes a real
Gemini embedding call and a real Qdrant write, exactly what a real
practitioner submission does. This is not free, but it is cheap: each
call embeds one short synthetic note, the same modest cost as any
other embedding call the real app already makes. This test makes
ZERO Claude/Anthropic API calls (embedding is a Gemini feature, not
Claude), so it has no effect on Claude usage or cost.

HOW TO READ THE RESULTS

For each concurrency level tested, you'll see:
  - How many finalize_draft() calls succeeded vs failed vs timed out
    (a timeout means the call never came back within 30 seconds --
    a real reliability problem in itself, not just a slow one).
  - Of the documents that DID finalize, how many actually ended up
    marked "indexed" (embedding really worked) vs "failed" (embedding
    was attempted and did not succeed) vs "not_applicable" (Qdrant
    wasn't configured for this run -- shouldn't happen if your
    load_test/.env has a real QDRANT_URL, but shown just in case).

A healthy result looks like: 100% finalized, 100% of those "indexed",
at every concurrency level tested. Any "failed" or timed-out count
above zero is a genuine reliability problem worth taking seriously
before the pilot -- not a formatting nitpick.

HOW TO RUN IT

    python load_test/confirmation_test_b.py
    python load_test/confirmation_test_b.py --levels 5,10,20
    python load_test/confirmation_test_b.py --no-cleanup

By default this tests group sizes 5, 10, and 20 practitioners
submitting at once. Every LOADTEST_-tagged document this run creates
is automatically deleted (Postgres + Qdrant) at the end, unless you
pass --no-cleanup.
"""

import argparse
import threading
import concurrent.futures

import _bootstrap  # noqa: F401  (sets up imports + loads .env -- must run first)

from services.draft_storage import save_draft, finalize_draft
from services.db_pool import get_conn

import common

DOC_TYPE = "LOADTEST_DOC_TYPE"
LANGUAGE = "Español"

# How long a single finalize_draft() call is allowed to run before
# this test gives up on it and counts it as a timeout, same value
# confirmation_test_a.py uses for its per-action timeout.
FINALIZE_TIMEOUT_SECONDS = 30


def _check_embedding_statuses(draft_ids):
    """
    Looks up, directly in the database, what actually happened to
    each of the given draft_ids' embedding attempt. Returns a dict
    counting how many landed in each status:
      indexed        -- embedding + Qdrant write genuinely succeeded
      failed         -- embedding was attempted and did not succeed
      not_applicable -- Qdrant wasn't configured for this run
      missing        -- the draft_id isn't in the database at all
                        (its own save/finalize must have failed
                        before embedding was even attempted)
    """
    if not draft_ids:
        return {"indexed": 0, "failed": 0, "not_applicable": 0, "missing": 0}

    conn = get_conn()
    try:
        with conn.cursor() as c:
            c.execute(
                "SELECT id, embedding_status FROM drafts WHERE id = ANY(%s)",
                (list(draft_ids),),
            )
            rows = c.fetchall()
    finally:
        conn.close()

    found = {row[0]: row[1] for row in rows}
    counts = {"indexed": 0, "failed": 0, "not_applicable": 0, "missing": 0}
    for draft_id in draft_ids:
        status = found.get(draft_id, None)
        if draft_id not in found:
            counts["missing"] += 1
        elif status == "indexed":
            counts["indexed"] += 1
        elif status == "failed":
            counts["failed"] += 1
        elif status == "not_applicable":
            counts["not_applicable"] += 1
        else:
            # Anything unexpected (e.g. still NULL, which shouldn't
            # happen since finalize_draft() records an outcome before
            # returning) -- counted separately so it's never silently
            # dropped from the tally.
            counts.setdefault(f"unexpected({status!r})", 0)
            counts[f"unexpected({status!r})"] += 1
    return counts


def _prepare_one_document(user_label, run_id):
    """
    Creates (but does not yet finalize) one synthetic pending draft,
    ready to be submitted in the synchronized burst below. Returns
    (draft_id, case_ref, user_name, content), or (None, ..., ..., ...)
    if even the initial save failed (counted as its own kind of
    failure, separate from an embedding failure).
    """
    case_ref = common.synthetic_case_ref(user_label, run_id)
    user_name = common.synthetic_user_name(user_label, run_id)
    content = common.random_note_text()
    try:
        draft_id = save_draft(
            case_ref=case_ref, doc_type=DOC_TYPE, language=LANGUAGE,
            content=content, created_by=user_name, created_by_role="Social Worker",
        )
    except Exception as e:  # noqa: BLE001
        print(f"    [prep] save_draft FAILED for {user_name!r}: {e!r}")
        return None, case_ref, user_name, content
    return draft_id, case_ref, user_name, content


def run_one_level(level, run_id, metrics):
    print(f"\n--- {level} simultaneous submissions ---")

    print(f"  Preparing {level} pending draft(s)...")
    prepared = []
    for i in range(level):
        draft_id, case_ref, user_name, content = _prepare_one_document(f"b{level}_{i}", run_id)
        prepared.append((draft_id, case_ref, user_name, content))
    ready = [p for p in prepared if p[0] is not None]
    prep_failures = level - len(ready)
    if prep_failures:
        print(f"  WARNING: {prep_failures} draft(s) failed to even save -- these are excluded from the finalize burst below.")

    if not ready:
        print("  No drafts were successfully prepared at this level -- skipping.")
        return []

    barrier = threading.Barrier(len(ready))

    def _submit(draft_id, case_ref, user_name, content):
        barrier.wait()  # every thread calls finalize_draft() at (as close to) the same instant
        r = common.timed_with_timeout(finalize_draft, draft_id, content, user_name, timeout=FINALIZE_TIMEOUT_SECONDS)
        metrics.record("finalize_draft", r["elapsed"], r["success"], r["timed_out"], r["error"])
        status = "ok" if r["success"] else ("TIMEOUT" if r["timed_out"] else "FAILED")
        print(f"    [draft {draft_id}] finalize_draft: {status} ({r['elapsed']:.1f}s)")
        return draft_id

    finalized_draft_ids = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(ready)) as executor:
        futures = [executor.submit(_submit, *p) for p in ready]
        for f in futures:
            finalized_draft_ids.append(f.result())

    print(f"  Checking what actually happened to embedding for all {len(finalized_draft_ids)} document(s)...")
    counts = _check_embedding_statuses(finalized_draft_ids)
    print(f"  Embedding outcome at {level} simultaneous submissions:")
    print(f"    indexed (success):        {counts.get('indexed', 0)}")
    print(f"    failed:                   {counts.get('failed', 0)}")
    print(f"    not_applicable (Qdrant not configured for this run): {counts.get('not_applicable', 0)}")
    print(f"    missing (never even saved/finalized):                {counts.get('missing', 0)}")
    for key, value in counts.items():
        if key.startswith("unexpected(") and value:
            print(f"    {key}: {value}")

    if counts.get("failed", 0) or any(k.startswith("unexpected(") for k in counts):
        print(f"    ^ Genuine embedding reliability problem at this concurrency level -- worth investigating before the pilot.")

    return finalized_draft_ids


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--levels", default="5,10,20", help="Comma-separated group sizes to test, e.g. 5,10,20")
    parser.add_argument("--no-cleanup", action="store_true", help="Skip automatic cleanup at the end (inspect the data yourself)")
    args = parser.parse_args()

    levels = [int(s.strip()) for s in args.levels.split(",") if s.strip()]
    run_id = common.new_run_id()

    print("\nStarting Confirmation Test B -- Embedding Reliability Under Concurrent Submission")
    print(f"  Concurrency levels to test: {levels}")
    print(f"  Run tag (for this batch of fake data): LOADTEST_{run_id}")
    print(f"  Per-finalize timeout: {FINALIZE_TIMEOUT_SECONDS}.0s")

    metrics = common.Metrics()
    all_draft_ids = []
    for level in levels:
        all_draft_ids.extend(run_one_level(level, run_id, metrics))

    metrics.print_summary(thresholds={
        "finalize_draft": {"pass": 5.0, "warn": 15.0},
    })

    if args.no_cleanup:
        print(
            f"--no-cleanup was set: this run's LOADTEST_{run_id} data was left in place.\n"
            f"    To remove it later, run:\n"
            f"    python load_test/cleanup_synthetic_data.py\n"
        )
    else:
        print("Cleaning up this run's synthetic data now...\n")
        import cleanup_synthetic_data
        cleanup_synthetic_data.run_cleanup(run_id_filter=run_id)


if __name__ == "__main__":
    main()