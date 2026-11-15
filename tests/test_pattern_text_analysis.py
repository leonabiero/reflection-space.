"""
Pattern Review analysis (15 November 2026) -- services/pattern_text_analysis.py.

No database and no real AI: Claude is replaced by a fake client.
Checks that:
  - texts are split into groups correctly;
  - only the texts themselves are sent (never codes, dates or authors);
  - the number of texts behind each pattern is COUNTED from the text
    numbers, not taken from the AI, and patterns in too few texts are left out;
  - any part of the report that copies a passage from a text is removed;
  - failures never raise and never produce a half-made report;
  - run_report() respects the minimum, duplicate protection and roles.
"""

import json
import random
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from services import pattern_text_analysis as pta


def _message(obj):
    text = obj if isinstance(obj, str) else json.dumps(obj)
    return SimpleNamespace(content=[SimpleNamespace(type="text", text=text)], usage=None)


class FakeClient:
    """Answers group calls with `batch_reply(user_message)` and the final
    call with `report_reply`."""

    def __init__(self, batch_reply, report_reply=None, fail_if=None):
        self.batch_reply = batch_reply
        self.report_reply = report_reply
        self.fail_if = fail_if
        self.calls = []
        self.messages = self

    def with_options(self, **kwargs):
        return self

    def create(self, model, max_tokens, system, messages):
        user = messages[0]["content"]
        self.calls.append({"system": system, "user": user})
        if user.startswith("TEXTS:"):
            if self.fail_if and self.fail_if(user):
                raise RuntimeError("boom")
            return _message(self.batch_reply(user))
        return _message(self.report_reply)


TEXTS = [f"Texto número {i}. La familia acude a la cita y se habla de vivienda." for i in range(1, 7)]


def _all_texts_pattern(user):
    count = user.count("\n[") + (1 if user.startswith("TEXTS:\n\n[") else 0)
    return {"patterns": [
        {"title": "Vivienda", "description": "La vivienda aparece a menudo.", "texts": list(range(1, count + 1))},
        {"title": "Raro", "description": "Solo una vez.", "texts": [1]},
    ]}


REPORT = {
    "overview": "Varios textos tratan la vivienda.",
    "patterns": [{"title": "Vivienda", "description": "La vivienda aparece a menudo.",
                  "why_it_may_matter": "Puede orientar la intervención.",
                  "questions": ["¿Qué recursos faltan?"], "sources": ["g1-p1", "g1-p2", "inventado"]}],
    "limitations": ["Es una lectura automática."],
}


def _patches(client):
    return [
        patch.object(pta.reflection_service, "client", client),
        patch.object(pta.reflection_service, "_record_claude_usage", lambda *a, **k: None),
    ]


class BatchingTests(unittest.TestCase):
    def test_every_text_goes_in_exactly_one_group(self):
        texts = [str(i) * 10 for i in range(95)]
        batches = pta.make_batches(texts, max_texts=40, max_chars=10_000)
        self.assertEqual([len(b) for b in batches], [40, 40, 15])
        self.assertEqual(sum(batches, []), texts)

    def test_groups_respect_the_size_limit(self):
        texts = ["x" * 3000] * 5
        batches = pta.make_batches(texts, max_texts=40, max_chars=7000)
        self.assertEqual([len(b) for b in batches], [2, 2, 1])

    def test_a_very_long_text_gets_its_own_group(self):
        batches = pta.make_batches(["a", "x" * 50_000, "b"], max_texts=40, max_chars=40_000)
        self.assertEqual(batches, [["a"], ["x" * 50_000], ["b"]])


class ValidationTests(unittest.TestCase):
    def test_batch_reply_ignores_numbers_outside_the_group(self):
        got = pta.validate_batch_reply({"patterns": [
            {"title": "T", "description": "D", "texts": [1, 2, 99, "x", 0]},
            {"title": "", "description": "D", "texts": [1]},
        ]}, batch_size=3)
        self.assertEqual(got, [{"title": "T", "description": "D", "texts": {1, 2}}])
        self.assertIsNone(pta.validate_batch_reply({"nope": []}, 3))

    def test_report_reply_keeps_only_known_sources(self):
        got = pta.validate_report_reply(REPORT, {"g1-p1", "g1-p2"})
        self.assertEqual(got["patterns"][0]["sources"], ["g1-p1", "g1-p2"])
        unknown_only = {"patterns": [dict(REPORT["patterns"][0], sources=["zz"])]}
        self.assertEqual(pta.validate_report_reply(unknown_only, {"g1-p1"})["patterns"], [])


class AnalysisTests(unittest.TestCase):
    def _run(self, client, texts=TEXTS, **kwargs):
        ps = _patches(client)
        for p in ps:
            p.start()
            self.addCleanup(p.stop)
        return pta.analyse_texts(texts, lang="Español", min_per_pattern=3,
                                 rng=random.Random(1), **kwargs)

    def test_counts_come_from_the_text_numbers(self):
        client = FakeClient(_all_texts_pattern, REPORT)
        out = self._run(client)
        report = out["report"]
        self.assertEqual(out["texts_read"], 6)
        self.assertEqual(len(report["patterns"]), 1)
        # "Vivienda" (all 6) merged with "Raro" (text 1): 6 distinct texts.
        self.assertEqual(report["patterns"][0]["texts_count"], 6)
        self.assertNotIn("sources", report["patterns"][0])

    def test_patterns_in_too_few_texts_are_left_out(self):
        rare_report = {"overview": "", "limitations": [], "patterns": [
            {"title": "Raro", "description": "Solo una vez.", "why_it_may_matter": "",
             "questions": [], "sources": ["g1-p2"]}]}
        out = self._run(FakeClient(_all_texts_pattern, rare_report))
        self.assertEqual(out["report"]["patterns"], [])

    def test_only_the_texts_are_sent(self):
        client = FakeClient(_all_texts_pattern, REPORT)
        self._run(client)
        batch_calls = [c for c in client.calls if c["user"].startswith("TEXTS:")]
        self.assertEqual(len(batch_calls), 1)
        sent = batch_calls[0]["user"]
        for text in TEXTS:
            self.assertIn(text, sent)
        for forbidden in ("RS-", "Leon", "Social Worker", "2026"):
            self.assertNotIn(forbidden, sent)
        self.assertIn("Responde completamente en español.", batch_calls[0]["system"])

    def test_copied_passages_are_removed_from_the_report(self):
        copied = dict(REPORT)
        copied["overview"] = "Texto número 2. La familia acude a la cita y se habla de vivienda."
        copied["patterns"] = [dict(REPORT["patterns"][0], questions=[
            "¿Qué recursos faltan?",
            "Texto número 3. La familia acude a la cita y se habla de vivienda?"])]
        out = self._run(FakeClient(_all_texts_pattern, copied))
        self.assertEqual(out["report"]["overview"], "")
        self.assertEqual(out["report"]["patterns"][0]["questions"], ["¿Qué recursos faltan?"])
        self.assertEqual(out["removed_for_privacy"], 2)

    def test_no_recurring_pattern_gives_an_empty_report_without_a_final_call(self):
        client = FakeClient(lambda user: {"patterns": []}, report_reply=None)
        out = self._run(client)
        self.assertEqual(out["report"], {"overview": "", "patterns": [], "limitations": []})
        self.assertEqual(len(client.calls), 1)

    def test_too_many_unread_texts_means_no_report(self):
        texts = ["x" * 3000, "y" * 3000, "z" * 3000]
        small = patch.object(pta, "MAX_BATCH_CHARS", 4000)      # one text per group
        small.start()
        self.addCleanup(small.stop)
        client = FakeClient(_all_texts_pattern, REPORT,
                            fail_if=lambda user: "yyyy" in user or "zzzz" in user)
        out = self._run(client, texts=texts)
        self.assertIsNone(out["report"])
        self.assertEqual(out["groups_failed"], 2)

    def test_a_broken_final_reply_means_no_report_and_no_exception(self):
        out = self._run(FakeClient(_all_texts_pattern, "not json"))
        self.assertIsNone(out["report"])


class ProtectTextsTests(unittest.TestCase):
    def test_names_are_removed_before_the_ai(self):
        protected, skipped = pta.protect_texts(
            ["Juan Pérez vive en Barakaldo con su madre Ana. Tiene 34 años.", "  "])
        self.assertEqual(skipped, 0)
        self.assertEqual(len(protected), 1)
        for private in ("Juan", "Pérez", "Barakaldo", "34"):
            self.assertNotIn(private, protected[0])

    def test_a_text_that_cannot_be_anonymised_is_never_sent(self):
        def broken(text):
            raise RuntimeError("boom")
        with patch.object(pta, "anonymize", broken):
            protected, skipped = pta.protect_texts(["Juan Pérez vive en Bilbao."])
        self.assertEqual((protected, skipped), ([], 1))


class RunReportTests(unittest.TestCase):
    def setUp(self):
        self.saved = []
        patches = [
            patch.object(pta.pattern_text_store, "save_report",
                         lambda *a, **k: self.saved.append((a, k)) or 42),
            patch.object(pta.request_dedup, "claim", lambda *a, **k: "claimed"),
            patch.object(pta.request_dedup, "complete", lambda *a, **k: None),
            patch.object(pta.request_dedup, "release", lambda *a, **k: None),
            *_patches(FakeClient(_all_texts_pattern, REPORT)),
        ]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)

    def _texts(self, n):
        return patch.object(pta.pattern_text_store, "texts_for_period",
                            lambda role, months: [{"language": "Español", "text": t} for t in TEXTS[:n]])

    def test_fewer_than_the_minimum_runs_nothing(self):
        with self._texts(4):
            out = pta.run_report("Supervisor", "boss", 3, "Español")
        self.assertEqual(out["status"], "not_enough")
        self.assertEqual(self.saved, [])

    def test_original_texts_reach_the_ai_only_after_anonymisation(self):
        client = FakeClient(_all_texts_pattern, REPORT)
        originals = [f"Juan Pérez acude a la cita número {i} y se habla de vivienda." for i in range(6)]
        with patch.object(pta.reflection_service, "client", client), \
             patch.object(pta.pattern_text_store, "texts_for_period",
                          lambda role, months: [{"language": "Español", "text": t} for t in originals]):
            out = pta.run_report("Supervisor", "boss", 3, "Español")
        self.assertEqual(out["status"], "ok")
        sent = " ".join(c["user"] for c in client.calls)
        self.assertNotIn("Juan", sent)
        self.assertNotIn("Pérez", sent)

    def test_a_report_is_saved_with_its_period(self):
        with self._texts(6):
            out = pta.run_report("Supervisor", "boss", 6, "Español")
        self.assertEqual(out["status"], "ok")
        self.assertEqual(out["report_id"], 42)
        args, _ = self.saved[0]
        self.assertEqual(args[:5], ("Supervisor", "boss", 6, 6, "Español"))
        self.assertEqual(args[5]["texts_read"], 6)

    def test_the_same_report_is_never_run_twice_at_once(self):
        with self._texts(6), patch.object(pta.request_dedup, "claim", lambda *a, **k: "in_progress"):
            self.assertEqual(pta.run_report("Supervisor", "boss", 3)["status"], "busy")
        with self._texts(6), patch.object(pta.request_dedup, "claim", lambda *a, **k: "completed"):
            self.assertEqual(pta.run_report("Supervisor", "boss", 3)["status"], "recent")
        self.assertEqual(self.saved, [])

    def test_other_roles_are_refused_by_the_store(self):
        with patch.object(pta.pattern_text_store, "_get_conn",
                          side_effect=AssertionError("no database for this role")):
            for role in ("Social Worker", "System Administrator", ""):
                with self.assertRaises(PermissionError):
                    pta.run_report(role, "someone", 3)


if __name__ == "__main__":
    unittest.main()
