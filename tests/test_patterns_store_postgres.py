"""REAL-DATABASE tests for the pattern explorer (Stage 2).

Skipped unless TEST_DATABASE_URL is set (see test_findings_store_postgres.py).
No AI provider is called: embeddings and explanations are replaced by
simple fakes; the database SQL is real.
"""
import os
import unittest
from unittest.mock import patch

TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL", "")
try:
    import psycopg2
except Exception:  # pragma: no cover
    psycopg2 = None

SUP, PM, ADMIN, SW = "Supervisor", "Programme Manager", "System Administrator", "Social Worker"


@unittest.skipUnless(TEST_DATABASE_URL and psycopg2, "TEST_DATABASE_URL not set -- real-database tests skipped")
class PatternsRealDatabaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from services import db_schema
        cls._connect = staticmethod(lambda: psycopg2.connect(TEST_DATABASE_URL))
        db_schema._schema_ready = False
        with patch.object(db_schema, "get_conn", cls._connect):
            db_schema.ensure_schema()

    def setUp(self):
        from services import findings_store, draft_storage, pattern_store, pattern_service
        self.fs, self.ds, self.ps, self.svc = findings_store, draft_storage, pattern_store, pattern_service
        for mod in (findings_store, draft_storage, pattern_store):
            p = patch.object(mod, "_get_conn", self._connect)
            p.start(); self.addCleanup(p.stop)
        for target, name, repl in ((draft_storage, "delete_document", lambda *a, **k: None),
                                   (draft_storage, "log_action", lambda *a, **k: None)):
            p = patch.object(target, name, repl)
            p.start(); self.addCleanup(p.stop)
        self._clean(); self.addCleanup(self._clean)

    def _clean(self):
        conn = self._connect()
        try:
            with conn.cursor() as c:
                c.execute("DELETE FROM pattern_runs")
                c.execute("DELETE FROM reflection_runs WHERE created_by LIKE 'test_%'")
                c.execute("DELETE FROM drafts WHERE created_by LIKE 'test_%'")
            conn.commit()
        finally:
            conn.close()

    # ---- helpers ----
    def _draft(self, owner, status="draft", deleted_hours_ago=None):
        conn = self._connect()
        try:
            with conn.cursor() as c:
                c.execute("INSERT INTO drafts (case_ref, doc_type, language, content, status, created_by, created_by_role) "
                          "VALUES ('X','Case note','Español','t',%s,%s,'Social Worker') RETURNING id", (status, owner))
                did = c.fetchone()[0]
                if deleted_hours_ago is not None:
                    c.execute("UPDATE drafts SET status='deleted', deleted_at = now() - (%s || ' hours')::interval WHERE id=%s",
                              (str(deleted_hours_ago), did))
            conn.commit()
            return did
        finally:
            conn.close()

    def _observation(self, owner, text, case_ref="", share=True, module="client_voice", draft_id=None):
        """One reflection with one observation; returns (finding_id, draft_id)."""
        did = draft_id or self._draft(owner)
        saved = self.fs.save_reflection_run(
            case_ref, [did], "Español", "v", "m", {module: "finding"},
            [{"module": module, "observation": text, "questions": ["¿?"],
              "evidence": [{"quote": "cita exacta"}]}], owner, SW)
        fid = saved["finding_ids"][module]
        if share:
            self.assertTrue(self.fs.upsert_feedback(fid, owner, shared_with_team=True))
        return fid, did

    def _vec(self, ids_to_vec):
        return lambda text: ids_to_vec(text)

    def _generate(self, role=SUP, **kw):
        # observations whose text starts with 'A' are alike; 'B' are alike
        def fake_embed(text):
            return [1.0, 0.05] if text.startswith("A") else [0.05, 1.0]
        fake_explained = lambda obs, labels, lang: {
            "explanation": {"title": "Tema", "description": "d", "why_it_matters": "w",
                            "alternative_explanations": ["a"], "limitations": ["l"], "questions": ["q1", "q2"]},
            "status": "ai"}
        with patch.object(self.svc.embedding_service, "is_available", lambda: True), \
             patch.object(self.svc.embedding_service, "embed_document", fake_embed), \
             patch.object(self.svc, "explain_pattern", fake_explained):
            return self.svc.generate_patterns(role, "test_mgr", "Español", {"client_voice": "Voz"}, **kw)

    def _three_shared(self, prefix="A"):
        return [self._observation(f"test_u{i}", f"{prefix} observación {i}", case_ref=f"C{i}")[0] for i in range(3)]

    # ---- access ----
    def test_only_supervisors_and_programme_managers_may_use_it(self):
        self._three_shared()
        self.assertEqual(len(self.ps.get_shared_findings(SUP)), 3)
        self.assertEqual(len(self.ps.get_shared_findings(PM)), 3)
        for role in (ADMIN, SW, "", None, "supervisor"):
            with self.assertRaises(PermissionError):
                self.ps.get_shared_findings(role)
            with self.assertRaises(PermissionError):
                self.ps.get_pool_counts(role)
            with self.assertRaises(PermissionError):
                self.svc.generate_patterns(role, "x", "Español", {})

    # ---- privacy ----
    def test_only_shared_observations_appear_and_never_with_author_or_notes(self):
        shared, _ = self._observation("test_alice", "A compartida", share=True)
        private, _ = self._observation("test_bob", "A privada", share=False)
        self.fs.upsert_feedback(shared, "test_alice", "useful", "NOTA PRIVADA SECRETA")
        rows = self.ps.get_shared_findings(SUP)
        self.assertEqual([r["id"] for r in rows], [shared])
        flat = repr(rows) + repr(self.ps.get_pool_counts(SUP))
        for secret in ("test_alice", "NOTA PRIVADA", "test_bob"):
            self.assertNotIn(secret, flat)
        for row in rows:
            self.assertFalse({"created_by", "user", "author", "note", "feedback"} & set(row))

    def test_sharing_is_the_authors_choice_and_can_be_withdrawn(self):
        fid, _ = self._observation("test_alice", "A uno", share=False)
        self.assertEqual(self.ps.get_shared_findings(SUP), [])
        self.assertFalse(self.fs.upsert_feedback(fid, "test_bob", shared_with_team=True))
        self.assertEqual(self.ps.get_shared_findings(SUP), [])
        self.assertTrue(self.fs.upsert_feedback(fid, "test_alice", shared_with_team=True))
        self.assertEqual(len(self.ps.get_shared_findings(SUP)), 1)
        # saving a private note afterwards must not silently change sharing
        self.assertTrue(self.fs.upsert_feedback(fid, "test_alice", "useful", "nota"))
        self.assertEqual(len(self.ps.get_shared_findings(SUP)), 1)
        self.assertTrue(self.fs.upsert_feedback(fid, "test_alice", shared_with_team=False))
        self.assertEqual(self.ps.get_shared_findings(SUP), [])

    def test_observations_awaiting_deletion_leave_the_pool_immediately(self):
        fid, did = self._observation("test_alice", "A uno")
        self.assertEqual(len(self.ps.get_shared_findings(SUP)), 1)
        conn = self._connect()
        with conn, conn.cursor() as c:
            c.execute("UPDATE drafts SET status='deleted', deleted_at=now() WHERE id=%s", (did,))
        conn.close()
        self.assertEqual(self.ps.get_shared_findings(SUP), [])
        self.assertEqual(self.ps.get_pool_counts(SUP)["observations"], 0)

    # ---- counts ----
    def test_pool_counts_are_honest(self):
        d = self._draft("test_a")
        self._observation("test_a", "A 1", case_ref=" Caso  1 ", draft_id=d)
        self._observation("test_b", "A 2", case_ref="caso 1")
        self._observation("test_c", "A 3", case_ref="")
        counts = self.ps.get_pool_counts(SUP)
        self.assertEqual((counts["observations"], counts["reflections"], counts["cases"],
                          counts["reflections_without_case"]), (3, 3, 1, 1))

    # ---- generation ----
    def test_generation_makes_one_pattern_from_alike_observations(self):
        self._three_shared("A")
        self._observation("test_x", "B otra cosa", case_ref="Z")
        result = self._generate()
        self.assertEqual((result["status"], result["patterns_created"], result["fallback_count"]), ("completed", 1, 0))
        patterns = self.ps.list_patterns(SUP, result["run_id"])
        self.assertEqual(len(patterns), 1)
        counts = patterns[0]["counts"]
        self.assertEqual((counts["observations"], counts["reflections"], counts["cases"]), (3, 3, 3))
        self.assertTrue(counts["case_recurrence_known"])
        self.assertEqual(patterns[0]["status"], "candidate")
        self.assertEqual(patterns[0]["lost_members"], 0)

    def test_too_few_or_same_reflection_makes_no_pattern(self):
        d = self._draft("test_a")
        saved = self.fs.save_reflection_run("C", [d], "Español", "v", "m", {"client_voice": "finding"},
                                            [{"module": "client_voice", "observation": "A solo", "questions": ["¿?"]}],
                                            "test_a", SW)
        self.fs.upsert_feedback(saved["finding_ids"]["client_voice"], "test_a", shared_with_team=True)
        result = self._generate()
        self.assertEqual((result["status"], result["patterns_created"]), ("completed", 0))

    def test_only_one_generation_can_run_at_once(self):
        first = self.ps.start_run(SUP, "test_m", {}, "Español", "e", "m", "p")
        self.assertIsNotNone(first)
        self.assertIsNone(self.ps.start_run(PM, "test_n", {}, "Español", "e", "m", "p"))
        busy = self._generate()
        self.assertEqual(busy["status"], "busy")
        self.ps.finish_run(first, "completed")
        self.assertIsNotNone(self.ps.start_run(PM, "test_n", {}, "Español", "e", "m", "p"))

    def test_unavailable_embedding_service_is_reported_not_crashed(self):
        with patch.object(self.svc.embedding_service, "is_available", lambda: False):
            self.assertEqual(self.svc.generate_patterns(SUP, "x", "Español", {})["status"], "unavailable")

    def test_failure_marks_run_failed_not_running(self):
        self._three_shared()
        with patch.object(self.svc.embedding_service, "is_available", lambda: True), \
             patch.object(self.svc.pattern_store, "get_cached_embeddings", side_effect=RuntimeError("boom")):
            with self.assertRaises(RuntimeError):
                self.svc.generate_patterns(SUP, "x", "Español", {})
        conn = self._connect()
        with conn.cursor() as c:
            c.execute("SELECT status FROM pattern_runs ORDER BY id DESC LIMIT 1")
            self.assertEqual(c.fetchone()[0], "failed")
        conn.close()
        self.assertIsNotNone(self.ps.start_run(SUP, "x", {}, "Español", "e", "m", "p"))

    def test_embeddings_are_cached_so_regeneration_does_not_repay(self):
        self._three_shared()
        calls = []
        def counting_embed(text):
            calls.append(text); return [1.0, 0.05]
        explained = lambda o, l, g: {"explanation": {"title": "T", "description": "d", "why_it_matters": "w",
                                     "alternative_explanations": ["a"], "limitations": ["l"], "questions": ["1", "2"]}, "status": "ai"}
        with patch.object(self.svc.embedding_service, "is_available", lambda: True), \
             patch.object(self.svc.embedding_service, "embed_document", counting_embed), \
             patch.object(self.svc, "explain_pattern", explained):
            self.svc.generate_patterns(SUP, "x", "Español", {})
            self.assertEqual(len(calls), 3)
            self.svc.generate_patterns(SUP, "x", "Español", {})
            self.assertEqual(len(calls), 3)

    # ---- withdrawal / erasure ----
    def test_withdrawn_observation_leaves_the_pattern_and_is_flagged(self):
        ids = self._three_shared()
        run = self._generate()["run_id"]
        self.fs.upsert_feedback(ids[0], "test_u0", shared_with_team=False)
        pattern = self.ps.list_patterns(SUP, run)[0]
        self.assertEqual(len(pattern["members"]), 2)
        self.assertEqual(pattern["lost_members"], 1)
        self.assertTrue(pattern["below_minimum"])
        self.assertNotIn(ids[0], [m["id"] for m in pattern["members"]])

    def test_pattern_with_no_remaining_members_disappears(self):
        ids = self._three_shared()
        run = self._generate()["run_id"]
        for i, fid in enumerate(ids):
            self.fs.upsert_feedback(fid, f"test_u{i}", shared_with_team=False)
        self.assertEqual(self.ps.list_patterns(SUP, run), [])

    def test_permanent_erasure_removes_empty_patterns_and_data(self):
        drafts = []
        for i in range(3):
            fid, did = self._observation(f"test_u{i}", f"A obs {i}", case_ref=f"C{i}")
            drafts.append(did)
        run = self._generate()["run_id"]
        conn = self._connect()
        with conn, conn.cursor() as c:
            c.execute("UPDATE drafts SET status='deleted', deleted_at = now() - interval '72 hours' WHERE id = ANY(%s)", (drafts,))
        conn.close()
        self.ds.purge_expired_deletions()
        conn = self._connect()
        with conn.cursor() as c:
            for table in ("patterns", "pattern_findings", "finding_embeddings"):
                c.execute(f"SELECT COUNT(*) FROM {table}")
                self.assertEqual(c.fetchone()[0], 0, table)
            c.execute("SELECT COUNT(*) FROM pattern_events")
        conn.close()
        self.assertEqual(self.ps.list_patterns(SUP, run), [])

    # ---- review ----
    def test_review_is_recorded_in_history_and_ai_text_is_unchanged(self):
        self._three_shared()
        run = self._generate()["run_id"]
        pattern = self.ps.list_patterns(SUP, run)[0]
        self.assertTrue(self.ps.set_pattern_status(SUP, "test_mgr", pattern["id"], "worth_discussing", "Comentar el martes"))
        self.assertFalse(self.ps.set_pattern_status(SUP, "test_mgr", pattern["id"], "bogus"))
        self.assertFalse(self.ps.set_pattern_status(SUP, "test_mgr", 999999, "archived"))
        after = self.ps.list_patterns(SUP, run)[0]
        self.assertEqual(after["status"], "worth_discussing")
        for key in ("title", "description", "why_it_matters", "alternative_explanations", "limitations", "questions"):
            self.assertEqual(after[key], pattern[key])
        kinds = [e["kind"] for e in self.ps.get_pattern_events(SUP, pattern["id"])]
        self.assertEqual(kinds, ["generated", "status_changed"])
        with self.assertRaises(PermissionError):
            self.ps.set_pattern_status(SW, "x", pattern["id"], "archived")
        with self.assertRaises(PermissionError):
            self.ps.get_pattern_events(ADMIN, pattern["id"])

    def test_excluding_and_restoring_a_member(self):
        ids = self._three_shared()
        run = self._generate()["run_id"]
        pid = self.ps.list_patterns(SUP, run)[0]["id"]
        self.assertTrue(self.ps.set_member_excluded(SUP, "m", pid, ids[0], True, "no encaja"))
        p = self.ps.list_patterns(SUP, run)[0]
        self.assertEqual((len(p["members"]), len(p["excluded_members"]), p["lost_members"]), (2, 1, 0))
        self.assertTrue(self.ps.set_member_excluded(SUP, "m", pid, ids[0], False))
        self.assertEqual(len(self.ps.list_patterns(SUP, run)[0]["members"]), 3)

    def test_review_carries_over_to_the_next_generation(self):
        self._three_shared()
        first = self._generate()["run_id"]
        pid = self.ps.list_patterns(SUP, first)[0]["id"]
        self.ps.set_pattern_status(SUP, "m", pid, "worth_discussing")
        second = self._generate()["run_id"]
        again = self.ps.list_patterns(SUP, second)[0]
        self.assertEqual(again["status"], "worth_discussing")
        kinds = [e["kind"] for e in self.ps.get_pattern_events(SUP, again["id"])]
        self.assertIn("carried_over", kinds)
        # the earlier snapshot is untouched
        self.assertEqual(len(self.ps.list_patterns(SUP, first)), 1)

    def test_fallback_explanation_can_be_replaced_but_ai_one_cannot(self):
        self._three_shared()
        fallback = lambda o, l, g: {"explanation": {"title": "Plano", "description": "d", "why_it_matters": "w",
                                    "alternative_explanations": ["a"], "limitations": ["l"], "questions": ["1", "2"]}, "status": "fallback"}
        with patch.object(self.svc.embedding_service, "is_available", lambda: True), \
             patch.object(self.svc.embedding_service, "embed_document", lambda t: [1.0, 0.05]), \
             patch.object(self.svc, "explain_pattern", fallback):
            result = self.svc.generate_patterns(SUP, "x", "Español", {})
        self.assertEqual(result["fallback_count"], 1)
        pattern = self.ps.list_patterns(SUP, result["run_id"])[0]
        self.assertEqual(pattern["explanation_status"], "fallback")
        good = {"title": "Real", "description": "d", "why_it_matters": "w", "alternative_explanations": ["a"],
                "limitations": ["l"], "questions": ["1", "2"]}
        self.assertTrue(self.ps.update_pattern_explanation(SUP, "m", pattern["id"], good))
        self.assertEqual(self.ps.list_patterns(SUP, result["run_id"])[0]["title"], "Real")
        self.assertFalse(self.ps.update_pattern_explanation(SUP, "m", pattern["id"], good))


if __name__ == "__main__":
    unittest.main()
