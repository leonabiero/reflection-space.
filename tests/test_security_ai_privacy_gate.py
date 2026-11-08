"""Privacy gate for free text typed by practitioners and supervisors
(November 2026).

Before this change, two routes sent text to Claude exactly as typed:
the messages written in a companion follow-up conversation, and the
question written into the Knowledge Assistant. These tests prove that
both now send only the anonymised version, and that a failure while
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


class KnowledgeAssistantPrivacyTests(unittest.TestCase):
    QUESTION = "Why did Ashley Rose, aged 30, ask for accommodation? Call +34 612 345 678."

    def _patches(self, ka):
        return (
            patch.object(ka, "retrieve_global_context", return_value=[]),
            patch.object(ka, "build_research_summary", return_value={}),
            patch.object(ka, "_build_stats_block", return_value="stats"),
            patch.object(ka, "usage_ledger"),
        )

    def test_question_is_anonymised_before_it_reaches_claude(self):
        from services import knowledge_assistant as ka

        reply = '{"answer": "ok", "confidence": "limited", "limitations": "", "evidence": []}'
        p1, p2, p3, p4 = self._patches(ka)
        with p1 as retrieve, p2, p3, p4, \
                patch.object(ka.client.messages, "create", return_value=_fake_message(reply)) as create:
            ka.ask(self.QUESTION, lang="English")

        # Only the parts that carry the question (the fixed instructions
        # and the search date contain unrelated digits).
        sent = repr(create.call_args.kwargs["messages"]) + retrieve.call_args.kwargs["query_text"]
        for secret in ("Ashley", "Rose", "30", "612 345 678"):
            self.assertNotIn(secret, sent, msg=f"{secret!r} reached an external service")
        self.assertIn("[PERSON]", sent)

    def test_anonymiser_exception_blocks_the_question(self):
        from services import knowledge_assistant as ka

        p1, p2, p3, p4 = self._patches(ka)
        with p1 as retrieve, p2, p3, p4, \
                patch.object(ka, "anonymize", side_effect=RuntimeError("boom")), \
                patch.object(ka.client.messages, "create") as create, \
                patch.object(ka, "log_error", return_value=(3, 4)) as log_error:
            result = ka.ask(self.QUESTION, lang="English")

        create.assert_not_called()
        retrieve.assert_not_called()   # not even the search step receives it
        self.assertTrue(result.get("privacy_blocked"))
        self.assertEqual(result["issue_id"], 4)
        self.assertNotIn("Ashley", repr(log_error.call_args))


class CorpusReadingPrivacyTests(unittest.TestCase):
    def test_stored_texts_are_re_protected_before_reading(self):
        """Texts saved before age protection existed may hold exact ages;
        they are protected again right before being sent."""
        from services import corpus_reading_service as crs

        sent_texts = []

        def fake_read(companion, text, lang, include_questions):
            sent_texts.append(text)
            return {"lens": companion["key"], "status": "no_finding"}

        docs = [{"id": 1, "content": "[PERSON] tiene 30 años, no 29."}]
        with patch.object(crs, "is_available", return_value=True), \
                patch.object(crs, "require_pattern_role"), \
                patch.object(crs.corpus_store, "get_documents_to_read", return_value=docs), \
                patch.object(crs.corpus_store, "start_reading_job", return_value=9), \
                patch.object(crs.corpus_store, "save_readings"), \
                patch.object(crs.corpus_store, "finish_reading_job"), \
                patch.object(crs.corpus_store, "get_reading_overview", return_value={"unread": 0}), \
                patch.object(crs, "read_lens", side_effect=fake_read):
            crs.read_texts("manager", "tester", 1, "Español")

        self.assertTrue(sent_texts)
        for text in sent_texts:
            self.assertNotIn("30", text)
            self.assertNotIn("29", text)

    def test_anonymiser_failure_stops_the_job_before_any_call(self):
        from services import corpus_reading_service as crs

        docs = [{"id": 1, "content": "[PERSON] tiene 30 años."}]
        with patch.object(crs, "is_available", return_value=True), \
                patch.object(crs, "require_pattern_role"), \
                patch.object(crs.corpus_store, "get_documents_to_read", return_value=docs), \
                patch.object(crs.corpus_store, "start_reading_job", return_value=9), \
                patch.object(crs.corpus_store, "finish_reading_job") as finish, \
                patch.object(crs, "anonymize", side_effect=RuntimeError("boom")), \
                patch.object(crs, "read_lens") as read_lens:
            with self.assertRaises(RuntimeError):
                crs.read_texts("manager", "tester", 1, "Español")

        read_lens.assert_not_called()
        self.assertEqual(finish.call_args.args[1], "failed")


class AllAiRoutesUseTheGateTests(unittest.TestCase):
    """Static guard: every module that calls Claude or Gemini with case
    material imports the anonymizer (or is documented as receiving only
    already-anonymised text / AI output)."""

    def test_modules_calling_ai_import_the_anonymizer(self):
        import inspect
        from services import (corpus_reading_service, knowledge_assistant,
                              qdrant_service, reflection_service)
        from rdi import orchestrator
        for module in (corpus_reading_service, knowledge_assistant, qdrant_service,
                       reflection_service, orchestrator):
            self.assertIn("from services.anonymizer import anonymize", inspect.getsource(module),
                          msg=module.__name__)


if __name__ == "__main__":
    unittest.main()
