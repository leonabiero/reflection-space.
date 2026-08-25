"""System Administration -- Section 4: RAG Status.

Extracted unchanged from the original system_administration.py file.
"""
import pandas as pd
import streamlit as st

from services.qdrant_service import get_diagnostics
from pages.admin_sections._shared import status_badge, bool_badge

def render(T):
    with st.expander(T["admin_rag_status_header"]):
        diagnostics = get_diagnostics()

        if diagnostics.get("error"):
            st.error(f"⚠️ {diagnostics['error']}")
        else:
            st.success(T["admin_rag_status_ok"])

        status_rows = [
            {"Item": T["admin_rag_qdrant_connection"], "Status": status_badge(diagnostics.get("connected"), T)},
            {"Item": T["admin_rag_collection"], "Status": diagnostics.get("collection_name") or "—"},
            {"Item": T["admin_rag_embedding_model"], "Status": diagnostics.get("embedding_model") or "—"},
            {"Item": T["admin_rag_embedding_dims"], "Status": str(diagnostics.get("embedding_dimensions") or "—")},
            {"Item": T["admin_rag_indexed_docs"], "Status": str(diagnostics.get("points_count")) if diagnostics.get("points_count") is not None else "—"},
            {"Item": T["admin_rag_case_ref_index"], "Status": bool_badge(diagnostics.get("case_ref_index_present"), T)},
            {"Item": T["admin_rag_doc_id_index"], "Status": bool_badge(diagnostics.get("document_id_index_present"), T)},
            {"Item": T["admin_rag_latest_doc_id"], "Status": str(diagnostics.get("latest_document_id")) if diagnostics.get("latest_document_id") is not None else "—"},
            {"Item": T["admin_rag_latest_case"], "Status": diagnostics.get("latest_case_ref") or "—"},
            {"Item": T["admin_rag_latest_doctype"], "Status": diagnostics.get("latest_doc_type") or "—"},
            {"Item": T["admin_rag_last_indexed"], "Status": (diagnostics.get("latest_completed_at") or "—")[:19]},
        ]
        st.table(pd.DataFrame(status_rows).set_index("Item"))

        with st.expander(T["admin_advanced_diagnostics"]):
            if st.checkbox(T["admin_show_raw_response"], key="admin_rag_status_raw_toggle"):
                st.json(diagnostics)
