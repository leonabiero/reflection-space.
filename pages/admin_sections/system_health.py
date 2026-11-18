"""System Administration -- Section 5: System Health.

November 2026: the Qdrant search service was removed (it served the old
document-based design), so its "connection" and "semantic retrieval"
rows are gone. 18 November 2026: Google Gemini was removed too (no text
had been sent to it since 15 November), so its row is gone and the two
components shown are the database and the reflection engine (Claude).
"""
import pandas as pd
import streamlit as st

from config import ANTHROPIC_API_KEY
from pages.admin_sections._shared import status_badge, check_database

def render(T):
    with st.expander(T["admin_health_header"]):
        db_ok, db_error = check_database()
        reflection_ok = bool(ANTHROPIC_API_KEY)

        if not db_ok or not reflection_ok:
            overall = T["admin_health_critical"]
        else:
            overall = T["admin_health_healthy"]

        st.markdown(T["admin_health_overall"])
        st.markdown(f"### {overall}")

        st.markdown(T["admin_health_components"])
        component_rows = [
            {T["admin_health_component_col"]: T["admin_health_component_database"], T["admin_health_status_col"]: status_badge(db_ok, T, "admin_health_healthy_label", "admin_health_unreachable_label")},
            {T["admin_health_component_col"]: T["admin_health_component_reflection"], T["admin_health_status_col"]: status_badge(reflection_ok, T, "admin_health_operational_label", "admin_health_not_configured_label")},
        ]
        st.table(pd.DataFrame(component_rows).set_index(T["admin_health_component_col"]))

        if not db_ok and db_error:
            st.error(f"{T['admin_health_db_error_prefix']} {db_error}")
        if not reflection_ok:
            st.error(T["admin_health_key_missing"])

        with st.expander(T["admin_advanced_diagnostics"]):
            if st.checkbox(T["admin_show_raw_response"], key="admin_health_raw_toggle"):
                st.json({
                    "database_ok": db_ok,
                    "database_error": db_error,
                    "reflection_engine_configured": reflection_ok,
                })
