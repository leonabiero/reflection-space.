"""
Pattern Review redesign (15 November 2026) -- screens, settings and texts.

  - The reflection screen saves an ANONYMISED copy straight after
    anonymisation (before the AI is called), never the original, and
    drops it if the reflection fails completely.
  - The AI's observations and questions are not saved.
  - The Pattern Review screen shows reports only, never texts.
  - Settings: 13 months, at least 5 texts, periods 3/6/9/12.
  - Every new text exists in Spanish, Basque and English.
"""

import ast
import importlib.util
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

PR_KEYS = (
    "pr_intro", "pr_new_header", "pr_texts_note", "pr_period_label",
    "pr_period_option", "pr_available", "pr_not_enough", "pr_cost_note", "pr_run_button",
    "pr_running", "pr_done", "pr_busy", "pr_recent", "pr_failed", "pr_saved_header",
    "pr_no_reports", "pr_report_select", "pr_report_option", "pr_report_meta", "pr_some_unread",
    "pr_candidate_note", "pr_overview_header", "pr_patterns_header", "pr_no_patterns",
    "pr_seen_in", "pr_why_header", "pr_questions_header", "pr_limits_header",
    "pr_standing_limits", "pr_download_button", "pr_how_to_print", "pr_print_title",
    "pr_print_confidential", "pr_print_prepared", "pr_print_footer",
)

PLACEHOLDERS = {
    "pr_texts_note": ("{months}",),
    "pr_period_option": ("{months}",), "pr_available": ("{count}", "{months}"),
    "pr_not_enough": ("{minimum}",), "pr_done": ("{patterns}", "{texts}"),
    "pr_report_option": ("{date}", "{months}", "{texts}"),
    "pr_report_meta": ("{date}", "{months}", "{texts}", "{read}"),
    "pr_seen_in": ("{count}", "{total}"), "pr_print_prepared": ("{date}",),
    "pr_print_footer": ("{date}",),
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

    def test_period_choices_and_minimum_come_from_settings(self):
        self.assertIn("list(PATTERN_PERIOD_CHOICES)", self.page)
        self.assertIn("available >= PATTERN_MIN_TEXTS", self.page)

    def test_every_key_used_exists(self):
        es = _load_locale("es")
        for key in set(re.findall(r'T\["([a-z_]+)"\]', self.page)):
            self.assertIn(key, es, key)


class SettingsTests(unittest.TestCase):
    def test_defaults(self):
        import os
        import config
        self.assertEqual(config.PATTERN_PERIOD_CHOICES, (3, 6, 9, 12))
        if "PATTERN_MIN_TEXTS" not in os.environ:
            self.assertEqual(config.PATTERN_MIN_TEXTS, 5)
        # Every period fits inside the time the original texts are kept.
        self.assertGreater(config.ORIGINAL_TEXT_RETENTION_MONTHS, max(config.PATTERN_PERIOD_CHOICES))
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


if __name__ == "__main__":
    unittest.main()
