import unittest
from unittest.mock import patch


class CompanionRecoveryBoundaryTests(unittest.TestCase):
    def test_manual_companion_retry_makes_exactly_one_provider_call(self):
        from rdi import companion_retry

        companions = [{"key": "one", "label": "One", "focus": ""}]
        with patch.object(companion_retry, "COMPANIONS", companions), \
                patch.object(companion_retry, "generate_companion_reflection", return_value={"error": "still down", "raw": ""}) as generate, \
                patch.object(companion_retry, "classify_reflection_failure_root_cause", return_value="Network Timeout"), \
                patch.object(companion_retry, "log_error", return_value=(7, 8)) as log_error:
            result = companion_retry.retry_companion_once("one", "SAFE", "English")

        self.assertFalse(result["success"])
        self.assertEqual(generate.call_count, 1)
        self.assertEqual(log_error.call_count, 1)
        self.assertEqual(result["issue_id"], 8)
        self.assertEqual(result["error_id"], 7)

    def test_unknown_companion_cannot_trigger_an_api_call(self):
        from rdi import companion_retry

        with patch.object(companion_retry, "COMPANIONS", []), \
                patch.object(companion_retry, "generate_companion_reflection") as generate:
            result = companion_retry.retry_companion_once("does-not-exist", "SAFE", "English")

        self.assertFalse(result["success"])
        generate.assert_not_called()


class ReflectionSessionCoverageTests(unittest.TestCase):
    def test_failed_companion_is_explicitly_unavailable_and_retryable(self):
        import streamlit as st
        from rdi.reflection_session import ReflectionSession
        from rdi.reflection_objects import ReflectiveOpportunity

        companions = [
            {"key": "one", "label": "One", "focus": ""},
            {"key": "two", "label": "Two", "focus": ""},
        ]
        st.session_state.clear()
        result = {
            "opportunities": [ReflectiveOpportunity("one", "ctx", "usable", ["q"])],
            "raw": {"one": {"observation": "usable", "questions": ["q"]}},
            "failed_count": 1,
            "failed_labels": ["Two"],
            "safe_text": "SAFE",
        }

        with patch("rdi.reflection_session.COMPANIONS", companions):
            session = ReflectionSession(result, [], "case-1")

        failed = session.get_opportunity("two")
        self.assertIsNotNone(failed)
        self.assertIn("temporarily unavailable", failed.focus)
        self.assertTrue(session.can_retry_companion("two"))
        self.assertEqual(len(session.opportunities), 2)
        st.session_state.clear()

    def test_manual_retry_failure_becomes_permanently_unavailable(self):
        import streamlit as st
        from rdi.reflection_session import ReflectionSession
        from rdi.reflection_objects import ReflectiveOpportunity

        companions = [{"key": "one", "label": "One", "focus": ""}]
        st.session_state.clear()
        result = {
            "opportunities": [],
            "raw": {},
            "failed_count": 1,
            "failed_labels": ["One"],
            "safe_text": "SAFE",
        }
        with patch("rdi.reflection_session.COMPANIONS", companions):
            session = ReflectionSession(result, [], "case-1")
            self.assertTrue(session.can_retry_companion("one"))
            session.mark_manual_retry_failed("one")

        self.assertFalse(session.can_retry_companion("one"))
        self.assertIn("issue has been recorded", session.get_opportunity("one").focus)
        st.session_state.clear()


if __name__ == "__main__":
    unittest.main()
