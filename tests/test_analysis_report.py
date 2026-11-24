"""
Analysis report ("Informe de análisis", November 2026) and typed evidence.

Protects: the checks made on the report's answer (only the four types,
framework areas 1-5, quotes verified word for word, limits), the typed
quotes on the lens cards (including short loaded labels, accepted only as
whole words), that a failed report never stops the lens cards from being
shown, and that the printable page never contains the original text.
"""

import threading
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from services import analysis_report as ar
from services.evidence import verify_quotes

SAFE = ("[PERSONA 1] es muy dócil y agradecida, como suele pasar con las mujeres de su cultura. "
        "Cumple con todo lo que se le pide.")


class TypedEvidenceTests(unittest.TestCase):
    def test_type_is_kept_when_valid(self):
        verified, bad = verify_quotes(
            [{"quote": "como suele pasar con las mujeres de su cultura", "type": "stereotype"}], SAFE)
        self.assertEqual(bad, 0)
        self.assertEqual(verified, [{"quote": "como suele pasar con las mujeres de su cultura",
                                     "type": "stereotype"}])

    def test_unknown_type_is_dropped_but_quote_kept(self):
        verified, _ = verify_quotes([{"quote": "Cumple con todo lo que se le pide", "type": "verdict"}], SAFE)
        self.assertEqual(verified, [{"quote": "Cumple con todo lo que se le pide"}])

    def test_old_plain_string_evidence_still_works(self):
        verified, bad = verify_quotes(["Cumple con todo lo que se le pide"], SAFE)
        self.assertEqual((verified, bad), ([{"quote": "Cumple con todo lo que se le pide"}], 0))

    def test_short_loaded_label_is_accepted_as_a_whole_word(self):
        verified, bad = verify_quotes([{"quote": "dócil", "type": "loaded_label"}], SAFE)
        self.assertEqual((verified, bad), ([{"quote": "dócil", "type": "loaded_label"}], 0))

    def test_short_quote_inside_a_word_or_untyped_is_refused(self):
        verified, bad = verify_quotes([{"quote": "ócil", "type": "loaded_label"}], SAFE)
        self.assertEqual((verified, bad), ([], 1))
        verified, bad = verify_quotes([{"quote": "dócil", "type": "bias"}], SAFE)
        self.assertEqual((verified, bad), ([], 1))

    def test_invented_quote_is_still_dropped(self):
        verified, bad = verify_quotes([{"quote": "es una persona conflictiva", "type": "loaded_label"}], SAFE)
        self.assertEqual((verified, bad), ([], 1))


class ValidateReportTests(unittest.TestCase):
    def test_good_report(self):
        report = ar.validate_report({
            "summary": "El texto describe a la persona desde la docilidad.",
            "items": [
                {"type": "loaded_label", "area": 5, "quote": "dócil", "why": "Premia la sumisión."},
                {"type": "stereotype", "area": "1", "quote": "como suele pasar con las mujeres de su cultura",
                 "why": "Generaliza por cultura."},
                {"type": "bias", "area": 2, "quote": "", "why": "No se nombran sus deseos."},
            ],
            "questions": ["¿Qué valor tiene que cumpla?", "¿Dónde está su voz?", "Una tercera"],
        }, SAFE)
        self.assertEqual(len(report["items"]), 3)
        self.assertEqual(report["items"][1]["area"], 1)
        self.assertEqual(report["items"][2]["quote"], "")
        self.assertEqual(len(report["questions"]), 2)
        self.assertEqual(report["unverified_quote_count"], 0)

    def test_bad_items_are_dropped_and_invented_quotes_removed(self):
        report = ar.validate_report({
            "summary": "s",
            "items": [
                {"type": "verdict", "area": 1, "quote": "", "why": "x"},          # bad type
                {"type": "bias", "area": 9, "quote": "", "why": "x"},             # bad area
                {"type": "bias", "area": 1, "quote": "", "why": ""},              # no reason
                {"type": "prejudice", "area": 3, "quote": "no aparece en el texto", "why": "y"},
                "not a dict",
            ],
            "questions": [],
        }, SAFE)
        self.assertEqual(len(report["items"]), 1)
        self.assertEqual(report["items"][0]["quote"], "")
        self.assertEqual(report["unverified_quote_count"], 1)

    def test_at_most_ten_items(self):
        items = [{"type": "bias", "area": 1, "quote": "", "why": f"r{i}"} for i in range(15)]
        self.assertEqual(len(ar.validate_report({"items": items}, SAFE)["items"]), ar.MAX_ITEMS)

    def test_unusable_answers(self):
        for answer in (None, [], {"error": "x"}, {"summary": "", "items": [], "questions": []}):
            self.assertIsNone(ar.validate_report(answer, SAFE), answer)


class GenerateReportTests(unittest.TestCase):
    def test_two_attempts_then_failure(self):
        calls = []

        def fake(safe, lens, lang):
            calls.append(lang)
            raise RuntimeError("network")

        with patch("services.reflection_service.generate_analysis_report", fake):
            outcome = ar.generate_report(SAFE, [], "Euskera")
        self.assertEqual(len(calls), ar.MAX_ATTEMPTS)
        self.assertIn("error", outcome)
        self.assertEqual(calls, ["Euskera", "Euskera"])

    def test_success_after_a_bad_reply(self):
        replies = iter([{"error": "Failed to parse JSON"},
                        {"summary": "ok", "items": [], "questions": ["¿Por qué?"]}])
        with patch("services.reflection_service.generate_analysis_report", lambda *a: next(replies)):
            outcome = ar.generate_report(SAFE, [], "Español")
        self.assertEqual(outcome["report"]["summary"], "ok")

    def test_lens_text_contains_only_what_the_lenses_said(self):
        text = ar.build_lens_results_text([{
            "module": "possible_bias", "observation": "Análisis.", "questions": ["¿P?"],
            "evidence": [{"quote": "dócil", "type": "loaded_label"}],
        }], {"possible_bias": "Possible Bias"})
        self.assertIn("## Possible Bias", text)
        self.assertIn('Quote (loaded_label): "dócil"', text)


class OrchestratorReportTests(unittest.TestCase):
    """A failed report never stops the lens cards from being shown."""

    def _run(self, report_outcome):
        from rdi import orchestrator
        logged = []
        fake_ar = SimpleNamespace(
            generate_report=lambda *a, **k: report_outcome,
            log_report_failure=lambda *a, **k: logged.append(a),
        )
        with patch.multiple(
            orchestrator,
            COMPANIONS=[{"key": "possible_bias", "label": "Bias", "focus": ""}],
            anonymize=lambda text, *a, **k: text,
            generate_companion_reflection=lambda c, t, l: {
                "observation": "obs", "questions": ["q"],
                "evidence": [{"quote": "dócil", "type": "loaded_label"}]},
            log_error=lambda **kw: (1, 2),
            analysis_report=fake_ar,
            _reflection_semaphore=threading.Semaphore(8),
        ):
            return orchestrator.run_reflection(SAFE, "Español"), logged

    def test_report_is_returned(self):
        report = {"summary": "s", "items": [], "questions": [], "unverified_quote_count": 0}
        result, logged = self._run({"report": report})
        self.assertEqual(result["analysis_report"], report)
        self.assertFalse(result["analysis_report_failed"])
        self.assertEqual(logged, [])
        self.assertEqual(result["findings"][0]["evidence"], [{"quote": "dócil", "type": "loaded_label"}])

    def test_failed_report_keeps_the_cards_and_is_logged_once(self):
        result, logged = self._run({"error": "API call failed", "raw": "", "traceback": None})
        self.assertIsNone(result["analysis_report"])
        self.assertTrue(result["analysis_report_failed"])
        self.assertEqual(len(result["opportunities"]), 1)
        self.assertEqual(len(logged), 1)


class PrintablePageTests(unittest.TestCase):
    def _T(self):
        from services.locales.es import LANG_ES
        return LANG_ES

    def test_page_has_report_lenses_and_highlights_but_no_original(self):
        from services.reflection_report_html import build_reflection_report_html
        report = {"summary": "Resumen <b>", "items": [
            {"type": "loaded_label", "area": 5, "quote": "dócil", "why": "Porque sí."}],
            "questions": ["¿Pregunta?"]}
        page = build_reflection_report_html(
            self._T(), "Español", "RS-TEST", "23/11/2026", report,
            [{"label": "Posibles sesgos", "analysis": "Análisis.",
              "evidence": [{"quote": "dócil", "type": "loaded_label"}], "questions": ["¿Q?"]}],
            SAFE, [{"quote": "dócil", "type": "loaded_label"}],
        )
        self.assertIn("Informe de análisis", page)
        self.assertIn("Resumen &lt;b&gt;", page)             # escaped
        self.assertIn("5 · Lenguaje, categorías y construcción de la realidad", page)
        self.assertIn("[Etiqueta cargada]", page)
        self.assertIn("<mark", page)
        self.assertNotIn("<script", page)
        self.assertNotIn("http", page.split("Content-Security-Policy")[1].split(">", 1)[1])

    def test_page_works_without_a_report(self):
        from services.reflection_report_html import build_reflection_report_html
        page = build_reflection_report_html(self._T(), "Español", "RS-TEST", "23/11/2026",
                                            None, [], SAFE, [])
        self.assertIn(self._T()["ar_failed_notice"], page)

    def test_colours_are_kept_when_printed(self):
        # 24 Nov 2026: browsers drop background colours when printing
        # unless the page asks them to keep them.
        from services.reflection_report_html import build_reflection_report_html
        from services import pattern_report_html
        page = build_reflection_report_html(self._T(), "Español", "RS-TEST", "23/11/2026",
                                            None, [], SAFE, [])
        for style in (page, pattern_report_html._STYLE):
            self.assertIn("print-color-adjust: exact", style)
            self.assertIn("-webkit-print-color-adjust: exact", style)


class TranslationTests(unittest.TestCase):
    KEYS = ("workspace_analysis_header", "ar_header", "ar_summary_header", "ar_items_header",
            "ar_questions_header", "ar_failed_notice", "ar_retry_button", "ar_missing_quote",
            "ar_unverified_notice", "ar_area_names", "evidence_type_labels", "hl_header",
            "hl_legend_title", "hl_intro", "hl_none_found", "rr_download_button", "rr_download_help",
            "rr_print_title", "rr_print_confidential", "rr_print_meta", "rr_print_footer",
            "rr_lenses_header", "anon_placeholders")

    def test_every_new_key_exists_in_three_languages(self):
        from services.locales.es import LANG_ES
        from services.locales.eu import LANG_EU
        from services.locales.en import LANG_EN
        for texts in (LANG_ES, LANG_EU, LANG_EN):
            for key in self.KEYS:
                self.assertTrue(texts.get(key), key)
            self.assertEqual(set(texts["evidence_type_labels"]),
                             {"bias", "stereotype", "prejudice", "loaded_label"})
            self.assertEqual(set(texts["ar_area_names"]), {"1", "2", "3", "4", "5"})
        self.assertEqual(LANG_ES["ar_header"], "Informe de análisis")


class ScreenOrderTests(unittest.TestCase):
    def test_report_first_then_optional_download_then_highlighted_text(self):
        from pathlib import Path
        page = (Path(__file__).resolve().parents[1] / "pages" / "reflection_space.py").read_text(encoding="utf-8")
        body = page[page.index("def _render_analysis_report"):page.index("def _render_highlighted_text")]
        self.assertLess(body.index('st.subheader(T["ar_header"])'), body.index("st.download_button("))
        call_report = page.index("_render_analysis_report(session)\n")
        call_text = page.index("_render_highlighted_text(session)\n")
        self.assertLess(call_report, call_text)
        # Only the anonymised text goes into the download.
        self.assertIn("session.safe_text", body)
        self.assertNotIn("session.case_text", body)


if __name__ == "__main__":
    unittest.main()
