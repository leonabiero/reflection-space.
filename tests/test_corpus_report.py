"""Offline tests for the printable corpus report: safety (escaping, no
scripts), honesty (X of N, no group comparison) and the switches."""
import re
import unittest

from services.corpus_report_builder import build_corpus_report
from services import corpus_terms
from services.locales.es import LANG_ES
from services.locales.en import LANG_EN
from services.locales.eu import LANG_EU

LENSES = {"client_voice": "Voz de la persona"}
CORPUS = {"name": "Colección <b>x</b>"}
COUNTS = {"documents": 10, "passages": 80}
RUN = {"created_at": "2026-10-20T10:00:00", "documents_considered": 10, "passages_considered": 80,
       "patterns_created": 1,
       "parameters": {"similarity_level": "balanced", "min_passages": 3, "min_documents": 3,
                      "include_questions": True}}


def pattern(**kw):
    base = {
        "id": 1, "title": "Tema <script>alert(1)</script>", "description": "Descripción & más",
        "why_it_matters": "Importa", "alternative_explanations": ["Otra"], "limitations": ["Límite"],
        "questions": ["¿Pregunta de la IA?"], "grouping_basis": {}, "explanation_status": "ai",
        "status": "candidate", "lost_members": 0, "below_minimum": False,
        "members": [{"id": i, "doc_no": i, "text": f"Fragmento exacto {i} <i>"} for i in range(1, 5)],
        "excluded_members": [],
        "counts": {"passages": 4, "documents": 4, "total_documents": 10, "doc_numbers": [1, 2, 3, 4], "share": 0.4},
    }
    base.update(kw)
    return base


READINGS = {
    "overview": {"documents": 10, "read": 10, "unread": 0,
                 "lenses": {"client_voice": {"finding": 2, "no_finding": 8, "failed": 0}}},
    "items": {"client_voice": [
        {"doc_no": 3, "observation": "Observación IA", "questions": ["¿Una pregunta de lectura?"],
         "evidence": [{"quote": "cita exacta de lectura"}], "unverified_count": 0}]},
}
TERMS = corpus_terms.count_terms(
    [{"id": 1, "term": "agresiv*", "norm": "agresiv*"}],
    [{"doc_no": 1, "content": "es agresivo"}, {"doc_no": 2, "content": "tranquilo"}])


def build(T=LANG_ES, lang="Español", **kw):
    args = dict(run=RUN, patterns=[pattern()], events_by_pattern={1: [{"comment": "Nota <b>", "created_at": "2026-10-20"}]},
                readings=READINGS, terms=TERMS)
    args.update(kw)
    return build_corpus_report(T, lang, LENSES, CORPUS, COUNTS, "2026-10-20", **args)


class ReportTests(unittest.TestCase):
    def test_every_text_key_it_uses_exists_in_all_languages(self):
        with open("services/corpus_report_builder.py", encoding="utf-8") as handle:
            source = handle.read()
        keys = set(re.findall(r"T\[['\"]([a-z_]+)['\"]\]", source))
        self.assertGreater(len(keys), 30)
        for name, lang in (("es", LANG_ES), ("en", LANG_EN), ("eu", LANG_EU)):
            for key in keys:
                self.assertIn(key, lang, f"{key} missing in {name}")
                self.assertTrue(lang[key], f"{key} empty in {name}")

    def test_everything_typed_is_escaped_and_no_script_can_run(self):
        html = build()
        self.assertNotIn("<script", html)
        self.assertNotIn("<b>x</b>", html)
        self.assertIn("&lt;b&gt;x&lt;/b&gt;", html)
        self.assertIn("&lt;i&gt;", html)
        self.assertIn("default-src 'none'", html)
        self.assertNotRegex(html, r"<(?:img|link|iframe|object|embed)\b")
        self.assertNotRegex(html, r"https?://")

    def test_it_says_x_of_n_and_that_groups_cannot_be_compared(self):
        for T, lang in ((LANG_ES, "Español"), (LANG_EN, "English"), (LANG_EU, "Euskera")):
            html = build(T, lang)
            self.assertIn(T["corpus_no_groups_note"].replace("'", "&#x27;"), html.replace("&#x27;", "&#x27;"))
            self.assertIn(T["corpus_terms_texts_cell"].format(documents=4, total=10), html)
            self.assertIn(T["patterns_candidate_label"], html)

    def test_texts_are_named_only_by_number(self):
        html = build()
        self.assertIn("T-001", html)
        self.assertNotRegex(html, r"\.(pdf|docx|txt)\b")

    def test_passages_and_quotes_can_be_left_out(self):
        html = build(include_passages=False)
        self.assertNotIn("Fragmento exacto", html)
        self.assertNotIn("cita exacta de lectura", html)
        self.assertNotIn("Observación IA", html)
        self.assertIn(LANG_ES["corpus_report_passages_omitted"], html)
        full = build(include_passages=True)
        self.assertIn("Fragmento exacto 1", full)
        self.assertIn("cita exacta de lectura", full)

    def test_questions_switch_is_honoured_everywhere(self):
        on = build(include_questions=True)
        self.assertIn("¿Pregunta de la IA?", on)
        self.assertIn("¿Una pregunta de lectura?", on)
        off = build(include_questions=False)
        self.assertNotIn("¿Pregunta de la IA?", off)
        self.assertNotIn("¿Una pregunta de lectura?", off)

    def test_a_search_made_without_questions_prints_none(self):
        run = dict(RUN, parameters=dict(RUN["parameters"], include_questions=False))
        self.assertNotIn("¿Pregunta de la IA?", build(run=run))

    def test_parts_can_be_left_out(self):
        only_terms = build(patterns=None, readings=None, run=None)
        self.assertNotIn("Tema", only_terms)
        self.assertIn("agresiv*", only_terms)
        self.assertNotIn(LANG_ES["corpus_report_readings_title"], only_terms)
        nothing_but_header = build(patterns=None, readings=None, terms=None, run=None)
        self.assertNotIn(LANG_ES["corpus_report_terms_title"], nothing_but_header)

    def test_team_comments_can_be_left_out(self):
        self.assertIn("Nota &lt;b&gt;", build(include_comments=True))
        self.assertNotIn("Nota &lt;b&gt;", build(include_comments=False))

    def test_no_conclusion_wording_about_bias_being_found(self):
        html = build(T=LANG_EN, lang="English").lower()
        self.assertNotIn("bias was found", html)
        self.assertNotIn("discrimination was found", html)

    def test_page_is_a_complete_document_in_the_right_language(self):
        self.assertIn("<html lang='eu'>", build(LANG_EU, "Euskera"))
        self.assertIn("<html lang='en'>", build(LANG_EN, "English"))
        self.assertTrue(build().startswith("<!doctype html>"))


if __name__ == "__main__":
    unittest.main()
