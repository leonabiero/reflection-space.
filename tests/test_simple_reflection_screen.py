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

import os
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
        # November 2026: it now sits inside the folded "Reflection info"
        # band and opens with a switch that starts OFF.
        self.assertIn('st.toggle(T["rs_anonymised_preview_label"], value=False', self.page)
        start = self.page.index('st.toggle(T["rs_anonymised_preview_label"]')
        block = self.page[start:self.page.index("st.write(session.safe_text)", start) + 40]
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


class SavedOriginalTextStaticTests(unittest.TestCase):
    """November 2026 (agreed with EDE): the ORIGINAL text is saved in the EU
    database for pattern analysis. The AI still only receives the
    anonymised text (see PagePrivacyFlowTests above)."""

    def test_page_saves_the_original_text_and_no_longer_the_anonymised_copy(self):
        page = _read("pages", "reflection_space.py")
        self.assertIn("material if SAVE_ORIGINAL_TEXT else None", page)
        self.assertNotIn("anonymised_text=", page)

    def test_schema_has_the_original_text_column(self):
        schema = _read("services", "db_schema.py")
        self.assertIn("ADD COLUMN IF NOT EXISTS original_text TEXT", schema)
        # Older reflections (4-10 November 2026) keep their anonymised copy.
        self.assertIn("ADD COLUMN IF NOT EXISTS anonymised_text TEXT", schema)

    def test_settings_have_safe_defaults(self):
        import config
        self.assertIsInstance(config.SAVE_ORIGINAL_TEXT, bool)
        self.assertGreaterEqual(config.ORIGINAL_TEXT_RETENTION_MONTHS, 1)
        if "ORIGINAL_TEXT_RETENTION_MONTHS" not in os.environ:
            self.assertEqual(config.ORIGINAL_TEXT_RETENTION_MONTHS, 15)
        self.assertGreaterEqual(config.ANONYMISED_TEXT_RETENTION_MONTHS, 1)

    def _capture(self, rr, call):
        captured = {}

        class _Cursor:
            def __enter__(self): return self
            def __exit__(self, *a): return False
            def execute(self, sql, params=None): captured["sql"], captured["params"] = sql, params
            def fetchone(self): return None
            def fetchall(self): return []

        class _Conn:
            def cursor(self): return _Cursor()
            def close(self): pass

        with patch.object(rr, "_get_conn", lambda: _Conn()):
            call()
        return captured

    def test_original_text_by_id_is_for_its_author_only(self):
        from services import reflection_records as rr
        self.assertIsNone(rr.get_original_text(5, ""))
        self.assertIsNone(rr.get_original_text(None, "ana"))
        captured = self._capture(rr, lambda: rr.get_original_text(5, "ana"))
        self.assertIn("r.created_by = %s", captured["sql"])
        self.assertIn("r.deleted_at IS NULL", captured["sql"])
        self.assertIn("make_interval(months", captured["sql"])
        self.assertEqual(captured["params"][:2], (5, "ana"))

    def test_management_list_has_no_names_codes_or_times(self):
        from services import reflection_records as rr
        with patch.object(rr, "_get_conn", side_effect=AssertionError("no DB for these roles")):
            for role in ("Social Worker", "System Administrator", ""):
                self.assertEqual(rr.list_original_texts(role), [])
                self.assertEqual(rr.count_original_texts(role), 0)
        captured = self._capture(rr, lambda: rr.list_original_texts("Supervisor"))
        select_part = captured["sql"].split("FROM", 1)[0]
        for forbidden in ("created_by", "reflection_code", "case_ref", "r.created_at,"):
            self.assertNotIn(forbidden, select_part)
        self.assertIn("r.created_at::date", select_part)

    def test_case_history_never_shows_the_original_text(self):
        page = _read("pages", "case_history.py")
        self.assertNotIn("get_original_text", page)
        self.assertNotIn("list_original_texts", page)
        self.assertIn('T["ch_original_text_in_patterns_note"]', page)

    def test_older_anonymised_text_is_still_limited_to_author_or_managers(self):
        from services import reflection_records as rr
        self.assertIsNone(rr.get_anonymised_text(5, "", "Supervisor"))
        captured = self._capture(rr, lambda: rr.get_anonymised_text(5, "ana", "Social Worker"))
        self.assertEqual(captured["params"][2:], (False, "ana"))
        captured = self._capture(rr, lambda: rr.get_anonymised_text(5, "boss", "Supervisor"))
        self.assertEqual(captured["params"][2:], (True, "boss"))

    def test_the_texts_are_never_logged(self):
        source = _read("services", "reflection_records.py")
        for call in re.findall(r"logger\.\w+\((?:.|\n)*?\)\n", source):
            args = call.split(",", 1)[-1]
            self.assertNotIn("anonymised_text", args)
            self.assertNotIn("original_text", args)


class TranslationTests(unittest.TestCase):
    NEW_KEYS = (
        "rs_heading", "rs_subheading", "rs_material_label", "rs_material_placeholder",
        "rs_file_loaded", "rs_both_inputs_notice", "rs_source_label", "rs_source_options",
        "rs_choose_source_warning", "rs_need_material", "rs_language_label",
        "rs_language_names", "rs_privacy_note", "rs_reflect_button", "rs_anonymised_status",
        "rs_preparing_status", "rs_anonymise_failed", "rs_anonymised_preview_label",
        "rs_anonymised_preview_help", "rs_try_again_button", "rs_original_saved_note",
        "ch_show_anonymised_text", "ch_anonymised_text_caption", "ch_anonymised_text_unavailable",
        "ch_show_saved_text", "ch_original_text_caption", "ch_saved_text_unavailable",
        "ch_original_text_in_patterns_note", "patterns_texts_header", "patterns_texts_caption",
        "patterns_texts_empty", "patterns_texts_showing", "patterns_texts_item",
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
        for lang in (LANG_ES, LANG_EU, LANG_EN):
            self.assertIn("{months}", lang["rs_original_saved_note"])
            self.assertIn("{months}", lang["help"]["original_saved_note"])
            self.assertIn("{months}", lang["ch_original_text_caption"])
            self.assertIn("{months}", lang["patterns_texts_caption"])
            self.assertIn("{shown}", lang["patterns_texts_showing"])
            self.assertIn("{date}", lang["patterns_texts_item"])
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


class OpportunityCardsTests(unittest.TestCase):
    """November 2026: the eight opportunities as cards with a status dot."""

    def _session(self, result_findings, failed=()):
        from rdi.reflection_session import ReflectionSession
        from rdi.reflection_objects import ReflectiveOpportunity
        from rdi.companions import COMPANIONS
        labels = {c["key"]: c["label"] for c in COMPANIONS}
        result = {
            "opportunities": [ReflectiveOpportunity(trigger=k, context="", focus="obs", invitation=["q"])
                              for k in result_findings],
            "failed_labels": [labels[k] for k in failed],
            "safe_text": "text",
        }
        with patch("rdi.reflection_session.st") as fake_st:
            fake_st.session_state = {"lang": "English"}
            return ReflectionSession(result, [], "RS-TEST01")

    def test_each_card_gets_the_right_status(self):
        s = self._session(["client_voice", "continuity"], failed=["possible_bias"])
        self.assertEqual(s.status_of("client_voice"), s.STATUS_FINDING)
        self.assertEqual(s.status_of("continuity"), s.STATUS_FINDING)
        self.assertEqual(s.status_of("possible_bias"), s.STATUS_UNAVAILABLE)
        self.assertEqual(s.status_of("labels_and_language"), s.STATUS_NONE)

    def test_a_successful_retry_turns_the_dot_green(self):
        from rdi.reflection_objects import ReflectiveOpportunity
        s = self._session([], failed=["possible_bias"])
        s.replace_opportunity("possible_bias",
                              ReflectiveOpportunity(trigger="possible_bias", context="", focus="o", invitation=["q"]),
                              generated=True)
        self.assertEqual(s.status_of("possible_bias"), s.STATUS_FINDING)

    def test_a_retry_with_nothing_found_turns_the_dot_grey(self):
        from rdi.reflection_objects import ReflectiveOpportunity
        s = self._session([], failed=["possible_bias"])
        s.replace_opportunity("possible_bias",
                              ReflectiveOpportunity(trigger="possible_bias", context="", focus="n/a", invitation=[]))
        self.assertEqual(s.status_of("possible_bias"), s.STATUS_NONE)

    def test_page_uses_cards_not_tabs(self):
        page = _read("pages", "reflection_space.py")
        self.assertNotIn("st.tabs(", page)
        self.assertIn('key=f"rs_card_{trigger}"', page)
        self.assertIn('help=T["rs_card_status"][status]', page)   # not colour alone
        self.assertIn('st.info(T["rs_cards_choose"])', page)      # nothing open at first

    def test_fixed_order_matches_the_drawing(self):
        from rdi.conversation_builder import CONVERSATION_ORDER
        self.assertEqual(CONVERSATION_ORDER, [
            "client_voice", "observation_vs_interpretation", "labels_and_language", "possible_bias",
            "missing_information", "evidence_for_decisions", "continuity", "strengths_and_deficits",
        ])

    def test_card_texts_exist_in_all_languages(self):
        from services.locales.es import LANG_ES
        from services.locales.eu import LANG_EU
        from services.locales.en import LANG_EN
        for lang in (LANG_ES, LANG_EU, LANG_EN):
            for key in ("rs_cards_hint", "rs_cards_choose", "rs_card_explored"):
                self.assertTrue(lang[key], key)
            self.assertEqual(set(lang["rs_card_status"]), {"finding", "none", "unavailable"})
            self.assertTrue(lang["help"]["cards_note"])


class SimplerResultsScreenTests(unittest.TestCase):
    """November 2026, after the first session with the EDE team: only what
    is needed to start reflecting is open after Reflect."""

    @classmethod
    def setUpClass(cls):
        cls.page = _read("pages", "reflection_space.py")

    def test_reflection_info_is_one_folded_band(self):
        self.assertIn('T[\'rs_info_header\']} · {session.case_ref} · {reflection_language}"', self.page)
        start = self.page.index("T['rs_info_header']")
        band = self.page[start:self.page.index('st.subheader(T["workspace_opportunities_header"])', start)]
        self.assertIn("expanded=False", band)
        self.assertIn("_render_identity_caption(session.case_ref)", band)
        self.assertIn('st.toggle(T["workspace_document_header"], value=False', band)
        self.assertIn("st.write(session.safe_text)", band)
        self.assertIn("st.write(session.case_text)", band)

    def test_only_the_questions_are_open(self):
        start = self.page.index("def _render_opportunity_tab_body")
        body = self.page[start:self.page.index("_render_finding_notes(session, opportunity)", start)]
        # The fold ("Why these questions?") comes first and holds everything
        # the AI noticed; the questions come after it, open.
        fold_at = body.index('st.expander(T["workspace_more_header"], expanded=False)')
        self.assertLess(fold_at, body.index('st.markdown(f"- {q}")'))
        fold = body[fold_at:body.index("elif opportunity.focus:")]
        self.assertIn("st.write(opportunity.focus)", fold)
        self.assertIn("render_evidence(", fold)
        self.assertIn('st.caption(T["workspace_reminder"])', fold)   # reminder stays inside the fold
        # The questions list is iterated once, so the Retry button still appears.
        self.assertEqual(body.count("for q in questions:"), 1)

    def test_new_texts_exist_in_all_languages(self):
        from services.locales.es import LANG_ES
        from services.locales.eu import LANG_EU
        from services.locales.en import LANG_EN
        for lang in (LANG_ES, LANG_EU, LANG_EN):
            for key in ("rs_info_header", "workspace_more_header", "workspace_questions_header",
                        "workspace_explore_button"):
                self.assertTrue(lang.get(key), key)
        self.assertEqual(LANG_EN["workspace_explore_button"], "Explore this with the companion")
        self.assertEqual(LANG_ES["workspace_explore_button"], "Explorar con el acompañante")


class MyReflectionGroupedTests(unittest.TestCase):
    """November 2026: My Reflection shows one line per reflection with its
    observations inside, instead of one line per observation."""

    def test_observations_are_grouped_under_their_reflection(self):
        from unittest.mock import MagicMock
        from datetime import datetime
        from services import findings_store as fs

        cursor = MagicMock()
        when = datetime(2026, 11, 8, 23, 1)
        cursor.fetchall.side_effect = [
            [(2, "RS-NEWER", when), (1, "RS-OLDER", when)],          # page of reflections
            [(21, 2, "RS-NEWER", "continuity", "o", "[]", "[]", 0, "English", "v", when,
              None, None, None, False, None, False),
             (11, 1, "RS-OLDER", "client_voice", "o", "[]", "[]", 0, "English", "v", when,
              "useful", "note", "", False, when, False),
             (12, 1, "RS-OLDER", "continuity", "o", "[]", "[]", 0, "English", "v", when,
              None, None, None, False, None, False)],
        ]
        conn = MagicMock()
        conn.cursor.return_value.__enter__.return_value = cursor
        with patch.object(fs, "_get_conn", return_value=conn):
            result = fs.get_my_findings_by_reflection("anneh", limit=5)

        self.assertEqual([r["case_ref"] for r in result], ["RS-NEWER", "RS-OLDER"])
        self.assertEqual([f["id"] for f in result[1]["findings"]], [11, 12])
        self.assertEqual(result[1]["findings"][0]["feedback"]["label"], "useful")
        self.assertIsNone(result[0]["findings"][0]["feedback"])
        # Only this person's reflections: the name is a filter in both queries.
        for call in cursor.execute.call_args_list:
            self.assertIn("r.created_by = %s", call.args[0])
        self.assertEqual(fs.get_my_findings_by_reflection(""), [])

    def test_page_uses_the_grouped_view(self):
        page = _read("pages", "growth_dashboard.py")
        self.assertIn("get_my_findings_by_reflection(", page)
        self.assertIn('T["findings_pick_observation"]', page)
        self.assertNotIn("get_my_findings(", page)

    def test_grouped_view_texts_exist_in_all_languages(self):
        from services.locales.es import LANG_ES
        from services.locales.eu import LANG_EU
        from services.locales.en import LANG_EN
        for lang in (LANG_ES, LANG_EU, LANG_EN):
            for key in ("findings_journal_count_reflections", "findings_reflection_line",
                        "findings_reflection_notes_suffix", "findings_pick_observation"):
                self.assertTrue(lang.get(key), key)
            lang["findings_reflection_line"].format(code="RS-X", date="d", count=3)
            lang["findings_reflection_notes_suffix"].format(count=1)
            lang["findings_journal_count_reflections"].format(total=1, page=1, pages=1)


class OwnDeletionStaticTests(unittest.TestCase):
    def test_hidden_rule_covers_deleted_reflections(self):
        from services.findings_store import NOT_IN_DELETION_WINDOW
        self.assertIn("r.deleted_at IS NULL", NOT_IN_DELETION_WINDOW)

    def test_my_reflection_page_offers_delete_with_confirmation_and_restore(self):
        page = _read("pages", "growth_dashboard.py")
        for needed in ("delete_own_reflection(", "restore_own_reflection(", "is_confirming(confirm_key)",
                       "purge_expired_reflection_deletions()", "list_own_deleted_reflections("):
            self.assertIn(needed, page, needed)

    def test_texts_exist_and_no_false_privacy_promise(self):
        from services.locales.es import LANG_ES
        from services.locales.eu import LANG_EU
        from services.locales.en import LANG_EN
        keys = [k for k in LANG_EN if k.startswith("my_reflections_")]
        self.assertGreaterEqual(len(keys), 15)
        for lang in (LANG_ES, LANG_EU, LANG_EN):
            for key in keys:
                self.assertTrue(lang.get(key), key)
            self.assertTrue(lang["help"]["delete_note"])
        self.assertNotIn("not visible to supervisors", LANG_EN["growth_intro"])
        self.assertNotIn("visible to no one but you", LANG_EN["help"]["growth_section_body"])
