"""
Pattern Review redesign (15 November 2026) -- screens, settings and texts.

  - The reflection screen saves an ANONYMISED copy straight after
    anonymisation (before the AI is called), never the original, and
    drops it if the reflection fails completely.
  - The AI's observations and questions are not saved.
  - The Pattern Review screen shows reports only, never texts.
  - Settings: at least 5 texts; since 17 November 2026 the manager types
    any whole number of months from 1 to 15 (it used to be 3/6/9/12;
    changed at the product owner's request, so the checks below were
    updated with it).
  - Every new text exists in Spanish, Basque and English.
"""

import ast
import importlib.util
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

PR_KEYS = (
    "pr_intro", "pr_new_header", "pr_texts_note", "pr_period_label", "pr_period_help",
    "pr_period_one", "pr_period_many", "pr_available", "pr_not_enough", "pr_cost_note", "pr_run_button",
    "pr_running", "pr_done", "pr_busy", "pr_recent", "pr_failed", "pr_saved_header",
    "pr_no_reports", "pr_report_select", "pr_report_option", "pr_report_meta", "pr_some_unread",
    "pr_candidate_note", "pr_overview_header", "pr_patterns_header", "pr_no_patterns",
    "pr_seen_in", "pr_why_header", "pr_questions_header", "pr_limits_header",
    "pr_standing_limits", "pr_download_button", "pr_how_to_print", "pr_print_title",
    "pr_print_confidential", "pr_print_prepared", "pr_print_footer",
    # 18 November 2026: deleting reports.
    "pr_delete_button", "pr_delete_confirm", "pr_delete_yes", "pr_delete_cancel",
    "pr_delete_done", "pr_delete_already_gone", "pr_delete_failed",
    "pr_delete_all_button", "pr_delete_all_confirm", "pr_delete_all_done",
)

PLACEHOLDERS = {
    "pr_texts_note": ("{months}",),
    "pr_period_label": ("{minimum}", "{maximum}"), "pr_period_help": ("{maximum}",),
    "pr_period_many": ("{months}",), "pr_available": ("{count}", "{period}"),
    "pr_not_enough": ("{minimum}",), "pr_done": ("{patterns}", "{texts}"),
    "pr_report_option": ("{date}", "{period}", "{texts}"),
    "pr_report_meta": ("{date}", "{period}", "{texts}", "{read}"),
    "pr_seen_in": ("{count}", "{total}"), "pr_print_prepared": ("{date}",),
    "pr_print_footer": ("{date}",),
    "pr_delete_all_confirm": ("{count}",), "pr_delete_all_done": ("{count}",),
}


def _read(*parts):
    return ROOT.joinpath(*parts).read_text(encoding="utf-8")


def _load_locale(lang):
    spec = importlib.util.spec_from_file_location(f"loc_{lang}", ROOT / "services" / "locales" / f"{lang}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return next(v for v in vars(module).values() if isinstance(v, dict) and "rs_finish_button" in v)


class ReflectionScreenTests(unittest.TestCase):
    def setUp(self):
        self.page = _read("pages", "reflection_space.py")

    def test_no_separate_copy_is_saved(self):
        # Product owner, 15 November 2026: Pattern Review uses the saved
        # ORIGINAL texts, so no anonymised copy is kept.
        for gone in ("pattern_text_store", "save_pattern_text", "discard_pattern_text",
                     "SAVE_PATTERN_TEXT"):
            self.assertNotIn(gone, self.page)
        self.assertIn("material if SAVE_ORIGINAL_TEXT else None", self.page)

    def test_observations_are_not_saved(self):
        self.assertIn('result.get("findings", []) if SAVE_OBSERVATIONS else []', self.page)
        session = _read("rdi", "reflection_session.py")
        self.assertIn("if self.session.run_id and SAVE_OBSERVATIONS:", session)
        import config
        self.assertFalse(config.SAVE_OBSERVATIONS)

    def test_notices_are_not_on_the_writing_screen_but_stay_in_help(self):
        for gone in ("rs_privacy_note", "rs_pattern_copy_note"):
            self.assertNotIn(gone, self.page)
        help_page = _read("pages", "help.py")
        self.assertIn('H["original_saved_note"]', help_page)
        self.assertNotIn("pattern_copy_note", help_page)


class AnalysisReadsOriginalTextsTests(unittest.TestCase):
    def test_store_reads_original_texts_without_names(self):
        source = _read("services", "pattern_text_store.py")
        select = source[source.index("def texts_for_period("):]
        select = select[select.index("SELECT"):select.index("FROM")]
        self.assertIn("r.original_text", select)
        for forbidden in ("created_by", "reflection_code", "created_at", "case_ref"):
            self.assertNotIn(forbidden, select)
        self.assertIn("NOT_IN_DELETION_WINDOW", source)

    def test_every_text_is_anonymised_before_the_ai(self):
        source = _read("services", "pattern_text_analysis.py")
        run = source[source.index("def run_report("):]
        self.assertLess(run.index("protect_texts(originals)"), run.index("analyse_texts(protected"))

class PatternReviewScreenTests(unittest.TestCase):
    def setUp(self):
        self.page = _read("pages", "pattern_explorer.py")

    def test_page_shows_reports_never_texts(self):
        for forbidden in (".texts_for_period(", "get_original_text", "anonymised_text", "render_evidence",
                          "pattern_store.", "list_reflections"):
            self.assertNotIn(forbidden, self.page)
        self.assertIn("pattern_text_store.list_reports(user_role)", self.page)
        self.assertIn("can_review_patterns(user_role)", self.page)

    def test_period_box_and_minimum_come_from_settings(self):
        # 17 November 2026: a box for the number of months replaced the
        # fixed choice of 3, 6, 9 or 12.
        self.assertIn("st.number_input(", self.page)
        self.assertIn("min_value=PATTERN_MIN_MONTHS", self.page)
        self.assertIn("max_value=PATTERN_MAX_MONTHS", self.page)
        self.assertIn("step=1", self.page)
        self.assertNotIn("PATTERN_PERIOD_CHOICES", self.page)
        self.assertNotIn("st.radio(", self.page)
        self.assertIn("available >= PATTERN_MIN_TEXTS", self.page)

    def test_every_key_used_exists(self):
        es = _load_locale("es")
        for key in set(re.findall(r'T\["([a-z_]+)"\]', self.page)):
            self.assertIn(key, es, key)


class SettingsTests(unittest.TestCase):
    def test_defaults(self):
        import os
        import config
        self.assertFalse(hasattr(config, "PATTERN_PERIOD_CHOICES"))
        self.assertEqual(config.PATTERN_MIN_MONTHS, 1)
        if "ORIGINAL_TEXT_RETENTION_MONTHS" not in os.environ:
            self.assertEqual(config.PATTERN_MAX_MONTHS, 15)
        self.assertTrue(config.PATTERN_MIN_MONTHS <= config.PATTERN_DEFAULT_MONTHS <= config.PATTERN_MAX_MONTHS)
        if "PATTERN_MIN_TEXTS" not in os.environ:
            self.assertEqual(config.PATTERN_MIN_TEXTS, 5)
        # Every period fits inside the time the original texts are kept:
        # the longest period is exactly the time they are kept.
        self.assertEqual(config.PATTERN_MAX_MONTHS, config.ORIGINAL_TEXT_RETENTION_MONTHS)
        self.assertGreaterEqual(config.PATTERN_MIN_TEXTS_PER_PATTERN, 2)
        self.assertFalse(hasattr(config, "SAVE_PATTERN_TEXT"))
        self.assertFalse(hasattr(config, "PATTERN_TEXT_RETENTION_MONTHS"))

    def test_schema_no_longer_creates_a_copy_table(self):
        schema = _read("services", "db_schema.py")
        self.assertNotIn("CREATE TABLE IF NOT EXISTS pattern_texts", schema)
        self.assertIn("CREATE TABLE IF NOT EXISTS pattern_reports", schema)

    def test_erase_all_data_covers_reports_and_drops_the_old_copy_table(self):
        from services.data_reset import DATA_TABLES, RETIRED_TABLES
        self.assertIn("pattern_reports", DATA_TABLES)
        self.assertIn("pattern_texts", RETIRED_TABLES)
        self.assertNotIn("pattern_texts", DATA_TABLES)

    def test_texts_are_never_logged(self):
        for name in ("pattern_text_store.py", "pattern_text_analysis.py"):
            source = _read("services", name)
            for call in re.findall(r"logger\.\w+\((?:.|\n)*?\)\n", source):
                for forbidden in ("anonymised_text", "texts)", "text)", "batch)", "report)"):
                    self.assertNotIn(forbidden, call.split(",", 1)[-1], (name, call))

    def test_old_observation_pattern_system_is_gone(self):
        for name in ("pattern_service", "pattern_engine", "pattern_explainer", "pattern_store",
                     "report_builder", "reflection_summary"):
            self.assertFalse((ROOT / "services" / f"{name}.py").exists(), name)
        for path in ROOT.rglob("*.py"):
            if "tests" in path.parts or ".git" in path.parts:
                continue
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, (ast.Import, ast.ImportFrom)):
                    names = [a.name for a in node.names] + [getattr(node, "module", "") or ""]
                    for n in names:
                        self.assertNotRegex(n, r"(pattern_store|pattern_service|reflection_summary)$", str(path))


class TranslationTests(unittest.TestCase):
    def test_every_new_text_exists_in_all_three_languages(self):
        for lang in ("es", "eu", "en"):
            texts = _load_locale(lang)
            for key in PR_KEYS:
                self.assertTrue(texts.get(key), f"{key} missing in {lang}")
            for key, marks in PLACEHOLDERS.items():
                for mark in marks:
                    self.assertIn(mark, texts[key], f"{key} {mark} in {lang}")
            self.assertEqual(len(texts["pr_standing_limits"]), 4)
            self.assertIn("{minimum}", texts["help"]["pattern_review_section_body"])
            self.assertIn("{maximum}", texts["help"]["pattern_review_section_body"])
            for old in ("3, 6, 9",):
                self.assertNotIn(old, texts["help"]["pattern_review_section_body"])
            self.assertNotIn("pr_period_option", texts)
            self.assertNotIn("pattern_copy_note", texts["help"])
            self.assertTrue(texts["help"]["pattern_review_section_title"])
            # Nothing tells practitioners any more that managers read their text.
            for word in ("supervisoras", "gainbegiraleek", "supervisors"):
                self.assertNotIn(word, texts["help"]["privacy_points"][0])
                self.assertNotIn(word, texts["rs_original_saved_note"])
                self.assertNotIn(word, texts["help"]["original_saved_note"])

    def test_spanish_is_still_the_default_language(self):
        source = _read("services", "translation_manager.py")
        self.assertIn('MASTER_LANGUAGE = "Español"', source)


class PrintableReportTests(unittest.TestCase):
    def test_everything_is_escaped_and_nothing_runs(self):
        from services.pattern_report_html import build_report_html
        T = _load_locale("en")
        saved = {"id": 1, "period_months": 6, "texts_count": 9, "report": {
            "overview": "<script>alert(1)</script>", "texts_read": 9, "limitations": [],
            "patterns": [{"title": "A & B", "description": "<b>x</b>", "why_it_may_matter": "",
                          "questions": ["<img src=x>"], "texts_count": 4}]}}
        html = build_report_html(T, "English", saved, "15/11/2026", "15/11/2026 20:00")
        self.assertNotIn("<script>", html)
        self.assertNotIn("<img", html)
        self.assertIn("&lt;script&gt;", html)
        self.assertIn("A &amp; B", html)
        self.assertIn("Seen in 4 of 9 texts", html)
        self.assertIn("default-src 'none'", html)
        self.assertIn("last 6 months", html)

    def test_one_month_reads_correctly_in_every_language(self):
        from services.pattern_report_html import period_phrase
        expected = {"es": ("último mes", "últimos 7 meses"),
                    "eu": ("azken hilabetea", "azken 7 hilabeteak"),
                    "en": ("last 1 month", "last 7 months")}
        for lang, (one, many) in expected.items():
            T = _load_locale(lang)
            self.assertEqual(period_phrase(T, 1), one)
            self.assertEqual(period_phrase(T, 7), many)


class PeriodLimitTests(unittest.TestCase):
    """The service layer accepts any whole number of months from 1 to 15
    and refuses everything else, whatever the screen sends."""

    def test_limits(self):
        from services.pattern_text_store import _clean_period
        import config
        for ok in range(config.PATTERN_MIN_MONTHS, config.PATTERN_MAX_MONTHS + 1):
            self.assertEqual(_clean_period(ok), ok)
        self.assertEqual(_clean_period("7"), 7)
        self.assertEqual(_clean_period(4.0), 4)
        for bad in (0, -1, config.PATTERN_MAX_MONTHS + 1, 100, 2.5, "abc", None, True):
            with self.assertRaises(ValueError, msg=repr(bad)):
                _clean_period(bad)

    def test_refused_period_never_reaches_the_database(self):
        from unittest import mock
        from services import pattern_text_store
        with mock.patch.object(pattern_text_store, "_get_conn") as conn:
            with self.assertRaises(ValueError):
                pattern_text_store.texts_for_period("Supervisor", 16)
            with self.assertRaises(ValueError):
                pattern_text_store.count_texts_for_period("Programme Manager", 0)
            conn.assert_not_called()


class DeleteReportTests(unittest.TestCase):
    """18 November 2026 (product owner's decision): once a manager has the
    downloaded file, they can delete the report -- after an "are you
    sure?" step. Downloading never deletes. Any Supervisor or Programme
    Manager may delete any report (reports are shared by the team)."""

    def setUp(self):
        self.page = _read("pages", "pattern_explorer.py")

    def _fake_conn(self, rows):
        from unittest import mock
        conn = mock.MagicMock()
        cursor = conn.cursor.return_value.__enter__.return_value
        cursor.fetchall.return_value = rows
        return conn, cursor

    def test_page_asks_for_confirmation_before_deleting(self):
        self.assertIn("from services.confirm_state import", self.page)
        self.assertIn('st.button(T["pr_delete_button"]', self.page)
        self.assertIn('st.warning(T["pr_delete_confirm"])', self.page)
        self.assertIn('st.button(T["pr_delete_yes"]', self.page)
        self.assertIn('st.button(T["pr_delete_cancel"]', self.page)
        # The delete call only happens after "Yes".
        yes = self.page.index('st.button(T["pr_delete_yes"], type="primary", key=f"pr_delete_yes_')
        self.assertGreater(self.page.index("pattern_text_store.delete_report(user_role, user_name"), yes)
        self.assertLess(self.page.index('st.button(T["pr_delete_button"]'), yes)
        # Delete all: only with two or more reports, also confirmed first.
        self.assertIn("if len(reports) > 1:", self.page)
        self.assertIn('st.warning(T["pr_delete_all_confirm"]', self.page)
        yes_all = self.page.index('key="pr_delete_all_yes"')
        self.assertGreater(self.page.index("pattern_text_store.delete_all_reports(user_role, user_name)"), yes_all)

    def test_download_is_unchanged_and_never_deletes(self):
        download = self.page[self.page.index("st.download_button("):]
        download = download[:download.index(")\n")]
        self.assertIn("page.encode", download)
        self.assertNotIn("delete", download.replace("pr_download", ""))
        self.assertIn("build_report_html(T,", self.page)
        # The download comes before the delete button on the page.
        self.assertLess(self.page.index("st.download_button("), self.page.index('T["pr_delete_button"]'))

    def test_refused_roles_never_reach_the_database(self):
        from unittest import mock
        from services import pattern_text_store
        with mock.patch.object(pattern_text_store, "_get_conn") as conn:
            for role in ("Social Worker", "System Administrator", "", None):
                with self.assertRaises(PermissionError):
                    pattern_text_store.delete_report(role, "someone", 1)
                with self.assertRaises(PermissionError):
                    pattern_text_store.delete_all_reports(role, "someone")
            conn.assert_not_called()

    def test_both_management_roles_may_delete(self):
        from unittest import mock
        from services import pattern_text_store
        for role in ("Supervisor", "Programme Manager"):
            conn, cursor = self._fake_conn([(3, 12, "Español")])
            with mock.patch.object(pattern_text_store, "_get_conn", return_value=conn), \
                    mock.patch.object(pattern_text_store.request_dedup, "release"):
                self.assertTrue(pattern_text_store.delete_report(role, "boss", 7))
            sql, params = cursor.execute.call_args[0]
            self.assertIn("DELETE FROM pattern_reports WHERE id = %s", sql)
            self.assertEqual(params, (7,))
            conn.commit.assert_called_once()

    def test_already_deleted_report_returns_false(self):
        from unittest import mock
        from services import pattern_text_store
        conn, _ = self._fake_conn([])
        with mock.patch.object(pattern_text_store, "_get_conn", return_value=conn), \
                mock.patch.object(pattern_text_store.request_dedup, "release") as release:
            self.assertFalse(pattern_text_store.delete_report("Supervisor", "boss", 7))
        release.assert_not_called()

    def test_delete_lifts_the_same_lock_run_report_uses(self):
        # After a delete, the same review (same months, texts, language)
        # can be run again at once -- no "made a few minutes ago" message.
        from unittest import mock
        from services import pattern_text_store, request_dedup
        conn, _ = self._fake_conn([(3, 12, "Español")])
        with mock.patch.object(pattern_text_store, "_get_conn", return_value=conn), \
                mock.patch.object(pattern_text_store.request_dedup, "release") as release:
            pattern_text_store.delete_report("Supervisor", "boss", 7)
        expected = request_dedup.fingerprint("pattern_text_report", 3, 12, "Español")
        release.assert_called_once_with(expected)
        analysis = _read("services", "pattern_text_analysis.py")
        run = analysis[analysis.index("def run_report("):]
        self.assertIn("pattern_text_store.report_fingerprint(int(period_months), len(texts), lang)", run)

    def test_delete_all_deletes_every_report_and_lifts_every_lock(self):
        from unittest import mock
        from services import pattern_text_store
        conn, cursor = self._fake_conn([(3, 12, "Español"), (6, 30, "English")])
        with mock.patch.object(pattern_text_store, "_get_conn", return_value=conn), \
                mock.patch.object(pattern_text_store.request_dedup, "release") as release:
            self.assertEqual(pattern_text_store.delete_all_reports("Programme Manager", "boss"), 2)
        sql = cursor.execute.call_args[0][0]
        self.assertIn("DELETE FROM pattern_reports", sql)
        self.assertNotIn("WHERE", sql)
        self.assertNotIn("LIMIT", sql)
        self.assertEqual(release.call_count, 2)

    def test_a_failed_lock_release_does_not_undo_the_delete(self):
        from unittest import mock
        from services import pattern_text_store
        conn, _ = self._fake_conn([(3, 12, "Español")])
        with mock.patch.object(pattern_text_store, "_get_conn", return_value=conn), \
                mock.patch.object(pattern_text_store.request_dedup, "release", side_effect=RuntimeError):
            self.assertTrue(pattern_text_store.delete_report("Supervisor", "boss", 7))

    def test_database_failure_deletes_nothing_and_is_reported(self):
        from unittest import mock
        from services import pattern_text_store
        conn, cursor = self._fake_conn([])
        cursor.execute.side_effect = RuntimeError("database down")
        with mock.patch.object(pattern_text_store, "_get_conn", return_value=conn):
            with self.assertRaises(RuntimeError):
                pattern_text_store.delete_report("Supervisor", "boss", 7)
        conn.rollback.assert_called_once()
        conn.commit.assert_not_called()
        # The page turns that into an error message, never a crash.
        self.assertIn('_after_delete("error", T["pr_delete_failed"])', self.page)

    def test_nothing_else_on_the_page_changed(self):
        for kept in ('T["pr_rating_line"]', "st.number_input(", "available >= PATTERN_MIN_TEXTS",
                     "st.download_button("):
            self.assertIn(kept, self.page)


if __name__ == "__main__":
    unittest.main()
