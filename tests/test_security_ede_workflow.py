"""Privacy and security tests for the EDE reflection workflow.
All names and texts are synthetic."""

import json
import re
import unittest
from unittest.mock import patch

from services import ede_export
from services.anonymizer import anonymize
from services.ede_analysis import EdeAnalysisError, run_ede_analysis
from services.language import get_lang

from ede_test_support import (
    ANALYSE_KWARGS, ES_DOC, ES_QUOTE, ProviderPatches, make_absence, make_finding, reply,
)


def read(path):
    with open(path, encoding="utf-8") as handle:
        return handle.read()


PERSONAL_DOC = (
    "Seguimiento mensual del caso. María José García Etxeberria llamó desde el teléfono 944 123 456 "
    "y escribió a maria.garcia@example.org.\n"
    "Parece que no está comprometida con el proceso, según el equipo."
)


class AnonymisationBoundaryTests(unittest.TestCase):
    def test_existing_anonymiser_runs_before_anything_is_sent_to_the_model(self):
        order = []

        def spy(text):
            order.append("anonymize")
            return anonymize(text)

        with ProviderPatches(reply([])) as p:
            p.client.messages.create.side_effect = lambda **kw: (order.append("provider"), reply([]))[1]
            with patch("services.ede_analysis.anonymize", spy):
                run_ede_analysis(PERSONAL_DOC, **ANALYSE_KWARGS)
        self.assertEqual(order, ["anonymize", "provider"])

    def test_personal_identifiers_do_not_reach_the_provider(self):
        with ProviderPatches(reply([])) as p:
            run_ede_analysis(PERSONAL_DOC, **ANALYSE_KWARGS)
        sent = json.dumps(p.client.messages.create.call_args.kwargs, ensure_ascii=False)
        for secret in ("María José García Etxeberria", "944 123 456", "maria.garcia@example.org"):
            self.assertNotIn(secret, sent)
        self.assertIn("[PERSON]", sent)
        self.assertIn("[EMAIL]", sent)

    def test_quotes_are_checked_against_the_anonymised_text_that_was_actually_sent(self):
        invented_with_name = make_finding(quote="María José García Etxeberria llamó desde el teléfono")
        valid = make_finding(quote="Parece que no está comprometida con el proceso")
        with ProviderPatches(reply([invented_with_name, valid])):
            result = run_ede_analysis(PERSONAL_DOC, **ANALYSE_KWARGS)
        self.assertEqual(result["accepted_count"], 1)
        self.assertEqual(result["discarded_count"], 1)


class SecretsAndErrorTests(unittest.TestCase):
    def test_provider_errors_never_leak_keys_provider_text_or_document_text(self):
        secret = "sk-ant-TEST-SECRET-123"
        boom = RuntimeError(f"401 invalid key {secret}; request body: {ES_DOC}")
        with ProviderPatches(boom, api_key=secret) as p:
            with self.assertRaises(EdeAnalysisError) as ctx:
                run_ede_analysis(ES_DOC, **ANALYSE_KWARGS)
        self.assertEqual(str(ctx.exception), "provider_unavailable")
        logged = repr(p.log_error.call_args_list)
        self.assertNotIn(secret, logged)
        self.assertNotIn("Parece que", logged)
        self.assertNotIn("conflictiva", logged)
        self.assertIn("RuntimeError", logged)  # only the exception CLASS name is kept

    def test_every_error_code_message_is_just_the_code(self):
        for code in ("input_empty", "output_invalid", "provider_unavailable", "not_authorised"):
            self.assertEqual(str(EdeAnalysisError(code)), code)

    def test_malformed_output_log_entry_contains_no_model_text(self):
        leaked = "TEXTO-SENSIBLE-DEL-MODELO " + ES_DOC
        with ProviderPatches(reply(leaked)) as p:
            with self.assertRaises(EdeAnalysisError):
                run_ede_analysis(ES_DOC, **ANALYSE_KWARGS)
        logged = repr(p.log_error.call_args_list)
        self.assertNotIn("TEXTO-SENSIBLE", logged)
        self.assertNotIn("Parece que", logged)

    def test_logging_failure_cannot_mask_the_original_error(self):
        with ProviderPatches(RuntimeError("x")) as p:
            p.log_error.side_effect = Exception("db down")
            with self.assertRaises(EdeAnalysisError) as ctx:
                run_ede_analysis(ES_DOC, **ANALYSE_KWARGS)
        self.assertEqual(ctx.exception.code, "provider_unavailable")
        self.assertIsNone(ctx.exception.issue_id)

    def test_new_code_does_not_print_or_log_document_content(self):
        for path in ("services/ede_analysis.py", "services/ede_framework.py", "services/ede_export.py",
                     "services/ede_language_detection.py", "pages/ede_reflection.py"):
            source = read(path)
            self.assertNotRegex(source, r"\bprint\(", path)
            self.assertNotRegex(source, r"logger\.|logging\.", path)
            self.assertNotIn("traceback.format_exc", source, path)
            self.assertNotIn("str(e)", source, path)
            self.assertNotIn("str(exc)", source, path)

    def test_no_api_key_is_hard_coded_in_new_files(self):
        for path in ("services/ede_analysis.py", "pages/ede_reflection.py", "config.py"):
            self.assertNotRegex(read(path), r"sk-ant-[A-Za-z0-9_\-]{10,}", path)


class AuthorisationTests(unittest.TestCase):
    def test_service_fails_closed_without_identity_or_with_unknown_role(self):
        cases = [("", "Social Worker"), ("Alice", ""), ("Alice", "Intern"), (None, None), ("Alice", "Guest")]
        for name, role in cases:
            with ProviderPatches(reply([])) as p:
                with self.assertRaises(EdeAnalysisError) as ctx:
                    run_ede_analysis(ES_DOC, **{**ANALYSE_KWARGS, "actor_name": name, "actor_role": role})
                self.assertEqual(ctx.exception.code, "not_authorised")
                p.client.messages.create.assert_not_called()

    def test_all_four_existing_roles_may_use_the_practitioner_workflow(self):
        for role in ("Social Worker", "Supervisor", "Programme Manager", "System Administrator"):
            with ProviderPatches(reply([])):
                result = run_ede_analysis(ES_DOC, **{**ANALYSE_KWARGS, "actor_role": role})
            self.assertEqual(result["accepted_count"], 0)

    def test_page_is_behind_login_and_work_mode_guard_before_any_analysis_code(self):
        source = read("pages/ede_reflection.py")
        positions = [source.index(marker) for marker in (
            "init_identity(T)", 'require_work_mode(T, "Practitioner")', "render_nav(", "error_boundary(")]
        self.assertEqual(positions, sorted(positions))
        self.assertLess(source.index('require_work_mode(T, "Practitioner")'), source.index("run_ede_analysis("))
        self.assertIn("actor_name=user_name, actor_role=user_role", source)

    def test_page_takes_identity_from_the_session_not_from_user_input(self):
        source = read("pages/ede_reflection.py")
        self.assertNotIn("query_params", source)
        self.assertNotIn("st.experimental_get_query_params", source)


class StorageAndSessionTests(unittest.TestCase):
    FORBIDDEN_IMPORTS = ("psycopg2", "db_pool", "qdrant", "embedding_service", "draft_storage",
                         "reflection_log", "feedback_store", "case_knowledge", "exploration_log",
                         "retrieval_service", "context_engine")

    def test_new_modules_have_no_database_vector_store_or_embedding_dependencies(self):
        for path in ("services/ede_analysis.py", "services/ede_framework.py", "services/ede_export.py",
                     "services/ede_language_detection.py", "pages/ede_reflection.py"):
            imports = "\n".join(l for l in read(path).splitlines() if re.match(r"\s*(from|import)\s", l))
            for name in self.FORBIDDEN_IMPORTS:
                self.assertNotIn(name, imports, f"{path} imports {name}")

    def test_page_only_uses_ede_prefixed_session_keys(self):
        source = read("pages/ede_reflection.py")
        for key in re.findall(r'st\.session_state(?:\.\w+\(|\[)\s*"([^"]+)"', source):
            self.assertTrue(key.startswith("ede_") or key in ("lang",), key)

    def test_result_object_holds_no_copy_of_the_source_document(self):
        with ProviderPatches(reply([make_finding()])):
            result = run_ede_analysis(ES_DOC, **ANALYSE_KWARGS)
        dumped = json.dumps(result, ensure_ascii=False)
        self.assertIn(ES_QUOTE, dumped)  # the cited passage is expected...
        for sentence in ("Seguimiento mensual del mes de marzo", "La usuaria faltó a dos citas",
                         "Su hermana comenta"):
            self.assertNotIn(sentence, dumped)  # ...but not the rest of the document

    def test_analysis_makes_no_database_calls_of_its_own(self):
        with ProviderPatches(reply([make_finding()])), \
             patch("services.db_pool.get_conn", side_effect=AssertionError("db used")) as conn:
            run_ede_analysis(ES_DOC, **ANALYSE_KWARGS)
            conn.assert_not_called()


class ExportTests(unittest.TestCase):
    def _result(self):
        findings = [make_finding(), make_absence(), make_finding("persons_voice", score=9)]
        with ProviderPatches(reply(findings)):
            return run_ede_analysis(ES_DOC, **ANALYSE_KWARGS)

    def test_export_contains_validated_findings_only(self):
        result = self._result()
        data = json.loads(ede_export.export_json(result))
        total = sum(len(v) for v in data["dimensions"].values())
        self.assertEqual(total, result["accepted_count"])
        self.assertEqual(total, 2)  # the finding with a forbidden extra field never got in

    def test_export_never_includes_the_full_source_document_or_user_identity(self):
        result = self._result()
        T = get_lang("Español")
        for blob in (ede_export.export_json(result), ede_export.export_markdown(result, T)):
            for sentence in ("Seguimiento mensual del mes de marzo", "La usuaria faltó a dos citas",
                             "Test Worker", "Su hermana comenta"):
                self.assertNotIn(sentence, blob)

    def test_export_keeps_evidence_references_and_limitations(self):
        result = self._result()
        data = json.loads(ede_export.export_json(result))
        item = data["dimensions"]["observation_vs_interpretation"][0]
        self.assertEqual(item["evidence"]["quote"], ES_QUOTE)
        self.assertEqual(item["evidence"]["paragraph"], 2)
        self.assertTrue(item["limitations"])
        absent = data["dimensions"]["persons_voice"][0]
        self.assertIsNone(absent["evidence"]["quote"])
        self.assertTrue(absent["evidence"]["not_documented"])
        markdown = ede_export.export_markdown(result, get_lang("Español"))
        self.assertIn("no demuestra", markdown)

    def test_export_uses_an_allow_list_so_unexpected_fields_cannot_leak(self):
        result = self._result()
        result["dimensions"]["persons_voice"][0]["internal_secret"] = "TOP-SECRET"
        result["dimensions"]["persons_voice"][0]["source_evidence"]["raw_text"] = "TOP-SECRET"
        self.assertNotIn("TOP-SECRET", ede_export.export_json(result))
        self.assertNotIn("TOP-SECRET", ede_export.export_markdown(result, get_lang("Español")))

    def test_export_has_no_scores_and_flags_ai_output_as_hypotheses(self):
        data = json.loads(ede_export.export_json(self._result()))
        flat = json.dumps(data).lower()
        for word in ("score", "rank", "risk"):
            self.assertNotIn(word, flat)
        self.assertIn("hypotheses", data["notice"])

    def test_feedback_in_export_is_only_what_the_professional_wrote(self):
        result = self._result()
        fid = result["dimensions"]["observation_vs_interpretation"][0]["id"]
        fb = {fid: {"rating": "unsupported", "alternative": "Otra lectura posible", "team_question": "¿Lo vemos en equipo?"}}
        data = json.loads(ede_export.export_json(result, fb))
        got = data["dimensions"]["observation_vs_interpretation"][0]["professional_feedback"]
        self.assertEqual(got["rating"], "unsupported")
        self.assertEqual(got["alternative_interpretation"], "Otra lectura posible")


class UploadSafetyTests(unittest.TestCase):
    def test_page_only_accepts_plain_text_uploads_and_checks_size_and_encoding(self):
        source = read("pages/ede_reflection.py")
        self.assertIn('type=["txt", "md"]', source)
        self.assertIn("EDE_MAX_UPLOAD_BYTES", source)
        self.assertIn('decode("utf-8-sig")', source)
        self.assertIn("UnicodeDecodeError", source)
        self.assertNotIn("uploaded.name)", source.replace("uploaded.name.lower()", ""))  # file name never shown/stored


if __name__ == "__main__":
    unittest.main()
