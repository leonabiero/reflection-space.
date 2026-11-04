"""
Simplified practitioner screen (November 2026) -- see REFLECTIONS.md.

Write / paste / upload -> choose language -> Reflect -> reflection.

These tests cover what can be checked without a browser:
  - input rules (typed text, document, both, neither),
  - privacy: the AI only ever receives anonymised text, and a failed
    anonymisation stops everything with no fallback,
  - the chosen language reaches every AI call,
  - the page no longer asks for any case metadata,
  - every new piece of on-screen text exists in Spanish, Basque and English.
"""

import re
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

from services import document_import as di
from services.anonymizer import anonymize

ROOT = Path(__file__).resolve().parents[1]

# Realistic note mixing the three app languages, full of identifiers.
SENSITIVE_NOTE = (
    "La madre, Lucía Etxeberria, vive en Barakaldo. DNI 12345678Z. "
    "Teléfono 612 345 678, correo lucia.etx@example.com. "
    "Mikel dice que su hijo no quiere ir al colegio. "
    "Visited on 03/10/2026; Mr John Smith (neighbour) was present."
)
IDENTIFIERS = ("Lucía", "Etxeberria", "Barakaldo", "12345678Z", "612 345 678",
               "lucia.etx@example.com", "Mikel", "John Smith", "03/10/2026")


def _read(*parts):
    return (ROOT.joinpath(*parts)).read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Input rules
# ---------------------------------------------------------------------------

class PickMaterialTests(unittest.TestCase):
    def test_typed_text_only(self):
        self.assertEqual(di.pick_material("  my note  ", ""), ("my note", ""))

    def test_document_only(self):
        self.assertEqual(di.pick_material("", "from file"), ("from file", ""))

    def test_nothing_is_reported_as_empty(self):
        self.assertEqual(di.pick_material("   ", None), ("", di.MATERIAL_EMPTY))
        self.assertEqual(di.pick_material(None, "  \n "), ("", di.MATERIAL_EMPTY))

    def test_both_without_a_choice_asks_instead_of_guessing(self):
        self.assertTrue(di.has_both("typed", "file"))
        self.assertEqual(di.pick_material("typed", "file"), ("", di.MATERIAL_CHOOSE))
        self.assertEqual(di.pick_material("typed", "file", "nonsense"), ("", di.MATERIAL_CHOOSE))

    def test_both_follows_the_choice(self):
        self.assertEqual(di.pick_material("typed", "file", di.SOURCE_TEXT), ("typed", ""))
        self.assertEqual(di.pick_material("typed", "file", di.SOURCE_FILE), ("file", ""))
        material, problem = di.pick_material("typed", "file", di.SOURCE_BOTH)
        self.assertEqual(problem, "")
        self.assertEqual(material, "typed" + di.BOTH_SEPARATOR + "file")

    def test_a_choice_is_ignored_when_only_one_input_exists(self):
        self.assertEqual(di.pick_material("typed", "", di.SOURCE_FILE), ("typed", ""))
        self.assertEqual(di.pick_material("", "file", di.SOURCE_TEXT), ("file", ""))

    def test_long_text_is_kept_whole(self):
        long_text = "Observación profesional. " * 2000
        material, problem = di.pick_material(long_text, "")
        self.assertEqual(problem, "")
        self.assertEqual(material, long_text.strip())


# ---------------------------------------------------------------------------
# Privacy
# ---------------------------------------------------------------------------

class AnonymisationTests(unittest.TestCase):
    def test_identifiers_are_removed(self):
        safe = anonymize(SENSITIVE_NOTE)
        for identifier in IDENTIFIERS:
            self.assertNotIn(identifier, safe, identifier)

    def test_anonymising_twice_changes_nothing(self):
        # The page anonymises, then the orchestrator anonymises again.
        safe = anonymize(SENSITIVE_NOTE)
        self.assertEqual(anonymize(safe), safe)


class OrchestratorPrivacyTests(unittest.TestCase):
    """Runs the REAL orchestrator with the REAL anonymiser; only the AI
    call itself is replaced by a recorder."""

    def setUp(self):
        from rdi import orchestrator
        self.orchestrator = orchestrator
        self.sent = []

    def _fake_ai(self, companion, safe_text, lang):
        self.sent.append((companion["key"], safe_text, lang))
        return {"observation": "obs", "questions": ["q"], "evidence": []}

    def _patches(self):
        return patch.multiple(
            self.orchestrator,
            generate_companion_reflection=self._fake_ai,
            log_error=lambda **kwargs: (1, 2),
            _reflection_semaphore=threading.Semaphore(8),
        )

    def test_the_ai_never_sees_the_original_text(self):
        safe = anonymize(SENSITIVE_NOTE)        # what the page sends
        with self._patches():
            result = self.orchestrator.run_reflection(safe, "Español")
        self.assertEqual(len(self.sent), len(self.orchestrator.COMPANIONS))
        for _key, text, _lang in self.sent:
            for identifier in IDENTIFIERS:
                self.assertNotIn(identifier, text, identifier)
        # The preview shows exactly what the AI received.
        self.assertEqual(result["safe_text"], self.sent[0][1])
        self.assertEqual(result["safe_text"], safe)

    def test_even_raw_text_is_anonymised_by_the_orchestrator(self):
        # Defence in depth: if raw text ever reached the orchestrator, it
        # would still be anonymised before any AI call.
        with self._patches():
            self.orchestrator.run_reflection(SENSITIVE_NOTE, "Español")
        for _key, text, _lang in self.sent:
            self.assertNotIn("Lucía", text)
            self.assertNotIn("12345678Z", text)

    def test_failed_anonymisation_sends_nothing(self):
        def broken(_text):
            raise RuntimeError("anonymiser broke")

        with self._patches(), patch.object(self.orchestrator, "anonymize", broken):
            with self.assertRaises(RuntimeError):
                self.orchestrator.run_reflection(SENSITIVE_NOTE, "Español")
        self.assertEqual(self.sent, [])

    def test_selected_language_reaches_every_ai_call(self):
        for lang in ("Español", "Euskera", "English"):
            self.sent.clear()
            with self._patches():
                self.orchestrator.run_reflection("Texto de prueba.", lang)
            self.assertTrue(self.sent)
            self.assertEqual({sent_lang for _k, _t, sent_lang in self.sent}, {lang})


class PagePrivacyFlowTests(unittest.TestCase):
    """Static checks of pages/reflection_space.py: the order of the steps
    and the absence of any fallback to the original text."""

    def setUp(self):
        self.page = _read("pages", "reflection_space.py")

    def test_anonymisation_happens_before_the_ai_call(self):
        anonymise_at = self.page.index("safe_text = anonymize(material)")
        ai_at = self.page.index("run_reflection(")
        self.assertLess(anonymise_at, ai_at)

    def test_only_the_anonymised_text_goes_to_the_ai(self):
        calls = re.findall(r"run_reflection\(([^,\)]+)", self.page)
        self.assertEqual(calls, ["safe_text"])
        for raw_name in ("material", "case_text", "file_text"):
            self.assertNotIn(f"run_reflection({raw_name}", self.page)

    def test_failure_stops_with_no_fallback(self):
        start = self.page.index("safe_text = anonymize(material)")
        end = self.page.index("run_reflection(", start)
        block = self.page[start:end]
        self.assertIn('if not (safe_text or "").strip():', block)
        self.assertIn('st.error(T["rs_anonymise_failed"])', block)
        # The failure record never carries the text or its traceback.
        self.assertIn("traceback_text=None", block)
        self.assertNotIn("message=material", block)
        self.assertNotIn("safe_text = material", self.page)

    def test_preview_is_collapsed_and_shows_the_protected_text(self):
        self.assertIn('st.expander(T["rs_anonymised_preview_label"], expanded=False)', self.page)
        start = self.page.index('st.expander(T["rs_anonymised_preview_label"]')
        block = self.page[start:start + 250]
        self.assertIn("st.write(session.safe_text)", block)
        self.assertNotIn("case_text", block)

    def test_chosen_language_is_used_everywhere(self):
        self.assertIn("run_reflection(safe_text, reflect_lang", self.page)
        self.assertIn("language=reflect_lang", self.page)
        self.assertIn("reflection_lang=reflect_lang", self.page)
        session_source = _read("rdi", "reflection_session.py")
        self.assertIn('getattr(self.session, "reflection_lang", None)', session_source)


# ---------------------------------------------------------------------------
# Interface
# ---------------------------------------------------------------------------

class SimpleScreenTests(unittest.TestCase):
    def setUp(self):
        self.page = _read("pages", "reflection_space.py")

    def test_no_case_metadata_is_asked(self):
        for removed in ("st.multiselect", "rs_tags_label", "rs_note_type_label",
                        "rs_previous_code_label", "rs_continue_button", "find_similar_reflections("):
            self.assertNotIn(removed, self.page, removed)

    def test_one_prominent_reflect_button(self):
        self.assertIn('T["rs_reflect_button"]', self.page)
        start = self.page.index('T["rs_reflect_button"]')
        block = self.page[start:start + 200]
        self.assertIn('type="primary"', block)
        self.assertIn("use_container_width=True", block)
        self.assertIn("disabled=is_generating", block)

    def test_reflection_code_is_created_automatically(self):
        self.assertIn("reflection_records.new_reflection_code()", self.page)

    def test_upload_and_both_inputs_choice(self):
        self.assertIn("document_import.extract_text", self.page)
        self.assertIn("document_import.has_both(case_text, file_text)", self.page)
        self.assertIn("index=None", self.page)   # no silent default choice

    def test_language_choice_offers_exactly_three(self):
        from services.language import LANGUAGE_ORDER
        self.assertEqual(LANGUAGE_ORDER, ["Español", "Euskera", "English"])
        self.assertEqual(LANGUAGE_ORDER[0], "Español")     # Spanish stays the default

    def test_duplicate_and_rate_limit_protection_kept(self):
        for guard in ("check_and_record(", "request_dedup.claim(", "request_dedup.release(",
                      "reset_flags=[GENERATING_KEY]"):
            self.assertIn(guard, self.page, guard)


class TranslationTests(unittest.TestCase):
    NEW_KEYS = (
        "rs_heading", "rs_subheading", "rs_material_label", "rs_material_placeholder",
        "rs_file_loaded", "rs_both_inputs_notice", "rs_source_label", "rs_source_options",
        "rs_choose_source_warning", "rs_need_material", "rs_language_label",
        "rs_language_names", "rs_privacy_note", "rs_reflect_button", "rs_anonymised_status",
        "rs_preparing_status", "rs_anonymise_failed", "rs_anonymised_preview_label",
        "rs_anonymised_preview_help", "rs_try_again_button",
    )

    def test_every_new_text_exists_in_all_three_languages(self):
        from services.locales.es import LANG_ES
        from services.locales.eu import LANG_EU
        from services.locales.en import LANG_EN
        for lang in (LANG_ES, LANG_EU, LANG_EN):
            for key in self.NEW_KEYS:
                self.assertTrue(lang.get(key), key)
            self.assertEqual(set(lang["rs_source_options"]), set(di.SOURCE_CHOICES))
            self.assertEqual(
                lang["rs_language_names"],
                {"Español": "Español", "Euskera": "Euskara", "English": "English"},
            )
        self.assertEqual(LANG_EN["rs_heading"], "Let's reflect.")
        self.assertEqual(LANG_EN["rs_reflect_button"], "Reflect")
        self.assertEqual(LANG_EN["rs_anonymised_preview_label"], "View anonymised text")

    def test_every_key_used_on_the_page_exists(self):
        from services.locales.es import LANG_ES
        page = _read("pages", "reflection_space.py")
        for key in set(re.findall(r'T\[["\']([a-z0-9_]+)["\']\]', page)):
            self.assertIn(key, LANG_ES, key)


if __name__ == "__main__":
    unittest.main()
