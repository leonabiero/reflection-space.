import threading
import time
import unittest
from unittest.mock import patch


class OrchestratorReliabilityTests(unittest.TestCase):
    def setUp(self):
        from rdi import orchestrator
        self.orchestrator = orchestrator
        self.companions = [
            {"key": "one", "label": "One", "focus": ""},
            {"key": "two", "label": "Two", "focus": ""},
            {"key": "three", "label": "Three", "focus": ""},
        ]

    def _patch_common(self, generator):
        return patch.multiple(
            self.orchestrator,
            COMPANIONS=self.companions,
            anonymize=lambda text: f"SAFE:{text}",
            generate_companion_reflection=generator,
            classify_reflection_failure_root_cause=lambda *args: "Network Timeout",
            log_error=lambda **kwargs: (101, 202),
            _reflection_semaphore=threading.Semaphore(8),
        )

    def test_success_uses_one_attempt_per_companion(self):
        calls = []

        def generate(companion, safe_text, lang):
            calls.append(companion["key"])
            return {"observation": f"obs-{companion['key']}", "questions": ["q"]}

        with self._patch_common(generate), patch.object(self.orchestrator.time, "sleep"):
            result = self.orchestrator.run_reflection("document")

        self.assertNotIn("error", result)
        self.assertEqual(len(calls), 3)
        self.assertEqual(result["failed_count"], 0)
        self.assertEqual(len(result["opportunities"]), 3)

    def test_transient_failure_retries_then_succeeds(self):
        attempts = {"one": 0, "two": 0, "three": 0}

        def generate(companion, safe_text, lang):
            key = companion["key"]
            attempts[key] += 1
            if attempts[key] == 1:
                return {"error": "temporary timeout", "raw": ""}
            return {"observation": f"obs-{key}", "questions": ["q"]}

        with self._patch_common(generate), patch.object(self.orchestrator.time, "sleep"):
            result = self.orchestrator.run_reflection("document")

        self.assertEqual(attempts, {"one": 2, "two": 2, "three": 2})
        self.assertEqual(result["failed_count"], 0)

    def test_exhausted_retries_is_one_complete_failure_and_stops(self):
        calls = []

        def generate(companion, safe_text, lang):
            calls.append(companion["key"])
            return {"error": "provider timeout", "raw": ""}

        with self._patch_common(generate), patch.object(self.orchestrator.time, "sleep"), \
                patch.object(self.orchestrator, "log_error", return_value=(11, 22)) as log_error:
            result = self.orchestrator.run_reflection("document")

        self.assertIn("error", result)
        self.assertEqual(len(calls), 9)  # 3 companions x 3 automatic attempts
        self.assertEqual(log_error.call_count, 1)
        self.assertEqual(result["issue_id"], 22)
        self.assertEqual(result["error_id"], 11)

    def test_partial_failure_is_not_reported_as_success(self):
        def generate(companion, safe_text, lang):
            if companion["key"] == "two":
                return {"error": "provider timeout", "raw": ""}
            return {"observation": "usable", "questions": ["q"]}

        with self._patch_common(generate), patch.object(self.orchestrator.time, "sleep"), \
                patch.object(self.orchestrator, "log_error", return_value=(11, 22)) as log_error:
            result = self.orchestrator.run_reflection("document")

        self.assertNotIn("error", result)
        self.assertEqual(result["failed_count"], 1)
        self.assertEqual(result["failed_labels"], ["Two"])
        self.assertEqual(len(result["opportunities"]), 2)
        self.assertEqual(log_error.call_count, 1)

    def test_concurrency_cap_serializes_reflection_operations(self):
        active_reflections = set()
        max_distinct_reflections = 0
        state_lock = threading.Lock()

        def generate(companion, safe_text, lang):
            nonlocal max_distinct_reflections
            with state_lock:
                active_reflections.add(safe_text)
                max_distinct_reflections = max(max_distinct_reflections, len(active_reflections))
            time.sleep(0.03)
            with state_lock:
                active_reflections.remove(safe_text)
            return {"observation": "ok", "questions": ["q"]}

        common = self._patch_common(generate)
        with common, patch.object(self.orchestrator, "_reflection_semaphore", threading.Semaphore(1)):
            threads = [
                threading.Thread(target=self.orchestrator.run_reflection, args=(f"doc-{i}",))
                for i in range(2)
            ]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join(timeout=5)

        self.assertEqual(max_distinct_reflections, 1)


if __name__ == "__main__":
    unittest.main()
