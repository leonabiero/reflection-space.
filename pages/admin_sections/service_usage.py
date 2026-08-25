"""System Administration -- Section 10: Service Usage & Costs (Service Cost & Usage Monitor).

Extracted unchanged from the original system_administration.py file.
"""
import pandas as pd
import streamlit as st

from services import cost_dashboard_service as usage_dashboard
from services import usage_alerts

def render(T):
    with st.expander(T.get("admin_usage_header", "💰 Service Usage & Costs"), expanded=False):
        st.caption(T.get(
            "admin_usage_caption",
            "What each external service is costing this pilot, estimated from actual "
            "recorded API usage. Figures marked \"estimate\" could not be tied to an exact "
            "provider price and should be treated as approximate.",
        ))

        def _status_label(status):
            return {
                "green": T.get("admin_usage_status_green", "🟢 OK"),
                "yellow": T.get("admin_usage_status_yellow", "🟡 Approaching limit"),
                "orange": T.get("admin_usage_status_orange", "🟠 Near limit"),
                "red": T.get("admin_usage_status_red", "🔴 At/over limit"),
                "unknown": T.get("admin_usage_status_unknown", "⚪ Limit unavailable"),
            }.get(status, status)

        def _money(v):
            return f"${v:,.2f}" if v is not None else T.get("admin_usage_unavailable", "Unavailable")

        def _pct(v):
            return f"{v:.1f}%" if v is not None else T.get("admin_usage_limit_unavailable", "Limit unavailable")

        # Check thresholds and send any newly-crossed alert (debounced,
        # see services/usage_alerts.py) -- cheap, safe to run on every
        # load of this panel.
        try:
            usage_alerts.check_and_alert()
        except Exception:
            pass

        overviews = usage_dashboard.get_all_service_overviews()

        st.markdown(f"### {T.get('admin_usage_overview_header', 'Overview')}")
        overview_rows = []
        a = overviews["anthropic"]
        overview_rows.append({
            T.get("admin_usage_col_service", "Service"): a["service"],
            T.get("admin_usage_col_usage", "Usage (this month)"): f"{a['requests_month']} calls",
            T.get("admin_usage_col_limit", "Budget"): _money(a["budget_usd"]),
            T.get("admin_usage_col_pct", "% used"): _pct(a["budget_pct_used"]),
            T.get("admin_usage_col_cost", "Est. cost (month)"): _money(a["cost_month_usd"]),
            T.get("admin_usage_col_status", "Status"): _status_label(a["status"]),
        })
        g = overviews["gemini"]
        overview_rows.append({
            T.get("admin_usage_col_service", "Service"): g["service"],
            T.get("admin_usage_col_usage", "Usage (this month)"): f"{g['requests_month']} calls",
            T.get("admin_usage_col_limit", "Budget"): _money(g["budget_usd"]),
            T.get("admin_usage_col_pct", "% used"): _pct(g["budget_pct_used"]),
            T.get("admin_usage_col_cost", "Est. cost (month)"): _money(g["cost_month_usd"]),
            T.get("admin_usage_col_status", "Status"): _status_label(g["status"]),
        })
        q = overviews["qdrant"]
        q_usage = f"{q['points_count']} vectors" if q.get("points_count") is not None else T.get("admin_usage_unavailable", "Unavailable")
        q_limit = f"{q['capacity']} vectors" if q.get("capacity") is not None else T.get("admin_usage_limit_unavailable", "Limit unavailable")
        overview_rows.append({
            T.get("admin_usage_col_service", "Service"): q["service"],
            T.get("admin_usage_col_usage", "Usage (this month)"): q_usage,
            T.get("admin_usage_col_limit", "Budget"): q_limit,
            T.get("admin_usage_col_pct", "% used"): _pct(q["budget_pct_used"]),
            T.get("admin_usage_col_cost", "Est. cost (month)"): T.get("admin_usage_no_billing_api", "No billing API"),
            T.get("admin_usage_col_status", "Status"): _status_label(q["status"]),
        })
        p = overviews["postgres"]
        p_usage = f"{p['active_conn']} / {p['max_conn']} " + T.get("admin_usage_connections", "connections") if p.get("pool_created") else T.get("admin_usage_not_started", "Not started yet")
        overview_rows.append({
            T.get("admin_usage_col_service", "Service"): p["service"],
            T.get("admin_usage_col_usage", "Usage (this month)"): p_usage,
            T.get("admin_usage_col_limit", "Budget"): f"{p['max_conn']} " + T.get("admin_usage_connections", "connections"),
            T.get("admin_usage_col_pct", "% used"): _pct(p["budget_pct_used"]),
            T.get("admin_usage_col_cost", "Est. cost (month)"): T.get("admin_usage_provider_billing_unavailable", "Provider billing data unavailable"),
            T.get("admin_usage_col_status", "Status"): _status_label(p["status"]),
        })
        s = overviews["streamlit"]
        overview_rows.append({
            T.get("admin_usage_col_service", "Service"): s["service"],
            T.get("admin_usage_col_usage", "Usage (this month)"): (
                f"{s['active_sessions_recent']} " + T.get("admin_usage_active_users", "active users")
                if s.get("active_sessions_recent") is not None else T.get("admin_usage_unavailable", "Unavailable")
            ),
            T.get("admin_usage_col_limit", "Budget"): T.get("admin_usage_limit_unavailable", "Limit unavailable"),
            T.get("admin_usage_col_pct", "% used"): _pct(None),
            T.get("admin_usage_col_cost", "Est. cost (month)"): T.get("admin_usage_no_billing_api", "No billing API"),
            T.get("admin_usage_col_status", "Status"): _status_label(s["status"]),
        })
        m = overviews["smtp"]
        overview_rows.append({
            T.get("admin_usage_col_service", "Service"): m["service"],
            T.get("admin_usage_col_usage", "Usage (this month)"): f"{m['emails_sent_30d']} " + T.get("admin_usage_emails_sent", "emails sent"),
            T.get("admin_usage_col_limit", "Budget"): T.get("admin_usage_limit_unavailable", "Limit unavailable"),
            T.get("admin_usage_col_pct", "% used"): _pct(None),
            T.get("admin_usage_col_cost", "Est. cost (month)"): T.get("admin_usage_no_billing_api", "No billing API"),
            T.get("admin_usage_col_status", "Status"): _status_label(m["status"]),
        })
        st.table(pd.DataFrame(overview_rows).set_index(T.get("admin_usage_col_service", "Service")))

        if p.get("configured"):
            st.caption(f"ℹ️ {p['provider_billing_note']}")
        if s.get("note"):
            st.caption(f"ℹ️ {s['note']}")

        # --- Claude cost detail -------------------------------------------------
        st.markdown(f"### {T.get('admin_usage_claude_detail_header', 'Claude (Anthropic) detail')}")
        st.metric(T.get("admin_usage_cost_today", "Est. cost today"), _money(a["cost_today_usd"]))
        st.metric(T.get("admin_usage_cost_month", "Est. cost this month"), _money(a["cost_month_usd"]))
        st.metric(T.get("admin_usage_cost_projected", "Projected month-end cost"), _money(a["projected_month_usd"]))
        st.metric(T.get("admin_usage_input_tokens", "Input tokens (month)"), f"{a['input_tokens_month']:,}")
        st.metric(T.get("admin_usage_output_tokens", "Output tokens (month)"), f"{a['output_tokens_month']:,}")
        if a["cost_is_estimate"]:
            st.caption(T.get("admin_usage_model_unrecognized",
                              "⚠️ Some calls used a model not in the pricing table -- their cost is a fallback estimate."))
        if not a["configured"]:
            st.warning(T.get("admin_usage_anthropic_not_configured", "Anthropic API key is not configured."))

        # --- Cost per reflection (Phase 12) -------------------------------------
        st.markdown(f"### {T.get('admin_usage_per_reflection_header', 'Cost per successful reflection')}")
        cpr = usage_dashboard.get_cost_per_reflection(window_days=30)
        if cpr["note"]:
            st.info(cpr["note"])
        else:
            st.metric(T.get("admin_usage_avg_cost_reflection", "Average Claude cost per reflection"),
                       _money(cpr["avg_cost_per_reflection_usd"]))
            st.metric(T.get("admin_usage_reflections_generated", "Reflections generated (30 days)"),
                       cpr["reflections_generated"])
            st.metric(T.get("admin_usage_companion_calls", "Companion calls (30 days, incl. retries)"),
                       cpr["companion_calls"])
            if cpr["retry_rate_pct"] is not None:
                st.metric(T.get("admin_usage_retry_rate", "Retry rate"), f"{cpr['retry_rate_pct']:.1f}%")
        st.caption(T.get("admin_usage_no_median_note",
                          "A median isn't available: individual companion calls aren't currently "
                          "tagged with which reflection they belong to, so only the overall average "
                          "can be computed."))

        # --- Gemini embeddings detail -------------------------------------------
        st.markdown(f"### {T.get('admin_usage_gemini_detail_header', 'Gemini Embeddings detail')}")
        st.metric(T.get("admin_usage_cost_month", "Est. cost this month"), _money(g["cost_month_usd"]))
        st.metric(T.get("admin_usage_embeddings_month", "Embeddings this month"), g["requests_month"])
        st.metric(T.get("admin_usage_embeddings_failed", "Failed embedding requests (month)"), g["fail_count_month"])
        if g["cost_is_estimate"] and g["requests_month"]:
            st.caption(T.get("admin_usage_gemini_estimate_note",
                              "⚠️ Some embedding calls did not return an exact token count from the "
                              "provider; their cost is marked as an estimate."))
        if not g["configured"]:
            st.warning(T.get("admin_usage_gemini_not_configured", "Gemini API key is not configured."))

        # --- Qdrant detail --------------------------------------------------------
        st.markdown(f"### {T.get('admin_usage_qdrant_detail_header', 'Qdrant detail')}")
        st.metric(T.get("admin_usage_qdrant_vectors", "Vectors stored"), q.get("points_count") if q.get("points_count") is not None else "—")
        st.metric(T.get("admin_usage_qdrant_capacity", "Configured capacity"), q.get("capacity") if q.get("capacity") is not None else T.get("admin_usage_limit_unavailable", "Limit unavailable"))
        if q.get("dimension_mismatch"):
            st.error(f"⚠️ {q['dimension_mismatch']}")
        if q.get("error"):
            st.warning(q["error"])

        # --- Alerts / budgets configuration note ----------------------------------
        with st.expander(T.get("admin_usage_pricing_header", "Pricing & budget configuration"), expanded=False):
            st.caption(T.get(
                "admin_usage_pricing_caption",
                "Provider prices are centralized in one place (services/cost_pricing.py) so "
                "they never have to be hunted down across the codebase when a provider changes "
                "its rates. Monthly budgets used for the status colours above are configured "
                "in config.py (MONTHLY_BUDGET_ANTHROPIC_USD, MONTHLY_BUDGET_GEMINI_USD).",
            ))
            pricing_rows = usage_dashboard.get_pricing_table()
            st.table(pd.DataFrame(pricing_rows).set_index("provider"))

        # --- Phase 13: user-volume scenario forecast -------------------------------
        st.markdown(f"### {T.get('admin_usage_forecast_header', 'User volume forecast (estimate)')}")
        st.caption(T.get(
            "admin_usage_forecast_caption",
            "Projects monthly cost at a hypothetical number of users, based on this pilot's "
            "own measured average cost per reflection. Adjust the numbers below.",
        ))
        forecast_users = st.number_input(
            T.get("admin_usage_forecast_users", "Number of users"),
            min_value=0, value=100, step=50, key="admin_usage_forecast_users",
        )
        forecast_reflections = st.number_input(
            T.get("admin_usage_forecast_reflections", "Reflections per user per month"),
            min_value=0, value=4, step=1, key="admin_usage_forecast_reflections",
        )
        forecast = usage_dashboard.forecast_scenario(int(forecast_users), int(forecast_reflections))
        st.metric(T.get("admin_usage_forecast_total_reflections", "Total reflections/month"),
                   forecast["total_reflections_per_month"])
        st.metric(T.get("admin_usage_forecast_claude_cost", "Projected Claude cost/month"),
                   _money(forecast["projected_claude_cost_usd"]))
        st.metric(T.get("admin_usage_forecast_gemini_cost", "Projected Gemini cost/month"),
                   _money(forecast["projected_gemini_cost_usd"]))
        if forecast.get("projected_vector_count") is not None:
            st.metric(T.get("admin_usage_forecast_vectors", "Projected vector count"),
                       forecast["projected_vector_count"])
        st.caption(f"ℹ️ {forecast['basis_note']}")

        # --- Preset scenario table --------------------------------------------------
        st.markdown(f"#### {T.get('admin_usage_forecast_presets_header', 'Common scenarios')}")
        preset_rows = []
        for preset_users in [0, 100, 250, 500, 1000]:
            label = T.get("admin_usage_forecast_current", "Current") if preset_users == 0 else str(preset_users)
            if preset_users == 0:
                fc = usage_dashboard.get_cost_per_reflection(window_days=30)
                claude_cost = fc["companion_cost_usd"]
                refl = fc["reflections_generated"]
            else:
                fc = usage_dashboard.forecast_scenario(preset_users, int(forecast_reflections))
                claude_cost = fc["projected_claude_cost_usd"]
                refl = fc["total_reflections_per_month"]
            preset_rows.append({
                T.get("admin_usage_forecast_col_users", "Users"): label,
                T.get("admin_usage_forecast_col_reflections", "Reflections/month"): refl,
                T.get("admin_usage_forecast_col_claude_cost", "Est. Claude cost/month"): _money(claude_cost),
            })
        st.table(pd.DataFrame(preset_rows).set_index(T.get("admin_usage_forecast_col_users", "Users")))
        st.caption(T.get("admin_usage_forecast_estimate_disclaimer",
                          "⚠️ All projections above are ESTIMATES based on currently observed "
                          "averages, not guaranteed costs."))
