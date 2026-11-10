"""System Administration -- Section 5: System Health.

November 2026: the Qdrant search service was removed (it served the old
document-based design), so its "connection" and "semantic retrieval"
rows are gone. Gemini embeddings are still listed: the pattern features
(Text analysis, Pattern Review) use them, and store their results in
PostgreSQL.
"""
import pandas as pd
import streamlit as st

from config import ANTHROPIC_API_KEY
from services.embedding_service import is_available as embeddings_available
from pages.admin_sections._shared import status_badge, check_database

def render(T):
    with st.expander(T["admin_health_header"]):
        db_ok, db_error = check_database()
        embed_ok = embeddings_available()
        reflection_ok = bool(ANTHROPIC_API_KEY)

        if not db_ok or not reflection_ok:
            overall = T["admin_health_critical"]
        elif not embed_ok:
            overall = T["admin_health_degraded"]
        else:
            overall = T["admin_health_healthy"]

        st.markdown(T["admin_health_overall"])
        st.markdown(f"### {overall}")

        st.markdown(T["admin_health_components"])
        component_rows = [
            {T["admin_health_component_col"]: T["admin_health_component_database"], T["admin_health_status_col"]: status_badge(db_ok, T, "admin_health_healthy_label", "admin_health_unreachable_label")},
            {T["admin_health_component_col"]: T["admin_health_component_embedding"], T["admin_health_status_col"]: status_badge(embed_ok, T, "admin_health_available_label", "admin_health_not_configured_label")},
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
                    "embeddings_available": embed_ok,
                    "reflection_engine_configured": reflection_ok,
                })
