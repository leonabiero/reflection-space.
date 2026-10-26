"""REAL-DATABASE tests for the reflection-only redesign (REFLECTIONS.md).

SKIPPED unless TEST_DATABASE_URL is set, e.g.

    TEST_DATABASE_URL=postgresql://user:pass@localhost/rs_test \
        python -m pytest tests/test_reflection_records_postgres.py -v

Use a throwaway database: the tests create the app's tables and delete
the rows they create. No AI provider is involved.
"""
import os
import unittest
from unittest.mock import patch

TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL", "")

try:
    import psycopg2
except Exception:  # pragma: no cover
    psycopg2 = None


def _finding(module, observation, quote="cita"):
    return {"module": module, "observation": observation,
            "questions": ["¿Pregunta?"], "evidence": [{"quote": quote}]}


@unittest.skipUnless(TEST_DATABASE_URL and psycopg2, "TEST_DATABASE_URL not set -- real-database tests skipped")
class ReflectionRecordsRealDatabaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from services import db_schema
        cls._connect = staticmethod(lambda: psycopg2.connect(TEST_DATABASE_URL))
        db_schema._schema_ready = False
        with patch.object(db_schema, "get_conn", cls._connect):
            db_schema.ensure_schema()

    def setUp(self):
        from services import findings_store, draft_storage, reflection_records
        self.fs = findings_store
        self.ds = draft_storage
        self.rr = reflection_records
        patches = [
            patch.object(findings_store, "_get_conn", self._connect),
            patch.object(draft_storage, "_get_conn", self._connect),
            patch.object(reflection_records, "_get_conn", self._connect),
            patch.object(draft_storage, "delete_document", lambda *a, **k: None),
            patch.object(draft_storage, "log_action", lambda *a, **k: None),
            patch("services.audit_log.log_action", lambda *a, **k: None),
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
                c.execute("DELETE FROM draft_history WHERE draft_id IN (SELECT id FROM drafts WHERE created_by LIKE 'test_%')")
                c.execute("DELETE FROM drafts WHERE created_by LIKE 'test_%'")
            conn.commit()
        finally:
            conn.close()

    def _save(self, owner="test_alice", tags=(), previous="", findings=None, code=None):
        code = code or self.rr.generate_code()
        saved = self.fs.save_reflection_run(
            case_ref=code, source_draft_ids=[], language="Español",
            prompt_version="v", model="m", module_status={},
            findings=findings if findings is not None else [_finding("client_voice", "observación " + code)],
            created_by=owner, created_by_role="Social Worker",
            reflection_code=code, case_tags=list(tags), note_type="Nota de caso",
            previous_code=previous,
        )
        return code, saved["run_id"]

    # --- saving -----------------------------------------------------
    def test_identifiers_are_saved_and_codes_are_unique(self):
        code, run_id = self._save(tags=["housing", "mental_health"])
        own = self.rr.get_own_reflection(code, "test_alice")
        self.assertEqual(own["run_id"], run_id)
        self.assertEqual(own["case_tags"], ["housing", "mental_health"])
        self.assertEqual(own["note_type"], "Nota de caso")
        self.assertTrue(self.rr.code_exists(code))
        self.assertNotEqual(self.rr.new_reflection_code(), code)
        with self.assertRaises(Exception):
            self._save(code=code)

    def test_own_reflection_lookup_is_private(self):
        code, _ = self._save(owner="test_alice")
        self.assertIsNone(self.rr.get_own_reflection(code, "test_bob"))

    # --- similar reflections ------------------------------------------
    def test_similar_reflections_are_own_only_and_ranked(self):
        two_shared, _ = self._save(tags=["housing", "mental_health"])
        one_shared, _ = self._save(tags=["housing"])
        unrelated, _ = self._save(tags=["older_people"])
        self._save(owner="test_bob", tags=["housing", "mental_health"])

        found = self.rr.find_similar_reflections("test_alice", ["housing", "mental_health"])
        codes = [f["code"] for f in found]
        self.assertEqual(codes, [two_shared, one_shared])
        self.assertNotIn(unrelated, codes)
        self.assertEqual(found[0]["shared_tags"], ["housing", "mental_health"])
        # Observations only -- never quotes.
        self.assertNotIn("evidence", found[0]["observations"][0])

    def test_linked_chain_comes_first(self):
        first, _ = self._save(tags=["older_people"])
        second, _ = self._save(tags=["older_people"], previous=first)
        tagged, _ = self._save(tags=["housing"])
        found = self.rr.find_similar_reflections("test_alice", ["housing"], previous_code=second)
        self.assertEqual([f["code"] for f in found], [second, first, tagged])
        self.assertIn("linked", found[0]["match_reasons"])

    def test_exclude_and_empty_reflections_are_skipped(self):
        current, _ = self._save(tags=["housing"])
        self._save(tags=["housing"], findings=[])
        found = self.rr.find_similar_reflections("test_alice", ["housing"], exclude_code=current)
        self.assertEqual(found, [])

    # --- management view ----------------------------------------------
    def test_management_listing_is_role_gated_and_filtered(self):
        code, run_id = self._save(tags=["housing"])
        self._save(tags=["older_people"])
        self.assertEqual(self.rr.list_reflections("Social Worker"), [])
        self.assertEqual(self.rr.count_reflections("Social Worker"), 0)
        rows = self.rr.list_reflections("Supervisor", tag="housing", limit=500)
        mine = [r for r in rows if r["created_by"] == "test_alice"]
        self.assertEqual([r["code"] for r in mine], [code])
        findings = self.rr.get_findings_for_reflections("Programme Manager", [run_id])
        self.assertEqual(findings[run_id][0]["evidence"], [{"quote": "cita"}])
        self.assertEqual(self.rr.get_findings_for_reflections("Social Worker", [run_id]), {})
        self.assertTrue(self.rr.get_reflection_dates("Supervisor"))

    def test_only_system_administrator_can_delete(self):
        code, run_id = self._save()
        self.assertFalse(self.rr.delete_reflection(run_id, "test_sup", "Supervisor"))
        self.assertIsNotNone(self.rr.get_own_reflection(code, "test_alice"))
        self.assertTrue(self.rr.delete_reflection(run_id, "test_admin", "System Administrator"))
        self.assertIsNone(self.rr.get_own_reflection(code, "test_alice"))

    # --- knowledge assistant / metrics ----------------------------------
    def test_evidence_search_prefers_matching_words(self):
        self._save(findings=[_finding("client_voice", "La vivienda aparece descrita sin la voz de la persona")])
        self._save(findings=[_finding("possible_bias", "Texto sobre otra cuestión distinta")])
        results = self.rr.search_reflection_evidence("¿Qué se dice sobre vivienda?", limit=50)
        self.assertTrue(results)
        self.assertIn("vivienda", results[0]["content"].lower())
        self.assertGreater(results[0]["score"], 0)
        self.assertEqual(results[0]["doc_type"], "client_voice")

    def test_observation_count(self):
        before = self.rr.count_saved_observations()
        self._save()
        self.assertEqual(self.rr.count_saved_observations(), before + 1)

    # --- erasing the old stored documents --------------------------------
    def _old_document(self):
        conn = self._connect()
        try:
            with conn.cursor() as c:
                c.execute(
                    "INSERT INTO drafts (case_ref, doc_type, language, content, status, created_by, created_by_role) "
                    "VALUES ('CASE-OLD','Case note','Español','texto antiguo','completed','test_alice','Social Worker') "
                    "RETURNING id"
                )
                draft_id = c.fetchone()[0]
                c.execute("INSERT INTO draft_history (draft_id, content, saved_at) VALUES (%s, 'v1', now())", (draft_id,))
            conn.commit()
            return draft_id
        finally:
            conn.close()

    def test_erase_old_documents_keeps_new_reflections(self):
        old_draft = self._old_document()
        old_run = self.fs.save_reflection_run(
            "CASE-OLD", [old_draft], "Español", "v", "m", {},
            [_finding("client_voice", "antigua")], "test_alice", "Social Worker",
        )["run_id"]
        new_code, new_run = self._save()

        self.assertIsNone(self.ds.erase_all_stored_documents("test_sup", "Supervisor"))
        self.assertGreaterEqual(self.ds.count_all_stored_documents(), 1)

        erased = self.ds.erase_all_stored_documents("test_admin", "System Administrator")
        self.assertGreaterEqual(erased, 1)
        self.assertEqual(self.ds.count_all_stored_documents(), 0)

        conn = self._connect()
        try:
            with conn.cursor() as c:
                c.execute("SELECT id FROM reflection_runs WHERE id = ANY(%s)", ([old_run, new_run],))
                remaining = {r[0] for r in c.fetchall()}
                c.execute("SELECT COUNT(*) FROM draft_history WHERE draft_id = %s", (old_draft,))
                history = c.fetchone()[0]
        finally:
            conn.close()
        self.assertEqual(remaining, {new_run})
        self.assertEqual(history, 0)
        self.assertIsNotNone(self.rr.get_own_reflection(new_code, "test_alice"))


if __name__ == "__main__":
    unittest.main()
