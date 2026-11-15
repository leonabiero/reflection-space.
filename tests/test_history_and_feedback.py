"""
Reflection History + optional feedback.

  - 15 November 2026: the AI's observations and questions are no longer
    saved, so Reflection History is one short line per reflection (code,
    readable Bilbao date, themes only if any, who did it). The AI summary
    and the folded observations were removed, and no text is ever shown.
  - Rating a reflection is optional: a small "Rate" pop-up in the corner
    of the results; "Finish reflection" no longer leads to a feedback step.
  - Every on-screen text used here exists in Spanish, Basque and English.
"""

import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

KEYS = (
    "rs_feedback_popover_button", "rs_feedback_optional_note",
    "rs_feedback_already_sent", "rs_feedback_failed", "ch_reflections_intro",
    "ch_author_label", "ch_delete_confirm",
)

RETIRED_KEYS = (
    "rs_summary_status", "ch_details_expander", "ch_summary_ai_note", "ch_summary_missing",
    "ch_summary_create_button", "ch_summary_creating", "ch_summary_failed",
    "ch_original_text_in_patterns_note", "ch_show_anonymised_text",
)


def _read(*parts):
    return ROOT.joinpath(*parts).read_text(encoding="utf-8")


def _load_locale(lang):
    spec = importlib.util.spec_from_file_location(f"loc_{lang}", ROOT / "services" / "locales" / f"{lang}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return next(v for v in vars(module).values() if isinstance(v, dict) and "rs_finish_button" in v)


class ScreenStaticTests(unittest.TestCase):
    def test_history_is_one_short_line_per_reflection(self):
        page = _read("pages", "case_history.py")
        self.assertIn("st.container(border=True)", page)
        self.assertIn("display_datetime(record[\"created_at\"])", page)
        # Themes only appear when a reflection has some.
        self.assertIn('if record["case_tags"]:', page)
        self.assertNotIn('T["rs_no_tags"]', page)
        # No summary, no observations, no texts of any kind.
        for gone in ("reflection_summary", "get_findings_for_reflections", "render_evidence",
                     "get_anonymised_text", "get_original_text", "_render_summary"):
            self.assertNotIn(gone, page)
        # Private notes are still never read on this page.
        self.assertNotIn("get_feedback_for_findings", page)
        # Deleting still asks "are you sure?" first.
        self.assertIn('T["ch_delete_confirm"]', page)

    def test_feedback_is_an_optional_corner_popover(self):
        page = _read("pages", "reflection_space.py")
        self.assertIn("st.popover(T[\"rs_feedback_popover_button\"]", page)
        self.assertNotIn("awaiting_feedback", page)
        self.assertNotIn("feedback_skip_button", page)
        finish = page[page.index('if st.button(T["rs_finish_button"]'):]
        self.assertIn('_start_fresh(flash=T["rs_finished_success"])', finish.split("\n\n")[0])

    def test_no_summary_is_written_any_more(self):
        page = _read("pages", "reflection_space.py")
        self.assertNotIn("reflection_summary", page)
        self.assertFalse((ROOT / "services" / "reflection_summary.py").exists())

    def test_texts_exist_in_all_three_languages_and_old_ones_are_gone(self):
        for lang in ("es", "eu", "en"):
            texts = _load_locale(lang)
            for key in KEYS:
                self.assertTrue(texts.get(key), f"{key} missing in {lang}")
            for key in RETIRED_KEYS:
                self.assertNotIn(key, texts, f"{key} still in {lang}")
            self.assertNotIn("feedback_skip_button", texts)
            # The intro no longer promises observations.
            self.assertNotIn("observaciones de la IA se muestran", texts["ch_reflections_intro"])


if __name__ == "__main__":
    unittest.main()
