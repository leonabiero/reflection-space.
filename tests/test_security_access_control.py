import unittest
from unittest.mock import MagicMock, patch

from services.access_control import can_access_case_history, require_management_role


class CaseAccessControlTests(unittest.TestCase):
    def test_management_roles_are_allowed_without_case_owner_lookup(self):
        for role in ("Supervisor", "Programme Manager", "System Administrator"):
            with self.subTest(role=role):
                self.assertTrue(can_access_case_history("manager", role, "CASE-123"))

    def test_unknown_or_missing_identity_fails_closed(self):
        self.assertFalse(can_access_case_history("", "Social Worker", "CASE-123"))
        self.assertFalse(can_access_case_history("alice", "", "CASE-123"))
        self.assertFalse(can_access_case_history("alice", "Unknown Role", "CASE-123"))
        self.assertFalse(can_access_case_history("alice", "Social Worker", ""))

    def test_social_worker_can_access_only_their_own_completed_case(self):
        conn = MagicMock()
        cursor = conn.cursor.return_value.__enter__.return_value
        cursor.fetchone.return_value = (1,)

        with patch("services.access_control._acquire_pooled_conn", return_value=conn):
            self.assertTrue(can_access_case_history("alice", "Social Worker", "CASE-123"))

        query, params = cursor.execute.call_args.args
        self.assertIn("created_by = %s", query)
        self.assertEqual(params, ("CASE-123", "alice"))

    def test_social_worker_is_denied_when_case_is_not_their_completed_case(self):
        conn = MagicMock()
        cursor = conn.cursor.return_value.__enter__.return_value
        cursor.fetchone.return_value = None

        with patch("services.access_control._acquire_pooled_conn", return_value=conn):
            self.assertFalse(can_access_case_history("alice", "Social Worker", "CASE-999"))

    def test_management_role_helper(self):
        self.assertTrue(require_management_role("Supervisor"))
        self.assertTrue(require_management_role("Programme Manager"))
        self.assertTrue(require_management_role("System Administrator"))
        self.assertFalse(require_management_role("Social Worker"))


if __name__ == "__main__":
    unittest.main()
