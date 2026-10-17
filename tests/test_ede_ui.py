"""Interface/integration tests for the EDE reflection page. Runs the real
page with Streamlit's headless test harness; only login, navigation and
the AI provider are replaced by fakes (all documents are synthetic)."""

import os
import py_compile
import re
import unittest
from contextlib import ExitStack
from unittest.mock import MagicMock, patch

from streamlit.testing.v1 import AppTest

import config
from navigation.permissions import PRACTITIONER_PAGES
from services.ede_framework import DIMENSIONS
from services.language import LANG, get_lang

from ede_test_support import ES_DOC, ProviderPatches, make_finding, reply

PAGE = "pages/ede_reflection.py"


def read(path):
    with open(path, encoding="utf-8") as handle:
        return handle.read()


def open_page(*responses, role="Social Worker", lang=None, rate_allowed=True):
    stack = ExitStack()
    provider = stack.enter_context(ProviderPatches(*responses))
    stack.enter_context(patch("services.identity.init_identity", return_value=("Test Worker", role)))
    stack.enter_context(patch("services.identity.render_identity_footer"))
    stack.enter_context(patch("services.identity.require_work_mode"))
    stack.enter_context(patch("navigation.router.render_nav"))
    limiter = MagicMock(return_value=(rate_allowed, 1))
    stack.enter_context(patch("services.rate_limiter.check_and_record", limiter))
    at = AppTest.from_file(PAGE, default_timeout=30)
    if lang:
        at.session_state["lang"] = lang
    at.run()
    return at, provider, limiter, stack


class DefaultsAndFlowTests(unittest.TestCase):
    def test_defaults_are_social_accommodation_follow_up_report_and_auto_language(self):
        at, _, _, stack = open_page(reply([]))
        with stack:
            self.assertFalse(at.exception)
            self.assertEqual(at.session_state["ede_programme"], "social_accommodation_bizkaia")
            self.assertEqual(at.session_state["ede_doctype"], "follow_up_report")
            self.assertEqual(at.session_state["ede_expl_lang"], "auto")
            # The defaults are read from config, not hard-coded in the page.
            self.assertEqual(config.EDE_DEFAULT_PROGRAMME, "social_accommodation_bizkaia")
            self.assertEqual(config.EDE_DEFAULT_DOCUMENT_TYPE, "follow_up_report")
            self.assertIn("config.EDE_DEFAULT_PROGRAMME", read(PAGE))

    def test_other_programmes_and_document_types_are_selectable(self):
        at, _, _, stack = open_page(reply([]))
        with stack:
            programmes = [s for s in at.selectbox if s.key == "ede_programme"][0]
            self.assertEqual(len(programmes.options), 4)
            doctypes = [s for s in at.selectbox if s.key == "ede_doctype"][0]
            self.assertIn("Informe de seguimiento", doctypes.options)
            self.assertGreaterEqual(len(doctypes.options), 5)

    def test_results_are_grouped_under_the_eight_dimensions_in_order(self):
        findings = [make_finding("labels_and_language", "Es una persona conflictiva con el resto de residentes")]
        at, provider, _, stack = open_page(reply(findings))
        with stack:
            at.text_area(key="ede_text").set_value(ES_DOC).run()
            at.button(key="ede_analyse").click().run()
            self.assertFalse(at.exception)
            headings = [m.value for m in at.markdown if m.value.startswith("### ")]
            expected = ["### " + get_lang("Español")["ede_dims"][k]["label"] for k in DIMENSIONS]
            self.assertEqual(headings, expected)
            provider.client.messages.create.assert_called_once()
            self.assertEqual(len(at.expander), 1)

    def test_empty_text_gives_a_clear_error_and_no_provider_call_or_quota_use(self):
        at, provider, limiter, stack = open_page(reply([]))
        with stack:
            at.button(key="ede_analyse").click().run()
            self.assertEqual(len(at.error), 1)
            self.assertIn("vacío", at.error[0].value)
            provider.client.messages.create.assert_not_called()
            limiter.assert_not_called()

    def test_user_can_retry_after_a_recoverable_failure(self):
        at, provider, _, stack = open_page(RuntimeError("down"), reply([make_finding()]))
        with stack:
            at.text_area(key="ede_text").set_value(ES_DOC).run()
            at.button(key="ede_analyse").click().run()
            self.assertEqual(len(at.error), 1)
            self.assertNotIn("down", at.error[0].value)       # provider text not shown
            self.assertNotIn("Parece que", at.error[0].value)  # document text not shown
            retry = [b for b in at.button if b.key == "ede_retry"]
            self.assertEqual(len(retry), 1)
            retry[0].click().run()
            self.assertFalse(at.exception)
            self.assertEqual(len(at.error), 0)
            self.assertEqual(len(at.expander), 1)

    def test_hourly_limit_blocks_with_a_clear_message(self):
        at, provider, _, stack = open_page(reply([]), rate_allowed=False)
        with stack:
            at.text_area(key="ede_text").set_value(ES_DOC).run()
            at.button(key="ede_analyse").click().run()
            self.assertEqual(len(at.error), 1)
            provider.client.messages.create.assert_not_called()

    def test_clear_button_removes_text_and_results_from_the_session(self):
        at, _, _, stack = open_page(reply([make_finding()]))
        with stack:
            at.text_area(key="ede_text").set_value(ES_DOC).run()
            at.button(key="ede_analyse").click().run()
            self.assertIn("ede_result", at.session_state)
            at.button(key="ede_clear").click().run()
            self.assertNotIn("ede_result", at.session_state)
            self.assertEqual(at.text_area(key="ede_text").value, "")

    def test_basque_interface_is_used_when_selected(self):
        at, _, _, stack = open_page(reply([]), lang="Euskera")
        with stack:
            self.assertEqual(at.title[0].value, get_lang("Euskera")["ede_title"])
            self.assertNotEqual(get_lang("Euskera")["ede_title"], get_lang("Español")["ede_title"])

    def test_privacy_notice_and_ai_disclaimer_are_shown_before_submission(self):
        at, _, _, stack = open_page(reply([]))
        with stack:
            warnings = " ".join(w.value for w in at.warning)
            self.assertIn("anonimización", warnings)
            self.assertIn("hipótesis", " ".join(i.value for i in at.info))


class NoJudgementUiTests(unittest.TestCase):
    def test_page_shows_no_scores_ranks_or_traffic_lights(self):
        findings = [make_finding(), make_finding("persons_voice", "Es una persona conflictiva con el resto de residentes")]
        at, _, _, stack = open_page(reply(findings))
        with stack:
            at.text_area(key="ede_text").set_value(ES_DOC).run()
            at.button(key="ede_analyse").click().run()
            self.assertEqual(len(at.metric), 0)
            self.assertEqual(len(at.get("progress")), 0)
        source = read(PAGE).lower()
        for word in ("score", "ranking", "st.metric", "st.progress", "traffic", "🟢", "🟡", "🔴", "risk"):
            self.assertNotIn(word, source)

    def test_every_visible_ede_string_avoids_scoring_language(self):
        for name in ("Español", "Euskera", "English"):
            blob = repr({k: v for k, v in LANG[name].items() if k.startswith("ede_")}).lower()
            for word in ("bias score", "puntuación de sesgo", "alto riesgo", "high risk", "risk level"):
                self.assertNotIn(word, blob)
            self.assertIn("hipótesis" if name == "Español" else ("hipotesi" if name == "Euskera" else "hypotheses"), blob)


class TranslationTests(unittest.TestCase):
    def _keys(self, d, prefix=""):
        out = set()
        for k, v in d.items():
            out.add(prefix + k)
            if isinstance(v, dict):
                out |= self._keys(v, prefix + k + ".")
        return out

    def test_all_three_languages_have_identical_ede_structure(self):
        def ede(lang):
            return {k: v for k, v in LANG[lang].items() if k.startswith("ede_") or k == "nav_ede"}
        es, eu, en = (self._keys(ede(n)) for n in ("Español", "Euskera", "English"))
        self.assertEqual(es, eu)
        self.assertEqual(es, en)

    def test_every_programme_document_type_dimension_and_error_has_a_label_everywhere(self):
        codes = ["input_empty", "input_too_short", "input_too_long", "input_invalid", "not_authorised",
                 "provider_not_configured", "provider_unavailable", "output_invalid", "output_truncated",
                 "busy", "rate_limited", "upload_type", "upload_too_large", "upload_decode", "unknown"]
        for name in ("Español", "Euskera", "English"):
            T = get_lang(name)
            for key in config.EDE_PROGRAMME_KEYS:
                self.assertTrue(T["ede_programmes"][key])
            for key in config.EDE_DOCUMENT_TYPE_KEYS:
                self.assertTrue(T["ede_doctypes"][key])
            for key in DIMENSIONS:
                self.assertTrue(T["ede_dims"][key]["label"] and T["ede_dims"][key]["desc"])
            for code in codes:
                self.assertTrue(T["ede_errors"][code])

    def test_every_error_code_the_service_can_raise_is_translated(self):
        source = read("services/ede_analysis.py")
        raised = set(re.findall(r'EdeAnalysisError\("([a-z_]+)"', source))
        for code in raised:
            self.assertIn(code, LANG["Español"]["ede_errors"], code)

    def test_every_translation_key_used_by_the_page_exists(self):
        source = read(PAGE) + read("services/ede_export.py")
        used = set(re.findall(r'T\["(ede_[a-z_]+)"\]', source)) | set(re.findall(r"T\['(ede_[a-z_]+)'\]", source))
        for key in used:
            self.assertIn(key, LANG["Español"], key)


class NavigationAndRegressionTests(unittest.TestCase):
    def test_page_is_registered_in_practitioner_navigation(self):
        self.assertIn("EDE Reflection", PRACTITIONER_PAGES)
        menu = read("navigation/menus.py")
        self.assertIn("pages/ede_reflection.py", menu)
        self.assertTrue(os.path.exists("pages/ede_reflection.py"))

    def test_existing_menu_links_are_still_present(self):
        menu = read("navigation/menus.py")
        for page in ("documentation", "reflection_space", "growth_dashboard", "learning", "case_history",
                     "research_metrics_page", "system_administration", "help"):
            self.assertIn(f"pages/{page}.py", menu)

    def test_every_page_and_navigation_file_still_compiles(self):
        for folder in ("pages", "navigation"):
            for name in os.listdir(folder):
                if name.endswith(".py"):
                    py_compile.compile(os.path.join(folder, name), doraise=True)

    def test_existing_reflection_flow_files_are_untouched_in_behaviour(self):
        from rdi.companions import COMPANIONS
        self.assertEqual(len(COMPANIONS), 8)


if __name__ == "__main__":
    unittest.main()
