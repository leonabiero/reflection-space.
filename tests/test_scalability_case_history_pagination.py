"""
Phase 3 (Scalability & Performance) regression tests.

pages/case_history.py's "All dates" view is the one screen in the app
whose data grows continuously for the entire life of the pilot -- every
completed document, from every social worker, accumulates there
forever. It now asks services.draft_storage.get_completed_drafts() for
only the most recently completed CASE_HISTORY_MAX_RESULTS documents
(config.py), plus a separate cheap COUNT(*) via
get_completed_draft_count(), instead of loading every completed
document (full text included) org-wide on every visit.

These tests check the underlying capability the page now depends on:
  1. get_completed_drafts(limit=N) actually bounds how many rows come
     back, and returns the N MOST RECENTLY COMPLETED documents (not an
     arbitrary N), even when far more than N exist.
  2. get_completed_draft_count() reports the TRUE total regardless of
     any limit -- this is what lets the page show an accurate "showing
     X of Y" note.
  3. The CASE_HISTORY_MAX_RESULTS / CASE_HISTORY_FEEDBACK_MAX_RESULTS
     bounds are actually configured (a regression here would silently
     turn the cap into "no limit" again, which is exactly the bug
     being fixed).

This does not re-test get_feedback_summary() -- see
tests/test_scalability_feedback_summary.py for that.
"""

import unittest
from unittest.mock import patch

from services import draft_storage
import config


def _make_draft_row(i):
    # Matches the column order get_completed_drafts() selects:
    # id, case_ref, doc_type, content, created_at, created_by,
    # created_by_role, was_edited, completed_at
    completed_at = f"2026-01-{(i % 27) + 1:02d}T00:00:00+00:00"
    return (
        i,
        f"CASE-{i}",
        "Case note",
        f"content {i}",
        completed_at,
        "worker",
        "Social Worker",
        False,
        completed_at,
        i,  # sort key only, stripped before returning to caller
    )


class _FakeCursor:
    def __init__(self, rows):
        # rows already sorted most-recently-completed first, exactly
        # as the real `ORDER BY completed_at DESC` query would return
        # them.
        self.rows = rows
        self._result = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def execute(self, sql, params=None):
        normalized = " ".join(sql.split()).upper()
        params = params or ()

        if normalized.startswith("SELECT COUNT(*) FROM DRAFTS WHERE STATUS='COMPLETED'"):
            self._result = ("one", (len(self.rows),))
            return

        if normalized.startswith("SELECT ID, CASE_REF"):
            result_rows = [row[:9] for row in self.rows]
            if "LIMIT %S OFFSET %S" in normalized:
                limit, offset = params[-2], params[-1]
                result_rows = result_rows[offset:offset + limit]
            self._result = ("many", result_rows)
            return

        raise AssertionError(f"Unexpected SQL in fake database: {sql}")

    def fetchone(self):
        kind, value = self._result
        assert kind == "one"
        return value

    def fetchall(self):
        kind, value = self._result
        assert kind == "many"
        return value


class _FakeConnection:
    def __init__(self, rows):
        self.cursor_obj = _FakeCursor(rows)

    def cursor(self):
        return self.cursor_obj

    def close(self):
        pass


class _FakeDB:
    def __init__(self, row_count):
        # Build rows most-recently-completed first, matching the real
        # ORDER BY completed_at DESC query.
        self.rows = [_make_draft_row(i) for i in range(row_count, 0, -1)]

    def connection(self):
        return _FakeConnection(self.rows)


class CaseHistoryPaginationScalabilityTests(unittest.TestCase):
    def test_config_bounds_are_configured_and_positive(self):
        # A regression here (e.g. the constant silently becoming None
        # or 0) would turn the cap back into "no limit" or "no results
        # at all" -- both defeat the fix.
        self.assertIsInstance(config.CASE_HISTORY_MAX_RESULTS, int)
        self.assertGreater(config.CASE_HISTORY_MAX_RESULTS, 0)
        self.assertIsInstance(config.CASE_HISTORY_FEEDBACK_MAX_RESULTS, int)
        self.assertGreater(config.CASE_HISTORY_FEEDBACK_MAX_RESULTS, 0)

    def test_limit_bounds_result_count_far_below_total_volume(self):
        # Simulate an organisation-wide volume well beyond the cap --
        # this is the exact scenario that used to make Case History's
        # "All dates" view unboundedly slow and memory-heavy.
        total_documents = config.CASE_HISTORY_MAX_RESULTS * 5
        db = _FakeDB(total_documents)

        with patch.object(draft_storage, "_get_conn", side_effect=db.connection):
            capped = draft_storage.get_completed_drafts(limit=config.CASE_HISTORY_MAX_RESULTS)
            total_count = draft_storage.get_completed_draft_count()

        self.assertEqual(len(capped), config.CASE_HISTORY_MAX_RESULTS)
        self.assertEqual(total_count, total_documents)
        self.assertGreater(total_count, len(capped))

    def test_limit_returns_the_most_recently_completed_documents(self):
        # It must always be the NEWEST documents that are kept visible
        # by default, not an arbitrary subset -- an admin/manager cares
        # about recent activity most.
        db = _FakeDB(config.CASE_HISTORY_MAX_RESULTS + 50)

        with patch.object(draft_storage, "_get_conn", side_effect=db.connection):
            capped = draft_storage.get_completed_drafts(limit=config.CASE_HISTORY_MAX_RESULTS)

        returned_ids = {row[0] for row in capped}
        # Rows were built with the highest id = most recently completed
        # (see _FakeDB), so the newest CASE_HISTORY_MAX_RESULTS ids must
        # be exactly what came back.
        expected_ids = set(
            range(config.CASE_HISTORY_MAX_RESULTS + 50, 50, -1)
        )
        self.assertEqual(returned_ids, expected_ids)

    def test_no_limit_still_returns_everything_for_other_callers(self):
        # Existing call sites that don't pass `limit` (e.g. the
        # single-date filtered view, or rdi/retrieval_service.py's
        # per-case lookups) must see zero behaviour change.
        db = _FakeDB(37)

        with patch.object(draft_storage, "_get_conn", side_effect=db.connection):
            unbounded = draft_storage.get_completed_drafts()

        self.assertEqual(len(unbounded), 37)

    def test_count_is_unaffected_by_any_limit_used_elsewhere(self):
        db = _FakeDB(1234)

        with patch.object(draft_storage, "_get_conn", side_effect=db.connection):
            draft_storage.get_completed_drafts(limit=10)
            total_count = draft_storage.get_completed_draft_count()

        self.assertEqual(total_count, 1234)


if __name__ == "__main__":
    unittest.main()
