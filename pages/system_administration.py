import time
import psycopg2
import pandas as pd
import streamlit as st

from services.language import init_language
from navigation.router import render_nav
from services.identity import init_identity, render_identity_footer
from services.qdrant_service import get_diagnostics, is_available as qdrant_available, upsert_document
from services.embedding_service import is_available as embeddings_available
from services.draft_storage import get_completed_drafts
from services.anonymizer import anonymize
from config import EMBEDDING_MODEL, EMBEDDING_DIMENSIONS, DATABASE_URL, ANTHROPIC_API_KEY, QDRANT_COLLECTION_NAME
from rdi.retrieval_service import retrieve_historical_context, retrieve_global_context
from rdi.context_engine import DEFAULT_HISTORY_LIMIT

# =============================================================================
# System Administration -- Admin Console
# =============================================================================
#
# This page is presentation-only. Every value shown here comes from
# services that already existed (services.qdrant_service,
# services.embedding_service, services.draft_storage,
# rdi.retrieval_service, config) -- nothing here makes a NEW call to
# Voyage AI or the Anthropic (Claude) API. The Retrieval Test panel
# calls rdi.retrieval_service.retrieve_historical_context() (case-
# specific mode) or rdi.retrieval_service.retrieve_global_context()
# (global mode, added alongside the optional Case Reference field) --
# both only ever call Voyage AI (embeddings) for the query text and
# Qdrant for the search; neither calls the Claude/Anthropic API at all.
# So this redesign, and the global-mode addition, have ZERO impact on
# Anthropic API cost -- see the docstring on the Retrieval Test section
# below for the one-line cost note kept alongside that button for
# transparency.
#
# Everything below only changes HOW existing data is displayed
# (tables/cards/badges instead of raw st.json(...)) -- it does not
# change what is retrieved, indexed, or computed, except for the
# Retrieval Test's new global mode, which is scoped narrowly and
# explained in that section's own comments below.


T = init_language()
init_identity(T)
render_nav(T)
render_identity_footer(T)

if st.session_state.get("user_role") != "System Administrator":
    st.stop()

st.title(T["admin_title"])
st.caption(T["admin_header_caption"])

# --- shared badge/label helpers --------------------------------------------

MATCH_REASON_LABELS = {
    "must_include": T["admin_match_reasons"]["must_include"],
    "semantic": T["admin_match_reasons"]["semantic"],
    "recency": T["admin_match_reasons"]["recency"],
}


def _status_badge(ok, true_label=None, false_label=None):
    if true_label is None:
        true_label = T["admin_status_healthy"]
    if false_label is None:
        false_label = T["admin_status_unavailable"]
    return f"✅ {true_label}" if ok else f"❌ {false_label}"


def _bool_badge(ok):
    return f"✅ {T['admin_present']}" if ok else f"❌ {T['admin_missing']}"


def _check_database():
    """Cheap, best-effort connection check -- opens and immediately
    closes a connection. Does not run any query beyond the driver's
    own handshake."""
    if not DATABASE_URL:
        return False, "DATABASE_URL is not configured."
    try:
        conn = psycopg2.connect(DATABASE_URL)
        conn.close()
        return True, None
    except Exception as e:
        return False, str(e)


# =============================================================================
# 1. User Management (unchanged)
# =============================================================================
with st.expander(T["admin_management_title"], expanded=True):
    st.info(T["admin_management_info"])
    users = dict(st.secrets.get("users", {}))
    if users:
        rows = []
        for username, info in users.items():
            rows.append({
                T["admin_username_col"]: username,
                T["admin_name_col"]: info.get("name", ""),
                T["admin_role_col"]: info.get("role", ""),
            })
        st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)
    else:
        st.warning(T["admin_no_users_warning"])

# =============================================================================
# 2. Document Indexing (unchanged -- backfill utility)
# =============================================================================
with st.expander(T["admin_doc_indexing_title"]):
    st.caption(T["admin_doc_indexing_caption"])
    st.caption(T["admin_cost_note_backfill"])
    if not qdrant_available():
        st.warning(T["admin_qdrant_not_configured"])
    elif st.button(T["admin_run_backfill_button"], type="primary"):
        rows = get_completed_drafts()
        indexed = 0
        progress = st.progress(0)
        for i, row in enumerate(rows):
            draft_id, case_ref, doc_type, content, created_at, created_by, created_by_role, was_edited, completed_at = row
            if upsert_document(draft_id, case_ref, doc_type, content=content, language="", created_at=created_at, completed_at=completed_at, created_by_role=created_by_role, was_edited=was_edited):
                indexed += 1
            progress.progress((i + 1) / len(rows) if rows else 1.0)
        st.success(T["admin_indexed_success"].format(indexed=indexed, total=len(rows)))

# =============================================================================
# 3. Retrieval Test
# =============================================================================
with st.expander(T["admin_retrieval_test_title"]):
    st.caption(T["admin_retrieval_test_caption"])
    st.caption(T["admin_cost_note_retrieval"])

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
    #   deliberate, admin-only exception to the app's per-case
    #   confidentiality boundary (see services/qdrant_service.py's
    #   search_global() docstring) -- results can include documents from
    #   any client's case, shown side by side, so an administrator can
    #   validate the RAG system as a whole rather than only one case at a
    #   time. This mode is only reachable from this page, gated to
    #   System Administrator above.
    case_ref = st.text_input(T["admin_case_ref_placeholder"], key="admin_retrieval_case_ref")
    query = st.text_area(T["admin_query_placeholder"], key="admin_retrieval_query")

    is_global_mode = not (case_ref or "").strip()

    if st.button(T["admin_run_retrieval_button"], type="primary"):
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

        st.markdown(f"#### {T['admin_retrieval_summary']}")
        summary_rows = [
            {"Item": T["admin_retrieval_status"], "Value": T["admin_retrieval_success"] if result["success"] else T["admin_retrieval_failed"]},
            {"Item": T["admin_retrieval_mode"], "Value": mode_label},
            {"Item": T["admin_search_time"], "Value": f"{result['elapsed']:.2f} seconds"},
            {"Item": T["admin_query_label"], "Value": result["query"] or "—"},
            {"Item": T["admin_docs_returned"], "Value": str(len(result["docs"]))},
            {"Item": T["admin_embedding_model"], "Value": EMBEDDING_MODEL},
        ]
        st.table(pd.DataFrame(summary_rows).set_index("Item"))

        if was_global:
            st.caption(T["admin_global_mode_notice"])

        if not result["success"]:
            st.error(T["admin_retrieval_failed_msg"].format(error=result['error']))
        elif result["docs"]:
            st.markdown(f"#### {T['admin_retrieved_documents']}")
            doc_rows = []
            for rank, d in enumerate(result["docs"], start=1):
                reasons = d.get("match_reasons") or ([d.get("match_reason")] if d.get("match_reason") else [])
                reason_label = " + ".join(MATCH_REASON_LABELS.get(r, r) for r in reasons) if reasons else "—"
                score = d.get("score")
                row_dict = {
                    T["admin_rank"]: rank,
                    T["admin_doc_type"]: d.get("doc_type", ""),
                    T["admin_retrieval_reason"]: reason_label,
                    T["admin_similarity"]: f"{score:.2f}" if score is not None else "—",
                }
                # Global mode can span cases, so show which case each
                # result belongs to. Case-specific mode already implies
                # the case (shown in Retrieval Mode above), so this
                # column is omitted there to avoid a redundant, always-
                # identical column.
                if was_global:
                    row_dict["Case Reference"] = d.get("case_ref") or "—"
                doc_rows.append(row_dict)
            st.dataframe(pd.DataFrame(doc_rows), hide_index=True, use_container_width=True)
        else:
            st.info(T["admin_no_docs_found"])

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

# =============================================================================
# 4. RAG Status (renamed from "RAG Diagnostics")
# =============================================================================
with st.expander(T["admin_rag_status_title"]):
    diagnostics = get_diagnostics()

    if diagnostics.get("error"):
        st.error(f"⚠️ {diagnostics['error']}")
    else:
        st.success(T["admin_rag_layer_reachable"])

    status_rows = [
        {"Item": T["admin_qdrant_connection"], "Status": _status_badge(diagnostics.get("connected"))},
        {"Item": T["admin_collection"], "Status": diagnostics.get("collection_name") or "—"},
        {"Item": T["admin_embedding_model"], "Status": diagnostics.get("embedding_model") or "—"},
        {"Item": T["admin_embedding_dimensions"], "Status": str(diagnostics.get("embedding_dimensions") or "—")},
        {"Item": T["admin_indexed_documents"], "Status": str(diagnostics.get("points_count")) if diagnostics.get("points_count") is not None else "—"},
        {"Item": T["admin_case_ref_index"], "Status": _bool_badge(diagnostics.get("case_ref_index_present"))},
        {"Item": T["admin_doc_id_index"], "Status": _bool_badge(diagnostics.get("document_id_index_present"))},
        {"Item": T["admin_latest_doc_id"], "Status": str(diagnostics.get("latest_document_id")) if diagnostics.get("latest_document_id") is not None else "—"},
        {"Item": T["admin_latest_case"], "Status": diagnostics.get("latest_case_ref") or "—"},
        {"Item": T["admin_latest_doc_type"], "Status": diagnostics.get("latest_doc_type") or "—"},
        {"Item": T["admin_last_indexed"], "Status": (diagnostics.get("latest_completed_at") or "—")[:19]},
    ]
    st.table(pd.DataFrame(status_rows).set_index("Item"))

    with st.expander(T["admin_advanced_diagnostics"]):
        if st.checkbox(T["admin_show_raw_response"], key="admin_rag_status_raw_toggle"):
            st.json(diagnostics)

# =============================================================================
# 5. System Health
# =============================================================================
with st.expander(T["admin_system_health"]):
    db_ok, db_error = _check_database()
    q_diag = get_diagnostics()
    qdrant_ok = bool(q_diag.get("connected"))
    embed_ok = embeddings_available()
    reflection_ok = bool(ANTHROPIC_API_KEY)
    retrieval_ok = qdrant_ok and embed_ok  # falls back gracefully if not

    if not db_ok or not reflection_ok:
        overall = "🔴 Critical"
    elif not retrieval_ok:
        overall = T["admin_fallback_mode"]
    else:
        overall = "🟢 Healthy"

    st.markdown(f"#### {T['admin_overall_status']}")
    st.markdown(f"### {overall}")

    st.markdown(f"#### {T['admin_components']}")
    component_rows = [
        {"Component": T["admin_component_db"], "Status": _status_badge(db_ok)},
        {"Component": T["admin_component_qdrant"], "Status": _status_badge(qdrant_ok)},
        {"Component": T["admin_component_embeddings"], "Status": _status_badge(embed_ok)},
        {"Component": T["admin_component_retrieval"], "Status": "✅ Operational" if retrieval_ok else T["admin_fallback_mode"]},
        {"Component": T["admin_component_reflection"], "Status": _status_badge(reflection_ok)},
    ]
    st.table(pd.DataFrame(component_rows).set_index("Component"))

    if not db_ok and db_error:
        st.error(f"Database error: {db_error}")
    if not reflection_ok:
        st.error(T["admin_reflection_key_missing"])

    with st.expander(T["admin_advanced_diagnostics"]):
        if st.checkbox(T["admin_show_raw_response"], key="admin_health_raw_toggle"):
            st.json({
                "database_ok": db_ok,
                "database_error": db_error,
                "qdrant_diagnostics": q_diag,
                "embeddings_available": embed_ok,
                "reflection_engine_configured": reflection_ok,
            })

# =============================================================================
# 6. Configuration
# =============================================================================
with st.expander(T["admin_configuration"]):
    st.markdown(f"""
- **{T['admin_embedding_model_label']}:** {EMBEDDING_MODEL}
- **{T['admin_embedding_dimensions_label']}:** {EMBEDDING_DIMENSIONS}
- **{T['admin_retrieval_limit']}:** {DEFAULT_HISTORY_LIMIT} documents
- **{T['admin_vector_db']}:** Qdrant
- **{T['admin_collection_label']}:** {QDRANT_COLLECTION_NAME}
""")

# =============================================================================
# 7. Administrative Tools (renamed from "Utilities")
# =============================================================================
with st.expander(T["admin_admin_tools"]):
    st.subheader(T["admin_anon_test_title"])
    st.caption(T["admin_anon_test_caption"])
    sample = st.text_area(T["admin_sample_text"], key="admin_anon_sample")
    if st.button(T["admin_run_anonymizer"]):
        st.code(anonymize(sample))

    st.divider()
    st.caption(T["admin_future_tools"])
