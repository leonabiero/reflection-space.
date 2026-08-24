"""
Service Cost & Usage Monitor -- Tests

Covers the behaviors the accompanying spec's Phase 17 calls out
explicitly: actual (not max_tokens-based) cost calculation, retries
and companion calls being recorded, Gemini/Qdrant/DB metrics failing
gracefully, centralized pricing, threshold status correctness, monthly
projection, cost-per-reflection, duplicate-alert prevention, monitoring
never breaking a reflection, and no sensitive content ever reaching
the ledger.

Uses in-memory fakes rather than a real database/API, consistent with
this repo's existing test style (see tests/test_reliability_rate_limiter.py).
"""

import time
import unittest
from unittest.mock import patch, MagicMock


class CostPricingTests(unittest.TestCase):
    def test_cost_uses_actual_tokens_not_max_tokens(self):
        """Two calls with the same max_tokens but different ACTUAL usage
        must produce different costs -- proves cost is derived from the
        API's reported usage, never from the max_tokens request parameter."""
        from services.cost_pricing import estimate_anthropic_cost

        cost_small, _ = estimate_anthropic_cost("claude-sonnet-5", input_tokens=100, output_tokens=50)
        cost_large, _ = estimate_anthropic_cost("claude-sonnet-5", input_tokens=100, output_tokens=900)
        self.assertLess(cost_small, cost_large)
        self.assertGreater(cost_small, 0)

    def test_unrecognized_model_falls_back_and_flags_estimate(self):
        from services.cost_pricing import estimate_anthropic_cost

        cost, recognized = estimate_anthropic_cost("some-future-model", input_tokens=1000, output_tokens=1000)
        self.assertFalse(recognized)
        self.assertGreater(cost, 0)  # still computes SOMETHING via fallback rate, but flagged

    def test_gemini_cost_from_actual_token_count(self):
        from services.cost_pricing import estimate_gemini_embedding_cost

        cost, recognized = estimate_gemini_embedding_cost("gemini-embedding-001", input_tokens=500)
        self.assertTrue(recognized)
        self.assertGreater(cost, 0)

    def test_pricing_is_centralized_in_one_registry(self):
        """Structural guard: every price lives in cost_pricing.py's
        registries, not scattered as inline literals elsewhere."""
        from services import cost_pricing

        self.assertIn("claude-sonnet-5", cost_pricing.ANTHROPIC_PRICING)
        self.assertIn("effective_date", cost_pricing.ANTHROPIC_PRICING["claude-sonnet-5"])
        self.assertIn("gemini-embedding-001", cost_pricing.GEMINI_PRICING)


class UsageLedgerRecordingTests(unittest.TestCase):
    def test_record_usage_never_raises_when_db_unavailable(self):
        """PHASE 16: a monitoring failure must never propagate."""
        from services import usage_ledger

        with patch.object(usage_ledger, "_get_conn", side_effect=Exception("db is down")):
            try:
                usage_ledger.record_usage("anthropic", "companion_reflection", input_tokens=10, output_tokens=10)
                # Give the background thread a moment to actually run and hit the failure.
                time.sleep(0.2)
            except Exception as e:  # pragma: no cover -- this must never happen
                self.fail(f"record_usage raised: {e!r}")

    def test_record_usage_never_raises_when_queue_full(self):
        from services import usage_ledger

        with patch.object(usage_ledger, "_queue_depth", usage_ledger._MAX_QUEUE):
            try:
                usage_ledger.record_usage("anthropic", "companion_reflection")
            except Exception as e:  # pragma: no cover
                self.fail(f"record_usage raised on a full queue: {e!r}")

    def test_metadata_allowlist_drops_unlisted_keys(self):
        from services import usage_ledger

        cleaned = usage_ledger._safe_metadata({
            "companion": "client_voice",
            "case_ref": "SHOULD-NOT-APPEAR",
            "reflection_text": "SHOULD-NOT-APPEAR-EITHER",
        })
        self.assertIn("client_voice", cleaned)
        self.assertNotIn("SHOULD-NOT-APPEAR", cleaned)
        self.assertNotIn("SHOULD-NOT-APPEAR-EITHER", cleaned)

    def test_metadata_with_no_allowlisted_keys_is_none(self):
        from services import usage_ledger

        self.assertIsNone(usage_ledger._safe_metadata({"case_ref": "x", "reflection_text": "y"}))


class ReflectionServiceInstrumentationTests(unittest.TestCase):
    def _fake_message(self, input_tokens=100, output_tokens=200, text='{"ok": true}'):
        msg = MagicMock()
        msg.usage.input_tokens = input_tokens
        msg.usage.output_tokens = output_tokens
        msg.usage.cache_read_input_tokens = 0
        msg.usage.cache_creation_input_tokens = 0
        msg.stop_reason = "end_turn"
        block = MagicMock()
        block.type = "text"
        block.text = text
        msg.content = [block]
        return msg

    def test_successful_companion_call_records_actual_usage(self):
        from services import reflection_service

        message = self._fake_message(input_tokens=321, output_tokens=654)
        with patch.object(reflection_service, "_call_companion_model", return_value=message), \
                patch.object(reflection_service, "usage_ledger") as fake_ledger:
            reflection_service.generate_companion_reflection(
                {"key": "client_voice", "label": "x", "focus": "y"}, "safe text", lang="English",
            )

        fake_ledger.record_usage.assert_called_once()
        _, kwargs = fake_ledger.record_usage.call_args
        self.assertEqual(kwargs["input_tokens"], 321)
        self.assertEqual(kwargs["output_tokens"], 654)
        self.assertTrue(kwargs["success"])
        self.assertEqual(kwargs["metadata"]["companion"], "client_voice")

    def test_failed_companion_call_records_failure_not_cost(self):
        from services import reflection_service

        with patch.object(reflection_service, "_call_companion_model", side_effect=RuntimeError("boom")), \
                patch.object(reflection_service, "usage_ledger") as fake_ledger:
            with self.assertRaises(RuntimeError):
                reflection_service.generate_companion_reflection(
                    {"key": "client_voice", "label": "x", "focus": "y"}, "safe text", lang="English",
                )

        fake_ledger.record_usage.assert_called_once()
        _, kwargs = fake_ledger.record_usage.call_args
        self.assertFalse(kwargs["success"])
        self.assertEqual(kwargs["metadata"]["error_type"], "RuntimeError")

    def test_a_retry_produces_two_separate_usage_records(self):
        """Two attempts at the same companion (a failure, then a manual
        retry that succeeds) must show up as TWO rows -- not
        collapsed/averaged -- so retry rate can be computed downstream."""
        from services import reflection_service

        message = self._fake_message()
        with patch.object(reflection_service, "usage_ledger") as fake_ledger:
            with patch.object(reflection_service, "_call_companion_model", side_effect=RuntimeError("boom")):
                with self.assertRaises(RuntimeError):
                    reflection_service.generate_companion_reflection(
                        {"key": "client_voice", "label": "x", "focus": "y"}, "safe text", lang="English",
                    )
            with patch.object(reflection_service, "_call_companion_model", return_value=message):
                reflection_service.generate_companion_reflection(
                    {"key": "client_voice", "label": "x", "focus": "y"}, "safe text", lang="English",
                )

        self.assertEqual(fake_ledger.record_usage.call_count, 2)
        first_call_kwargs = fake_ledger.record_usage.call_args_list[0].kwargs
        second_call_kwargs = fake_ledger.record_usage.call_args_list[1].kwargs
        self.assertFalse(first_call_kwargs["success"])
        self.assertTrue(second_call_kwargs["success"])


class EmbeddingInstrumentationTests(unittest.TestCase):
    def test_successful_embedding_uses_actual_token_count_from_sdk(self):
        from services import embedding_service

        fake_result = MagicMock()
        fake_embedding = MagicMock()
        fake_embedding.values = [0.1, 0.2, 0.3]
        fake_embedding.statistics.token_count = 42
        fake_result.embeddings = [fake_embedding]
        fake_result.metadata.billable_character_count = 210

        fake_client = MagicMock()
        fake_client.models.embed_content.return_value = fake_result

        with patch.object(embedding_service, "_get_client", return_value=fake_client), \
                patch.object(embedding_service, "usage_ledger") as fake_ledger:
            vector = embedding_service.embed_document("some safe anonymized text")

        self.assertEqual(vector, [0.1, 0.2, 0.3])
        fake_ledger.record_usage.assert_called_once()
        _, kwargs = fake_ledger.record_usage.call_args
        self.assertEqual(kwargs["input_tokens"], 42)
        self.assertEqual(kwargs["units_used"], 210)
        self.assertTrue(kwargs["success"])

    def test_embedding_failure_records_failure_and_returns_none(self):
        from services import embedding_service

        fake_client = MagicMock()
        fake_client.models.embed_content.side_effect = RuntimeError("gemini is down")

        with patch.object(embedding_service, "_get_client", return_value=fake_client), \
                patch.object(embedding_service, "usage_ledger") as fake_ledger:
            vector = embedding_service.embed_query("some safe text")

        self.assertIsNone(vector)
        fake_ledger.record_usage.assert_called_once()
        _, kwargs = fake_ledger.record_usage.call_args
        self.assertFalse(kwargs["success"])


class DashboardStatusTests(unittest.TestCase):
    def test_status_thresholds(self):
        from services.cost_dashboard_service import _status_for_pct, STATUS_GREEN, STATUS_YELLOW, STATUS_ORANGE, STATUS_RED, STATUS_UNKNOWN

        self.assertEqual(_status_for_pct(None), STATUS_UNKNOWN)
        self.assertEqual(_status_for_pct(0), STATUS_GREEN)
        self.assertEqual(_status_for_pct(69.9), STATUS_GREEN)
        self.assertEqual(_status_for_pct(70), STATUS_YELLOW)
        self.assertEqual(_status_for_pct(84.9), STATUS_YELLOW)
        self.assertEqual(_status_for_pct(85), STATUS_ORANGE)
        self.assertEqual(_status_for_pct(94.9), STATUS_ORANGE)
        self.assertEqual(_status_for_pct(95), STATUS_RED)
        self.assertEqual(_status_for_pct(100), STATUS_RED)

    def test_cost_per_reflection_with_no_data_reports_note_not_error(self):
        from services import cost_dashboard_service as dashboard

        with patch.object(dashboard.usage_ledger, "get_operation_breakdown", return_value=[]), \
                patch.object(dashboard, "get_total_reflection_count", return_value=0):
            result = dashboard.get_cost_per_reflection(window_days=30)

        self.assertIsNone(result["avg_cost_per_reflection_usd"])
        self.assertIsNotNone(result["note"])

    def test_cost_per_reflection_accounts_for_multiple_companions(self):
        from services import cost_dashboard_service as dashboard

        breakdown = [
            {"operation": "companion_reflection", "request_count": 16, "fail_count": 2,
             "retry_count": 2, "estimated_cost_usd": 0.40},
        ]
        with patch.object(dashboard.usage_ledger, "get_operation_breakdown", return_value=breakdown), \
                patch.object(dashboard, "get_total_reflection_count", return_value=2), \
                patch.object(dashboard.usage_ledger, "get_month_summary",
                             return_value={"cost_is_estimate": False}):
            result = dashboard.get_cost_per_reflection(window_days=30)

        # 8 companions x 2 reflections = 16 calls; $0.40 total / 2 reflections = $0.20/reflection
        self.assertAlmostEqual(result["avg_cost_per_reflection_usd"], 0.20)
        self.assertEqual(result["companion_calls"], 16)


class UsageAlertDebounceTests(unittest.TestCase):
    def test_same_tier_does_not_send_a_second_email(self):
        from services import usage_alerts

        store = {}

        def fake_get(key, default=None):
            return store.get(key, default)

        def fake_set(key, value):
            store[key] = value

        with patch.object(usage_alerts.settings_store, "get_setting", side_effect=fake_get), \
                patch.object(usage_alerts.settings_store, "set_setting", side_effect=fake_set), \
                patch.object(usage_alerts.email_alert, "send_alert_email", return_value=True) as send:
            usage_alerts._maybe_alert("anthropic", "Claude", "yellow", ["detail"])
            usage_alerts._maybe_alert("anthropic", "Claude", "yellow", ["detail"])  # same tier again

        send.assert_called_once()

    def test_escalating_tier_sends_again(self):
        from services import usage_alerts

        store = {}
        with patch.object(usage_alerts.settings_store, "get_setting", side_effect=lambda k, default=None: store.get(k, default)), \
                patch.object(usage_alerts.settings_store, "set_setting", side_effect=lambda k, v: store.__setitem__(k, v)), \
                patch.object(usage_alerts.email_alert, "send_alert_email", return_value=True) as send:
            usage_alerts._maybe_alert("anthropic", "Claude", "yellow", ["detail"])
            usage_alerts._maybe_alert("anthropic", "Claude", "red", ["detail"])

        self.assertEqual(send.call_count, 2)

    def test_check_and_alert_never_raises_on_internal_failure(self):
        from services import usage_alerts

        with patch.object(usage_alerts.dashboard, "get_all_service_overviews", side_effect=Exception("boom")):
            try:
                usage_alerts.check_and_alert()
            except Exception as e:  # pragma: no cover
                self.fail(f"check_and_alert raised: {e!r}")


class NoSensitiveDataTests(unittest.TestCase):
    def test_service_usage_schema_has_no_content_columns(self):
        """Structural guard against ever adding a free-text content
        column to the ledger table."""
        import inspect
        from services import db_schema

        source = inspect.getsource(db_schema)
        table_start = source.index("CREATE TABLE IF NOT EXISTS service_usage")
        table_def = source[table_start:table_start + 1200]
        for forbidden in ["reflection_text", "case_content", "ai_response", "raw_text", "content TEXT"]:
            self.assertNotIn(forbidden, table_def)


class KnowledgeAssistantInstrumentationTests(unittest.TestCase):
    def test_knowledge_assistant_failure_records_usage_without_crashing(self):
        """Guards against a NameError/UnboundLocalError in the except
        branch (the started-at timer must be set before the try)."""
        from services import knowledge_assistant as ka

        with patch.object(ka, "retrieve_global_context", return_value=[]), \
                patch.object(ka, "build_research_summary", return_value={}), \
                patch.object(ka, "_build_stats_block", return_value="stats"), \
                patch.object(ka.client.messages, "create", side_effect=RuntimeError("down")), \
                patch.object(ka, "usage_ledger") as fake_ledger, \
                patch.object(ka, "log_error", return_value=(1, 2)):
            result = ka.ask("a real question", lang="English")

        self.assertEqual(result["error"], "API call failed")
        fake_ledger.record_usage.assert_called_once()
        self.assertFalse(fake_ledger.record_usage.call_args.kwargs["success"])

    def test_knowledge_assistant_success_records_actual_tokens(self):
        from services import knowledge_assistant as ka

        message = MagicMock()
        message.usage.input_tokens = 555
        message.usage.output_tokens = 111
        block = MagicMock()
        block.type = "text"
        block.text = '{"answer": "ok", "confidence": "strong", "limitations": "", "evidence": []}'
        message.content = [block]

        with patch.object(ka, "retrieve_global_context", return_value=[]), \
                patch.object(ka, "build_research_summary", return_value={}), \
                patch.object(ka, "_build_stats_block", return_value="stats"), \
                patch.object(ka.client.messages, "create", return_value=message), \
                patch.object(ka, "usage_ledger") as fake_ledger:
            ka.ask("a real question", lang="English")

        fake_ledger.record_usage.assert_called_once()
        kwargs = fake_ledger.record_usage.call_args.kwargs
        self.assertEqual(kwargs["input_tokens"], 555)
        self.assertEqual(kwargs["output_tokens"], 111)
        self.assertTrue(kwargs["success"])


if __name__ == "__main__":
    unittest.main()
