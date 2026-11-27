"""
Reflect step timing (27 November 2026, Batch 1 -- services/reflection_timing.py).

What these tests protect:
  - only a reflection code, a fixed step name and milliseconds are ever
    saved -- never any text;
  - the Stopwatch is thread-safe (the eight lenses record at once);
  - timing can never break or slow a reflection, and can be switched off;
  - only the System Administrator can read the figures (service layer);
  - timings are erased with their reflection and by "Erase all data";
  - the measured cost per reflection uses reflections from the same period;
  - every new text exists in Spanish, Basque and English.
"""
import inspect
import re
import threading
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parents[1]


def _read(*parts):
    return ROOT.joinpath(*parts).read_text(encoding="utf-8")


class _NoSubmitExecutor:
    """Stands in for the background writer: keeps what would be written."""

    def __init__(self):
        self.submitted = []

    def submit(self, fn, *args):
        self.submitted.append(args)


class StopwatchTests(unittest.TestCase):
    def setUp(self):
        from services import reflection_timing
        self.rt = reflection_timing
        self.executor = _NoSubmitExecutor()
        p = patch.object(reflection_timing, "_EXECUTOR", self.executor)
        p.start()
        self.addCleanup(p.stop)
        reflection_timing._queue_depth = 0

    def test_many_threads_recording_at_once_lose_and_mix_up_nothing(self):
        watch = self.rt.Stopwatch("RS-TEST", enabled=True)
        steps = list(self.rt.STEPS)
        threads_count, per_thread = 50, 200
        barrier = threading.Barrier(threads_count)

        def worker(n):
            barrier.wait()
            for i in range(per_thread):
                # Each record is unique: its step and duration both encode
                # (thread, i), so a mixed-up record would be detected.
                step = steps[(n + i) % len(steps)]
                watch.record(step, n * 1000 + i)

        threads = [threading.Thread(target=worker, args=(n,)) for n in range(threads_count)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        rows = watch.rows()
        self.assertEqual(len(rows), threads_count * per_thread)
        expected = sorted(
            (steps[(n + i) % len(steps)], n * 1000 + i)
            for n in range(threads_count) for i in range(per_thread)
        )
        self.assertEqual(sorted(rows), expected)

    def test_saving_while_threads_record_saves_one_consistent_copy_once(self):
        watch = self.rt.Stopwatch("RS-TEST", enabled=True)
        stop = threading.Event()

        def worker():
            while not stop.is_set():
                watch.record("anonymise", 5)

        threads = [threading.Thread(target=worker) for _ in range(8)]
        for t in threads:
            t.start()
        try:
            self.assertTrue(watch.save())
            self.assertFalse(watch.save())     # second save does nothing
        finally:
            stop.set()
            for t in threads:
                t.join()
        self.assertEqual(len(self.executor.submitted), 1)
        code, saved_rows = self.executor.submitted[0]
        self.assertEqual(code, "RS-TEST")
        self.assertTrue(all(row == ("anonymise", 5) for row in saved_rows))
        # Records made after saving never reach the saved copy.
        self.assertLessEqual(len(saved_rows), len(watch.rows()))

    def test_unknown_steps_and_bad_numbers_are_dropped(self):
        watch = self.rt.Stopwatch("RS-TEST", enabled=True)
        watch.record("Ane García, calle Mayor 3", 10)      # not a step name
        watch.record("anonymise", "not a number")
        watch.record("anonymise", -50)
        watch.record("total", 10 ** 12)
        watch.record("limit_check", 12.6)
        self.assertEqual(watch.rows(), [("anonymise", 0), ("total", self.rt.MAX_DURATION_MS),
                                        ("limit_check", 13)])

    def test_switched_off_records_and_saves_nothing(self):
        watch = self.rt.Stopwatch("RS-TEST", enabled=False)
        watch.record("anonymise", 10)
        with patch.object(self.rt, "_get_conn") as get_conn:
            self.assertFalse(watch.save())
        get_conn.assert_not_called()
        self.assertEqual(watch.rows(), [])
        self.assertEqual(self.executor.submitted, [])

    def test_the_setting_decides_by_default(self):
        import config
        with patch.object(config, "REFLECTION_TIMING_LOG", False):
            self.assertFalse(self.rt.Stopwatch("RS-TEST").enabled)
        with patch.object(config, "REFLECTION_TIMING_LOG", True):
            self.assertTrue(self.rt.Stopwatch("RS-TEST").enabled)

    def test_errors_inside_a_timed_step_are_not_hidden(self):
        watch = self.rt.Stopwatch("RS-TEST", enabled=True)
        with self.assertRaises(ValueError):
            with watch.step("anonymise"):
                raise ValueError("the anonymiser failed")
        self.assertEqual([s for s, _ in watch.rows()], ["anonymise"])

    def test_a_full_queue_skips_quietly(self):
        watch = self.rt.Stopwatch("RS-TEST", enabled=True)
        watch.record("anonymise", 1)
        self.rt._queue_depth = self.rt._MAX_QUEUE
        try:
            with self.assertLogs(self.rt.logger, level="WARNING"):
                self.assertFalse(watch.save())
        finally:
            self.rt._queue_depth = 0
        self.assertEqual(self.executor.submitted, [])


class WriteRowsTests(unittest.TestCase):
    def setUp(self):
        from services import reflection_timing
        self.rt = reflection_timing
        reflection_timing._queue_depth = 1

    def test_a_database_failure_never_raises_and_is_logged(self):
        with patch.object(self.rt, "_get_conn", side_effect=RuntimeError("database is down")):
            with self.assertLogs(self.rt.logger, level="WARNING"):
                self.rt._write_rows("RS-TEST", [("anonymise", 5)])
        self.assertEqual(self.rt._queue_depth, 0)

    def test_only_code_step_and_milliseconds_are_written(self):
        cursor = MagicMock()
        conn = MagicMock()
        conn.cursor.return_value.__enter__.return_value = cursor
        with patch.object(self.rt, "_get_conn", return_value=conn):
            self.rt._write_rows("RS-TEST", [("anonymise", 5), ("not_a_step", 9)])
        inserts = [call for call in cursor.execute.call_args_list
                   if call.args[0].startswith("INSERT")]
        self.assertEqual(len(inserts), 1)
        sql, params = inserts[0].args
        self.assertIn("(reflection_code, step, duration_ms, recorded_at)", sql)
        self.assertEqual(params[:3], ("RS-TEST", "anonymise", 5))
        # The old rows are cleaned up in the same write.
        self.assertTrue(any("DELETE FROM reflection_timings WHERE recorded_at <" in c.args[0]
                            for c in cursor.execute.call_args_list))
        conn.commit.assert_called_once()

    def test_the_save_functions_accept_no_text(self):
        self.assertEqual(list(inspect.signature(self.rt.Stopwatch.record).parameters), ["self", "step", "ms"])
        self.assertEqual(list(inspect.signature(self.rt._write_rows).parameters), ["reflection_code", "rows"])

    def test_the_table_has_only_these_columns(self):
        schema = _read("services", "db_schema.py")
        block = re.search(r"CREATE TABLE IF NOT EXISTS reflection_timings \(([\s\S]*?)\)\n", schema).group(1)
        columns = [line.strip().split()[0] for line in block.strip().splitlines() if line.strip()]
        self.assertEqual(columns, ["id", "reflection_code", "step", "duration_ms", "recorded_at"])


class NothingFromTheCaseIsPassedInTests(unittest.TestCase):
    def test_page_and_orchestrator_use_only_constant_step_names(self):
        from services.reflection_timing import STEPS
        for parts in (("pages", "reflection_space.py"), ("rdi", "orchestrator.py")):
            source = _read(*parts)
            for name in re.findall(r"timer\.(?:step|record_since|record)\(([^,)]+)", source):
                name = name.strip()
                if name == '"lens_" + companion["key"]':
                    # The only non-literal: the lens name built from the
                    # fixed companion key (and dropped if not in STEPS).
                    continue
                self.assertRegex(name, r'^"[a-z_]+"$', (parts, name))
                self.assertIn(name.strip('"'), STEPS, (parts, name))

    def test_timing_is_saved_only_after_the_results_are_drawn(self):
        page = _read("pages", "reflection_space.py")
        # Called twice (results, and the error screen), plus its definition.
        self.assertEqual(page.count("_finish_timing()"), 3)
        self.assertEqual(page.count("def _finish_timing()"), 1)
        self.assertIn("timer=timer", page)


class OrchestratorTimingTests(unittest.TestCase):
    def setUp(self):
        from rdi import orchestrator
        self.orchestrator = orchestrator

    def _patch(self, generate):
        return patch.multiple(
            self.orchestrator,
            anonymize=lambda text, *a, **k: text,
            analysis_report=SimpleNamespace(
                generate_report=lambda *a, **k: {"report": {"summary": "s", "items": [], "questions": [],
                                                           "unverified_quote_count": 0}},
                log_report_failure=lambda *a, **k: (None, None)),
            generate_companion_reflection=generate,
            log_error=lambda **kwargs: (1, 2),
            _reflection_semaphore=threading.Semaphore(8),
        )

    def test_without_a_stopwatch_nothing_changes(self):
        def generate(companion, safe_text, lang):
            return {"observation": "obs", "questions": ["q"]}
        with self._patch(generate):
            result = self.orchestrator.run_reflection("texto")
        self.assertEqual(result["failed_count"], 0)
        self.assertIsNotNone(result["analysis_report"])

    def test_with_a_stopwatch_every_lens_the_wait_and_the_report_are_timed(self):
        from services.reflection_timing import Stopwatch, LENS_STEPS

        def generate(companion, safe_text, lang):
            return {"observation": "obs", "questions": ["q"]}
        watch = Stopwatch("RS-TEST", enabled=True)
        with self._patch(generate):
            result = self.orchestrator.run_reflection("texto", timer=watch)
        self.assertEqual(result["failed_count"], 0)
        steps = [s for s, _ in watch.rows()]
        self.assertEqual(sorted(s for s in steps if s.startswith("lens_")), sorted(LENS_STEPS))
        self.assertEqual(steps.count("lenses_total"), 1)
        self.assertEqual(steps.count("analysis_report"), 1)

    def test_a_broken_stopwatch_never_breaks_the_reflection(self):
        class Broken:
            def record_since(self, *a, **k):
                raise RuntimeError("timing broke")

        def generate(companion, safe_text, lang):
            return {"observation": "obs", "questions": ["q"]}
        with self._patch(generate):
            result = self.orchestrator.run_reflection("texto", timer=Broken())
        self.assertEqual(result["failed_count"], 0)


class ReadingIsForTheSystemAdministratorOnlyTests(unittest.TestCase):
    def test_other_roles_get_nothing_and_no_database_call(self):
        from services import reflection_timing, usage_ledger
        with patch.object(reflection_timing, "_get_conn") as get_conn, \
                patch.object(usage_ledger, "_get_conn") as ledger_conn:
            for role in ("Social Worker", "Supervisor", "Programme Manager", "", None):
                self.assertIsNone(reflection_timing.get_step_summary(role), role)
                self.assertIsNone(reflection_timing.get_ai_call_summary(role), role)
                self.assertIsNone(reflection_timing.get_measured_cost_per_reflection(role), role)
        get_conn.assert_not_called()
        ledger_conn.assert_not_called()

    def test_step_summary_follows_the_step_order(self):
        from services import reflection_timing
        cursor = MagicMock()
        cursor.fetchall.return_value = [("total", 3, 40000.0, 50000.0, 60000),
                                        ("anonymise", 3, 20.0, 30.0, 40)]
        conn = MagicMock()
        conn.cursor.return_value.__enter__.return_value = cursor
        with patch.object(reflection_timing, "_get_conn", return_value=conn):
            rows = reflection_timing.get_step_summary("System Administrator", 7)
        self.assertEqual([r["step"] for r in rows], ["anonymise", "total"])
        self.assertEqual(rows[1]["p90_ms"], 50000.0)


class MeasuredCostTests(unittest.TestCase):
    def test_cost_is_divided_by_reflections_from_the_same_period(self):
        from services import reflection_timing, usage_ledger
        stats = [{"operation": "companion_reflection", "cost_usd": 0.50},
                 {"operation": "analysis_report", "cost_usd": 0.20}]
        with patch.object(usage_ledger, "get_call_stats", return_value=stats), \
                patch("services.reflection_log.get_total_reflection_count", return_value=10) as count:
            result = reflection_timing.get_measured_cost_per_reflection("System Administrator", 7)
        self.assertAlmostEqual(result["avg_cost_usd"], 0.07)
        self.assertEqual(result["reflections"], 10)
        self.assertIn("since_iso", count.call_args.kwargs)

    def test_no_reflections_means_no_average(self):
        from services import reflection_timing, usage_ledger
        with patch.object(usage_ledger, "get_call_stats", return_value=[]), \
                patch("services.reflection_log.get_total_reflection_count", return_value=0):
            result = reflection_timing.get_measured_cost_per_reflection("System Administrator", 7)
        self.assertIsNone(result["avg_cost_usd"])

    def test_dashboard_cost_per_reflection_counts_the_same_window(self):
        from services import cost_dashboard_service as dashboard
        with patch.object(dashboard.usage_ledger, "get_operation_breakdown", return_value=[]), \
                patch.object(dashboard.usage_ledger, "get_month_summary",
                             return_value={"cost_is_estimate": False}), \
                patch.object(dashboard, "get_total_reflection_count", return_value=0) as count:
            dashboard.get_cost_per_reflection(window_days=30)
        self.assertIn("since_iso", count.call_args.kwargs)


class CallStatsTests(unittest.TestCase):
    def test_figures_come_from_the_database_row(self):
        from services import usage_ledger
        cursor = MagicMock()
        cursor.fetchall.return_value = [
            ("analysis_report", 4, 1, 1, 20000.0, 30000.0, 61000, 3700.0, 1500.0, 0.09),
        ]
        conn = MagicMock()
        conn.cursor.return_value.__enter__.return_value = cursor
        with patch.object(usage_ledger, "_get_conn", return_value=conn):
            rows = usage_ledger.get_call_stats("anthropic", ["analysis_report"], 7)
        self.assertEqual(rows, [{
            "operation": "analysis_report", "calls": 4, "failed": 1, "timed_out": 1,
            "avg_ms": 20000.0, "p90_ms": 30000.0, "max_ms": 61000.0,
            "avg_input_tokens": 3700.0, "avg_output_tokens": 1500.0, "cost_usd": 0.09,
        }])
        sql = cursor.execute.call_args.args[0]
        self.assertTrue(sql.strip().startswith("SELECT"))

    def test_a_database_failure_gives_an_empty_list(self):
        from services import usage_ledger
        with patch.object(usage_ledger, "_get_conn", side_effect=RuntimeError("down")):
            self.assertEqual(usage_ledger.get_call_stats("anthropic", ["analysis_report"], 7), [])

    def test_recording_usage_is_unchanged(self):
        from services import usage_ledger
        params = list(inspect.signature(usage_ledger.record_usage).parameters)
        self.assertEqual(params, [
            "service", "operation", "input_tokens", "output_tokens", "cache_read_tokens",
            "cache_creation_tokens", "units_used", "estimated_cost_usd", "cost_is_estimate",
            "success", "retry_count", "latency_ms", "request_count", "model", "metadata",
        ])


class ErasureTests(unittest.TestCase):
    def _cursor(self, has_table=True, codes=("RS-1",)):
        cursor = MagicMock()
        cursor.fetchone.return_value = ("reflection_timings" if has_table else None,)
        cursor.fetchall.return_value = [(c,) for c in codes]
        return cursor

    def _sql(self, cursor):
        return [c.args[0] for c in cursor.execute.call_args_list]

    def test_erasing_reflections_erases_their_timings(self):
        from services import reflection_records
        cursor = self._cursor()
        reflection_records._erase_runs(cursor, [1])
        self.assertTrue(any("DELETE FROM reflection_timings WHERE reflection_code = ANY" in s
                            for s in self._sql(cursor)))

    def test_old_document_deletion_erases_their_timings(self):
        from services import findings_store
        cursor = self._cursor()
        findings_store.delete_runs_for_drafts(cursor, [7])
        sql = self._sql(cursor)
        timing = [i for i, s in enumerate(sql) if "DELETE FROM reflection_timings" in s]
        runs = [i for i, s in enumerate(sql) if "DELETE FROM reflection_runs" in s]
        self.assertTrue(timing and runs and timing[0] < runs[0])

    def test_a_database_without_the_table_is_skipped(self):
        from services.reflection_timing import erase_timings_for_codes
        cursor = self._cursor(has_table=False)
        erase_timings_for_codes(cursor, ["RS-1"])
        self.assertFalse(any("DELETE" in s for s in self._sql(cursor)))

    def test_erase_all_data_empties_the_timings(self):
        from services import data_reset
        self.assertIn("reflection_timings", data_reset.DATA_TABLES)


class AdminSectionTests(unittest.TestCase):
    KEYS = (
        "admin_timing_header", "admin_timing_intro", "admin_timing_period_label",
        "admin_timing_period_option", "admin_timing_recording_on", "admin_timing_recording_off",
        "admin_timing_not_measured", "admin_timing_cost_header", "admin_timing_cost_measured",
        "admin_timing_cost_none", "admin_timing_cost_estimate", "admin_timing_ai_header",
        "admin_timing_ai_lens", "admin_timing_ai_report", "admin_timing_ai_line",
        "admin_timing_steps_header", "admin_timing_step_line", "admin_timing_lens_step",
        "admin_timing_seconds", "admin_timing_no_data", "admin_timing_refused",
        "admin_timing_step_names",
    )

    def test_every_text_exists_in_spanish_basque_and_english(self):
        from services.locales.es import LANG_ES
        from services.locales.eu import LANG_EU
        from services.locales.en import LANG_EN
        from services.reflection_timing import STEPS, LENS_STEP_PREFIX
        for name, lang in (("es", LANG_ES), ("eu", LANG_EU), ("en", LANG_EN)):
            for key in self.KEYS:
                self.assertIn(key, lang, (name, key))
                self.assertTrue(lang[key], (name, key))
            for step in STEPS:
                if not step.startswith(LENS_STEP_PREFIX):
                    self.assertIn(step, lang["admin_timing_step_names"], (name, step))

    def test_the_section_is_on_the_admin_page_and_checks_the_role(self):
        page = _read("pages", "system_administration.py")
        self.assertIn("reflection_timing.render(T)", page)
        section = _read("pages", "admin_sections", "reflection_timing.py")
        self.assertIn('role != ADMIN_ROLE', section)
        code = re.sub(r'"""[\s\S]*?"""', "", section)
        for forbidden in ("st.dataframe(", "st.tabs(", "st.columns("):
            self.assertNotIn(forbidden, code)


if __name__ == "__main__":
    unittest.main()
