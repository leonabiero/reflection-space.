"""
Login form (24 November 2026).

When the browser autofilled the username and password, Streamlit only
received the values after a box was clicked, so pressing the button
straight away behaved as if the boxes were empty. The two boxes and the
button are now ONE form, so both values are sent together when the button
(or Enter) is pressed. Everything else about logging in is unchanged.
"""

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class LoginFormTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        source = (ROOT / "services" / "identity.py").read_text(encoding="utf-8")
        start = source.index('st.title(T["login_heading"])')
        cls.login = source[start:]

    def test_both_boxes_and_the_button_are_in_one_form(self):
        form_at = self.login.index('with st.form("login_form"')
        user_at = self.login.index('st.text_input(T["username"]')
        pass_at = self.login.index('st.text_input(T["password_label"], type="password"')
        button_at = self.login.index('st.form_submit_button(T["login_button"])')
        self.assertLess(form_at, user_at)
        self.assertLess(user_at, pass_at)
        self.assertLess(pass_at, button_at)
        # The block ends after the button: the checks run outside it.
        handled_at = self.login.index("if login_submitted:")
        self.assertLess(button_at, handled_at)
        self.assertNotIn('st.button(T["login_button"])', self.login)

    def test_existing_behaviour_is_kept(self):
        for kept in ("is_locked_out(username)", 'T["login_locked"]',
                     "_check_login(username, password, users)", "clear_failed_attempts(username)",
                     "record_failed_attempt(username)", 'T["login_error"]',
                     "_wipe_session_for_logout()", "create_session(username",
                     "set_session_cookie(", "default_workspace_for_role(",
                     "st.switch_page(landing_page_for_workspace("):
            self.assertIn(kept, self.login, kept)

    def test_username_is_matched_as_before(self):
        # No new trimming or case change was introduced.
        self.assertNotIn("username.strip()", self.login)
        self.assertNotIn("username.lower()", self.login)

    def test_password_is_never_kept_by_name_or_printed(self):
        password_line = next(line for line in self.login.splitlines() if "type=\"password\"" in line)
        self.assertNotIn("key=", password_line)
        self.assertNotIn("session_state.password", self.login)
        self.assertNotIn('session_state["password"]', self.login)
        for leak in ("print(password", "logger.info(password", "rag_log(password", "{password}"):
            self.assertNotIn(leak, self.login)

    def test_no_new_text_was_needed(self):
        from services.locales.es import LANG_ES
        from services.locales.eu import LANG_EU
        from services.locales.en import LANG_EN
        for texts in (LANG_ES, LANG_EU, LANG_EN):
            for key in ("username", "password_label", "login_button", "login_error", "login_locked"):
                self.assertTrue(texts.get(key), key)


if __name__ == "__main__":
    unittest.main()
