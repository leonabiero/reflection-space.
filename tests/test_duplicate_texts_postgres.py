"""REAL-DATABASE tests for "one saved copy per text" (24 November 2026).

SKIPPED unless TEST_DATABASE_URL is set, e.g.

    TEST_DATABASE_URL=postgresql://user:pass@localhost/rs_test \\
        python -m pytest tests/test_duplicate_texts_postgres.py -v

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

TEXT = "Texto de prueba duplicado: la usuaria vive sola.\nNo tiene apoyo familiar."


@unittest.skipUnless(TEST_DATABASE_URL and psycopg2, "TEST_DATABASE_URL not set -- real-database tests skipped")
class DuplicateTextsRealDatabaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from services import db_schema
        cls._connect = staticmethod(lambda: psycopg2.connect(TEST_DATABASE_URL))
        db_schema._schema_ready = False
        with patch.object(db_schema, "get_conn", cls._connect):
            db_schema.ensure_schema()

    def setUp(self):
        from services import pattern_text_store, findings_store, reflection_records
        from services.text_fingerprint import text_fingerprint
        self.st = pattern_text_store
        self.fs = findings_store
        self.rr = reflection_records
        self.fp = text_fingerprint
        patches = [
            patch.object(pattern_text_store, "_get_conn", self._connect),
            patch.object(findings_store, "_get_conn", self._connect),
            patch.object(reflection_records, "_get_conn", self._connect),
            patch("services.audit_log.log_action", lambda *a, **k: None),
        ]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)
        self._n = 0
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
        self._sql("DELETE FROM reflection_runs WHERE created_by LIKE 'test_dup_%'")
        # Other test files may leave texts; only ours should be counted.
        self._sql("UPDATE reflection_runs SET original_text = NULL, text_fingerprint = NULL")

    def _save(self, text=TEXT, owner="test_dup_ana", language="Español"):
        self._n += 1
        code = f"RS-DUP{self._n:03d}"[:9]
        return self.fs.save_reflection_run(
            case_ref=code, source_draft_ids=[], language=language, prompt_version="v",
            model="m", module_status={}, findings=[], created_by=owner,
            created_by_role="Social Worker", reflection_code=code,
            original_text=text, text_fingerprint=self.fp(text),
        )

    def _saved_count(self):
        return self._sql("SELECT COUNT(*) FROM reflection_runs WHERE created_by LIKE 'test_dup_%'")[0][0]

    def test_identical_text_not_saved_twice(self):
        self.assertFalse(self._save()["duplicate"])
        self.assertTrue(self._save()["duplicate"])
        self.assertEqual(self._saved_count(), 1)

    def test_spacing_and_capitals_ignored(self):
        self._save()
        self.assertTrue(self._save("  " + TEXT.upper().replace("\n", "\n\n  "))["duplicate"])
        self.assertEqual(self._saved_count(), 1)

    def test_one_different_word_saved(self):
        self._save()
        self.assertFalse(self._save(TEXT.replace("sola", "acompañada"))["duplicate"])
        self.assertEqual(self._saved_count(), 2)

    def test_different_users_and_languages(self):
        self._save(owner="test_dup_ana", language="Español")
        self.assertTrue(self._save(owner="test_dup_mikel", language="Euskara")["duplicate"])
        self.assertTrue(self._save(owner="test_dup_jon", language="English")["duplicate"])
        self.assertEqual(self._saved_count(), 1)

    def test_text_in_the_bin_does_not_block_and_purge_frees_it(self):
        first = self._save()["run_id"]
        self.assertTrue(self.rr.delete_own_reflection(first, "test_dup_ana"))
        # A colleague's identical text is saved while the first waits in the bin.
        self.assertFalse(self._save(owner="test_dup_mikel")["duplicate"])
        # The bin empties: the first row (and its fingerprint) is gone.
        self._sql("UPDATE reflection_runs SET deleted_at = now() - interval '1000 hours' WHERE id = %s", (first,))
        self.rr.purge_expired_reflection_deletions()
        self.assertEqual(self._sql("SELECT COUNT(*) FROM reflection_runs WHERE id = %s", (first,))[0][0], 0)
        self.assertEqual(self._saved_count(), 1)

    def test_admin_delete_frees_the_text(self):
        run_id = self._save()["run_id"]
        self.assertTrue(self.rr.delete_reflection(run_id, "test_dup_admin", "System Administrator"))
        self.assertFalse(self._save()["duplicate"])

    def test_fifteen_month_cleanup_clears_fingerprint(self):
        from config import ORIGINAL_TEXT_RETENTION_MONTHS as months
        run_id = self._save()["run_id"]
        self._sql("UPDATE reflection_runs SET created_at = now() - make_interval(months => %s) WHERE id = %s",
                  (months + 1, run_id))
        self.rr.purge_expired_original_text()
        row = self._sql("SELECT original_text, text_fingerprint FROM reflection_runs WHERE id = %s", (run_id,))
        self.assertEqual(row, [(None, None)])
        self.assertFalse(self._save()["duplicate"])

    def test_erase_all_data_frees_the_text(self):
        # Emptying reflection_runs removes the fingerprints with the texts.
        self._save()
        self._sql("DELETE FROM reflection_runs WHERE created_by LIKE 'test_dup_%'")
        self.assertFalse(self._save()["duplicate"])

    def test_pattern_review_counts_copies_saved_before_the_change_once(self):
        # Two identical texts saved before the change (no fingerprint check).
        for owner in ("test_dup_ana", "test_dup_mikel"):
            self._n += 1
            self._sql(
                "INSERT INTO reflection_runs (case_ref, language, module_status, created_by, created_at, "
                "reflection_code, original_text) VALUES (%s, 'Español', '{}', %s, now(), %s, %s)",
                (f"RS-OLD{self._n}", owner, f"RS-OLD{self._n}", TEXT),
            )
        self._save(TEXT.replace("sola", "acompañada"))
        self.assertEqual(self.st.count_texts_for_period("Supervisor", 3), 3)  # before backfill
        from services.text_fingerprint import backfill_fingerprints
        conn = self._connect()
        try:
            backfill_fingerprints(conn)
        finally:
            conn.close()
        self.assertEqual(self.st.count_texts_for_period("Supervisor", 3), 2)
        self.assertEqual(len(self.st.texts_for_period("Supervisor", 3)), 2)
        # And no new copy can be added on top.
        self.assertTrue(self._save()["duplicate"])


if __name__ == "__main__":
    unittest.main()
