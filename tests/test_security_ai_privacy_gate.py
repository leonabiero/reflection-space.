"""Privacy gate for free text typed by practitioners and supervisors
(November 2026).

Before this change, the messages written in a companion follow-up
conversation were sent to Claude exactly as typed. These tests prove that
only the anonymised version is sent now, and that a failure while
anonymising means NOTHING is sent (no fallback to the original text).
"""
import unittest
from unittest.mock import MagicMock, patch


def _fake_message(text):
    message = MagicMock()
    block = MagicMock()
    block.type = "text"
    block.text = text
    message.content = [block]
    message.usage.input_tokens = 1
    message.usage.output_tokens = 1
    message.usage.cache_read_input_tokens = 0
    message.usage.cache_creation_input_tokens = 0
    return message


def _everything_sent(create_mock):
    """All text handed to the AI client, joined, for searching."""
    return repr([call.kwargs for call in create_mock.call_args_list])


COMPANION = {"key": "possible_bias", "label": "Possible bias", "focus": ""}
RAW_MESSAGE = "Ashley Rose told me she is 30, not 29. Her phone is +34 612 345 678."


class CompanionConversationPrivacyTests(unittest.TestCase):
    def _call(self, rs, history=None):
        return rs.continue_companion_conversation(
            companion=COMPANION,
            safe_text="[PERSON] asked for accommodation.",
            initial_observation="An observation.",
            initial_questions=["A question?"],
            conversation_history=history or [],
            professional_message=RAW_MESSAGE,
            lang="English",
        )

    def test_typed_message_is_anonymised_before_it_reaches_claude(self):
        from services import reflection_service as rs

        history = [
            {"role": "professional", "content": "Earlier I said Mikel Etxeberria is 17 years old."},
            {"role": "ai", "content": "Thank you for sharing that."},
        ]
        with patch.object(rs.client.messages, "create", return_value=_fake_message("A reply.")) as create, \
                patch.object(rs, "_record_claude_usage"):
            result = self._call(rs, history)

        self.assertEqual(result, {"reply": "A reply."})
        sent = _everything_sent(create)
        for secret in ("Ashley", "Rose", "30", "29", "612 345 678", "Mikel", "Etxeberria", "17"):
            self.assertNotIn(secret, sent, msg=f"{secret!r} reached Claude")
        self.assertIn("[PERSON]", sent)
        self.assertIn("[AGE_", sent)
        # The AI's own earlier reply is passed through unchanged.
        self.assertIn("Thank you for sharing that.", sent)

    def test_anonymiser_exception_blocks_the_call(self):
        from services import reflection_service as rs

        with patch.object(rs, "anonymize", side_effect=RuntimeError("boom")), \
                patch.object(rs.client.messages, "create") as create, \
                patch.object(rs, "log_error", return_value=(5, 6)) as log_error:
            result = self._call(rs)

        create.assert_not_called()
        self.assertTrue(result.get("privacy_blocked"))
        self.assertEqual(result["issue_id"], 6)
        # The error record never contains the practitioner's text.
        logged = repr(log_error.call_args)
        self.assertNotIn("Ashley", logged)
        self.assertNotIn("612 345 678", logged)

    def test_anonymiser_returning_nothing_blocks_the_call(self):
        from services import reflection_service as rs

        with patch.object(rs, "anonymize", return_value=""), \
                patch.object(rs.client.messages, "create") as create:
            result = self._call(rs)

        create.assert_not_called()
        self.assertTrue(result.get("privacy_blocked"))

    def test_no_fallback_to_original_text_when_anonymiser_fails_on_history(self):
        from services import reflection_service as rs

        calls = {"n": 0}

        def flaky(text):
            calls["n"] += 1
            if calls["n"] > 1:
                raise RuntimeError("fails on the history")
            return "[PERSON] said something."

        history = [{"role": "professional", "content": "Mikel Etxeberria is 17."}]
        with patch.object(rs, "anonymize", side_effect=flaky), \
                patch.object(rs.client.messages, "create") as create, \
                patch.object(rs, "log_error", return_value=(1, 2)):
            result = self._call(rs, history)

        create.assert_not_called()
        self.assertTrue(result.get("privacy_blocked"))


class SavedNotesPrivacyTests(unittest.TestCase):
    """November 2026: a professional's own notes on an observation are
    anonymised before they are stored (they never go to the AI, but they
    are kept in the database)."""

    def test_note_text_is_anonymised(self):
        from services.findings_store import protect_note_text
        stored = protect_note_text("  Sarah Mitchell is 34; call +34 612 345 678.  ", 4000)
        for secret in ("Sarah", "Mitchell", "34", "612 345 678"):
            self.assertNotIn(secret, stored)
        self.assertIn("[PERSON]", stored)
        self.assertEqual(protect_note_text("", 4000), "")
        self.assertEqual(protect_note_text(None, 4000), "")

    def test_only_protected_text_reaches_the_database(self):
        from services import findings_store as fs

        cursor = MagicMock()
        cursor.fetchone.return_value = ("anneh",)
        conn = MagicMock()
        conn.cursor.return_value.__enter__.return_value = cursor
        with patch.object(fs, "_get_conn", return_value=conn):
            ok = fs.upsert_feedback(
                1, "anneh", label=None,
                note="Sarah Mitchell is 34 years old.",
                alternative_explanation="Her ex-partner John Hughes calls her.",
            )
        self.assertTrue(ok)
        written = repr(cursor.execute.call_args_list)
        # "34 years" rather than a bare "34": the recorded calls also
        # contain a timestamp, which can itself contain the digits 34.
        for secret in ("Sarah", "Mitchell", "34 years", "John", "Hughes"):
            self.assertNotIn(secret, written)

    def test_anonymiser_failure_saves_nothing(self):
        from services import findings_store as fs

        with patch.object(fs, "anonymize", side_effect=RuntimeError("boom")), \
                patch.object(fs, "_get_conn") as get_conn:
            ok = fs.upsert_feedback(1, "anneh", note="Sarah Mitchell is 34.")
        self.assertFalse(ok)
        get_conn.assert_not_called()


class AllAiRoutesUseTheGateTests(unittest.TestCase):
    """Static guard: every module that calls Claude or Gemini with case
    material imports the anonymizer (or is documented as receiving only
    already-anonymised text / AI output)."""

    def test_modules_calling_ai_import_the_anonymizer(self):
        import inspect
        from services import reflection_service
        from rdi import orchestrator
        for module in (reflection_service, orchestrator):
            self.assertIn("from services.anonymizer import anonymize", inspect.getsource(module),
                          msg=module.__name__)


if __name__ == "__main__":
    unittest.main()
