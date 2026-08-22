from datetime import datetime, timedelta, timezone
import unittest
from unittest.mock import MagicMock, patch

import bcrypt


class AuthenticationReliabilityTests(unittest.TestCase):
    def test_correct_password_authenticates(self):
        from services.identity import _check_login

        password = "Correct Horse Battery Staple"
        hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        users = {"alice": {"password": hashed, "name": "Alice", "role": "Social Worker"}}

        self.assertEqual(_check_login("alice", password, users), users["alice"])

    def test_incorrect_password_is_rejected(self):
        from services.identity import _check_login

        password = "Correct Password"
        hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        users = {"alice": {"password": hashed, "name": "Alice", "role": "Social Worker"}}

        self.assertIsNone(_check_login("alice", "wrong password", users))

    def test_nonexistent_username_is_rejected_without_plaintext_fallback(self):
        from services.identity import _check_login, _DUMMY_HASH

        with patch("services.identity.verify_password", return_value=False) as verify:
            self.assertIsNone(_check_login("missing", "anything", {}))

        verify.assert_called_once_with("anything", _DUMMY_HASH)

    def test_successful_login_helper_returns_role_and_name(self):
        from services.identity import _check_login

        users = {
            "manager": {
                "password": bcrypt.hashpw(b"pw", bcrypt.gensalt()).decode(),
                "name": "Programme Manager",
                "role": "Programme Manager",
            }
        }
        result = _check_login("manager", "pw", users)
        self.assertEqual(result["role"], "Programme Manager")
        self.assertEqual(result["name"], "Programme Manager")


class SessionReliabilityTests(unittest.TestCase):
    def _connection_with_row(self, row):
        cursor = MagicMock()
        cursor.__enter__.return_value = cursor
        cursor.__exit__.return_value = False
        cursor.fetchone.return_value = row
        connection = MagicMock()
        connection.cursor.return_value = cursor
        return connection

    def test_unexpired_session_is_valid(self):
        from services import session_store

        now = datetime.now(timezone.utc)
        conn = self._connection_with_row(("alice", "Practitioner", now + timedelta(minutes=10)))
        with patch.object(session_store, "_get_conn", return_value=conn), patch.object(session_store, "now_utc", return_value=now):
            result = session_store.validate_session("opaque-token")

        self.assertEqual(result, {"username": "alice", "active_work_mode": "Practitioner"})
        conn.close.assert_called_once()

    def test_expired_session_is_rejected(self):
        from services import session_store

        now = datetime.now(timezone.utc)
        conn = self._connection_with_row(("alice", "Practitioner", now - timedelta(seconds=1)))
        with patch.object(session_store, "_get_conn", return_value=conn), patch.object(session_store, "now_utc", return_value=now):
            self.assertIsNone(session_store.validate_session("expired-token"))

    def test_database_failure_fails_closed_for_session_validation(self):
        from services import session_store

        with patch.object(session_store, "_get_conn", side_effect=RuntimeError("postgres unavailable")):
            self.assertIsNone(session_store.validate_session("opaque-token"))


class ExternalDependencyReliabilityTests(unittest.TestCase):
    def test_gemini_embedding_failure_degrades_to_none(self):
        from services import embedding_service

        client = MagicMock()
        client.models.embed_content.side_effect = TimeoutError("Gemini timeout")
        with patch.object(embedding_service, "GEMINI_API_KEY", "configured"), patch.object(embedding_service, "_client", client):
            self.assertIsNone(embedding_service.embed_document("already anonymized text"))

    def test_empty_embedding_degrades_to_none(self):
        from services import embedding_service

        client = MagicMock()
        client.models.embed_content.return_value.embeddings = []
        with patch.object(embedding_service, "GEMINI_API_KEY", "configured"), patch.object(embedding_service, "_client", client):
            self.assertIsNone(embedding_service.embed_query("query"))

    def test_request_fingerprint_is_stable_and_one_way(self):
        from services.request_dedup import fingerprint

        first = fingerprint("alice", "case-1", "same request")
        second = fingerprint("alice", "case-1", "same request")
        different = fingerprint("alice", "case-1", "different request")
        self.assertEqual(first, second)
        self.assertNotEqual(first, different)
        self.assertEqual(len(first), 64)

    def test_request_dedup_uses_atomic_insert_conflict(self):
        from services import request_dedup

        cursor = MagicMock()
        cursor.__enter__.return_value = cursor
        cursor.__exit__.return_value = False
        cursor.rowcount = 0
        cursor.fetchone.return_value = ("in_progress",)
        conn = MagicMock()
        conn.cursor.return_value = cursor

        with patch.object(request_dedup, "_get_conn", return_value=conn):
            result = request_dedup.claim("request-id", "reflection")

        self.assertEqual(result, "in_progress")
        executed_sql = " ".join(str(call.args[0]) for call in cursor.execute.call_args_list)
        self.assertIn("ON CONFLICT (request_id) DO NOTHING", executed_sql)


if __name__ == "__main__":
    unittest.main()
