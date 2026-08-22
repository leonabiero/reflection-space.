"""
Phase 3 (Scalability & Performance) regression tests.

services.feedback_store.get_feedback_summary() used to read every row
of the `feedback` table -- rating AND the full comment text -- into
Python just to add numbers up. That grows slower and heavier with
every feedback submission ever made, forever, with no ceiling, and it
transfers comment text across the wire that is never actually needed
(only whether a comment is non-empty).

These tests check two things at once:
  1. The four numbers get_feedback_summary() returns are still exactly
     correct (same rounding, same treatment of NULL ratings and
     blank/whitespace-only comments) -- a behavioural check, not a
     source-formatting one.
  2. The function never issues a query that would pull every row's
     `comment` text across the wire -- i.e. it stays a small,
     constant-cost aggregate query no matter how much feedback has
     accumulated. This is the actual regression this test protects
     against: a future edit accidentally reverting to a full
     `SELECT ... comment FROM feedback` scan.
"""

import unittest
from unittest.mock import patch

from services import feedback_store


class _FakeCursor:
    def __init__(self, rows):
        # rows: list of (rating, comment) tuples, exactly as stored.
        self.rows = rows
        self._result = None
        self.queries = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def execute(self, sql, params=None):
        normalized = " ".join(sql.split()).upper()
        self.queries.append(normalized)
        params = params or ()

        if normalized.startswith("SELECT COUNT(*) AS TOTAL_COUNT"):
            total_count = len(self.rows)
            rated = [r for r, c in self.rows if r is not None]
            avg_rating = (sum(rated) / len(rated)) if rated else None
            comment_count = sum(
                1 for _, c in self.rows if c is not None and c.strip() != ""
            )
            self._result = ("fetchone", (total_count, avg_rating, comment_count))
            return

        if normalized.startswith("SELECT RATING, COUNT(*)") and "GROUP BY RATING" in normalized:
            counts = {}
            for rating, _ in self.rows:
                if rating is not None and 1 <= rating <= 5:
                    counts[rating] = counts.get(rating, 0) + 1
            self._result = ("fetchall", list(counts.items()))
            return

        # Anything else -- most importantly, a full-table row/comment
        # pull like "SELECT rating, comment FROM feedback" with no
        # aggregation -- is exactly the regression this test guards
        # against.
        raise AssertionError(
            f"get_feedback_summary() issued an unexpected (non-aggregate) "
            f"query -- this looks like a regression back to pulling every "
            f"row into Python: {sql}"
        )

    def fetchone(self):
        kind, value = self._result
        assert kind == "fetchone"
        return value

    def fetchall(self):
        kind, value = self._result
        assert kind == "fetchall"
        return value


class _FakeConnection:
    def __init__(self, rows):
        self.cursor_obj = _FakeCursor(rows)

    def cursor(self):
        return self.cursor_obj

    def close(self):
        pass


class _FakeDB:
    def __init__(self, rows):
        self.rows = rows
        self.last_connection = None

    def connection(self):
        self.last_connection = _FakeConnection(self.rows)
        return self.last_connection


class FeedbackSummaryScalabilityTests(unittest.TestCase):
    def test_empty_table(self):
        db = _FakeDB([])
        with patch.object(feedback_store, "_get_conn", side_effect=db.connection):
            summary = feedback_store.get_feedback_summary()

        self.assertEqual(summary["count"], 0)
        self.assertIsNone(summary["average"])
        self.assertEqual(summary["distribution"], {1: 0, 2: 0, 3: 0, 4: 0, 5: 0})
        self.assertEqual(summary["comment_count"], 0)

    def test_matches_manual_python_computation_at_moderate_volume(self):
        # A representative mix: full range of ratings, some blank
        # comments, some whitespace-only comments (must NOT count),
        # some no comment at all.
        rows = (
            [(5, "Really helpful")] * 40
            + [(4, "")] * 15
            + [(4, "   ")] * 5
            + [(3, None)] * 20
            + [(2, "Not very useful")] * 10
            + [(1, "Confusing")] * 5
        )
        db = _FakeDB(rows)
        with patch.object(feedback_store, "_get_conn", side_effect=db.connection):
            summary = feedback_store.get_feedback_summary()

        expected_ratings = [r for r, _ in rows if r is not None]
        expected_average = sum(expected_ratings) / len(expected_ratings)
        expected_comment_count = sum(
            1 for _, c in rows if c and c.strip()
        )

        self.assertEqual(summary["count"], len(rows))
        self.assertAlmostEqual(summary["average"], expected_average)
        self.assertEqual(summary["comment_count"], expected_comment_count)
        self.assertEqual(summary["distribution"], {1: 5, 2: 10, 3: 20, 4: 20, 5: 40})

    def test_large_volume_stays_a_small_constant_number_of_queries(self):
        # The real-world scalability concern: even at a feedback volume
        # far beyond anything realistic for this pilot, the function
        # must still complete via exactly two aggregate queries -- not
        # one query per row, and not a full-table row-by-row scan.
        rows = [(((i % 5) + 1), f"comment {i}" if i % 3 == 0 else "") for i in range(20000)]
        db = _FakeDB(rows)
        with patch.object(feedback_store, "_get_conn", side_effect=db.connection):
            summary = feedback_store.get_feedback_summary()

        self.assertEqual(summary["count"], 20000)
        # Exactly two queries were issued for the whole call -- the
        # aggregate COUNT/AVG query and the GROUP BY distribution
        # query -- never one per row, and never a full row/comment scan
        # (any other query shape would already have raised above).
        self.assertEqual(len(db.last_connection.cursor_obj.queries), 2)


if __name__ == "__main__":
    unittest.main()
