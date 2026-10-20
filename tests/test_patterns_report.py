"""Tests for the printable pattern report (Stage 3)."""
import re
import unittest
from pathlib import Path

from services.report_builder import build_pattern_report, case_message
from services.locales.es import LANG_ES
from services.locales.en import LANG_EN
from services.locales.eu import LANG_EU

ROOT = Path(__file__).resolve().parents[1]
LENSES = {"client_voice": "Voz de la persona", "possible_bias": "Posible sesgo"}


def _member(i, case="CASO-7", quote="cita exacta de prueba"):
    return {"id": i, "run_id": i, "case_ref": case, "module": "client_voice",
            "observation": f"Observación número {i}", "questions": [],
            "evidence": [{"quote": quote}], "language": "Español",
            "created_at": "2026-03-01T10:00:00"}


def _pattern(pid=1, title="Tema <uno>", status="worth_discussing", **over):
    p = {"id": pid, "title": title, "description": "Descripción & más", "why_it_matters": "Importa",
         "modules": ["client_voice"], "alternative_explanations": ["Alternativa A"],
         "limitations": ["Límite A"], "questions": ["¿Pregunta 1?", "¿Pregunta 2?"],
         "grouping_basis": {}, "explanation_status": "ai", "status": status,
         "created_at": "2026-03-02T10:00:00", "lost_members": 0,
         "members": [_member(1), _member(2, "CASO-8"), _member(3, "CASO-9")], "excluded_members": [],
         "counts": {"observations": 3, "reflections": 3, "cases": 3, "reflections_without_case": 0,
                    "case_recurrence_known": True, "date_first": "2026-03-01", "date_last": "2026-03-01",
                    "modules": {"client_voice": 3}},
         "below_minimum": False}
    p.update(over)
    return p


RUN = {"id": 5, "created_at": "2026-03-02T10:00:00", "observations_considered": 40, "patterns_created": 1,
       "parameters": {"similarity_level": "balanced", "min_observations": 3, "min_reflections": 2,
                      "modules": ["client_voice"], "date_from": "2026-01-01", "date_to": None}}
EVENTS = {1: [{"kind": "status_changed", "actor": "NOMBRE-GESTOR", "actor_role": "Supervisor",
               "old_value": "candidate", "new_value": "worth_discussing",
               "comment": "Comentar el martes", "created_at": "2026-03-03T09:00:00"}]}


def build(T=LANG_ES, lang="Español", patterns=None, **kw):
    options = dict(include_observations=True, include_case_refs=False, include_comments=True)
    options.update(kw)
    return build_pattern_report(T, lang, LENSES, RUN, [_pattern()] if patterns is None else patterns,
                                EVENTS, "2026-10-20", **options)


class ContentTests(unittest.TestCase):
    def test_is_a_complete_cautious_page(self):
        html = build()
        self.assertTrue(html.startswith("<!doctype html>"))
        self.assertIn("candidato", html.lower())
        self.assertIn("No son conclusiones", html)
        self.assertIn("Límites de este informe", html)
        self.assertIn("@page", html)
        self.assertIn("Observación número 1", html)
        self.assertIn("cita exacta de prueba", html)

    def test_all_languages_render(self):
        for T, lang, marker in ((LANG_ES, "Español", "lang='es'"), (LANG_EN, "English", "lang='en'"),
                                (LANG_EU, "Euskera", "lang='eu'")):
            html = build(T, lang)
            self.assertIn(marker, html)
            self.assertNotIn("{", re.sub(r"<style>.*?</style>", "", html, flags=re.S))   # no unfilled placeholder

    def test_counts_are_shown_separately(self):
        html = build(LANG_EN, "English")
        self.assertIn("3 observation(s) · 3 distinct reflection(s) · 3 distinct case(s)", html)

    def test_cases_not_claimed_when_references_are_missing(self):
        counts = dict(_pattern()["counts"], cases=1, reflections_without_case=2, case_recurrence_known=False)
        html = build(LANG_EN, "English", patterns=[_pattern(counts=counts)])
        self.assertIn("recurrence across cases cannot be established", html)
        self.assertIn("cannot be established", case_message(LANG_EN, counts))

    def test_warnings_for_withdrawn_and_failed_explanations(self):
        html = build(LANG_EN, "English", patterns=[_pattern(lost_members=2, below_minimum=True,
                                                            explanation_status="fallback")])
        self.assertIn("no longer available", html)
        self.assertIn("no longer reaches the minimums", html)
        self.assertIn("could not be written", html)

    def test_no_patterns_message(self):
        self.assertIn("No hay patrones", build(patterns=[]))


class PrivacyAndSafetyTests(unittest.TestCase):
    def test_no_author_or_private_material(self):
        html = build()
        self.assertNotIn("NOMBRE-GESTOR", html)          # even the manager who commented is not named
        for forbidden in ("test_", "created_by", "flagged", "actor", "alternative_explanation"):
            self.assertNotIn(forbidden, html.lower())

    def test_case_references_only_when_asked(self):
        self.assertNotIn("CASO-7", build())
        self.assertIn("CASO-7", build(include_case_refs=True))

    def test_options_remove_observations_and_comments(self):
        html = build(include_observations=False, include_comments=False)
        self.assertNotIn("Observación número", html)
        self.assertNotIn("cita exacta de prueba", html)
        self.assertNotIn("Comentar el martes", html)
        self.assertIn("no se incluyen", html)
        self.assertIn("Comentar el martes", build())

    def test_everything_is_escaped_and_no_scripts(self):
        hostile = "<script>alert(1)</script>"
        p = _pattern(title=hostile, description=hostile, alternative_explanations=[hostile])
        p["members"][0]["observation"] = hostile
        p["members"][0]["evidence"] = [{"quote": hostile}]
        events = {1: [{"kind": "x", "comment": hostile, "created_at": "2026-03-03"}]}
        html = build_pattern_report(LANG_ES, "Español", LENSES, RUN, [p], events, "<b>x</b>",
                                    include_observations=True, include_case_refs=True, include_comments=True)
        self.assertNotIn("<script", html.lower())
        self.assertNotIn("<b>x</b>", html)
        self.assertIn("&lt;script&gt;", html)

    def test_page_loads_nothing_from_outside(self):
        html = build()
        self.assertIn("Content-Security-Policy", html)
        self.assertIn("default-src 'none'", html)
        self.assertNotRegex(html, r"(?i)(src|href)\s*=\s*[\"']?https?:")
        self.assertNotIn("<link", html.lower())

    def test_never_says_bias_was_found(self):
        html = build(LANG_EN, "English").lower()
        for phrase in ("bias has been found", "proves bias", "discrimination was found", "confirmed bias"):
            self.assertNotIn(phrase, html)
        self.assertIn("not evidence of bias", html)


class WiringTests(unittest.TestCase):
    def test_keys_exist_in_all_languages_and_match(self):
        source = (ROOT / "services" / "report_builder.py").read_text(encoding="utf-8")
        page = (ROOT / "pages" / "pattern_explorer.py").read_text(encoding="utf-8")
        keys = set(re.findall(r"T\[['\"](report_[a-z_]+)['\"]\]", source + page))
        self.assertGreater(len(keys), 25)
        for name, lang in (("es", LANG_ES), ("en", LANG_EN), ("eu", LANG_EU)):
            for key in keys:
                self.assertTrue(lang.get(key), f"{key} missing/empty in {name}")
        for key in [k for k in LANG_ES if k.startswith("report_")]:
            holes = lambda v: set(re.findall(r"\{(\w+)\}", v)) if isinstance(v, str) else None
            self.assertEqual(holes(LANG_ES[key]), holes(LANG_EN[key]), key)
            self.assertEqual(holes(LANG_ES[key]), holes(LANG_EU[key]), key)
        self.assertEqual(len(LANG_ES["report_limits_list"]), len(LANG_EN["report_limits_list"]))
        self.assertEqual(len(LANG_ES["report_limits_list"]), len(LANG_EU["report_limits_list"]))
        self.assertEqual(set(LANG_ES), set(LANG_EN))
        self.assertEqual(set(LANG_ES), set(LANG_EU))

    def test_report_is_only_offered_on_the_manager_page(self):
        page = (ROOT / "pages" / "pattern_explorer.py").read_text(encoding="utf-8")
        self.assertIn("build_pattern_report", page)
        self.assertIn("can_review_patterns(user_role)", page)
        for other in (ROOT / "pages").glob("*.py"):
            if other.name != "pattern_explorer.py":
                self.assertNotIn("build_pattern_report", other.read_text(encoding="utf-8"))

    def test_builder_does_no_io_and_logs_nothing(self):
        source = (ROOT / "services" / "report_builder.py").read_text(encoding="utf-8")
        code = re.sub(r'""".*?"""', "", source, flags=re.S)
        for forbidden in ("logger", "open(", "pattern_store", "psycopg2", "anthropic", "requests"):
            self.assertNotIn(forbidden, code)


if __name__ == "__main__":
    unittest.main()
