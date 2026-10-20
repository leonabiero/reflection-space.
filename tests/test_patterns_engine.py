"""Pure-logic tests for the pattern engine and explainer (no database, no AI)."""
import unittest
from unittest.mock import patch, MagicMock

from services import pattern_engine as pe
from services import pattern_explainer as ex


def _f(i, run, case="", module="client_voice", created="2026-03-01T10:00:00"):
    return {"id": i, "run_id": run, "case_ref": case, "module": module, "created_at": created,
            "observation": f"obs {i}"}


class ClusteringTests(unittest.TestCase):
    def test_similar_vectors_group_and_different_ones_do_not(self):
        vectors = [[1, 0, 0], [0.99, 0.05, 0], [0.98, 0.1, 0], [0, 1, 0], [0.02, 0.99, 0]]
        clusters = pe.cluster_by_similarity(vectors, 0.8)
        self.assertEqual(clusters, [[0, 1, 2], [3, 4]])

    def test_every_index_appears_exactly_once(self):
        vectors = [[1, 0], [0, 1], [1, 1], [-1, 0]]
        flat = sorted(i for c in pe.cluster_by_similarity(vectors, 0.7) for i in c)
        self.assertEqual(flat, [0, 1, 2, 3])

    def test_edge_cases(self):
        self.assertEqual(pe.cluster_by_similarity([], 0.7), [])
        self.assertEqual(pe.cluster_by_similarity([[1, 0]], 0.7), [[0]])
        self.assertEqual(pe.cluster_by_similarity([[0, 0], [0, 0]], 0.7), [[0], [1]])

    def test_deterministic(self):
        vectors = [[1, 0.1], [1, 0.2], [0.9, 0.1], [0, 1]]
        self.assertEqual(pe.cluster_by_similarity(vectors, 0.9), pe.cluster_by_similarity(vectors, 0.9))

    def test_stricter_threshold_never_merges_more(self):
        vectors = [[1, 0], [0.9, 0.4], [0.7, 0.7], [0.4, 0.9], [0, 1]]
        loose = pe.cluster_by_similarity(vectors, 0.70)
        strict = pe.cluster_by_similarity(vectors, 0.95)
        self.assertGreaterEqual(len(strict), len(loose))


class CountingTests(unittest.TestCase):
    def test_case_refs_are_normalised_and_blank_is_not_a_case(self):
        self.assertEqual(pe.normalise_case_ref("  Caso   12 "), pe.normalise_case_ref("caso 12"))
        self.assertIsNone(pe.normalise_case_ref(""))
        self.assertIsNone(pe.normalise_case_ref("   "))
        self.assertIsNone(pe.normalise_case_ref(None))

    def test_three_observations_one_reflection_is_one_reflection(self):
        counts = pe.summarise_members([_f(1, 7, "A"), _f(2, 7, "A"), _f(3, 7, "A")])
        self.assertEqual((counts["observations"], counts["reflections"], counts["cases"]), (3, 1, 1))

    def test_case_recurrence_only_known_when_every_reflection_has_a_case(self):
        full = pe.summarise_members([_f(1, 1, "A"), _f(2, 2, "B")])
        self.assertTrue(full["case_recurrence_known"])
        self.assertEqual(full["cases"], 2)
        partial = pe.summarise_members([_f(1, 1, "A"), _f(2, 2, "")])
        self.assertFalse(partial["case_recurrence_known"])
        self.assertEqual(partial["reflections_without_case"], 1)
        none = pe.summarise_members([_f(1, 1, ""), _f(2, 2, "")])
        self.assertEqual(none["cases"], 0)
        self.assertFalse(none["case_recurrence_known"])

    def test_dates_and_modules(self):
        counts = pe.summarise_members([
            _f(1, 1, "A", "client_voice", "2026-01-05T09:00:00"),
            _f(2, 2, "B", "possible_bias", "2026-02-09T09:00:00"),
            _f(3, 3, "C", "possible_bias", "2026-02-01T09:00:00"),
        ])
        self.assertEqual((counts["date_first"], counts["date_last"]), ("2026-01-05", "2026-02-09"))
        self.assertEqual(counts["modules"], {"client_voice": 1, "possible_bias": 2})


class SelectionTests(unittest.TestCase):
    def test_one_reflection_repeating_itself_never_makes_a_pattern(self):
        findings = [_f(i, 1, "A") for i in range(5)]
        self.assertEqual(pe.select_candidates(findings, [[0, 1, 2, 3, 4]]), [])

    def test_minimums_and_cap_and_order(self):
        findings = [_f(1, 1), _f(2, 2), _f(3, 3), _f(4, 4), _f(5, 4)]
        clusters = [[0, 1, 2], [3, 4]]
        result = pe.select_candidates(findings, clusters, min_observations=3, min_reflections=2)
        self.assertEqual([c["indices"] for c in result], [[0, 1, 2]])
        many = [[i, i + 1, i + 2] for i in range(0, 9, 3)]
        capped = pe.select_candidates([_f(i, i) for i in range(9)], many, 3, 2, max_patterns=2)
        self.assertEqual(len(capped), 2)

    def test_representatives_are_limited_and_ordered(self):
        vectors = [[1, 0], [0.9, 0.1], [0.8, 0.2], [0, 1]]
        chosen = pe.representative_indices(vectors, [0, 1, 2, 3], 3)
        self.assertEqual(len(chosen), 3)
        self.assertEqual(chosen, sorted(chosen))
        self.assertNotIn(3, chosen)
        self.assertEqual(pe.representative_indices(vectors, [0, 1], 5), [0, 1])


class CarryOverTests(unittest.TestCase):
    def test_overlap_decides_same_pattern(self):
        prev = [{"id": 1, "member_ids": [1, 2, 3, 4]}, {"id": 2, "member_ids": [9, 10]}]
        self.assertEqual(pe.match_previous({1, 2, 3}, prev)["id"], 1)
        self.assertIsNone(pe.match_previous({3, 20, 21, 22}, prev))
        self.assertIsNone(pe.match_previous({1}, []))


class ExplainerValidationTests(unittest.TestCase):
    GOOD = {"title": "T", "description": "D", "why_it_matters": "W",
            "alternative_explanations": ["a"], "limitations": ["l"], "questions": ["q1", "q2"]}

    def test_valid_passes(self):
        self.assertEqual(ex.validate_explanation(dict(self.GOOD))["title"], "T")

    def test_invalid_shapes_are_rejected(self):
        bad = [None, [], {}, {**self.GOOD, "title": ""}, {**self.GOOD, "questions": ["only one"]},
               {**self.GOOD, "limitations": []}, {**self.GOOD, "description": "x" * 5000},
               {**self.GOOD, "alternative_explanations": "text"}, {**self.GOOD, "title": 5}]
        for obj in bad:
            self.assertIsNone(ex.validate_explanation(obj), obj)

    def test_message_contains_only_lens_and_observation(self):
        msg = ex.build_user_message(
            [{"module": "client_voice", "observation": "Se habla de ella",
              "case_ref": "SECRET-1", "evidence": [{"quote": "SECRET QUOTE"}]}],
            {"client_voice": "Voz de la persona"})
        self.assertIn("Voz de la persona", msg)
        self.assertNotIn("SECRET", msg)

    def test_system_prompt_is_cautious(self):
        text = ex.SYSTEM_PROMPT.lower()
        for phrase in ("candidate pattern", "not proof", "do not state how many"):
            self.assertIn(phrase, text)


def _reply(text):
    block = MagicMock(); block.type = "text"; block.text = text
    message = MagicMock(); message.content = [block]
    return message


class ExplainerCallTests(unittest.TestCase):
    OBS = [{"module": "client_voice", "observation": "x"}]
    LABELS = {"client_voice": "Voz"}

    def _run(self, side_effect):
        import json
        with patch.object(ex.reflection_service, "client") as client, \
             patch.object(ex.reflection_service, "_record_claude_usage"):
            client.messages.create.side_effect = side_effect
            result = ex.explain_pattern(self.OBS, self.LABELS, "Español")
            return result, client.messages.create.call_count

    def test_good_reply(self):
        import json
        result, calls = self._run([_reply(json.dumps(ExplainerValidationTests.GOOD))])
        self.assertEqual((result["status"], calls), ("ai", 1))

    def test_invalid_then_good_retries_once(self):
        import json
        result, calls = self._run([_reply("not json"), _reply(json.dumps(ExplainerValidationTests.GOOD))])
        self.assertEqual((result["status"], calls), ("ai", 2))

    def test_failures_fall_back_without_raising(self):
        result, calls = self._run([RuntimeError("down"), RuntimeError("down")])
        self.assertEqual((result["status"], calls), ("fallback", 2))
        self.assertTrue(result["explanation"]["title"])

    def test_fallback_exists_in_all_languages(self):
        for lang in ("Español", "English", "Euskera"):
            fb = ex.fallback_explanation(lang, ["Voz"])
            self.assertIsNotNone(ex.validate_explanation(fb), lang)


if __name__ == "__main__":
    unittest.main()
