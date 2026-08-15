"""
cleanup_synthetic_data.py
==========================

WHAT THIS SCRIPT DOES (plain English)

Finds every fake case this load-testing toolkit ever created (every
case reference starting with "LOADTEST_"), and permanently deletes it
-- from your real database AND from your real Qdrant search index.

It NEVER touches anything that isn't tagged LOADTEST_. A real social
worker's case can never accidentally be deleted by this script,
because the search is always restricted to that exact tag.

HOW TO RUN IT

    python load_test/cleanup_synthetic_data.py

This deletes ALL LOADTEST_ data, from every past test run, not just
the most recent one. If you want to see what it would delete first
without actually deleting anything, use:

    python load_test/cleanup_synthetic_data.py --dry-run

Confirmation Test A already runs this automatically at the end of
every run (unless you passed --no-cleanup to it), so you normally
only need to run this by hand if you used --no-cleanup, or if a test
run was interrupted partway through (e.g. you closed the terminal).
"""

import argparse

import _bootstrap  # noqa: F401

from services.db_pool import get_conn
from services.qdrant_service import delete_document

import common


def _find_synthetic_draft_ids(conn, run_id_filter=None):
    like_pattern = (
        f"{common.SYNTHETIC_PREFIX}{run_id_filter}_%"
        if run_id_filter else f"{common.SYNTHETIC_PREFIX}%"
    )
    with conn.cursor() as c:
        c.execute("SELECT id FROM drafts WHERE case_ref LIKE %s", (like_pattern,))
        return [row[0] for row in c.fetchall()]


def _find_synthetic_user_names(conn, run_id_filter=None):
    like_pattern = (
        f"{common.SYNTHETIC_USER_PREFIX}{run_id_filter}_%"
        if run_id_filter else f"{common.SYNTHETIC_USER_PREFIX}%"
    )
    with conn.cursor() as c:
        c.execute("SELECT DISTINCT user_name FROM user_activity WHERE user_name LIKE %s", (like_pattern,))
        return [row[0] for row in c.fetchall()]


def run_cleanup(run_id_filter=None, dry_run=False):
    """
    Deletes every LOADTEST_ record. If run_id_filter is given (e.g.
    "ab12cd"), only that specific test run's data is deleted --
    otherwise ALL load-test data, from every run ever, is deleted.
    """
    conn = get_conn()
    try:
        draft_ids = _find_synthetic_draft_ids(conn, run_id_filter)
        user_names = _find_synthetic_user_names(conn, run_id_filter)

        print(f"Found {len(draft_ids)} synthetic draft(s) and {len(user_names)} synthetic user(s) to remove.")

        if dry_run:
            print("(--dry-run: nothing will actually be deleted)")
            return {"drafts_deleted": 0, "qdrant_deleted": 0, "users_deleted": 0}

        if not draft_ids and not user_names:
            print("Nothing to clean up.")
            return {"drafts_deleted": 0, "qdrant_deleted": 0, "users_deleted": 0}

        # 1. Remove each document from the real Qdrant search index
        # first (best-effort -- if a document was never successfully
        # indexed, or Qdrant isn't reachable, this just moves on; the
        # database cleanup below still happens regardless).
        qdrant_deleted = 0
        for draft_id in draft_ids:
            try:
                delete_document(draft_id)
                qdrant_deleted += 1
            except Exception as e:
                print(f"  (Qdrant cleanup note: could not remove draft {draft_id}: {e})")

        # 2. Remove database rows. draft_history has no automatic
        # cascade, so it must be cleared before drafts; the
        # context_prefetch_cache table DOES cascade automatically when
        # its draft is deleted, so nothing extra is needed for that one.
        with conn.cursor() as c:
            if draft_ids:
                c.execute("DELETE FROM draft_history WHERE draft_id = ANY(%s)", (draft_ids,))
                c.execute("DELETE FROM drafts WHERE id = ANY(%s)", (draft_ids,))
            if user_names:
                c.execute("DELETE FROM user_activity WHERE user_name = ANY(%s)", (user_names,))
        conn.commit()

        print(
            f"Cleanup complete: {len(draft_ids)} draft(s) removed from the database, "
            f"{qdrant_deleted} vector(s) removed from Qdrant, "
            f"{len(user_names)} synthetic user(s) removed."
        )
        return {
            "drafts_deleted": len(draft_ids),
            "qdrant_deleted": qdrant_deleted,
            "users_deleted": len(user_names),
        }
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Delete all LOADTEST_ synthetic data")
    parser.add_argument("--dry-run", action="store_true", help="Show counts without deleting anything")
    args = parser.parse_args()
    run_cleanup(dry_run=args.dry_run)
