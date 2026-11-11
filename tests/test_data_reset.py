"""
"Erase all data" (services/data_reset.py) and the November 2026 clean-up.

Static tests always run. The real-database tests run the erase against
an actual PostgreSQL database and are SKIPPED unless TEST_DATABASE_URL is
set (see tests/test_findings_store_postgres.py). They empty every data
table of that database, so TEST_DATABASE_URL must only ever point at a
throw-away test database.
"""
import os
import re
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parents[1]
TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL", "")

try:
    import psycopg2
except Exception:  # pragma: no cover
    psycopg2 = None


def _read(*parts):
    return ROOT.joinpath(*parts).read_text(encoding="utf-8")


class EraseAllDataGuardTests(unittest.TestCase):
    def test_refused_for_everyone_but_the_system_administrator(self):
        from services import data_reset
        with patch.object(data_reset, "_acquire_pooled_conn") as acquire:
            for role in ("Social Worker", "Supervisor", "Programme Manager", "", None):
                self.assertIsNone(data_reset.erase_all_data("someone", role), role)
            self.assertIsNone(data_reset.erase_all_data("", "System Administrator"))
        acquire.assert_not_called()

    def test_a_database_failure_rolls_back_and_is_reported(self):
        from services import data_reset
        cursor = MagicMock()
        cursor.execute.side_effect = RuntimeError("database is down")
        conn = MagicMock()
        conn.cursor.return_value.__enter__.return_value = cursor
        with patch.object(data_reset, "_acquire_pooled_conn", return_value=conn), \
                patch.object(data_reset, "log_action") as log_action:
            with self.assertRaises(RuntimeError):
                data_reset.erase_all_data("admin", "System Administrator")
        conn.rollback.assert_called_once()
        conn.commit.assert_not_called()
        conn.close.assert_called_once()
        log_action.assert_not_called()

    def test_every_table_the_app_creates_is_either_erased_or_deliberately_kept(self):
        """A table added to the schema later must be consciously added to
        the erase list (or to the kept list below) -- otherwise 'every
        count shows 0' would silently stop being true."""
        from services import data_reset
        created = set(re.findall(r"CREATE TABLE IF NOT EXISTS (\w+) \(", _read("services", "db_schema.py")))
        deliberately_kept = {"auth_sessions", "app_settings"}
        self.assertEqual(created - set(data_reset.DATA_TABLES), deliberately_kept)
        self.assertFalse(set(data_reset.DATA_TABLES) - created, "erase list names a table the app no longer creates")
        self.assertFalse(set(data_reset.DATA_TABLES) & set(data_reset.RETIRED_TABLES))
        self.assertFalse(created & set(data_reset.RETIRED_TABLES), "a retired table is still created at startup")

    def test_nothing_erases_data_automatically(self):
        """erase_all_data may only be reached from the admin panel."""
        callers = []
        for path in ROOT.rglob("*.py"):
            rel = path.relative_to(ROOT).as_posix()
            if rel.startswith(("tests/", ".git/")) or rel == "services/data_reset.py":
                continue
            if "erase_all_data" in path.read_text(encoding="utf-8"):
                callers.append(rel)
        self.assertEqual(callers, ["pages/admin_sections/data_reset.py"])

    def test_the_panel_asks_for_a_typed_confirmation(self):
        source = _read("pages", "admin_sections", "data_reset.py")
        self.assertIn('T["admin_reset_confirm_word"]', source)
        self.assertIn("disabled=(typed or \"\").strip().upper() != confirm_word.upper()", source)


class AdminPageCleanupTests(unittest.TestCase):
    REMOVED_FILES = (
        ("pages", "learning.py"),
        ("pages", "corpus_analysis.py"),
        ("pages", "research_metrics_page.py"),
        ("pages", "documentation.py"),
        ("pages", "admin_sections", "legacy_documents.py"),
        ("pages", "admin_sections", "configuration.py"),
        ("pages", "admin_sections", "case_knowledge_search.py"),
        ("services", "knowledge_assistant.py"),
        ("services", "presence.py"),
        ("services", "research_metrics_service.py"),
        ("services", "corpus_service.py"),
    )

    def test_removed_screens_are_gone_and_not_linked(self):
        for parts in self.REMOVED_FILES:
            self.assertFalse(ROOT.joinpath(*parts).exists(), "/".join(parts))
        menus = _read("navigation", "menus.py")
        for page in ("learning.py", "corpus_analysis.py", "research_metrics_page.py", "documentation.py"):
            self.assertNotIn(f'page_link("pages/{page}"', menus)

    def test_no_page_link_or_switch_points_at_a_missing_page(self):
        pattern = re.compile(r'(?:page_link|switch_page)\(\s*"(pages/[a-z_]+\.py)"')
        for path in list(ROOT.joinpath("pages").rglob("*.py")) + list(ROOT.joinpath("navigation").glob("*.py")) \
                + list(ROOT.joinpath("services").glob("*.py")) + [ROOT / "app.py"]:
            for target in pattern.findall(path.read_text(encoding="utf-8")):
                self.assertTrue(ROOT.joinpath(target).exists(), f"{path.name} -> {target}")

    def test_manager_mode_lands_on_case_history(self):
        from navigation.permissions import landing_page_for_workspace, MANAGER_PAGES
        self.assertEqual(landing_page_for_workspace("Manager"), "pages/case_history.py")
        self.assertEqual(MANAGER_PAGES, {"Case History", "Pattern Review"})

    def test_admin_page_keeps_the_no_tabs_no_columns_no_dataframe_rule(self):
        sources = [_read("pages", "system_administration.py")] + [
            p.read_text(encoding="utf-8") for p in ROOT.joinpath("pages", "admin_sections").glob("*.py")
        ]
        for source in sources:
            code = "\n".join(line for line in source.splitlines() if not line.lstrip().startswith("#"))
            code = re.sub(r'"""[\s\S]*?"""', "", code)
            for forbidden in ("st.dataframe(", "st.tabs(", "st.columns("):
                self.assertNotIn(forbidden, code)

    def test_diagnostic_centre_is_the_bare_minimum(self):
        source = _read("pages", "admin_sections", "ai_diagnostic_centre.py")
        for removed in ("build_ai_prompt", "from services import case_knowledge", "download_button", "text_area(", "text_input(",
                        "compute_ai_readiness", "date_input("):
            self.assertNotIn(removed, source)
        # Still lets the administrator change a problem's status.
        self.assertIn("update_issue_status", source)

    def test_case_history_shows_only_the_average_rating(self):
        source = _read("pages", "case_history.py")
        self.assertNotIn("get_all_feedback", source)
        self.assertNotIn("submitted_by", source)
        self.assertIn('T[\'feedback_average_label\']', source)


class CleanupTranslationTests(unittest.TestCase):
    def _languages(self):
        from services.locales.es import LANG_ES
        from services.locales.eu import LANG_EU
        from services.locales.en import LANG_EN
        return (("es", LANG_ES), ("eu", LANG_EU), ("en", LANG_EN))

    def test_new_keys_exist_in_all_three_languages(self):
        languages = self._languages()
        keys = [k for k in languages[0][1] if k.startswith(("admin_reset_", "admin_problem_"))]
        self.assertGreaterEqual(len(keys), 14)
        for name, lang in languages:
            for key in keys:
                self.assertTrue(lang.get(key), f"{key} missing or empty in {name}")

    def test_every_key_used_by_the_changed_screens_exists(self):
        spanish = self._languages()[0][1]
        for rel in (("pages", "admin_sections", "data_reset.py"),
                    ("pages", "admin_sections", "ai_diagnostic_centre.py"),
                    ("pages", "system_administration.py"),
                    ("pages", "case_history.py")):
            for key in re.findall(r'T\[["\']([a-zA-Z0-9_]+)["\']\]', _read(*rel)):
                self.assertIn(key, spanish, f"{key} used in {'/'.join(rel)}")
        for key in re.findall(r'H\["([a-zA-Z0-9_]+)"\]', _read("pages", "help.py")):
            self.assertIn(key, spanish["help"], f"help.{key}")

    def test_removed_features_left_no_texts_behind(self):
        for name, lang in self._languages():
            leftovers = [k for k in lang if k.startswith((
                "corpus_", "ka_", "learning_", "team_learning_", "presence_", "research_",
                "admin_legacy_docs_", "admin_case_search_", "admin_config_"))]
            self.assertEqual(leftovers, [], name)
            self.assertNotIn("learning_section_title", lang["help"], name)
            self.assertNotIn("research_metrics_section_title", lang["help"], name)


@unittest.skipUnless(TEST_DATABASE_URL and psycopg2, "TEST_DATABASE_URL not set -- real-database tests skipped")
class EraseAllDataRealDatabaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from services import db_schema
        cls._connect = staticmethod(lambda: psycopg2.connect(TEST_DATABASE_URL))
        db_schema._schema_ready = False
        with patch.object(db_schema, "get_conn", cls._connect):
            db_schema.ensure_schema()

    def _run(self, sql, params=None, fetch=False):
        conn = self._connect()
        try:
            with conn.cursor() as c:
                c.execute(sql, params)
                rows = c.fetchall() if fetch else None
            conn.commit()
            return rows
        finally:
            conn.close()

    def _count(self, table):
        return self._run(f"SELECT COUNT(*) FROM {table}", fetch=True)[0][0]

    def test_everything_goes_to_zero_and_the_right_things_survive(self):
        from services import data_reset, audit_log

        # Something in a spread of tables, a kept session, a kept setting,
        # a remembered cost-alert level, and two left-over retired tables.
        self._run("INSERT INTO feedback (draft_ids, rating, comment, submitted_by, submitted_by_role, submitted_at) "
                  "VALUES ('RS-TEST', 4, 'ok', 'test_reset', 'Social Worker', now())")
        self._run("INSERT INTO reflection_rate_log (user_name, occurred_at) VALUES ('test_reset', now())")
        self._run("INSERT INTO login_failure_log (username, occurred_at) VALUES ('test_reset', now())")
        self._run("INSERT INTO audit_log (action, actor_name, occurred_at) VALUES ('test', 'test_reset', now())")
        self._run("INSERT INTO app_settings (key, value) VALUES ('usage_alert_last_tier__anthropic', 'red') "
                  "ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value")
        self._run("INSERT INTO app_settings (key, value) VALUES ('test_reset_keep_me', 'yes') "
                  "ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value")
        self._run("CREATE TABLE IF NOT EXISTS corpora (id SERIAL PRIMARY KEY, name TEXT)")
        self._run("CREATE TABLE IF NOT EXISTS user_presence (professional_name TEXT PRIMARY KEY)")
        self._run("INSERT INTO corpora (name) VALUES ('old collection')")
        sessions_before = self._count("auth_sessions")
        self.addCleanup(self._run, "DELETE FROM app_settings WHERE key = 'test_reset_keep_me'")

        with patch.object(data_reset, "_acquire_pooled_conn", self._connect), \
                patch.object(audit_log, "_get_conn", self._connect):
            result = data_reset.erase_all_data("test_admin", "System Administrator")

        self.assertIsNotNone(result)
        self.assertEqual(set(result["emptied"]), set(data_reset.DATA_TABLES))
        self.assertIn("corpora", result["removed"])
        self.assertIn("user_presence", result["removed"])

        for table in data_reset.DATA_TABLES:
            expected = 1 if table == "audit_log" else 0   # the one line recording the erase itself
            self.assertEqual(self._count(table), expected, table)

        remaining = {row[0] for row in self._run(
            "SELECT table_name FROM information_schema.tables WHERE table_schema = current_schema()", fetch=True)}
        self.assertFalse(remaining & set(data_reset.RETIRED_TABLES))

        self.assertEqual(self._count("auth_sessions"), sessions_before)
        settings = dict(self._run("SELECT key, value FROM app_settings", fetch=True))
        self.assertEqual(settings.get("test_reset_keep_me"), "yes")
        self.assertNotIn("usage_alert_last_tier__anthropic", settings)

        audit = self._run("SELECT action, actor_name, doc_type FROM audit_log", fetch=True)
        self.assertEqual(audit, [("purged", "test_admin", "all data")])

        # Numbering starts again from 1.
        self._run("INSERT INTO feedback (draft_ids, rating, submitted_at) VALUES ('RS-TEST2', 5, now())")
        self.assertEqual(self._run("SELECT id FROM feedback", fetch=True), [(1,)])
        self._run("DELETE FROM feedback")

    def test_refused_role_erases_nothing(self):
        from services import data_reset
        self._run("INSERT INTO reflection_rate_log (user_name, occurred_at) VALUES ('test_reset_refused', now())")
        self.addCleanup(self._run, "DELETE FROM reflection_rate_log WHERE user_name = 'test_reset_refused'")
        with patch.object(data_reset, "_acquire_pooled_conn", self._connect):
            self.assertIsNone(data_reset.erase_all_data("test_supervisor", "Supervisor"))
        self.assertEqual(self._run(
            "SELECT COUNT(*) FROM reflection_rate_log WHERE user_name = 'test_reset_refused'", fetch=True)[0][0], 1)


if __name__ == "__main__":
    unittest.main()
