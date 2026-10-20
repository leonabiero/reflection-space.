"""REAL-DATABASE tests for Corpus analysis (Step 1).

Skipped unless TEST_DATABASE_URL is set. No AI provider is called:
embeddings and explanations are replaced by simple fakes; SQL is real.
"""
import os
import unittest
import zlib
from unittest.mock import patch

TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL", "")
try:
    import psycopg2
except Exception:  # pragma: no cover
    psycopg2 = None

SUP, PM, ADMIN, SW = "Supervisor", "Programme Manager", "System Administrator", "Social Worker"

DIMS = 1003


def unique_vector(text):
    """A vector unlike any other text's, so filler never groups together."""
    v = [0.0] * DIMS
    v[3 + zlib.crc32(text.encode("utf-8")) % 1000] = 1.0
    return v


def alpha_vector():
    return [1.0, 0.05] + [0.0] * (DIMS - 2)


def beta_vector():
    return [0.05, 1.0] + [0.0] * (DIMS - 2)


FILLER = ("La persona acudió a la cita acompañada y se trató la organización de la semana, "
          "los horarios del centro y los documentos pendientes de entregar en el servicio. ")


def sentence(marker, n=0):
    """A ~250-character sentence carrying a marker word, so each lands in its own passage."""
    return (f"{marker} {n}, se anota que la situación se describe de este modo en la conversación mantenida "
            "durante la visita al domicilio, sin más detalle sobre lo ocurrido antes ni sobre el entorno familiar "
            f"que rodeaba a la persona en ese momento concreto del proceso de acompañamiento (visita {marker}{n}).")


def make_text(*markers, tag=0):
    return " ".join(sentence(m, tag) for m in markers) + " " + FILLER.replace("la cita", f"la cita número {tag}")


@unittest.skipUnless(TEST_DATABASE_URL and psycopg2, "TEST_DATABASE_URL not set -- real-database tests skipped")
class CorpusRealDatabaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from services import db_schema
        cls._connect = staticmethod(lambda: psycopg2.connect(TEST_DATABASE_URL))
        db_schema._schema_ready = False
        with patch.object(db_schema, "get_conn", cls._connect):
            db_schema.ensure_schema()

    def setUp(self):
        from services import corpus_store, corpus_service
        self.cs, self.svc = corpus_store, corpus_service
        p = patch.object(corpus_store, "_get_conn", self._connect)
        p.start(); self.addCleanup(p.stop)
        self._clean(); self.addCleanup(self._clean)
        self.cid = self.cs.create_corpus(SUP, "test_mgr", "Prueba")

    def _clean(self):
        conn = self._connect()
        try:
            with conn.cursor() as c:
                c.execute("DELETE FROM corpus_pattern_runs")
                c.execute("DELETE FROM corpora")
            conn.commit()
        finally:
            conn.close()

    def _fill(self, count, marker="ALPHA", start=0):
        return [self.cs.add_document(SUP, "test_mgr", self.cid, make_text(marker, "OTRO", tag=start + i))
                for i in range(count)]

    def _generate(self, role=SUP, include_questions=True, **kw):
        def fake_embed(text):
            if "ALPHA" in text:
                return alpha_vector()
            if "BETA" in text:
                return beta_vector()
            return unique_vector(text)
        seen = {}

        def fake_explained(passages, lang, include_questions=True):
            seen["include_questions"] = include_questions
            seen["texts"] = [p["text"] for p in passages]
            return {"explanation": {"title": "Tema", "description": "d", "why_it_matters": "w",
                                    "alternative_explanations": ["a"], "limitations": ["l"],
                                    "questions": ["q1", "q2"] if include_questions else []},
                    "status": "ai"}
        with patch.object(self.svc.embedding_service, "is_available", lambda: True), \
             patch.object(self.svc.embedding_service, "embed_document", fake_embed), \
             patch.object(self.svc, "explain_passage_group", fake_explained):
            outcome = self.svc.generate_corpus_patterns(
                role, "test_mgr", self.cid, "Español", include_questions=include_questions, **kw)
        outcome["_seen"] = seen
        return outcome

    # ---- access ----
    def test_only_supervisors_and_programme_managers_may_use_it(self):
        calls = [
            lambda r: self.cs.list_corpora(r), lambda r: self.cs.create_corpus(r, "x", "n"),
            lambda r: self.cs.add_document(r, "x", self.cid, make_text("ALPHA")),
            lambda r: self.cs.list_documents(r, self.cid), lambda r: self.cs.get_counts(r, self.cid),
            lambda r: self.cs.get_passages(r, self.cid), lambda r: self.cs.delete_corpus(r, "x", self.cid),
            lambda r: self.cs.delete_document(r, "x", self.cid, 1),
            lambda r: self.cs.list_runs(r, self.cid), lambda r: self.cs.list_patterns(r, 1),
            lambda r: self.cs.set_pattern_status(r, "x", 1, "worth_discussing"),
            lambda r: self.svc.generate_corpus_patterns(r, "x", self.cid, "Español"),
        ]
        for role in (SW, ADMIN, "", None, "Intruder"):
            for call in calls:
                with self.assertRaises(PermissionError):
                    call(role)
        self.assertEqual(len(self.cs.list_corpora(PM)), 1)

    # ---- adding texts ----
    def test_texts_get_neutral_numbers_that_are_never_reused(self):
        first, second, third = self._fill(3)
        self.assertEqual([first["doc_no"], second["doc_no"], third["doc_no"]], [1, 2, 3])
        self.assertTrue(self.cs.delete_document(SUP, "m", self.cid, 3))
        fourth = self._fill(1, start=50)[0]
        self.assertEqual(fourth["doc_no"], 4)

    def test_same_text_twice_is_detected_even_with_spacing_and_capital_differences(self):
        text = make_text("ALPHA", tag=1)
        self.assertEqual(self.cs.add_document(SUP, "m", self.cid, text)["status"], "added")
        again = self.cs.add_document(SUP, "m", self.cid, "  " + text.upper().replace(" ", "  ") + " ")
        self.assertEqual(again["status"], "duplicate")
        self.assertEqual(again["doc_no"], 1)
        self.assertEqual(self.cs.get_counts(SUP, self.cid)["documents"], 1)

    def test_empty_or_too_short_text_is_refused_and_unknown_collection_reported(self):
        self.assertEqual(self.cs.add_document(SUP, "m", self.cid, "   ")["status"], "empty")
        self.assertEqual(self.cs.add_document(SUP, "m", self.cid, "Hola.")["status"], "empty")
        self.assertEqual(self.cs.add_document(SUP, "m", 999999, make_text("ALPHA"))["status"], "missing")

    def test_passages_are_exact_pieces_of_the_stored_text(self):
        text = make_text("ALPHA", "BETA", tag=7)
        self.cs.add_document(SUP, "m", self.cid, text)
        passages = self.cs.get_passages(SUP, self.cid)
        self.assertGreaterEqual(len(passages), 2)
        for p in passages:
            self.assertIn(p["text"], text)

    def test_listing_never_includes_text_or_file_names(self):
        self._fill(1)
        doc = self.cs.list_documents(SUP, self.cid)[0]
        self.assertEqual(set(doc), {"id", "doc_no", "char_count", "created_at", "passages"})

    def test_names_of_files_are_not_a_column_anywhere(self):
        conn = self._connect()
        with conn.cursor() as c:
            c.execute("SELECT column_name FROM information_schema.columns WHERE table_name LIKE 'corpus%'")
            columns = {r[0] for r in c.fetchall()}
        conn.close()
        for forbidden in ("filename", "file_name", "name_of_file", "original_name", "path"):
            self.assertNotIn(forbidden, columns)

    # ---- deleting ----
    def test_deleting_a_text_erases_passages_vectors_and_place_in_patterns(self):
        self._fill(4)
        outcome = self._generate()
        self.assertEqual(outcome["status"], "completed")
        self.assertEqual(outcome["patterns_created"], 1)
        self.assertTrue(self.cs.delete_document(SUP, "m", self.cid, 1))
        conn = self._connect()
        with conn.cursor() as c:
            c.execute("SELECT COUNT(*) FROM corpus_passages p JOIN corpus_documents d ON d.id=p.document_id "
                      "WHERE d.doc_no=1")
            self.assertEqual(c.fetchone()[0], 0)
            c.execute("SELECT COUNT(*) FROM corpus_passage_embeddings e "
                      "WHERE NOT EXISTS (SELECT 1 FROM corpus_passages p WHERE p.id=e.passage_id)")
            self.assertEqual(c.fetchone()[0], 0)
        conn.close()
        pattern = self.cs.list_patterns(SUP, outcome["run_id"])[0]
        self.assertEqual(pattern["lost_members"], 1)
        self.assertEqual(pattern["counts"]["documents"], 3)
        self.assertEqual(pattern["counts"]["total_documents"], 3)

    def test_deleting_all_texts_of_a_pattern_makes_it_disappear(self):
        self._fill(3)
        outcome = self._generate()
        for n in (1, 2, 3):
            self.cs.delete_document(SUP, "m", self.cid, n)
        self.assertEqual(self.cs.list_patterns(SUP, outcome["run_id"]), [])

    def test_deleting_a_collection_erases_everything_in_it(self):
        self._fill(3)
        self._generate()
        self.assertTrue(self.cs.delete_corpus(SUP, "m", self.cid))
        conn = self._connect()
        with conn.cursor() as c:
            for table in ("corpus_documents", "corpus_passages", "corpus_passage_embeddings",
                          "corpus_pattern_runs", "corpus_patterns", "corpus_pattern_passages",
                          "corpus_pattern_events"):
                c.execute(f"SELECT COUNT(*) FROM {table}")
                self.assertEqual(c.fetchone()[0], 0, table)
        conn.close()

    # ---- generation ----
    def test_a_pattern_needs_enough_different_documents(self):
        self._fill(2)                                   # only 2 documents, minimum is 3
        outcome = self._generate()
        self.assertEqual(outcome["status"], "empty")
        self._fill(1, start=10)
        outcome = self._generate()
        self.assertEqual(outcome["status"], "completed")
        self.assertEqual(outcome["patterns_created"], 1)

    def test_one_long_document_repeating_itself_never_makes_a_pattern(self):
        text = " ".join(sentence("ALPHA", i) for i in range(6))
        self.cs.add_document(SUP, "m", self.cid, text)
        self._fill(2, marker="GAMMA", start=20)   # unrelated, unique content
        outcome = self._generate(min_documents=2)
        self.assertEqual(outcome["patterns_created"], 0)

    def test_counts_are_documents_out_of_total(self):
        self._fill(3)
        self._fill(2, marker="BETA", start=30)
        outcome = self._generate(min_documents=3)
        patterns = self.cs.list_patterns(SUP, outcome["run_id"])
        alpha = [p for p in patterns if any("ALPHA" in m["text"] for m in p["members"])]
        self.assertEqual(len(alpha), 1)
        self.assertEqual(alpha[0]["counts"]["documents"], 3)
        self.assertEqual(alpha[0]["counts"]["total_documents"], 5)
        self.assertAlmostEqual(alpha[0]["counts"]["share"], 0.6)

    def test_questions_switch_off_asks_for_none_and_stores_none(self):
        self._fill(3)
        outcome = self._generate(include_questions=False)
        self.assertFalse(outcome["_seen"]["include_questions"])
        pattern = self.cs.list_patterns(SUP, outcome["run_id"])[0]
        self.assertEqual(pattern["questions"], [])
        self.assertFalse(self.cs.get_run(SUP, outcome["run_id"])["parameters"]["include_questions"])

    def test_questions_switch_on_keeps_questions(self):
        self._fill(3)
        outcome = self._generate(include_questions=True)
        self.assertTrue(outcome["_seen"]["include_questions"])
        self.assertEqual(self.cs.list_patterns(SUP, outcome["run_id"])[0]["questions"], ["q1", "q2"])

    def test_explainer_receives_only_passage_text(self):
        self._fill(3)
        outcome = self._generate()
        for text in outcome["_seen"]["texts"]:
            self.assertNotRegex(text, r"T-\d{3}")

    def test_only_one_search_can_run_at_once(self):
        first = self.cs.start_run(SUP, "m", self.cid, {}, "Español", "e", "m", "p")
        self.assertIsNotNone(first)
        self.assertIsNone(self.cs.start_run(PM, "n", self.cid, {}, "Español", "e", "m", "p"))
        self._fill(3)
        self.assertEqual(self._generate()["status"], "busy")
        self.cs.finish_run(first, "completed")
        self.assertIsNotNone(self.cs.start_run(PM, "n", self.cid, {}, "Español", "e", "m", "p"))

    def test_unavailable_embedding_service_is_reported_not_crashed(self):
        self._fill(3)
        with patch.object(self.svc.embedding_service, "is_available", lambda: False):
            self.assertEqual(self.svc.generate_corpus_patterns(SUP, "x", self.cid, "Español")["status"],
                             "unavailable")

    def test_failure_marks_run_failed_not_running(self):
        self._fill(3)
        with patch.object(self.svc.embedding_service, "is_available", lambda: True), \
             patch.object(self.svc.corpus_store, "get_cached_embeddings", side_effect=RuntimeError("boom")):
            with self.assertRaises(RuntimeError):
                self.svc.generate_corpus_patterns(SUP, "x", self.cid, "Español")
        conn = self._connect()
        with conn.cursor() as c:
            c.execute("SELECT status, error_summary FROM corpus_pattern_runs ORDER BY id DESC LIMIT 1")
            status, error = c.fetchone()
        conn.close()
        self.assertEqual((status, error), ("failed", "RuntimeError"))
        self.assertIsNotNone(self.cs.start_run(SUP, "x", self.cid, {}, "Español", "e", "m", "p"))

    def test_embeddings_are_cached_so_searching_again_does_not_repay(self):
        self._fill(3)
        calls = []

        def counting(text):
            calls.append(1)
            return alpha_vector() if "ALPHA" in text else unique_vector(text)
        explained = lambda p, lang, include_questions=True: {
            "explanation": {"title": "T", "description": "d", "why_it_matters": "w",
                            "alternative_explanations": ["a"], "limitations": ["l"], "questions": []},
            "status": "ai"}
        with patch.object(self.svc.embedding_service, "is_available", lambda: True), \
             patch.object(self.svc.embedding_service, "embed_document", counting), \
             patch.object(self.svc, "explain_passage_group", explained):
            self.svc.generate_corpus_patterns(SUP, "x", self.cid, "Español")
            first = len(calls)
            self.svc.generate_corpus_patterns(SUP, "x", self.cid, "Español")
        self.assertGreater(first, 0)
        self.assertEqual(len(calls), first)

    # ---- review ----
    def test_review_is_recorded_and_ai_text_is_unchanged(self):
        self._fill(3)
        outcome = self._generate()
        pid = self.cs.list_patterns(SUP, outcome["run_id"])[0]["id"]
        self.assertTrue(self.cs.set_pattern_status(SUP, "ana", pid, "worth_discussing", "para el equipo"))
        self.assertFalse(self.cs.set_pattern_status(SUP, "ana", pid, "worth_discussing"))
        self.assertFalse(self.cs.set_pattern_status(SUP, "ana", pid, "bogus"))
        pattern = self.cs.list_patterns(SUP, outcome["run_id"])[0]
        self.assertEqual(pattern["status"], "worth_discussing")
        self.assertEqual(pattern["title"], "Tema")
        kinds = [e["kind"] for e in self.cs.get_pattern_events(SUP, pid)]
        self.assertEqual(kinds, ["generated", "status_changed"])

    def test_excluding_and_restoring_a_passage_changes_counts(self):
        self._fill(4)
        outcome = self._generate()
        pattern = self.cs.list_patterns(SUP, outcome["run_id"])[0]
        member = pattern["members"][0]
        self.assertTrue(self.cs.set_member_excluded(SUP, "ana", pattern["id"], member["id"], True))
        after = self.cs.list_patterns(SUP, outcome["run_id"])[0]
        self.assertEqual(after["counts"]["documents"], 3)
        self.assertEqual(len(after["excluded_members"]), 1)
        self.assertEqual(after["lost_members"], 0)
        self.assertTrue(self.cs.set_member_excluded(SUP, "ana", pattern["id"], member["id"], False))
        self.assertEqual(self.cs.list_patterns(SUP, outcome["run_id"])[0]["counts"]["documents"], 4)

    def test_review_carries_over_to_the_next_search(self):
        self._fill(3)
        first = self._generate()
        pid = self.cs.list_patterns(SUP, first["run_id"])[0]["id"]
        self.cs.set_pattern_status(SUP, "ana", pid, "not_supported", "revisado")
        second = self._generate()
        carried = self.cs.list_patterns(SUP, second["run_id"])[0]
        self.assertEqual(carried["status"], "not_supported")
        kinds = [e["kind"] for e in self.cs.get_pattern_events(SUP, carried["id"])]
        self.assertIn("carried_over", kinds)

    def test_fallback_explanation_can_be_replaced_but_ai_one_cannot(self):
        self._fill(3)
        with patch.object(self.svc.embedding_service, "is_available", lambda: True), \
             patch.object(self.svc.embedding_service, "embed_document", lambda t: alpha_vector()), \
             patch.object(self.svc, "explain_passage_group", lambda p, lang, include_questions=True: {
                 "explanation": {"title": "Plano", "description": "d", "why_it_matters": "w",
                                 "alternative_explanations": ["a"], "limitations": ["l"], "questions": []},
                 "status": "fallback"}):
            outcome = self.svc.generate_corpus_patterns(SUP, "x", self.cid, "Español")
        self.assertEqual(outcome["fallback_count"], 1)
        pattern = self.cs.list_patterns(SUP, outcome["run_id"])[0]
        better = {"title": "Bueno", "description": "d", "why_it_matters": "w",
                  "alternative_explanations": ["a"], "limitations": ["l"], "questions": []}
        self.assertTrue(self.cs.update_pattern_explanation(SUP, "ana", pattern["id"], better))
        self.assertFalse(self.cs.update_pattern_explanation(SUP, "ana", pattern["id"], better))
        self.assertEqual(self.cs.list_patterns(SUP, outcome["run_id"])[0]["title"], "Bueno")

    # ---- Step 2: readings ----
    def _read_all(self, role=SUP, include_questions=True, batch_size=10, fail_lens=None, replies=None):
        """Run read_texts with a fake AI: every lens raises an observation quoting the first
        30 characters of the text, except lenses listed in fail_lens, which fail."""
        from services import corpus_reading_service as crs

        def fake_read_lens(companion, text, lang, inc):
            if fail_lens and companion["key"] in fail_lens:
                return {"lens": companion["key"], "status": "failed", "observation": "",
                        "questions": [], "evidence": [], "unverified_count": 0}
            return {"lens": companion["key"], "status": "finding", "observation": f"Obs {companion['key']}",
                    "questions": ["q"] if inc else [], "evidence": [{"quote": text[:30]}],
                    "unverified_count": 0}
        seen = []
        with patch.object(crs, "is_available", lambda: True), \
             patch.object(crs, "read_lens", fake_read_lens):
            outcome = crs.read_texts(role, "test_mgr", self.cid, "Español",
                                     include_questions=include_questions, batch_size=batch_size,
                                     progress=lambda d, t: seen.append((d, t)))
        outcome["_progress"] = seen
        return outcome

    def test_reading_only_for_the_two_manager_roles(self):
        from services import corpus_reading_service as crs
        self._fill(1)
        for role in (SW, ADMIN, "", None):
            with self.assertRaises(PermissionError):
                crs.read_texts(role, "x", self.cid, "Español")
            for call in (lambda r: self.cs.get_reading_overview(r, self.cid),
                         lambda r: self.cs.list_lens_readings(r, self.cid, "client_voice"),
                         lambda r: self.cs.get_text_readings(r, self.cid, 1),
                         lambda r: self.cs.get_documents_to_read(r, self.cid, 5),
                         lambda r: self.cs.clear_readings(r, "x", self.cid),
                         lambda r: self.cs.save_readings(r, 1, []),
                         lambda r: self.cs.start_reading_job(r, "x", self.cid, 1)):
                with self.assertRaises(PermissionError):
                    call(role)

    def test_reads_in_batches_and_resumes_with_the_unread(self):
        self._fill(5)
        first = self._read_all(batch_size=3)
        self.assertEqual((first["status"], first["documents_read"], first["remaining"]), ("completed", 3, 2))
        self.assertEqual(first["_progress"][-1], (3, 3))
        overview = self.cs.get_reading_overview(SUP, self.cid)
        self.assertEqual((overview["documents"], overview["read"], overview["unread"]), (5, 3, 2))
        second = self._read_all(batch_size=3)
        self.assertEqual((second["documents_read"], second["remaining"]), (2, 0))
        self.assertEqual(self._read_all()["status"], "nothing_to_read")
        counts = self.cs.get_reading_overview(SUP, self.cid)["lenses"]["client_voice"]
        self.assertEqual(counts, {"finding": 5, "no_finding": 0, "failed": 0})

    def test_a_failed_lens_is_recorded_and_retried_next_time(self):
        self._fill(2)
        first = self._read_all(fail_lens={"possible_bias"})
        self.assertEqual(first["failed_lenses"], 2)
        self.assertEqual(first["remaining"], 2)           # not fully read -> still to do
        self.assertEqual(self.cs.get_reading_overview(SUP, self.cid)["lenses"]["possible_bias"]["failed"], 2)
        second = self._read_all()
        self.assertEqual((second["documents_read"], second["failed_lenses"], second["remaining"]), (2, 0, 0))

    def test_readings_are_listed_by_lens_with_quotes_and_per_text(self):
        self._fill(2)
        self._read_all()
        items = self.cs.list_lens_readings(SUP, self.cid, "client_voice")
        self.assertEqual([i["doc_no"] for i in items], [1, 2])
        self.assertTrue(all(i["evidence"] and i["questions"] == ["q"] for i in items))
        per_text = self.cs.get_text_readings(SUP, self.cid, 2)
        self.assertEqual(set(per_text), set(self.cs.READING_LENSES))
        self.assertEqual(self.cs.list_lens_readings(SUP, self.cid, "not_a_lens"), [])

    def test_questions_switch_off_stores_no_questions(self):
        self._fill(1)
        self._read_all(include_questions=False)
        self.assertEqual(self.cs.list_lens_readings(SUP, self.cid, "client_voice")[0]["questions"], [])

    def test_deleting_a_text_or_collection_erases_its_readings(self):
        self._fill(2)
        self._read_all()
        self.cs.delete_document(SUP, "m", self.cid, 1)
        overview = self.cs.get_reading_overview(SUP, self.cid)
        self.assertEqual((overview["documents"], overview["read"]), (1, 1))
        conn = self._connect()
        with conn.cursor() as c:
            c.execute("SELECT COUNT(*) FROM corpus_readings")
            self.assertEqual(c.fetchone()[0], len(self.cs.READING_LENSES))
        conn.close()
        self.cs.delete_corpus(SUP, "m", self.cid)
        conn = self._connect()
        with conn.cursor() as c:
            for table in ("corpus_readings", "corpus_reading_jobs"):
                c.execute(f"SELECT COUNT(*) FROM {table}")
                self.assertEqual(c.fetchone()[0], 0, table)
        conn.close()

    def test_only_one_reading_job_at_once_and_failure_marks_job_failed(self):
        from services import corpus_reading_service as crs
        self._fill(2)
        job = self.cs.start_reading_job(SUP, "m", self.cid, 2)
        self.assertIsNotNone(job)
        self.assertEqual(self._read_all()["status"], "busy")
        self.cs.finish_reading_job(job, "completed")
        with patch.object(crs, "is_available", lambda: True), \
             patch.object(crs, "read_lens", side_effect=RuntimeError("boom")):
            with self.assertRaises(RuntimeError):
                crs.read_texts(SUP, "x", self.cid, "Español")
        conn = self._connect()
        with conn.cursor() as c:
            c.execute("SELECT status, error_summary FROM corpus_reading_jobs ORDER BY id DESC LIMIT 1")
            self.assertEqual(c.fetchone(), ("failed", "RuntimeError"))
        conn.close()
        self.assertIsNotNone(self.cs.start_reading_job(SUP, "m", self.cid, 1))

    def test_unavailable_ai_is_reported_not_crashed(self):
        from services import corpus_reading_service as crs
        self._fill(1)
        with patch.object(crs, "is_available", lambda: False):
            self.assertEqual(crs.read_texts(SUP, "x", self.cid, "Español")["status"], "unavailable")

    def test_clearing_readings_lets_everything_be_read_again(self):
        self._fill(2)
        self._read_all()
        self.assertEqual(self.cs.clear_readings(SUP, "m", self.cid), 2 * len(self.cs.READING_LENSES))
        self.assertEqual(self.cs.get_reading_overview(SUP, self.cid)["unread"], 2)
        self.assertEqual(self._read_all()["documents_read"], 2)

    def test_a_text_erased_while_being_read_is_skipped_not_an_error(self):
        self._fill(1)
        document_id = self.cs.get_documents_to_read(SUP, self.cid, 1)[0]["id"]
        self.cs.delete_document(SUP, "m", self.cid, 1)
        self.assertEqual(self.cs.save_readings(SUP, document_id, [
            {"lens": "client_voice", "status": "no_finding"}]), 0)

    def test_invalid_readings_are_refused(self):
        self._fill(1)
        document_id = self.cs.get_documents_to_read(SUP, self.cid, 1)[0]["id"]
        with self.assertRaises(ValueError):
            self.cs.save_readings(SUP, document_id, [{"lens": "bogus", "status": "finding"}])
        with self.assertRaises(ValueError):
            self.cs.save_readings(SUP, document_id, [{"lens": "client_voice", "status": "bogus"}])


if __name__ == "__main__":
    unittest.main()
