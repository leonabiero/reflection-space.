"""Static / pure checks for the reflection-only redesign (REFLECTIONS.md):
neutral codes, case tags, translations, and the guarantee that the case
text is never stored. No database and no AI provider are needed."""
import re
import unittest
from pathlib import Path

from services import reflection_records as rr

ROOT = Path(__file__).resolve().parents[1]


def _read(*parts):
    return ROOT.joinpath(*parts).read_text(encoding="utf-8")


class CodeTests(unittest.TestCase):
    def test_generated_codes_are_valid_and_varied(self):
        codes = {rr.generate_code() for _ in range(200)}
        self.assertGreater(len(codes), 190)
        for code in codes:
            self.assertTrue(rr.is_valid_code(code), code)
            self.assertRegex(code, r"^RS-[A-Z2-9]{6}$")
            # Easily-confused characters are never used.
            self.assertFalse(set(code[3:]) & set("01OIL"), code)

    def test_normalize_accepts_sloppy_typing(self):
        self.assertEqual(rr.normalize_code(" rs-7f3k2q "), "RS-7F3K2Q")
        self.assertEqual(rr.normalize_code("7f3k2q"), "RS-7F3K2Q")
        self.assertEqual(rr.normalize_code("RS - 7F3 K2Q"), "RS-7F3K2Q")

    def test_normalize_rejects_anything_else(self):
        for bad in ("", None, "RS-123", "Maria Lopez", "RS-0OOOOO", "12345678Z", "RS-7F3K2Q9"):
            self.assertEqual(rr.normalize_code(bad), "", bad)


class TagTests(unittest.TestCase):
    def test_clean_tags_keeps_known_tags_in_order_and_caps(self):
        self.assertEqual(rr.clean_tags(["mental_health", "housing", "nonsense", "housing"]),
                         ["housing", "mental_health"])
        self.assertEqual(len(rr.clean_tags(list(rr.CASE_TAGS))), rr.MAX_TAGS)
        self.assertEqual(rr.clean_tags(None), [])

    def test_tags_are_situations_never_identifiers(self):
        for tag in rr.CASE_TAGS:
            self.assertRegex(tag, r"^[a-z_]+$")


class ContextBlockTests(unittest.TestCase):
    def test_block_is_clearly_separated_from_todays_case(self):
        block = rr.build_context_block([{
            "code": "RS-ABCDEF", "created_at": "2026-10-01T10:00:00+00:00",
            "match_reasons": ["linked"], "case_tags": ["housing"],
            "observations": [{"module": "client_voice", "observation": "obs text"}],
        }])
        self.assertIn("EARLIER REFLECTIONS", block)
        self.assertIn("NOT part of today's case text", block)
        self.assertIn("RS-ABCDEF", block)
        self.assertIn("client_voice: obs text", block)
        self.assertEqual(rr.build_context_block([]), "")


class CaseTextNeverStoredTests(unittest.TestCase):
    def test_reflection_screen_never_saves_documents(self):
        page = _read("pages", "reflection_space.py")
        for forbidden in ("draft_storage", "save_draft", "finalize_draft", "get_drafts"):
            self.assertNotIn(forbidden, page, forbidden)
        # The saved reflection carries the neutral identifiers and no sources.
        self.assertIn("source_draft_ids=[]", page)
        self.assertIn("reflection_code=ctx.reflection_code", page)
        self.assertIn("case_tags=ctx.case_tags", page)

    def test_case_text_is_not_a_database_column(self):
        schema = _read("services", "db_schema.py")
        start = schema.index("CREATE TABLE IF NOT EXISTS reflection_runs")
        end = schema.index("reflection_run_sources: which documents", start)
        section = schema[start:end]
        for forbidden in ("case_text", "content", "document"):
            self.assertNotIn(forbidden + " TEXT", section)

    def test_reflection_records_never_logs_text(self):
        source = _read("services", "reflection_records.py")
        for call in re.findall(r"logger\.\w+\((?:.|\n)*?\)\n", source):
            for forbidden in ("observation", "question", "quote", "note", "text", "tags_json"):
                self.assertNotIn(forbidden, call.split(",", 1)[-1], f"logger call mentions {forbidden!r}: {call!r}")


class NavigationTests(unittest.TestCase):
    def test_documentation_screen_is_merged(self):
        from navigation.permissions import landing_page_for_workspace, PRACTITIONER_PAGES
        self.assertEqual(landing_page_for_workspace("Practitioner"), "pages/reflection_space.py")
        self.assertNotIn("Documentation", PRACTITIONER_PAGES)
        self.assertNotIn('page_link("pages/documentation.py"', _read("navigation", "menus.py"))
        # Old links still work: the retired page only redirects.
        self.assertIn('st.switch_page("pages/reflection_space.py")', _read("pages", "documentation.py"))


class TranslationTests(unittest.TestCase):
    def test_new_keys_exist_in_all_three_languages(self):
        from services.locales.es import LANG_ES
        from services.locales.eu import LANG_EU
        from services.locales.en import LANG_EN
        prefixes = ("rs_", "ch_", "admin_legacy_docs_")
        keys = [k for k in LANG_ES if k.startswith(prefixes)]
        self.assertGreaterEqual(len(keys), 50)
        for name, lang in (("es", LANG_ES), ("eu", LANG_EU), ("en", LANG_EN)):
            for key in keys:
                self.assertTrue(lang.get(key), f"{key} missing or empty in {name}")
            self.assertEqual(set(lang["case_tag_labels"]), set(rr.CASE_TAGS), name)

    def test_every_key_used_by_the_changed_screens_exists(self):
        from services.locales.es import LANG_ES
        for rel in (("pages", "reflection_space.py"), ("pages", "case_history.py"),
                    ("pages", "admin_sections", "legacy_documents.py"),
                    ("pages", "research_metrics_page.py")):
            for key in re.findall(r'T\["([a-zA-Z0-9_]+)"\]', _read(*rel)):
                self.assertIn(key, LANG_ES, f"{key} used in {'/'.join(rel)}")

    def test_placeholders_match_across_languages(self):
        from services.locales.es import LANG_ES
        from services.locales.eu import LANG_EU
        from services.locales.en import LANG_EN
        for key, value in LANG_ES.items():
            if not key.startswith(("rs_", "ch_", "admin_legacy_docs_")) or not isinstance(value, str):
                continue
            expected = set(re.findall(r"\{(\w+)\}", value))
            for lang in (LANG_EU, LANG_EN):
                self.assertEqual(set(re.findall(r"\{(\w+)\}", lang[key])), expected, key)


if __name__ == "__main__":
    unittest.main()
