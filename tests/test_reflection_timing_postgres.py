"""REAL-DATABASE tests for Reflect step timing (services/reflection_timing.py).

SKIPPED unless TEST_DATABASE_URL is set, e.g.

    TEST_DATABASE_URL=postgresql://user:pass@localhost/rs_test \
        python -m pytest tests/test_reflection_timing_postgres.py -v

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


@unittest.skipUnless(TEST_DATABASE_URL and psycopg2, "TEST_DATABASE_URL not set -- real-database tests skipped")
class ReflectionTimingRealDatabaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from services import db_schema
        cls._connect = staticmethod(lambda: psycopg2.connect(TEST_DATABASE_URL))
        db_schema._schema_ready = False
        with patch.object(db_schema, "get_conn", cls._connect):
            db_schema.ensure_schema()

    def setUp(self):
        from services import reflection_timing, findings_store, reflection_records
        self.rt = reflection_timing
        self.fs = findings_store
        self.rr = reflection_records
        patches = [
            patch.object(reflection_timing, "_get_conn", self._connect),
            patch.object(findings_store, "_get_conn", self._connect),
            patch.object(reflection_records, "_get_conn", self._connect),
            patch("services.audit_log.log_action", lambda *a, **k: None),
        ]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)
        self._clean()
        self.addCleanup(self._clean)

    def _run(self, sql, params=()):
        conn = self._connect()
        try:
            with conn.cursor() as c:
                c.execute(sql, params)
                rows = c.fetchall() if c.description else None
            conn.commit()
            return rows
        finally:
            conn.close()

    def _clean(self):
        self._run("DELETE FROM reflection_timings WHERE reflection_code LIKE 'TT-%'")
        self._run("DELETE FROM reflection_runs WHERE created_by LIKE 'test_timing%'")

    def _write(self, code, rows):
        self.rt._queue_depth = 1
        self.rt._write_rows(code, rows)

    def test_rows_hold_only_code_step_and_milliseconds(self):
        self._write("TT-1", [("anonymise", 12), ("total", 45000)])
        rows = self._run("SELECT reflection_code, step, duration_ms FROM reflection_timings "
                         "WHERE reflection_code = 'TT-1' ORDER BY step")
        self.assertEqual(rows, [("TT-1", "anonymise", 12), ("TT-1", "total", 45000)])
        columns = [r[0] for r in self._run(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name = 'reflection_timings' ORDER BY ordinal_position")]
        self.assertEqual(columns, ["id", "reflection_code", "step", "duration_ms", "recorded_at"])

    def test_summary_for_the_system_administrator(self):
        self._write("TT-2", [("anonymise", 10)])
        self._write("TT-3", [("anonymise", 30)])
        rows = self.rt.get_step_summary("System Administrator", 7)
        anonymise = next(r for r in rows if r["step"] == "anonymise")
        self.assertGreaterEqual(anonymise["count"], 2)
        self.assertGreaterEqual(anonymise["max_ms"], 30)

    def test_old_rows_are_deleted_automatically(self):
        self._run("INSERT INTO reflection_timings (reflection_code, step, duration_ms, recorded_at) "
                  "VALUES ('TT-OLD', 'total', 5, now() - interval '400 days')")
        self._write("TT-4", [("total", 5)])
        self.assertEqual(self._run("SELECT COUNT(*) FROM reflection_timings WHERE reflection_code = 'TT-OLD'"),
                         [(0,)])

    def test_deleting_a_reflection_deletes_its_timings(self):
        code = "TT-" + self.rr.generate_code()
        saved = self.fs.save_reflection_run(
            case_ref=code, source_draft_ids=[], language="Español", prompt_version="v", model="m",
            module_status={}, findings=[], created_by="test_timing_owner",
            created_by_role="Social Worker", reflection_code=code,
        )
        self._write(code, [("total", 5)])
        self.assertTrue(self.rr.delete_reflection(saved["run_id"], "test_timing_admin", "System Administrator"))
        self.assertEqual(self._run("SELECT COUNT(*) FROM reflection_timings WHERE reflection_code = %s",
                                   (code,)), [(0,)])


if __name__ == "__main__":
    unittest.main()
