"""REAL-DATABASE tests for Pattern Review texts and reports (15 November 2026).

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
        self._sql("DELETE FROM pattern_texts")
        self._sql("DELETE FROM pattern_reports WHERE created_by LIKE 'test_%'")
        self._sql("DELETE FROM reflection_runs WHERE created_by LIKE 'test_%'")

    def _copy(self, n, months_ago=0):
        code = f"{CODE_PREFIX}{n:02d}"
        self.assertTrue(self.st.save_pattern_text(code, "Español", f"Texto anonimizado {n} de [PERSON]."))
        if months_ago:
            self._sql("UPDATE pattern_texts SET created_at = now() - make_interval(months => %s) "
                      "WHERE reflection_code = %s", (months_ago, code))
        return code

    def _run_for(self, code, owner="test_alice"):
        return self.fs.save_reflection_run(
            case_ref=code, source_draft_ids=[], language="Español", prompt_version="v",
            model="m", module_status={}, findings=[], created_by=owner,
            created_by_role="Social Worker", reflection_code=code,
        )["run_id"]

    def test_copy_holds_no_author_and_is_saved_once(self):
        code = self._copy(1)
        self.assertFalse(self.st.save_pattern_text(code, "Español", "otra vez"))
        columns = {r[0] for r in self._sql(
            "SELECT column_name FROM information_schema.columns WHERE table_name = 'pattern_texts'")}
        self.assertEqual(columns, {"id", "reflection_code", "language", "anonymised_text", "created_at"})
        self.assertFalse(self.st.save_pattern_text(code + "X", "Español", "   "))

    def test_texts_for_period_carry_only_language_and_text(self):
        for n in range(3):
            self._copy(n)
        self._copy(7, months_ago=4)
        texts = self.st.texts_for_period("Supervisor", 3)
        self.assertEqual(len(texts), 3)
        self.assertEqual(set(texts[0]), {"language", "text"})
        self.assertEqual(self.st.count_texts_for_period("Programme Manager", 3), 3)
        self.assertEqual(self.st.count_texts_for_period("Supervisor", 6), 4)

    def test_only_management_roles_can_read(self):
        self._copy(1)
        for role in ("Social Worker", "System Administrator", ""):
            self.assertEqual(self.st.count_texts_for_period(role, 3), 0)
            with self.assertRaises(PermissionError):
                self.st.texts_for_period(role, 3)
            self.assertEqual(self.st.list_reports(role), [])
        with self.assertRaises(ValueError):
            self.st.count_texts_for_period("Supervisor", 5)

    def test_copies_older_than_13_months_are_never_used_then_deleted(self):
        from config import PATTERN_TEXT_RETENTION_MONTHS as months
        self._copy(1)
        old = self._copy(2, months_ago=months + 1)
        self.assertEqual(self.st.count_texts_for_period("Supervisor", 12), 1)
        self.assertGreaterEqual(self.st.purge_expired_pattern_texts(), 1)
        self.assertEqual(self._sql("SELECT COUNT(*) FROM pattern_texts WHERE reflection_code = %s", (old,))[0][0], 0)

    def test_deleted_reflection_is_left_out_at_once_and_its_copy_erased_later(self):
        from config import DELETION_WINDOW_HOURS
        code = self._copy(1)
        self._copy(2)
        run_id = self._run_for(code)
        self.assertEqual(self.st.count_texts_for_period("Supervisor", 3), 2)
        self.assertTrue(self.rr.delete_own_reflection(run_id, "test_alice"))
        self.assertEqual(self.st.count_texts_for_period("Supervisor", 3), 1)
        self.assertTrue(self.rr.restore_own_reflection(run_id, "test_alice"))
        self.assertEqual(self.st.count_texts_for_period("Supervisor", 3), 2)
        self.assertTrue(self.rr.delete_own_reflection(run_id, "test_alice"))
        self._sql("UPDATE reflection_runs SET deleted_at = now() - make_interval(hours => %s) WHERE id = %s",
                  (DELETION_WINDOW_HOURS + 1, run_id))
        self.rr.purge_expired_reflection_deletions()
        self.assertEqual(self._sql("SELECT COUNT(*) FROM pattern_texts WHERE reflection_code = %s", (code,))[0][0], 0)

    def test_administrator_deletion_erases_the_copy(self):
        code = self._copy(1)
        run_id = self._run_for(code)
        self.assertTrue(self.rr.delete_reflection(run_id, "test_admin", "System Administrator"))
        self.assertEqual(self._sql("SELECT COUNT(*) FROM pattern_texts WHERE reflection_code = %s", (code,))[0][0], 0)

    def test_failed_reflection_copy_can_be_discarded(self):
        code = self._copy(1)
        self.assertTrue(self.st.discard_pattern_text(code))
        self.assertFalse(self.st.discard_pattern_text(code))

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
