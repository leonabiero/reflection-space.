"""REAL-DATABASE tests for the saved-findings feature.

These run the actual SQL in services/findings_store.py and the two
permanent-deletion paths in services/draft_storage.py against a real
PostgreSQL database. They are SKIPPED unless TEST_DATABASE_URL is set, e.g.

    TEST_DATABASE_URL=postgresql://user:pass@localhost/rs_test \
        python -m pytest tests/test_findings_store_postgres.py -v

Use a throwaway database: the tests create the app's tables and delete
rows they create. No AI provider is involved (nothing is mocked about the
database; only the vector-index deletion and the audit log are stubbed).
"""
import os
import unittest
from datetime import timedelta
from unittest.mock import patch

TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL", "")

try:
    import psycopg2
except Exception:  # pragma: no cover
    psycopg2 = None


@unittest.skipUnless(TEST_DATABASE_URL and psycopg2, "TEST_DATABASE_URL not set -- real-database tests skipped")
class FindingsStoreRealDatabaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from services import db_schema
        cls.db_schema = db_schema
        cls._connect = staticmethod(lambda: psycopg2.connect(TEST_DATABASE_URL))
        db_schema._schema_ready = False
        with patch.object(db_schema, "get_conn", cls._connect):
            db_schema.ensure_schema()

    def setUp(self):
        from services import findings_store, draft_storage
        self.fs = findings_store
        self.ds = draft_storage
        patches = [
            patch.object(findings_store, "_get_conn", self._connect),
            patch.object(draft_storage, "_get_conn", self._connect),
            patch.object(draft_storage, "delete_document", lambda *a, **k: None),
            patch.object(draft_storage, "log_action", lambda *a, **k: None),
        ]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)
        self._clean()
        self.addCleanup(self._clean)

    def _clean(self):
        conn = self._connect()
        try:
            with conn.cursor() as c:
                c.execute("DELETE FROM reflection_runs WHERE created_by LIKE 'test_%'")
                c.execute("DELETE FROM drafts WHERE created_by LIKE 'test_%'")
            conn.commit()
        finally:
            conn.close()

    # ---- helpers ----------------------------------------------------
    def _draft(self, owner="test_alice", status="draft", deleted_hours_ago=None):
        conn = self._connect()
        try:
            with conn.cursor() as c:
                c.execute(
                    "INSERT INTO drafts (case_ref, doc_type, language, content, status, created_by, created_by_role) "
                    "VALUES ('CASE-1','Case note','Español','texto',%s,%s,'Social Worker') RETURNING id",
                    (status, owner),
                )
                draft_id = c.fetchone()[0]
                if deleted_hours_ago is not None:
                    c.execute(
                        "UPDATE drafts SET status='deleted', deleted_at = now() - (%s || ' hours')::interval WHERE id=%s",
                        (str(deleted_hours_ago), draft_id),
                    )
            conn.commit()
            return draft_id
        finally:
            conn.close()

    def _save(self, owner="test_alice", draft_ids=(), findings=None, case_ref="CASE-1"):
        findings = findings if findings is not None else [
            {"module": "client_voice", "observation": "Observación con ñ, á y ü.",
             "questions": ["¿Qué ha dicho ella?"],
             "evidence": [{"quote": "quiere vivir cerca de su hermana"}], "unverified_quote_count": 1},
            {"module": "possible_bias", "observation": "Ikuspegi bat.", "questions": ["Zer?"],
             "evidence": [], "unverified_quote_count": 0},
        ]
        return self.fs.save_reflection_run(
            case_ref, list(draft_ids), "Español", "v-test", "model-test",
            {"client_voice": "finding", "possible_bias": "finding", "continuity": "no_finding"},
            findings, owner, "Social Worker",
        )

    def _count(self, table, where="TRUE", params=()):
        conn = self._connect()
        try:
            with conn.cursor() as c:
                c.execute(f"SELECT COUNT(*) FROM {table} WHERE {where}", params)
                return c.fetchone()[0]
        finally:
            conn.close()

    # ---- saving and reading ----------------------------------------
    def test_findings_persist_and_round_trip_exactly(self):
        saved = self._save()
        self.assertEqual(set(saved["finding_ids"]), {"client_voice", "possible_bias"})
        rows = self.fs.get_my_findings("test_alice")
        by_module = {r["module"]: r for r in rows}
        voice = by_module["client_voice"]
        self.assertEqual(voice["observation"], "Observación con ñ, á y ü.")
        self.assertEqual(voice["questions"], ["¿Qué ha dicho ella?"])
        self.assertEqual(voice["evidence"], [{"quote": "quiere vivir cerca de su hermana"}])
        self.assertEqual(voice["unverified_quote_count"], 1)
        self.assertEqual(voice["prompt_version"], "v-test")
        self.assertEqual(by_module["possible_bias"]["observation"], "Ikuspegi bat.")
        self.assertEqual(self.fs.count_my_findings("test_alice"), 2)

    def test_empty_module_creates_no_finding_but_is_recorded_in_status(self):
        saved = self._save(findings=[])
        self.assertEqual(saved["finding_ids"], {})
        self.assertEqual(self.fs.count_my_findings("test_alice"), 0)
        self.assertEqual(self._count("reflection_runs", "id=%s", (saved["run_id"],)), 1)

    def test_save_is_atomic_nothing_is_left_if_a_finding_fails(self):
        before = self._count("reflection_runs", "created_by='test_alice'")
        bad = [
            {"module": "client_voice", "observation": "ok", "questions": [], "evidence": [], "unverified_quote_count": 0},
            {"module": "possible_bias", "observation": "bad", "questions": [], "evidence": [],
             "unverified_quote_count": 10 ** 12},   # out of range for an integer column
        ]
        with self.assertRaises(Exception):
            self._save(findings=bad)
        self.assertEqual(self._count("reflection_runs", "created_by='test_alice'"), before)
        self.assertEqual(self._count("reflection_findings", "observation IN ('ok','bad')"), 0)

    def test_one_finding_per_module_per_run(self):
        dup = [
            {"module": "client_voice", "observation": "first", "questions": [], "evidence": []},
            {"module": "client_voice", "observation": "second", "questions": [], "evidence": []},
        ]
        saved = self._save(findings=dup)
        self.assertEqual(len(saved["finding_ids"]), 1)
        self.assertEqual(self.fs.get_my_findings("test_alice")[0]["observation"], "first")

    def test_invalid_findings_are_not_stored(self):
        junk = [
            {"module": "not_a_module", "observation": "x", "questions": ["q"]},
            {"module": "continuity", "observation": "", "questions": []},
            "not a dict",
        ]
        self.assertEqual(self._save(findings=junk)["finding_ids"], {})

    def test_created_by_is_required(self):
        with self.assertRaises(ValueError):
            self.fs.save_reflection_run("C", [], "Español", "v", "m", {}, [], "", "")

    # ---- privacy ----------------------------------------------------
    def test_one_professional_cannot_see_anothers_findings_or_notes(self):
        saved = self._save(owner="test_alice")
        fid = saved["finding_ids"]["client_voice"]
        self.assertTrue(self.fs.upsert_feedback(fid, "test_alice", "useful", "private note"))
        self.assertEqual(self.fs.get_my_findings("test_bob"), [])
        self.assertEqual(self.fs.count_my_findings("test_bob"), 0)
        self.assertEqual(self.fs.get_feedback_for_findings("test_bob", [fid]), {})
        self.assertEqual(self.fs.get_my_findings("", limit=5), [])

    def test_only_the_author_can_write_feedback(self):
        fid = self._save(owner="test_alice")["finding_ids"]["client_voice"]
        self.assertFalse(self.fs.upsert_feedback(fid, "test_bob", "useful", "x"))
        self.assertEqual(self._count("finding_feedback"), 0)
        self.assertFalse(self.fs.upsert_feedback(999999999, "test_alice", "useful", "x"))
        self.assertFalse(self.fs.upsert_feedback(fid, "", "useful", "x"))

    # ---- feedback ---------------------------------------------------
    def test_feedback_saves_updates_and_never_touches_the_ai_finding(self):
        fid = self._save()["finding_ids"]["client_voice"]
        before = self.fs.get_my_findings("test_alice")
        original = next(r for r in before if r["id"] == fid)

        self.assertTrue(self.fs.upsert_feedback(
            fid, "test_alice", "discuss", "mi nota", "otra explicación", True))
        fb = self.fs.get_feedback_for_findings("test_alice", [fid])[fid]
        self.assertEqual((fb["label"], fb["note"], fb["alternative_explanation"], fb["flagged_misread"]),
                         ("discuss", "mi nota", "otra explicación", True))

        self.assertTrue(self.fs.upsert_feedback(fid, "test_alice", "useful", "nota 2", "", False))
        fb = self.fs.get_feedback_for_findings("test_alice", [fid])[fid]
        self.assertEqual((fb["label"], fb["note"], fb["flagged_misread"]), ("useful", "nota 2", False))
        self.assertEqual(self._count("finding_feedback", "finding_id=%s", (fid,)), 1)   # replaced, not duplicated

        after = next(r for r in self.fs.get_my_findings("test_alice") if r["id"] == fid)
        for key in ("observation", "questions", "evidence", "module", "prompt_version"):
            self.assertEqual(after[key], original[key])          # AI text untouched
        self.assertEqual(after["feedback"]["note"], "nota 2")     # shown next to it

    def test_invalid_label_is_refused_and_empty_label_is_allowed(self):
        fid = self._save()["finding_ids"]["client_voice"]
        self.assertFalse(self.fs.upsert_feedback(fid, "test_alice", "definitely-true", "x"))
        self.assertTrue(self.fs.upsert_feedback(fid, "test_alice", "", "solo nota"))
        self.assertIsNone(self.fs.get_feedback_for_findings("test_alice", [fid])[fid]["label"])

    def test_overlong_notes_are_capped(self):
        fid = self._save()["finding_ids"]["client_voice"]
        self.fs.upsert_feedback(fid, "test_alice", "useful", "n" * 10000, "a" * 10000)
        fb = self.fs.get_feedback_for_findings("test_alice", [fid])[fid]
        self.assertEqual(len(fb["note"]), self.fs.MAX_NOTE_CHARS)
        self.assertEqual(len(fb["alternative_explanation"]), self.fs.MAX_ALTERNATIVE_CHARS)

    # ---- manual retry -----------------------------------------------
    def test_add_finding_to_run_owner_only_and_updates_status(self):
        saved = self._save(findings=[], draft_ids=[])
        run_id = saved["run_id"]
        finding = {"module": "continuity", "observation": "late", "questions": ["q"], "evidence": []}
        self.assertIsNone(self.fs.add_finding_to_run(run_id, finding, "test_bob"))
        new_id = self.fs.add_finding_to_run(run_id, finding, "test_alice")
        self.assertIsNotNone(new_id)
        self.assertIsNone(self.fs.add_finding_to_run(run_id, finding, "test_alice"))  # already has one
        conn = self._connect()
        try:
            with conn.cursor() as c:
                c.execute("SELECT module_status FROM reflection_runs WHERE id=%s", (run_id,))
                self.assertIn('"continuity": "finding"', c.fetchone()[0])
        finally:
            conn.close()

    # ---- deletion ---------------------------------------------------
    def test_deleting_a_pending_draft_erases_its_findings_and_notes_but_not_others(self):
        d1, d2 = self._draft(), self._draft()
        run1 = self._save(draft_ids=[d1])
        run2 = self._save(draft_ids=[d2])
        self.fs.upsert_feedback(run1["finding_ids"]["client_voice"], "test_alice", "useful", "n")
        self.fs.upsert_feedback(run2["finding_ids"]["client_voice"], "test_alice", "useful", "n")
        self.assertEqual(self._count("finding_feedback"), 2)

        self.assertTrue(self.ds.delete_pending_draft(d1, "test_alice", "Social Worker"))

        self.assertEqual(self._count("reflection_runs", "id=%s", (run1["run_id"],)), 0)
        self.assertEqual(self._count("reflection_findings", "run_id=%s", (run1["run_id"],)), 0)
        self.assertEqual(self._count("reflection_run_sources", "run_id=%s", (run1["run_id"],)), 0)
        self.assertEqual(self._count("finding_feedback", "finding_id=%s", (run1["finding_ids"]["client_voice"],)), 0)
        # the other document's run is untouched
        self.assertEqual(self._count("reflection_runs", "id=%s", (run2["run_id"],)), 1)
        self.assertEqual(self._count("finding_feedback", "finding_id=%s", (run2["finding_ids"]["client_voice"],)), 1)

    def test_refused_pending_deletion_by_a_non_owner_keeps_findings(self):
        d = self._draft(owner="test_alice")
        run = self._save(draft_ids=[d])
        self.assertFalse(self.ds.delete_pending_draft(d, "test_bob", "Supervisor"))
        self.assertEqual(self._count("reflection_runs", "id=%s", (run["run_id"],)), 1)

    def test_findings_are_hidden_during_the_deletion_window_and_return_on_restore(self):
        d = self._draft(status="completed")
        self._save(draft_ids=[d])
        self.assertEqual(self.fs.count_my_findings("test_alice"), 2)

        conn = self._connect()
        try:
            with conn.cursor() as c:
                c.execute("UPDATE drafts SET status='deleted', deleted_at=now() WHERE id=%s", (d,))
            conn.commit()
        finally:
            conn.close()
        self.assertEqual(self.fs.count_my_findings("test_alice"), 0)
        self.assertEqual(self.fs.get_my_findings("test_alice"), [])

        conn = self._connect()
        try:
            with conn.cursor() as c:
                c.execute("UPDATE drafts SET status='completed', deleted_at=NULL WHERE id=%s", (d,))
            conn.commit()
        finally:
            conn.close()
        self.assertEqual(self.fs.count_my_findings("test_alice"), 2)

    def test_permanent_purge_erases_findings_only_after_the_window(self):
        from config import DELETION_WINDOW_HOURS
        fresh = self._draft(status="completed", deleted_hours_ago=1)
        expired = self._draft(status="completed", deleted_hours_ago=DELETION_WINDOW_HOURS + 5)
        run_fresh = self._save(draft_ids=[fresh])
        run_expired = self._save(draft_ids=[expired])

        self.ds.purge_expired_deletions()

        self.assertEqual(self._count("reflection_runs", "id=%s", (run_expired["run_id"],)), 0)
        self.assertEqual(self._count("reflection_findings", "run_id=%s", (run_expired["run_id"],)), 0)
        # still inside its restore window: kept (but hidden from the author)
        self.assertEqual(self._count("reflection_runs", "id=%s", (run_fresh["run_id"],)), 1)

    def test_run_that_used_a_purged_document_as_history_is_erased_too(self):
        from config import DELETION_WINDOW_HOURS
        current = self._draft(status="completed")
        history = self._draft(status="completed", deleted_hours_ago=DELETION_WINDOW_HOURS + 5)
        run = self._save(draft_ids=[current, history])

        self.ds.purge_expired_deletions()

        self.assertEqual(self._count("drafts", "id=%s", (current,)), 1)      # current document survives
        self.assertEqual(self._count("reflection_runs", "id=%s", (run["run_id"],)), 0)  # but quotes might be from history

    def test_pagination_returns_newest_first_without_overlap(self):
        for i in range(5):
            self._save(findings=[{"module": "continuity", "observation": f"obs {i}", "questions": [], "evidence": []}])
        page1 = self.fs.get_my_findings("test_alice", limit=2, offset=0)
        page2 = self.fs.get_my_findings("test_alice", limit=2, offset=2)
        page3 = self.fs.get_my_findings("test_alice", limit=2, offset=4)
        observations = [r["observation"] for r in page1 + page2 + page3]
        self.assertEqual(observations, ["obs 4", "obs 3", "obs 2", "obs 1", "obs 0"])


if __name__ == "__main__":
    unittest.main()
