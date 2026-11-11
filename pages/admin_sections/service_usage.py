"""System Administration -- Service Usage & Costs (Service Cost & Usage Monitor).

November 2026 simplification (product owner's decision): the screen now
shows only the overview table (one row per external service: usage,
budget, % used, estimated cost, status) and its two informational
notes. The detailed breakdowns that used to sit below it -- Claude
cost detail, cost-per-reflection, Gemini embeddings detail, the pricing
table, and the user-volume forecast with its preset scenarios -- were
removed as more detail than the pilot needs here. The underlying
calculations (services/cost_dashboard_service.py) are unchanged and
still covered by tests, so a fuller view could be brought back later
without losing anything.
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
