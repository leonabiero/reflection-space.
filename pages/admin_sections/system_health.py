"""System Administration -- Section 5: System Health.

Extracted unchanged from the original system_administration.py file.
"""
import pandas as pd
import streamlit as st

from config import ANTHROPIC_API_KEY
from services.qdrant_service import get_diagnostics
from services.embedding_service import is_available as embeddings_available
from pages.admin_sections._shared import status_badge, check_database

def render(T):
    with st.expander(T["admin_health_header"]):
        db_ok, db_error = check_database()
        q_diag = get_diagnostics()
        qdrant_ok = bool(q_diag.get("connected"))
        embed_ok = embeddings_available()
        reflection_ok = bool(ANTHROPIC_API_KEY)
        retrieval_ok = qdrant_ok and embed_ok  # falls back gracefully if not

        if not db_ok or not reflection_ok:
            overall = T["admin_health_critical"]
        elif not retrieval_ok:
            overall = T["admin_health_degraded"]
        else:
            overall = T["admin_health_healthy"]

        st.markdown(T["admin_health_overall"])
        st.markdown(f"### {overall}")

        st.markdown(T["admin_health_components"])
        component_rows = [
            {T["admin_health_component_col"]: T["admin_health_component_database"], T["admin_health_status_col"]: status_badge(db_ok, T, "admin_health_healthy_label", "admin_health_unreachable_label")},
            {T["admin_health_component_col"]: T["admin_health_component_qdrant"], T["admin_health_status_col"]: status_badge(qdrant_ok, T, "admin_status_connected", "admin_status_not_connected")},
            {T["admin_health_component_col"]: T["admin_health_component_embedding"], T["admin_health_status_col"]: status_badge(embed_ok, T, "admin_health_available_label", "admin_health_not_configured_label")},
            {T["admin_health_component_col"]: T["admin_health_component_retrieval"], T["admin_health_status_col"]: T["admin_health_operational_label"] if retrieval_ok else T["admin_health_fallback_label"]},
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
                    "qdrant_diagnostics": q_diag,
                    "embeddings_available": embed_ok,
                    "reflection_engine_configured": reflection_ok,
                })
