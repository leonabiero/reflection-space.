"""Tests that rdi/orchestrator.py verifies evidence and returns findings.

MOCKED: the AI provider is replaced by a fake generator. These tests do
NOT call a real model.
"""
import threading
import unittest
from unittest.mock import patch

DOC = "Maite dice que quiere vivir cerca de su hermana. El equipo considera que no esta motivada."


class OrchestratorFindingsTests(unittest.TestCase):
    def setUp(self):
        from rdi import orchestrator
        self.orchestrator = orchestrator
        self.companions = [
            {"key": "client_voice", "label": "Voice", "focus": ""},
            {"key": "possible_bias", "label": "Bias", "focus": ""},
            {"key": "continuity", "label": "Continuity", "focus": ""},
        ]

    def _run(self, generator):
        with patch.multiple(
            self.orchestrator,
            COMPANIONS=self.companions,
            anonymize=lambda text: text,
            generate_companion_reflection=generator,
            classify_reflection_failure_root_cause=lambda *a: "Network Timeout",
            log_error=lambda **kw: (1, 2),
            _reflection_semaphore=threading.Semaphore(8),
        ), patch.object(self.orchestrator.time, "sleep"):
            return self.orchestrator.run_reflection(DOC)

    def test_verified_quote_is_kept_and_fabricated_quote_is_dropped(self):
        def generate(companion, safe_text, lang):
            if companion["key"] == "client_voice":
                return {
                    "observation": "The note records a stated preference.",
                    "evidence": ["quiere vivir cerca de su hermana", "she wants to live near her sister"],
                    "questions": ["What else has she said?"],
                }
            return {"observation": "", "evidence": [], "questions": []}

        result = self._run(generate)
        self.assertNotIn("error", result)
        finding = next(f for f in result["findings"] if f["module"] == "client_voice")
        self.assertEqual(finding["evidence"], [{"quote": "quiere vivir cerca de su hermana"}])
        self.assertEqual(finding["unverified_quote_count"], 1)
        opportunity = next(o for o in result["opportunities"] if o.trigger == "client_voice")
        self.assertEqual(opportunity.evidence, finding["evidence"])
        self.assertEqual(opportunity.unverified_quote_count, 1)

    def test_every_saved_quote_is_an_exact_substring_of_the_source(self):
        def generate(companion, safe_text, lang):
            return {
                "observation": "obs", "questions": ["q"],
                "evidence": ["El equipo considera que no esta motivada", "invented sentence that is not there"],
            }
        result = self._run(generate)
        for finding in result["findings"]:
            for item in finding["evidence"]:
                self.assertIn(item["quote"], DOC)

    def test_empty_module_is_no_finding_and_is_not_invented(self):
        def generate(companion, safe_text, lang):
            if companion["key"] == "possible_bias":
                return {"observation": "", "evidence": [], "questions": []}
            return {"observation": "obs", "evidence": [], "questions": ["q"]}

        result = self._run(generate)
        modules_with_findings = {f["module"] for f in result["findings"]}
        self.assertNotIn("possible_bias", modules_with_findings)
        self.assertEqual(result["module_status"]["possible_bias"], "no_finding")
        self.assertEqual(result["module_status"]["client_voice"], "finding")

    def test_failed_module_is_reported_as_failed_not_as_a_finding(self):
        def generate(companion, safe_text, lang):
            if companion["key"] == "continuity":
                return {"error": "provider timeout", "raw": ""}
            return {"observation": "obs", "evidence": [], "questions": ["q"]}

        result = self._run(generate)
        self.assertEqual(result["module_status"]["continuity"], "failed")
        self.assertNotIn("continuity", {f["module"] for f in result["findings"]})
        self.assertEqual(result["failed_count"], 1)

    def test_malformed_evidence_from_the_model_is_handled_safely(self):
        def generate(companion, safe_text, lang):
            return {"observation": "obs", "evidence": "not a list", "questions": ["q"]}
        result = self._run(generate)
        self.assertNotIn("error", result)
        for finding in result["findings"]:
            self.assertEqual(finding["evidence"], [])

    def test_existing_return_keys_are_unchanged_and_new_ones_added(self):
        def generate(companion, safe_text, lang):
            return {"observation": "obs", "questions": ["q"]}   # old-shape reply, no evidence
        result = self._run(generate)
        for key in ("opportunities", "raw", "failed_count", "failed_labels", "safe_text"):
            self.assertIn(key, result)
        for key in ("findings", "module_status", "model", "prompt_version"):
            self.assertIn(key, result)
        self.assertTrue(result["prompt_version"])


class PromptTests(unittest.TestCase):
    def test_prompt_asks_for_exact_evidence_and_has_a_version(self):
        from rdi.companions.prompt_builder import build_companion_prompt, PROMPT_VERSION
        from rdi.companions import COMPANIONS
        self.assertTrue(PROMPT_VERSION)
        for companion in COMPANIONS:
            prompt = build_companion_prompt(companion)
            self.assertIn('"evidence"', prompt)
            self.assertIn("EXACTLY", prompt)
            self.assertIn("never invent", prompt.lower())

    def test_ceiling_for_reply_length_was_raised_not_lowered(self):
        import inspect
        from services import reflection_service
        source = inspect.getsource(reflection_service._call_companion_model)
        self.assertIn("max_tokens=1280", source)


if __name__ == "__main__":
    unittest.main()
