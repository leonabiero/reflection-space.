from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]


class AuthenticationSecurityTests(unittest.TestCase):
    def test_persistent_cookie_uses_secure_samesite_and_documents_httponly_limit(self):
        source = (ROOT / "services" / "session_cookie.py").read_text(encoding="utf-8")
        self.assertIn("SameSite=Lax", source)
        self.assertIn("Secure", source)
        self.assertIn("HttpOnly", source)  # documented limitation/analysis
        # Documentation wraps the sentence across lines; normalize whitespace
        # rather than making the security assertion dependent on formatting.
        normalized = re.sub(r"\s+", " ", source)
        self.assertIn("CANNOT be marked `HttpOnly`", normalized)

    def test_session_token_is_cryptographically_random(self):
        source = (ROOT / "services" / "session_store.py").read_text(encoding="utf-8")
        self.assertIn("secrets.token_urlsafe(32)", source)
        self.assertNotIn("hashlib.md5", source)
        self.assertNotIn("random.random", source)

    def test_password_verification_uses_bcrypt_and_dummy_hash(self):
        identity = (ROOT / "services" / "identity.py").read_text(encoding="utf-8")
        login_security = (ROOT / "services" / "login_security.py").read_text(encoding="utf-8")
        self.assertIn("_DUMMY_HASH", identity)
        self.assertIn("verify_password", identity)
        self.assertRegex(login_security, re.compile(r"bcrypt", re.IGNORECASE))
        self.assertRegex(identity, re.compile(r"\$2b\$12\$", re.IGNORECASE))

    def test_logout_revokes_server_session_and_wipes_session_state(self):
        identity = (ROOT / "services" / "identity.py").read_text(encoding="utf-8")
        self.assertIn("delete_session", identity)
        self.assertIn("clear_session_cookie", identity)
        self.assertIn("_wipe_session_for_logout", identity)
        self.assertIn("for key in list(st.session_state.keys())", identity)


if __name__ == "__main__":
    unittest.main()
