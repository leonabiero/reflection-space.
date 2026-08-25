"""System Administration -- Section 3: Retrieval Test.

Extracted unchanged from the original system_administration.py file.
"""
import time

import pandas as pd
import streamlit as st

from config import EMBEDDING_MODEL
from rdi.retrieval_service import retrieve_historical_context, retrieve_global_context
from pages.admin_sections._shared import reason_label

def render(T):
    with st.expander(T["admin_retrieval_test_header"]):
        st.caption(T["admin_retrieval_test_caption"])
        st.caption(T["admin_retrieval_test_cost"])

        # Case Reference is optional -- see the two modes below.
        #
        # - Case Reference filled in  -> CASE-SPECIFIC mode: calls
        #   rdi.retrieval_service.retrieve_historical_context(), exactly as
        #   before. Confidentiality-scoped: only ever returns documents from
        #   that one case (see services/qdrant_service.py's search_similar()).
        #
        # - Case Reference left blank -> GLOBAL mode: calls
        #   rdi.retrieval_service.retrieve_global_context(), which applies NO
        #   case filter and searches the entire Qdrant collection. This is a
        #   deliberate, intentional exception to the app's per-case
        #   confidentiality boundary (see services/qdrant_service.py's
        #   search_global() docstring) -- results can include documents from
        #   any client's case, shown side by side, so an administrator can
        #   validate the RAG system as a whole rather than only one case at a
        #   time. On this page, this mode is gated to System Administrator
        #   only (see the role check above). Organisation-wide retrieval is
        #   NOT unique to this page, though: the Knowledge Assistant on the
        #   Learning page (services/knowledge_assistant.py) intentionally
        #   reuses this same retrieve_global_context() path so Supervisors
        #   and Programme Managers can ask organisational questions that need
        #   evidence from across every case. See rdi/retrieval_service.py's
        #   retrieve_global_context() docstring for the full list of
        #   authorised call sites and the roles permitted to use each one.
        case_ref = st.text_input(T["admin_retrieval_case_label"], key="admin_retrieval_case_ref")
        query = st.text_area(T["admin_retrieval_query_label"], key="admin_retrieval_query")

        is_global_mode = not (case_ref or "").strip()

        if st.button(T["admin_retrieval_run_button"], type="primary"):
            success = True
            error_message = None
            docs = []
            elapsed = 0.0

            start = time.time()
            try:
                if is_global_mode:
                    docs = retrieve_global_context(query_text=query)
                else:
                    docs = retrieve_historical_context(case_ref, query_text=query)
            except Exception as e:
                success = False
                error_message = str(e)
            elapsed = time.time() - start

            st.session_state["admin_last_retrieval_result"] = {
                "success": success,
                "error": error_message,
                "elapsed": elapsed,
                "case_ref": case_ref,
                "query": query,
                "docs": docs,
                "is_global_mode": is_global_mode,
            }

        result = st.session_state.get("admin_last_retrieval_result")
        if result:
            was_global = result.get("is_global_mode", not (result.get("case_ref") or "").strip())
            mode_label = T["admin_retrieval_mode_global"] if was_global else T["admin_retrieval_mode_case"].format(case_ref=result['case_ref'])

            st.markdown(T["admin_retrieval_summary_header"])
            summary_rows = [
                {"Item": T["admin_retrieval_status_label"], "Value": T["admin_retrieval_status_success"] if result["success"] else T["admin_retrieval_status_failed"]},
                {"Item": T["admin_retrieval_mode_row_label"], "Value": mode_label},
                {"Item": T["admin_retrieval_time_label"], "Value": f"{result['elapsed']:.2f} s"},
                {"Item": T["admin_retrieval_query_row_label"], "Value": result["query"] or "—"},
                {"Item": T["admin_retrieval_docs_returned_label"], "Value": str(len(result["docs"]))},
                {"Item": T["admin_retrieval_embedding_model_label"], "Value": EMBEDDING_MODEL},
            ]
            st.table(pd.DataFrame(summary_rows).set_index("Item"))

            if was_global:
                st.caption(T["admin_retrieval_global_notice"])

            if not result["success"]:
                st.error(f"{T['admin_retrieval_failed_label']} {result['error']}")
            elif result["docs"]:
                st.markdown(T["admin_retrieval_documents_header"])
                doc_rows = []
                for rank, d in enumerate(result["docs"], start=1):
                    reasons = d.get("match_reasons") or ([d.get("match_reason")] if d.get("match_reason") else [])
                    reason_label = " + ".join(reason_label(r, T) for r in reasons) if reasons else "—"
                    score = d.get("score")
                    row_dict = {
                        T["admin_retrieval_col_rank"]: rank,
                        T["admin_retrieval_col_doctype"]: d.get("doc_type", ""),
                        T["admin_retrieval_col_reason"]: reason_label,
                        T["admin_retrieval_col_similarity"]: f"{score:.2f}" if score is not None else "—",
                    }
                    # Global mode can span cases, so show which case each
                    # result belongs to. Case-specific mode already implies
                    # the case (shown in Retrieval Mode above), so this
                    # column is omitted there to avoid a redundant, always-
                    # identical column.
                    if was_global:
                        row_dict[T["admin_retrieval_col_case"]] = d.get("case_ref") or "—"
                    doc_rows.append(row_dict)
                docs_table = pd.DataFrame(doc_rows)
                rank_col = T["admin_retrieval_col_rank"]
                if rank_col in docs_table.columns:
                    docs_table = docs_table.set_index(rank_col)
                st.table(docs_table)
            else:
                st.info(T["admin_retrieval_no_docs"])

            with st.expander(T["admin_advanced_diagnostics"]):
                if st.checkbox(T["admin_show_raw_response"], key="admin_retrieval_raw_toggle"):
                    st.json({
                        "success": result["success"],
                        "error": result["error"],
                        "retrieval_mode": "global" if was_global else "case_specific",
                        "search_time_seconds": round(result["elapsed"], 3),
                        "case_reference": result["case_ref"],
                        "query": result["query"],
                        "documents": result["docs"],
                    })
