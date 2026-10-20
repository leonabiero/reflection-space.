"""Static and offline checks for Corpus analysis: translations, access
wiring, privacy (no file names stored or logged), and the questions switch
in the AI explanation. No database and no AI provider is used."""
import json
import re
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


def _read(*parts):
    return ROOT.joinpath(*parts).read_text(encoding="utf-8")


def _langs():
    from services.locales.es import LANG_ES
    from services.locales.eu import LANG_EU
    from services.locales.en import LANG_EN
    return LANG_ES, LANG_EU, LANG_EN


class TranslationTests(unittest.TestCase):
    def test_same_keys_in_all_languages(self):
        es, eu, en = _langs()
        self.assertEqual(set(es), set(en))
        self.assertEqual(set(es), set(eu))

    def test_every_text_key_used_by_the_page_exists_and_is_filled(self):
        es, eu, en = _langs()
        page = _read("pages", "corpus_analysis.py")
        used = set(re.findall(r'T\["([a-z_]+)"\]', page)) | set(re.findall(r"T\['([a-z_]+)'\]", page))
        used |= {"nav_corpus"}
        self.assertGreater(len(used), 60)
        for name, lang in (("es", es), ("eu", eu), ("en", en)):
            for key in used:
                self.assertIn(key, lang, f"{key} missing in {name}")
                self.assertTrue(lang[key], f"{key} empty in {name}")

    def test_placeholders_match_between_languages(self):
        es, eu, en = _langs()
        holes = lambda s: set(re.findall(r"\{(\w+)\}", s))
        for key in [k for k in es if k.startswith("corpus_") and isinstance(es[k], str)]:
            self.assertEqual(holes(es[key]), holes(en[key]), key)
            self.assertEqual(holes(es[key]), holes(eu[key]), key)

    def test_no_text_is_left_hardcoded_on_the_page(self):
        page = _read("pages", "corpus_analysis.py")
        for call in re.findall(r'st\.(?:title|subheader|header|info|warning|error|success|button|caption|'
                               r'checkbox|toggle|text_input|text_area|markdown)\(\s*(f?"[^"]*")', page):
            if call.startswith('f"') or not re.search(r"[A-Za-zÁ-ÿ]", call):
                continue          # f-strings only wrap translated values; quote marks are not wording
            self.fail(f"hard-coded visible text: {call}")


class AccessAndPrivacyTests(unittest.TestCase):
    def test_page_menu_and_permissions_are_wired(self):
        self.assertIn("pages/corpus_analysis.py", _read("navigation", "menus.py"))
        self.assertIn("can_review_patterns(role)", _read("navigation", "menus.py").split("corpus_analysis")[0][-400:])
        self.assertIn("Text Analysis", _read("navigation", "permissions.py"))
        page = _read("pages", "corpus_analysis.py")
        self.assertIn('require_work_mode(T, "Manager")', page)
        self.assertIn("can_review_patterns(user_role)", page)

    def test_every_store_function_checks_the_role_first(self):
        source = _read("services", "corpus_store.py")
        for match in re.finditer(r"^def ([a-z_]+)\((role[^)]*)\):\n(?:    \"\"\"(?:.|\n)*?\"\"\"\n)?(.*)", source, re.M):
            name, _, first = match.groups()
            self.assertTrue(first.strip().startswith("require_pattern_role(role)"), name)

    def test_only_two_functions_take_no_role_and_are_not_reachable_from_pages(self):
        source = _read("services", "corpus_store.py")
        no_role = re.findall(r"^def ([a-z_]+)\((?!role)", source, re.M)
        self.assertEqual(sorted(n for n in no_role if not n.startswith("_")),
                         ["content_fingerprint", "finish_reading_job", "finish_run"])
        self.assertNotIn("finish_run", _read("pages", "corpus_analysis.py"))
        self.assertNotIn("finish_reading_job", _read("pages", "corpus_analysis.py"))

    def test_file_names_are_never_stored_or_logged(self):
        store = _read("services", "corpus_store.py")
        service = _read("services", "corpus_service.py") + _read("services", "corpus_reading_service.py")
        schema = _read("services", "db_schema.py")
        corpus_ddl = schema[schema.index("CREATE TABLE IF NOT EXISTS corpora"):]
        for word in ("filename", "file_name", "upload.name", "uploaded.name"):
            self.assertNotIn(word, store)
            self.assertNotIn(word, service)
        self.assertNotIn("filename", corpus_ddl.split("One-time")[0])
        page = _read("pages", "corpus_analysis.py")
        self.assertNotRegex(page, r"logger|logging|print\(")
        self.assertIn("add_document(user_role, user_name, corpus_id, anonymize(text))", page)

    def test_no_document_text_in_log_calls(self):
        for name in ("corpus_store.py", "corpus_service.py", "corpus_reading_service.py"):
            for call in re.findall(r"logger\.\w+\((.*?)\)\n", _read("services", name), re.S):
                self.assertNotRegex(call, r"\btext\b|content|passage\[", name)

    def test_collection_is_separate_from_practitioner_data(self):
        source = (_read("services", "corpus_store.py") + _read("services", "corpus_service.py")
                  + _read("services", "corpus_reading_service.py"))
        for table in ("drafts", "reflection_findings", "finding_feedback", "reflections", "pattern_runs"):
            self.assertNotRegex(source, rf"(FROM|JOIN|INTO|UPDATE)\s+{table}\b")

    def test_social_workers_and_admin_are_refused_by_the_role_check(self):
        from services.pattern_access import can_review_patterns
        self.assertFalse(can_review_patterns("Social Worker"))
        self.assertFalse(can_review_patterns("System Administrator"))
        self.assertTrue(can_review_patterns("Supervisor"))
        self.assertTrue(can_review_patterns("Programme Manager"))


class ReadingServiceOfflineTests(unittest.TestCase):
    TEXT = "La usuaria no quiso sentarse. Claramente no está motivada para trabajar con nosotros."
    GOOD = {"observation": "El texto presenta una valoración como hecho.",
            "evidence": [{"quote": "Claramente no está motivada para trabajar con nosotros."}],
            "questions": ["¿Qué otra explicación cabría?"]}

    def setUp(self):
        from services import corpus_reading_service
        self.rs = corpus_reading_service

    def _reply(self, payload):
        return SimpleNamespace(content=[SimpleNamespace(type="text", text=payload)], usage=None)

    def _read(self, replies, include_questions=True):
        calls = []

        def create(**kw):
            calls.append(kw)
            reply = replies[min(len(calls) - 1, len(replies) - 1)]
            if isinstance(reply, Exception):
                raise reply
            return self._reply(reply)
        client = SimpleNamespace(messages=SimpleNamespace(create=create))
        companion = self.rs.COMPANIONS[0]
        with patch.object(self.rs.reflection_service, "client", client), \
             patch.object(self.rs.reflection_service, "_record_claude_usage", lambda *a, **k: None), \
             patch.object(self.rs.time, "sleep", lambda *_: None):
            return self.rs.read_lens(companion, self.TEXT, "Español", include_questions), calls

    def test_prompt_follows_the_questions_switch(self):
        companion = self.rs.COMPANIONS[0]
        on = self.rs.build_reading_prompt(companion, True)
        off = self.rs.build_reading_prompt(companion, False)
        self.assertIn('"questions": []', on)
        self.assertNotIn('"questions"', off)
        self.assertIn("Do NOT include any questions", off)
        self.assertNotIn("1-3 reflective questions", off)
        for prompt in (on, off):
            self.assertIn("ONE document", prompt)
            self.assertIn("never the person", prompt)
            self.assertIn(companion["label"], prompt)

    def test_a_verified_quote_is_kept_and_a_made_up_one_is_dropped_and_counted(self):
        bad = dict(self.GOOD, evidence=[{"quote": "Claramente no está motivada para trabajar con nosotros."},
                                         {"quote": "Esta frase no existe en el texto original."}])
        reading, _ = self._read([json.dumps(bad)])
        self.assertEqual(reading["status"], "finding")
        self.assertEqual(len(reading["evidence"]), 1)
        self.assertEqual(reading["unverified_count"], 1)
        self.assertIn(reading["evidence"][0]["quote"], self.TEXT)

    def test_empty_observation_is_no_finding(self):
        reading, _ = self._read([json.dumps({"observation": "", "evidence": [], "questions": []})])
        self.assertEqual(reading["status"], "no_finding")

    def test_questions_off_drops_any_questions_sent(self):
        reading, _ = self._read([json.dumps(self.GOOD)], include_questions=False)
        self.assertEqual(reading["questions"], [])
        reading, _ = self._read([json.dumps(self.GOOD)], include_questions=True)
        self.assertEqual(reading["questions"], ["¿Qué otra explicación cabría?"])

    def test_invalid_reply_is_retried_then_marked_failed(self):
        reading, calls = self._read(["not json"])
        self.assertEqual(reading["status"], "failed")
        self.assertEqual(len(calls), self.rs.MAX_ATTEMPTS)
        reading, calls = self._read([RuntimeError("down"), json.dumps(self.GOOD)])
        self.assertEqual(reading["status"], "finding")
        self.assertEqual(len(calls), 2)

    def test_over_long_observation_is_rejected(self):
        long_reply = dict(self.GOOD, observation="x" * (self.rs.MAX_OBSERVATION_CHARS + 1))
        reading, _ = self._read([json.dumps(long_reply)])
        self.assertEqual(reading["status"], "failed")

    def test_document_text_is_sent_as_stored_and_lens_list_matches_the_practitioner_tool(self):
        _, calls = self._read([json.dumps(self.GOOD)])
        self.assertIn(self.TEXT, calls[0]["messages"][0]["content"])
        self.assertEqual([c["key"] for c in self.rs.COMPANIONS], list(self.rs.READING_LENSES))


class ExplainerSwitchTests(unittest.TestCase):
    GOOD = {"title": "Tema", "description": "d", "why_it_matters": "w",
            "alternative_explanations": ["a"], "limitations": ["l"], "questions": ["q1", "q2"]}

    def setUp(self):
        from services import pattern_explainer
        self.ex = pattern_explainer

    def _message(self, payload):
        return SimpleNamespace(content=[SimpleNamespace(type="text", text=payload)], usage=None)

    def _run(self, replies, include_questions):
        calls = []

        def create(**kw):
            calls.append(kw)
            reply = replies[min(len(calls) - 1, len(replies) - 1)]
            if isinstance(reply, Exception):
                raise reply
            return self._message(reply)
        client = SimpleNamespace(messages=SimpleNamespace(create=create))
        with patch.object(self.ex.reflection_service, "client", client), \
             patch.object(self.ex.reflection_service, "_record_claude_usage", lambda *a, **k: None):
            result = self.ex.explain_passage_group([{"text": "Texto uno."}, {"text": "Texto dos."}],
                                                   "Español", include_questions)
        return result, calls

    def test_questions_on_requires_and_keeps_questions(self):
        result, calls = self._run([json.dumps(self.GOOD)], True)
        self.assertEqual(result["status"], "ai")
        self.assertEqual(result["explanation"]["questions"], ["q1", "q2"])
        self.assertIn('"questions"', calls[0]["system"])

    def test_questions_off_does_not_ask_and_drops_any_that_arrive(self):
        result, calls = self._run([json.dumps(self.GOOD)], False)
        self.assertEqual(result["status"], "ai")
        self.assertEqual(result["explanation"]["questions"], [])
        self.assertNotIn('"questions"', calls[0]["system"])
        self.assertIn("Do NOT include any questions", calls[0]["system"])

    def test_questions_off_accepts_a_reply_without_questions(self):
        no_q = {k: v for k, v in self.GOOD.items() if k != "questions"}
        result, _ = self._run([json.dumps(no_q)], False)
        self.assertEqual(result["status"], "ai")

    def test_questions_on_rejects_a_reply_without_questions(self):
        no_q = {k: v for k, v in self.GOOD.items() if k != "questions"}
        result, calls = self._run([json.dumps(no_q)], True)
        self.assertEqual(result["status"], "fallback")
        self.assertEqual(len(calls), self.ex.MAX_ATTEMPTS)

    def test_invalid_then_valid_reply_is_retried(self):
        result, calls = self._run(["not json", json.dumps(self.GOOD)], True)
        self.assertEqual(result["status"], "ai")
        self.assertEqual(len(calls), 2)

    def test_provider_failure_gives_a_plain_fallback_without_questions_when_off(self):
        for lang in ("Español", "English", "Euskera"):
            fb = self.ex.corpus_fallback_explanation(lang, include_questions=False)
            self.assertEqual(fb["questions"], [])
            self.assertTrue(fb["title"] and fb["description"])
        result, _ = self._run([RuntimeError("down")], False)
        self.assertEqual(result["status"], "fallback")
        self.assertEqual(result["explanation"]["questions"], [])

    def test_prompt_cannot_claim_bias_or_counts_and_user_message_has_only_passages(self):
        prompt = self.ex.corpus_system_prompt(True)
        self.assertIn("NOT proof of bias", prompt)
        self.assertIn("Do not state how many", prompt)
        self.assertIn("unequal treatment", prompt)
        message = self.ex.build_corpus_user_message([{"text": "Hola", "doc_no": 7, "id": 99}])
        self.assertNotIn("7", message.replace("Return", ""))
        self.assertNotIn("T-", message)

    def test_observation_search_is_unchanged(self):
        self.assertEqual(self.ex.validate_explanation(self.GOOD)["questions"], ["q1", "q2"])
        no_q = {k: v for k, v in self.GOOD.items() if k != "questions"}
        self.assertIsNone(self.ex.validate_explanation(no_q))
        self.assertEqual(self.ex.PATTERN_PROMPT_VERSION, "2026-10-patterns-1")


if __name__ == "__main__":
    unittest.main()
