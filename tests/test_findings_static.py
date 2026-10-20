"""Static checks for the saved-findings feature: deletion wiring,
translation parity, and no sensitive text in logs."""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _read(*parts):
    return (ROOT.joinpath(*parts)).read_text(encoding="utf-8")


class DeletionWiringTests(unittest.TestCase):
    def test_pending_draft_deletion_erases_saved_findings_in_same_transaction(self):
        source = _read("services", "draft_storage.py")
        start = source.index("def delete_pending_draft")
        end = source.index("def soft_delete_draft", start)
        section = source[start:end]
        self.assertIn("delete_runs_for_drafts(c, [draft_id])", section)
        self.assertLess(section.index("delete_runs_for_drafts"), section.index("conn.commit()"))

    def test_permanent_purge_erases_saved_findings_in_same_transaction(self):
        source = _read("services", "draft_storage.py")
        section = source[source.index("def purge_expired_deletions"):]
        self.assertIn("delete_runs_for_drafts(c, expired_ids)", section)
        self.assertLess(section.index("delete_runs_for_drafts"), section.index("conn.commit()"))

    def test_schema_cascades_children_from_runs(self):
        schema = _read("services", "db_schema.py")
        self.assertGreaterEqual(schema.count("ON DELETE CASCADE"), 3)
        for table in ("reflection_runs", "reflection_run_sources",
                      "reflection_findings", "finding_feedback"):
            self.assertIn(f"CREATE TABLE IF NOT EXISTS {table}", schema)


class LoggingTests(unittest.TestCase):
    def test_store_never_logs_finding_text_quotes_or_notes(self):
        source = _read("services", "findings_store.py")
        for call in re.findall(r"logger\.\w+\((?:.|\n)*?\)\n", source):
            for forbidden in ("observation", "quote", "note", "alternative", "questions", "evidence"):
                self.assertNotIn(forbidden, call.replace("findings=%d", ""),
                                 f"logger call mentions {forbidden!r}: {call!r}")


class TranslationTests(unittest.TestCase):
    def test_all_findings_keys_exist_in_all_three_languages(self):
        from services.locales.es import LANG_ES
        from services.locales.eu import LANG_EU
        from services.locales.en import LANG_EN
        keys = [k for k in LANG_ES if k.startswith("findings_")]
        self.assertGreaterEqual(len(keys), 20)
        for name, lang in (("es", LANG_ES), ("eu", LANG_EU), ("en", LANG_EN)):
            for key in keys:
                self.assertIn(key, lang, f"{key} missing in {name}")
                self.assertTrue(lang[key], f"{key} empty in {name}")
        self.assertEqual(set(LANG_ES["findings_labels"]), set(LANG_EN["findings_labels"]))
        self.assertEqual(set(LANG_ES["findings_labels"]), set(LANG_EU["findings_labels"]))

    def test_every_findings_key_used_in_code_exists(self):
        from services.locales.es import LANG_ES
        used = set()
        for rel in (("pages", "reflection_space.py"), ("pages", "growth_dashboard.py"),
                    ("services", "findings_ui.py")):
            used |= set(re.findall(r'T\["(findings_[a-z_]+)"\]', _read(*rel)))
        self.assertTrue(used)
        for key in used:
            self.assertIn(key, LANG_ES, key)

    def test_label_set_matches_store(self):
        from services.findings_store import FEEDBACK_LABELS
        from services.locales.es import LANG_ES
        self.assertEqual(set(FEEDBACK_LABELS), set(LANG_ES["findings_labels"]))


class UiEscapingTests(unittest.TestCase):
    def test_markdown_in_a_quote_is_displayed_literally(self):
        import sys, types
        # findings_ui imports streamlit; the real package is installed, but
        # only the pure helper is exercised here.
        from services.findings_ui import md_escape
        self.assertEqual(md_escape("a *b* _c_ [d](e) #f"), r"a \*b\* \_c\_ \[d\](e) \#f")
        self.assertEqual(md_escape("line one\n   line two"), "line one line two")
        self.assertEqual(md_escape("<script>x</script>"), r"\<script\>x\</script\>")


if __name__ == "__main__":
    unittest.main()
