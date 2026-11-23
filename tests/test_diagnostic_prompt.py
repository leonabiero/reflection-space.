"""
Claude Code prompt in the Diagnostic Centre (18 November 2026).

Guards the product owner's rules for this feature:
  - the prompt in the alert email is SAVED with the error record when the
    email prompt is made (no extra AI call, no second builder);
  - the alert email and System Administration > Diagnostic Centre show
    the EXACT same prompt, read through one shared helper
    (services/error_log.py:get_saved_ai_prompt);
  - older records with no saved prompt show a friendly message instead of
    crashing or showing an empty box;
  - the alert email's own "no prompt" line is unchanged;
  - every new on-screen text exists in Spanish, Basque and English.
"""
import json
import re
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent

EMAIL_NO_PROMPT_LINE = (
    "(no AI prompt available -- open System Administration > AI Diagnostic "
    "Centre in the app)"
)
NEW_KEYS = (
    "admin_problem_prompt_title",
    "admin_problem_prompt_help",
    "admin_problem_prompt_unavailable",
)


class _FakeCursor:
    def __init__(self, store):
        self._store = store

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def execute(self, sql, params=None):
        if "INSERT INTO error_log" in sql:
            self._store["insert_params"] = params

    def fetchone(self):
        return (101,)


class _FakeConn:
    def __init__(self, store):
        self._store = store

    def cursor(self):
        return _FakeCursor(self._store)

    def commit(self):
        pass

    def rollback(self):
        pass

    def close(self):
        pass


def _log_one_error():
    """Runs the real log_error() with the database, email sending and
    lookups replaced by fakes. Returns (saved_package_json, email_body)."""
    from services import error_log

    store = {}
    sent = {}

    def fake_send(subject, body_text):
        sent["body"] = body_text
        return False

    with mock.patch.object(error_log, "_get_conn", lambda: _FakeConn(store)), \
         mock.patch.object(error_log, "_get_or_create_issue", return_value=(7, "Database connection")), \
         mock.patch.object(error_log, "send_alert_email", side_effect=fake_send), \
         mock.patch.object(error_log, "record_event"), \
         mock.patch("services.diagnostics.find_similar_issues", return_value=[]), \
         mock.patch("services.diagnostics.get_timeline", return_value=[]):
        error_log.log_error(
            page="reflection_space",
            error_type="ValueError",
            message="something broke",
            traceback_text="Traceback (most recent call last):\n  ValueError: something broke",
            user_name="Test Admin",
            user_role="System Administrator",
        )
    # diagnostic_package is the 10th value of the INSERT.
    return store["insert_params"][9], sent["body"]


class SharedHelperTests(unittest.TestCase):
    def test_returns_the_saved_prompt_exactly(self):
        from services.error_log import get_saved_ai_prompt
        prompt = "Line one\n\n=== Summary ===\n  indented line  "
        self.assertEqual(get_saved_ai_prompt({"ai_prompt": prompt}), prompt)

    def test_no_prompt_cases_return_none(self):
        from services.error_log import get_saved_ai_prompt, parse_diagnostic_package
        for package in (None, {}, {"summary": "x"}, {"ai_prompt": ""},
                        {"ai_prompt": "   "}, {"ai_prompt": None}, "not a dict"):
            self.assertIsNone(get_saved_ai_prompt(package), repr(package))
        # Older records: nothing stored, the "{}" placeholder, or bad JSON.
        for stored in (None, "", "{}", "not json"):
            self.assertIsNone(get_saved_ai_prompt(parse_diagnostic_package(stored)), repr(stored))


class PromptIsSavedAndMatchesEmailTests(unittest.TestCase):
    def test_prompt_is_saved_with_the_record_and_equals_the_email_prompt(self):
        from services.error_log import get_saved_ai_prompt, parse_diagnostic_package
        saved_json, email_body = _log_one_error()

        saved_prompt = get_saved_ai_prompt(parse_diagnostic_package(saved_json))
        self.assertIsNotNone(saved_prompt, "the prompt must be saved with the error record")
        self.assertIn("=== Summary ===", saved_prompt)
        self.assertIn("something broke", saved_prompt)

        # The email carries exactly the saved prompt under "AI Prompt".
        self.assertIn("AI Prompt\n\n" + saved_prompt + "\n\nFor status updates", email_body)

    def test_email_still_shows_its_own_no_prompt_line(self):
        from services.error_log import build_diagnostic_report_email
        self.assertIn(EMAIL_NO_PROMPT_LINE, build_diagnostic_report_email({}))
        self.assertIn(EMAIL_NO_PROMPT_LINE, build_diagnostic_report_email({"summary": "x"}))

    def test_email_uses_the_shared_helper(self):
        source = (ROOT / "services" / "error_log.py").read_text(encoding="utf-8")
        self.assertIn("ai_prompt = get_saved_ai_prompt(package) or", source)


class DiagnosticCentreScreenTests(unittest.TestCase):
    T = {
        "admin_problem_prompt_title": "TITLE",
        "admin_problem_prompt_help": "HELP",
        "admin_problem_prompt_unavailable": "NO PROMPT",
    }

    def _render(self, err):
        from pages.admin_sections import ai_diagnostic_centre as screen
        fake_st = mock.MagicMock()
        with mock.patch.object(screen, "st", fake_st):
            screen._render_claude_code_prompt(self.T, err)
        return fake_st

    def test_screen_shows_the_same_prompt_as_the_email(self):
        saved_json, email_body = _log_one_error()
        fake_st = self._render({"id": 101, "diagnostic_package": saved_json})

        fake_st.code.assert_called_once()
        shown = fake_st.code.call_args.args[0]
        self.assertEqual(shown, json.loads(saved_json)["ai_prompt"])
        self.assertIn(shown, email_body)
        fake_st.info.assert_not_called()

    def test_older_records_show_the_friendly_message(self):
        for stored in (None, "", "{}", "not json", json.dumps({"summary": "old"})):
            fake_st = self._render({"id": 1, "diagnostic_package": stored})
            fake_st.code.assert_not_called()
            fake_st.info.assert_called_once_with("NO PROMPT")

    def test_screen_reads_the_saved_prompt_and_never_rebuilds_it(self):
        source = (ROOT / "pages" / "admin_sections" / "ai_diagnostic_centre.py").read_text(encoding="utf-8")
        self.assertIn("get_saved_ai_prompt(", source)
        self.assertIn("st.code(", source)
        for forbidden in ("build_ai_prompt", "build_diagnostic_package", "anthropic", "text_area("):
            self.assertNotIn(forbidden, source)


class TranslationTests(unittest.TestCase):
    def test_new_texts_exist_in_all_three_languages(self):
        from services.locales.es import LANG_ES
        from services.locales.eu import LANG_EU
        from services.locales.en import LANG_EN
        for name, lang in (("es", LANG_ES), ("eu", LANG_EU), ("en", LANG_EN)):
            for key in NEW_KEYS:
                self.assertTrue(lang.get(key), f"{key} missing or empty in {name}")

    def test_screen_uses_only_translated_texts_for_the_prompt_box(self):
        source = (ROOT / "pages" / "admin_sections" / "ai_diagnostic_centre.py").read_text(encoding="utf-8")
        for key in NEW_KEYS:
            self.assertIn(f'T["{key}"]', source.replace("T['", 'T["').replace("']", '"]'))
        self.assertEqual(re.findall(r'st\.(?:info|caption|markdown)\(\s*["\']', source), [])


if __name__ == "__main__":
    unittest.main()
