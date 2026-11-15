"""
Reflection History summary + optional feedback (November 2026).

  - Reflection History shows a short AI summary per reflection, with the
    full observations folded underneath (services/reflection_summary.py).
  - The AI summary is written ONLY from the saved observations: never the
    quoted passages, the code, dates or anything about the author.
  - It never raises; failures return None so the page can offer a retry.
  - Rating a reflection is optional: a small "Rate" pop-up in the corner
    of the results; "Finish reflection" no longer leads to a feedback step.
  - Every new on-screen text exists in Spanish, Basque and English.

The real-database part is SKIPPED unless TEST_DATABASE_URL is set.
"""

import importlib.util
import os
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from services import reflection_summary as rsum

ROOT = Path(__file__).resolve().parents[1]

NEW_KEYS = (
    "rs_summary_status", "rs_feedback_popover_button", "rs_feedback_optional_note",
    "rs_feedback_already_sent", "rs_feedback_failed", "ch_details_expander",
    "ch_summary_ai_note", "ch_summary_missing", "ch_summary_create_button",
    "ch_summary_creating", "ch_summary_failed",
)

LABELS = {"client_voice": "Voz de la persona", "facts_vs_interpretation": "Hechos vs. interpretación"}

FINDINGS = [
    {"module": "client_voice", "observation": "La voz de la madre apenas aparece.",
     "questions": ["¿Qué diría ella?"], "evidence": [{"quote": "CITA SECRETA RS-AB12CD"}]},
    {"module": "facts_vs_interpretation", "observation": "Se presentan interpretaciones como hechos.",
     "questions": [], "evidence": []},
]

GOOD_SUMMARY = ("La reflexión destaca que la voz de la madre apenas aparece y que algunas "
                "interpretaciones se presentan como hechos.")


def _read(*parts):
    return ROOT.joinpath(*parts).read_text(encoding="utf-8")


def _load_locale(lang):
    spec = importlib.util.spec_from_file_location(f"loc_{lang}", ROOT / "services" / "locales" / f"{lang}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return next(v for v in vars(module).values() if isinstance(v, dict) and "rs_finish_button" in v)


def _message(text):
    return SimpleNamespace(content=[SimpleNamespace(type="text", text=text)], usage=None)


class FakeClient:
    def __init__(self, replies):
        self.replies = list(replies)
        self.calls = []
        self.messages = self

    def create(self, **kwargs):
        self.calls.append(kwargs)
        reply = self.replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        return _message(reply)


class SummaryServiceTests(unittest.TestCase):
    def _run(self, replies, findings=FINDINGS, lang="Español"):
        client = FakeClient(replies)
        recorded = []
        with patch.object(rsum.reflection_service, "client", client), \
             patch.object(rsum.reflection_service, "_record_claude_usage",
                          lambda op, *a, **k: recorded.append(op)):
            result = rsum.write_summary(findings, LABELS, lang)
        return result, client, recorded

    def test_valid_reply_is_returned_and_usage_recorded(self):
        result, client, recorded = self._run(['{"summary": "%s"}' % GOOD_SUMMARY])
        self.assertEqual(result, GOOD_SUMMARY)
        self.assertEqual(len(client.calls), 1)
        self.assertEqual(recorded, ["reflection_summary"])

    def test_only_observations_and_lens_names_are_sent(self):
        _, client, _ = self._run(['{"summary": "%s"}' % GOOD_SUMMARY])
        sent = client.calls[0]["messages"][0]["content"]
        self.assertIn("La voz de la madre apenas aparece.", sent)
        self.assertIn("Voz de la persona", sent)
        self.assertNotIn("CITA SECRETA", sent)
        self.assertNotIn("RS-AB12CD", sent)
        self.assertNotIn("¿Qué diría ella?", sent)

    def test_answer_language_follows_the_reflection(self):
        _, client, _ = self._run(['{"summary": "%s"}' % GOOD_SUMMARY], lang="Euskera")
        self.assertIn("euskaraz", client.calls[0]["system"])

    def test_invalid_then_valid_reply_retries_once(self):
        result, client, _ = self._run(["not json", '{"summary": "%s"}' % GOOD_SUMMARY])
        self.assertEqual(result, GOOD_SUMMARY)
        self.assertEqual(len(client.calls), 2)

    def test_failures_return_none_and_never_raise(self):
        result, client, recorded = self._run([RuntimeError("down"), RuntimeError("down")])
        self.assertIsNone(result)
        self.assertEqual(len(client.calls), rsum.MAX_ATTEMPTS)
        self.assertEqual(recorded, ["reflection_summary"] * rsum.MAX_ATTEMPTS)

    def test_no_observations_means_no_ai_call(self):
        empty = [{"module": "client_voice", "observation": "  ", "questions": ["?"]}]
        result, client, _ = self._run([], findings=empty)
        self.assertIsNone(result)
        self.assertEqual(client.calls, [])

    def test_validation_limits(self):
        self.assertIsNone(rsum.validate_summary(None))
        self.assertIsNone(rsum.validate_summary({"summary": "corto"}))
        self.assertIsNone(rsum.validate_summary({"summary": "x" * (rsum.MAX_SUMMARY_CHARS + 1)}))
        self.assertEqual(rsum.validate_summary({"summary": "  " + GOOD_SUMMARY + "\n"}), GOOD_SUMMARY)

    def test_create_and_save_stores_on_the_reflection(self):
        saved = []
        with patch.object(rsum, "write_summary", lambda *a, **k: GOOD_SUMMARY), \
             patch("services.reflection_records.save_summary",
                   lambda run_id, text: saved.append((run_id, text)) or True):
            self.assertEqual(rsum.create_and_save(7, FINDINGS, LABELS), GOOD_SUMMARY)
        self.assertEqual(saved, [(7, GOOD_SUMMARY)])

    def test_create_and_save_survives_a_database_error(self):
        def boom(*_a, **_k):
            raise RuntimeError("db down")
        with patch.object(rsum, "write_summary", lambda *a, **k: GOOD_SUMMARY), \
             patch("services.reflection_records.save_summary", boom):
            self.assertIsNone(rsum.create_and_save(7, FINDINGS, LABELS))


class ScreenStaticTests(unittest.TestCase):
    def test_history_shows_summary_then_folded_details(self):
        page = _read("pages", "case_history.py")
        self.assertIn("st.container(border=True)", page)
        self.assertIn('T["ch_details_expander"]', page)
        self.assertIn("_render_summary(record, findings)", page)
        self.assertNotIn("with st.expander(header)", page)
        # Private notes are still never read on this page.
        self.assertNotIn("get_feedback_for_findings", page)

    def test_feedback_is_an_optional_corner_popover(self):
        page = _read("pages", "reflection_space.py")
        self.assertIn("st.popover(T[\"rs_feedback_popover_button\"]", page)
        self.assertNotIn("awaiting_feedback", page)
        self.assertNotIn("feedback_skip_button", page)
        # Finishing goes straight to a fresh form.
        finish = page[page.index('if st.button(T["rs_finish_button"]'):]
        self.assertIn('_start_fresh(flash=T["rs_finished_success"])', finish.split("\n\n")[0])

    def test_summary_is_written_from_findings_not_case_text(self):
        page = _read("pages", "reflection_space.py")
        call = page[page.index("reflection_summary.create_and_save("):]
        call = call[:call.index(")") + 1]
        self.assertIn('result.get("findings", [])', call)
        self.assertNotIn("material", call)
        self.assertNotIn("safe_text", call)

    def test_new_texts_exist_in_all_three_languages(self):
        for lang in ("es", "eu", "en"):
            texts = _load_locale(lang)
            for key in NEW_KEYS:
                self.assertTrue(texts.get(key), f"{key} missing in {lang}")
            self.assertIn("{count}", texts["ch_details_expander"])
            self.assertNotIn("feedback_skip_button", texts)


TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL", "")
try:
    import psycopg2
except Exception:  # pragma: no cover
    psycopg2 = None


@unittest.skipUnless(TEST_DATABASE_URL and psycopg2, "TEST_DATABASE_URL not set -- real-database tests skipped")
class SummaryRealDatabaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from services import db_schema
        cls._connect = staticmethod(lambda: psycopg2.connect(TEST_DATABASE_URL))
        db_schema._schema_ready = False
        with patch.object(db_schema, "get_conn", cls._connect):
            db_schema.ensure_schema()

    def setUp(self):
        from services import findings_store, reflection_records
        self.fs = findings_store
        self.rr = reflection_records
        for p in (patch.object(findings_store, "_get_conn", self._connect),
                  patch.object(reflection_records, "_get_conn", self._connect)):
            p.start()
            self.addCleanup(p.stop)
        self._clean()
        self.addCleanup(self._clean)

    def _clean(self):
        conn = self._connect()
        try:
            with conn.cursor() as c:
                c.execute("DELETE FROM reflection_runs WHERE created_by LIKE 'test_sum_%'")
            conn.commit()
        finally:
            conn.close()

    def test_summary_is_saved_once_and_listed(self):
        code = self.rr.generate_code()
        run_id = self.fs.save_reflection_run(
            case_ref=code, source_draft_ids=[], language="Euskera",
            prompt_version="v", model="m", module_status={}, findings=FINDINGS,
            created_by="test_sum_alice", created_by_role="Social Worker", reflection_code=code,
        )["run_id"]

        listed = next(r for r in self.rr.list_reflections("Supervisor") if r["run_id"] == run_id)
        self.assertEqual(listed["summary"], "")
        self.assertEqual(listed["language"], "Euskera")

        self.assertTrue(self.rr.save_summary(run_id, GOOD_SUMMARY))
        self.assertFalse(self.rr.save_summary(run_id, "otro resumen distinto que no debe guardarse"))
        listed = next(r for r in self.rr.list_reflections("Supervisor") if r["run_id"] == run_id)
        self.assertEqual(listed["summary"], GOOD_SUMMARY)

    def test_summary_is_erased_with_the_reflection(self):
        code = self.rr.generate_code()
        run_id = self.fs.save_reflection_run(
            case_ref=code, source_draft_ids=[], language="Español",
            prompt_version="v", model="m", module_status={}, findings=FINDINGS,
            created_by="test_sum_bob", created_by_role="Social Worker", reflection_code=code,
        )["run_id"]
        self.rr.save_summary(run_id, GOOD_SUMMARY)
        with patch("services.audit_log.log_action", lambda *a, **k: None):
            self.assertTrue(self.rr.delete_reflection(run_id, "admin", "System Administrator"))
        conn = self._connect()
        try:
            with conn.cursor() as c:
                c.execute("SELECT COUNT(*) FROM reflection_runs WHERE summary_text = %s", (GOOD_SUMMARY,))
                self.assertEqual(c.fetchone()[0], 0)
        finally:
            conn.close()


if __name__ == "__main__":
    unittest.main()
