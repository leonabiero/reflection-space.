"""Static checks for the pattern explorer: translations, access wiring,
privacy of the management queries, and no sensitive text in logs."""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _read(*parts):
    return ROOT.joinpath(*parts).read_text(encoding="utf-8")


class TranslationTests(unittest.TestCase):
    def _langs(self):
        from services.locales.es import LANG_ES
        from services.locales.eu import LANG_EU
        from services.locales.en import LANG_EN
        return LANG_ES, LANG_EU, LANG_EN

    def test_all_three_languages_have_exactly_the_same_keys(self):
        es, eu, en = self._langs()
        self.assertEqual(set(es), set(en))
        self.assertEqual(set(es), set(eu))

    def test_every_pattern_key_used_in_code_exists_and_is_filled(self):
        es, eu, en = self._langs()
        used = set()
        for path in (ROOT / "pages" / "pattern_explorer.py", ROOT / "services" / "findings_ui.py",
                     ROOT / "navigation" / "menus.py"):
            used |= set(re.findall(r'T(?:\.get)?\[?\(?["\']((?:patterns|findings_share|nav_patterns)[a-z_]*)["\']', path.read_text(encoding="utf-8")))
        self.assertGreater(len(used), 40)
        for name, lang in (("es", es), ("eu", eu), ("en", en)):
            for key in used:
                self.assertIn(key, lang, f"{key} missing in {name}")
                self.assertTrue(lang[key], f"{key} empty in {name}")

    def test_dictionary_texts_cover_the_same_options(self):
        es, eu, en = self._langs()
        for key in ("patterns_similarity_levels", "patterns_statuses", "patterns_event_kinds"):
            self.assertEqual(set(es[key]), set(en[key]), key)
            self.assertEqual(set(es[key]), set(eu[key]), key)
        from services.pattern_store import PATTERN_STATUSES
        from services.pattern_engine import SIMILARITY_LEVELS
        self.assertEqual(set(es["patterns_statuses"]), set(PATTERN_STATUSES))
        self.assertEqual(set(es["patterns_similarity_levels"]), set(SIMILARITY_LEVELS))

    def test_placeholders_match_between_languages(self):
        es, eu, en = self._langs()
        for key in [k for k in es if k.startswith("patterns_") and isinstance(es[k], str)]:
            holes = lambda s: set(re.findall(r"\{(\w+)\}", s))
            self.assertEqual(holes(es[key]), holes(en[key]), key)
            self.assertEqual(holes(es[key]), holes(eu[key]), key)

    def test_privacy_sentence_now_mentions_sharing(self):
        es, eu, en = self._langs()
        self.assertIn("Compartir", es["findings_notes_privacy"])
        self.assertIn("Share", en["findings_notes_privacy"])
        self.assertIn("Partekatu", eu["findings_notes_privacy"])


class AccessTests(unittest.TestCase):
    def test_role_set_is_exactly_supervisor_and_programme_manager(self):
        from services.pattern_access import PATTERN_REVIEW_ROLES
        self.assertEqual(PATTERN_REVIEW_ROLES, {"Supervisor", "Programme Manager"})

    def test_every_store_function_checks_the_role_first(self):
        source = _read("services", "pattern_store.py")
        source = re.sub(r'""".*?"""', "", source, flags=re.S)   # ignore docstrings
        for match in re.finditer(r"^def ([a-z]\w*)\(([^)]*)\):", source, re.M):
            name, args = match.groups()
            if not args.startswith("role"):
                continue
            self.assertIn("require_pattern_role(role)", source[match.end(): match.end() + 300],
                          f"{name} does not check the role")

    def test_page_checks_role_and_is_in_menu_and_manager_pages(self):
        page = _read("pages", "pattern_explorer.py")
        self.assertIn("can_review_patterns", page)
        self.assertIn('require_work_mode(T, "Manager")', page)
        self.assertIn("pattern_explorer.py", _read("navigation", "menus.py"))
        self.assertIn("Pattern Review", _read("navigation", "permissions.py"))


class PrivacyTests(unittest.TestCase):
    def test_management_queries_never_read_the_author_or_private_notes(self):
        source = _read("services", "pattern_store.py")
        code = re.sub(r'""".*?"""', "", source, flags=re.S)   # ignore docstrings
        code = re.sub(r"#.*", "", code)
        for pattern in (r"fb\.note", r"fb\.label", r"flagged_misread", r"alternative_explanation(?!s)",
                        r"user_name", r"f\.created_by", r"r\.created_by", r"d\.created_by"):
            self.assertIsNone(re.search(pattern, code), f"management code touches {pattern}")

    def test_no_query_joins_findings_to_their_author_column(self):
        source = _read("services", "pattern_store.py")
        self.assertNotIn("r.created_by", source)
        self.assertNotIn("reflection_runs.created_by", source)

    def test_explainer_prompt_input_has_no_quotes_cases_or_dates(self):
        source = _read("services", "pattern_explainer.py")
        body = source[source.index("def build_user_message"): source.index("def explain_pattern")]
        for forbidden in ("evidence", "quote", "case_ref", "created_at", "created_by"):
            self.assertNotIn(forbidden, body)

    def test_new_modules_never_log_text(self):
        for name in ("pattern_store.py", "pattern_service.py", "pattern_explainer.py"):
            source = _read("services", name)
            for call in re.findall(r"logger\.\w+\((?:.|\n)*?\)\n", source):
                for forbidden in ("observation", "quote", "note", "description", "evidence", "raw", "user"):
                    self.assertNotIn(forbidden, call.replace("%s", "").replace("%r", "").replace("%d", ""),
                                     f"{name}: logger call mentions {forbidden!r}: {call!r}")


class WordingTests(unittest.TestCase):
    def test_interface_never_claims_bias_is_proven(self):
        es, eu, en = (__import__("services.locales.es", fromlist=["x"]).LANG_ES,
                      __import__("services.locales.eu", fromlist=["x"]).LANG_EU,
                      __import__("services.locales.en", fromlist=["x"]).LANG_EN)
        for key in ("patterns_intro", "patterns_candidate_label"):
            self.assertIn("no ", es[key].lower())      # states it is not a conclusion
        self.assertIn("not", en["patterns_candidate_label"].lower())
        self.assertIn("candidate", en["patterns_intro"].lower())


if __name__ == "__main__":
    unittest.main()
