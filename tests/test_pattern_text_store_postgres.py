"""REAL-DATABASE tests for Pattern Review texts and reports (15 November 2026).

Pattern Review reads the saved ORIGINAL texts (reflection_runs.original_text);
no separate copy is kept.

SKIPPED unless TEST_DATABASE_URL is set, e.g.

    TEST_DATABASE_URL=postgresql://user:pass@localhost/rs_test \\
        python -m pytest tests/test_pattern_text_store_postgres.py -v

Use a throwaway database: the tests create the app's tables and delete the
rows they create. No AI provider is involved.
"""
import os
import unittest
from unittest.mock import patch

TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL", "")

try:
    import psycopg2
except Exception:  # pragma: no cover
    psycopg2 = None

CODE_PREFIX = "RS-TST"


@unittest.skipUnless(TEST_DATABASE_URL and psycopg2, "TEST_DATABASE_URL not set -- real-database tests skipped")
class PatternTextStoreRealDatabaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from services import db_schema
        cls._connect = staticmethod(lambda: psycopg2.connect(TEST_DATABASE_URL))
        db_schema._schema_ready = False
        with patch.object(db_schema, "get_conn", cls._connect):
            db_schema.ensure_schema()

    def setUp(self):
        from services import pattern_text_store, findings_store, reflection_records
        self.st = pattern_text_store
        self.fs = findings_store
        self.rr = reflection_records
        patches = [
            patch.object(pattern_text_store, "_get_conn", self._connect),
            patch.object(findings_store, "_get_conn", self._connect),
            patch.object(reflection_records, "_get_conn", self._connect),
            patch("services.audit_log.log_action", lambda *a, **k: None),
        ]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)
        self._clean()
        self.addCleanup(self._clean)

    def _sql(self, sql, params=()):
        conn = self._connect()
        try:
            with conn.cursor() as c:
                c.execute(sql, params or None)
                rows = c.fetchall() if c.description else None
            conn.commit()
            return rows
        finally:
            conn.close()

    def _clean(self):
        # Other test files may leave reflections; count only ours.
        self._sql("DELETE FROM pattern_reports WHERE created_by LIKE 'test_%'")
        self._sql("DELETE FROM reflection_runs WHERE created_by LIKE 'test_%'")
        self._sql("UPDATE reflection_runs SET original_text = NULL")

    def _reflection(self, n, text=None, months_ago=0, owner="test_alice"):
        code = f"{CODE_PREFIX}{n:02d}"
        run_id = self.fs.save_reflection_run(
            case_ref=code, source_draft_ids=[], language="Español", prompt_version="v",
            model="m", module_status={}, findings=[], created_by=owner,
            created_by_role="Social Worker", reflection_code=code,
            original_text=text if text is not None else f"Texto original {n} de Juan.",
        )["run_id"]
        if months_ago:
            self._sql("UPDATE reflection_runs SET created_at = now() - make_interval(months => %s) WHERE id = %s",
                      (months_ago, run_id))
        return run_id

    def test_texts_for_period_carry_only_language_and_text(self):
        for n in range(3):
            self._reflection(n)
        self._reflection(7, months_ago=4)
        self._reflection(8, text="   ")
        texts = self.st.texts_for_period("Supervisor", 3)
        self.assertEqual(len(texts), 3)
        self.assertEqual(set(texts[0]), {"language", "text"})
        self.assertNotIn("test_alice", str(texts))
        self.assertNotIn(CODE_PREFIX, str(texts))
        self.assertEqual(self.st.count_texts_for_period("Programme Manager", 3), 3)
        self.assertEqual(self.st.count_texts_for_period("Supervisor", 6), 4)

    def test_only_management_roles_can_read(self):
        self._reflection(1)
        for role in ("Social Worker", "System Administrator", ""):
            self.assertEqual(self.st.count_texts_for_period(role, 3), 0)
            with self.assertRaises(PermissionError):
                self.st.texts_for_period(role, 3)
            self.assertEqual(self.st.list_reports(role), [])
        with self.assertRaises(ValueError):
            self.st.count_texts_for_period("Supervisor", 5)

    def test_texts_past_their_time_limit_are_never_used(self):
        from config import ORIGINAL_TEXT_RETENTION_MONTHS as months
        self._reflection(1)
        self._reflection(2, months_ago=months + 1)
        self.assertEqual(self.st.count_texts_for_period("Supervisor", 12), 1)

    def test_deleted_reflection_is_left_out_at_once(self):
        run_id = self._reflection(1)
        self._reflection(2)
        self.assertEqual(self.st.count_texts_for_period("Supervisor", 3), 2)
        self.assertTrue(self.rr.delete_own_reflection(run_id, "test_alice"))
        self.assertEqual(self.st.count_texts_for_period("Supervisor", 3), 1)
        self.assertTrue(self.rr.restore_own_reflection(run_id, "test_alice"))
        self.assertEqual(self.st.count_texts_for_period("Supervisor", 3), 2)
        self.assertTrue(self.rr.delete_reflection(run_id, "test_admin", "System Administrator"))
        self.assertEqual(self.st.count_texts_for_period("Supervisor", 3), 1)

    def test_reports_are_saved_and_listed_newest_first(self):
        first = self.st.save_report("Supervisor", "test_boss", 3, 6, "Español",
                                    {"overview": "uno", "patterns": [], "limitations": []})
        second = self.st.save_report("Programme Manager", "test_boss", 12, 40, "English",
                                     {"overview": "dos", "patterns": [], "limitations": []})
        listed = [r for r in self.st.list_reports("Supervisor") if r["id"] in (first, second)]
        self.assertEqual([r["id"] for r in listed], [second, first])
        self.assertEqual(listed[0]["period_months"], 12)
        self.assertEqual(listed[0]["texts_count"], 40)
        self.assertEqual(listed[0]["report"]["overview"], "dos")
        with self.assertRaises(PermissionError):
            self.st.save_report("Social Worker", "test_x", 3, 6, "Español", {})


if __name__ == "__main__":
    unittest.main()
