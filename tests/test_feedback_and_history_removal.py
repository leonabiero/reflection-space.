"""
Optional feedback, and the removal of Reflection History (15 November 2026).

  - Rating a reflection is optional: a small "Rate" pop-up in the corner of
    the results; "Finish reflection" no longer leads to a feedback step.
  - Reflection History (pages/case_history.py) was removed: the AI's
    observations and questions are no longer saved, so it had no job left.
    The average rating moved to Pattern Review; the System Administrator
    no longer has Manager mode.
  - The sentence about the saved original text on the results screen now
    also says it is used, anonymised again, in Pattern Review.
  - Every text used here exists in Spanish, Basque and English.
"""

import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

KEYS = (
    "rs_feedback_popover_button", "rs_feedback_optional_note",
    "rs_feedback_already_sent", "rs_feedback_failed", "pr_rating_line", "pr_rating_none",
    "rs_original_saved_note",
)

RETIRED_KEYS = (
    "rs_summary_status", "ch_details_expander", "ch_summary_ai_note", "ch_summary_missing",
    "ch_summary_create_button", "ch_original_text_in_patterns_note", "ch_show_anonymised_text",
    "nav_case_history", "case_history_title", "ch_reflections_intro", "ch_delete_confirm",
    "feedback_section_header",
)


def _read(*parts):
    return ROOT.joinpath(*parts).read_text(encoding="utf-8")


def _load_locale(lang):
    spec = importlib.util.spec_from_file_location(f"loc_{lang}", ROOT / "services" / "locales" / f"{lang}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return next(v for v in vars(module).values() if isinstance(v, dict) and "rs_finish_button" in v)


class HistoryRemovedTests(unittest.TestCase):
    def test_page_and_links_are_gone(self):
        self.assertFalse((ROOT / "pages" / "case_history.py").exists())
        for rel in (("navigation", "menus.py"), ("navigation", "permissions.py"), ("pages", "help.py")):
            self.assertNotIn("case_history", _read(*rel).split('"""', 2)[-1].replace("Case History", ""))

    def test_rating_moved_to_pattern_review(self):
        page = _read("pages", "pattern_explorer.py")
        self.assertIn("get_feedback_summary()", page)
        self.assertLess(page.index('T["pr_rating_line"]'), page.index('T["pr_intro"]'))

    def test_results_sentence_mentions_pattern_review(self):
        for lang, word in (("es", "Revisión de patrones"), ("eu", "Patroien berrikuspen"), ("en", "Pattern Review")):
            note = _load_locale(lang)["rs_original_saved_note"]
            self.assertIn(word, note)
            self.assertIn("{months}", note)


class FeedbackTests(unittest.TestCase):
    def test_feedback_is_an_optional_corner_popover(self):
        page = _read("pages", "reflection_space.py")
        self.assertIn("st.popover(T[\"rs_feedback_popover_button\"]", page)
        self.assertNotIn("awaiting_feedback", page)
        self.assertNotIn("feedback_skip_button", page)
        finish = page[page.index('if st.button(T["rs_finish_button"]'):]
        self.assertIn('_start_fresh(flash=T["rs_finished_success"])', finish.split("\n\n")[0])

    def test_no_summary_is_written_any_more(self):
        self.assertNotIn("reflection_summary", _read("pages", "reflection_space.py"))
        self.assertFalse((ROOT / "services" / "reflection_summary.py").exists())

    def test_texts_exist_in_all_three_languages_and_old_ones_are_gone(self):
        for lang in ("es", "eu", "en"):
            texts = _load_locale(lang)
            for key in KEYS:
                self.assertTrue(texts.get(key), f"{key} missing in {lang}")
            for key in RETIRED_KEYS:
                self.assertNotIn(key, texts, f"{key} still in {lang}")
            self.assertNotIn("case_history_section_title", texts["help"])
            for mark in ("{average}", "{count}"):
                self.assertIn(mark, texts["pr_rating_line"])


if __name__ == "__main__":
    unittest.main()
