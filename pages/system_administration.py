import time
import base64
import psycopg2
import pandas as pd
import streamlit as st

from services.language import init_language
from navigation.router import render_nav
from services.identity import init_identity, render_identity_footer, require_work_mode
from services.qdrant_service import get_diagnostics, is_available as qdrant_available, upsert_document
from services.embedding_service import is_available as embeddings_available
from services.draft_storage import get_completed_drafts
from services.anonymizer import anonymize
from services.error_log import (
    get_recent_errors,
    build_ai_prompt,
    error_boundary,
    update_error_status,
    update_issue_status,
    parse_diagnostic_package,
    compute_ai_readiness,
    group_errors_by_signature,
)
from services import case_knowledge
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
# So this page has ZERO impact on Anthropic API cost.
#
# Sprint 12 translation audit
# -------------------------------
# Every user-facing string on this page now goes through the existing
# central language service (services/language.py, key T) -- no second
# translation table was created. See the "admin_*" / "admin_rag_*" /
# "admin_health_*" / "admin_retrieval_*" keys added there.

T = init_language()
init_identity(T)
require_work_mode(T, "System Administration")
render_nav(T, page_name="system_administration")
render_identity_footer(T)

if st.session_state.get("user_role") != "System Administrator":
    st.stop()

with error_boundary(
    "system_administration",
    T=T,
    user_name=st.session_state.get("user_name", ""),
    user_role=st.session_state.get("user_role", ""),
):
    st.title(T.get("nav_system_admin", "🛠️ System Administration"))
    st.caption("Administration console for Reflection Space -- system status, indexing, and diagnostic tools.")

    # --- shared badge/label helpers --------------------------------------------

    MATCH_REASON_LABEL_KEYS = {
        "must_include": "why_reason_must_include_generic",
        "semantic": "why_reason_semantic_generic",
        "recency": "why_reason_recency",
    }
    MATCH_REASON_ICONS = {
        "must_include": "📌",
        "semantic": "🔎",
        "recency": "🕒",
    }


    def _reason_label(reason):
        icon = MATCH_REASON_ICONS.get(reason, "")
        text = T.get(MATCH_REASON_LABEL_KEYS.get(reason, ""), reason)
        return f"{icon} {text}".strip()


    def _status_badge(ok, true_key="admin_status_connected", false_key="admin_status_not_connected"):
        return f"✅ {T[true_key]}" if ok else f"❌ {T[false_key]}"


    def _bool_badge(ok):
        return T["admin_status_present"] if ok else T["admin_status_missing"]


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
    # 1. User Management
    # =============================================================================
    with st.expander(T["admin_user_mgmt_header"], expanded=True):
        st.info(T["admin_user_mgmt_info"])
        users = dict(st.secrets.get("users", {}))
        if users:
            rows = []
            for username, info in users.items():
                rows.append({
                    T["admin_user_col_username"]: username,
                    T["admin_user_col_name"]: info.get("name", ""),
                    T["admin_user_col_role"]: T.get("role_labels", {}).get(info.get("role", ""), info.get("role", "")),
                })
            st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)
        else:
            st.warning(T["admin_user_mgmt_empty"])

    # =============================================================================
    # 2. Document Indexing (backfill utility)
    # =============================================================================
    with st.expander(T["admin_doc_indexing_header"]):
        st.caption(T["admin_doc_indexing_caption"])
        st.caption(T["admin_doc_indexing_cost"])
        if not qdrant_available():
            st.warning(T["admin_doc_indexing_unavailable"])
        elif st.button(T["admin_doc_indexing_button"], type="primary"):
            rows = get_completed_drafts()
            indexed = 0
            progress = st.progress(0)
            for i, row in enumerate(rows):
                draft_id, case_ref, doc_type, content, created_at, created_by, created_by_role, was_edited, completed_at = row
                if upsert_document(draft_id, case_ref, doc_type, content=content, language="", created_at=created_at, completed_at=completed_at, created_by_role=created_by_role, was_edited=was_edited):
                    indexed += 1
                progress.progress((i + 1) / len(rows) if rows else 1.0)
            st.success(T["admin_doc_indexing_success"].format(indexed=indexed, total=len(rows)))

    # =============================================================================
    # 3. Retrieval Test
    # =============================================================================
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
                    reason_label = " + ".join(_reason_label(r) for r in reasons) if reasons else "—"
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
                st.dataframe(pd.DataFrame(doc_rows), hide_index=True, use_container_width=True)
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

    # =============================================================================
    # 4. RAG Status
    # =============================================================================
    with st.expander(T["admin_rag_status_header"]):
        diagnostics = get_diagnostics()

        if diagnostics.get("error"):
            st.error(f"⚠️ {diagnostics['error']}")
        else:
            st.success(T["admin_rag_status_ok"])

        status_rows = [
            {"Item": T["admin_rag_qdrant_connection"], "Status": _status_badge(diagnostics.get("connected"))},
            {"Item": T["admin_rag_collection"], "Status": diagnostics.get("collection_name") or "—"},
            {"Item": T["admin_rag_embedding_model"], "Status": diagnostics.get("embedding_model") or "—"},
            {"Item": T["admin_rag_embedding_dims"], "Status": str(diagnostics.get("embedding_dimensions") or "—")},
            {"Item": T["admin_rag_indexed_docs"], "Status": str(diagnostics.get("points_count")) if diagnostics.get("points_count") is not None else "—"},
            {"Item": T["admin_rag_case_ref_index"], "Status": _bool_badge(diagnostics.get("case_ref_index_present"))},
            {"Item": T["admin_rag_doc_id_index"], "Status": _bool_badge(diagnostics.get("document_id_index_present"))},
            {"Item": T["admin_rag_latest_doc_id"], "Status": str(diagnostics.get("latest_document_id")) if diagnostics.get("latest_document_id") is not None else "—"},
            {"Item": T["admin_rag_latest_case"], "Status": diagnostics.get("latest_case_ref") or "—"},
            {"Item": T["admin_rag_latest_doctype"], "Status": diagnostics.get("latest_doc_type") or "—"},
            {"Item": T["admin_rag_last_indexed"], "Status": (diagnostics.get("latest_completed_at") or "—")[:19]},
        ]
        st.table(pd.DataFrame(status_rows).set_index("Item"))

        with st.expander(T["admin_advanced_diagnostics"]):
            if st.checkbox(T["admin_show_raw_response"], key="admin_rag_status_raw_toggle"):
                st.json(diagnostics)

    # =============================================================================
    # 5. System Health
    # =============================================================================
    with st.expander(T["admin_health_header"]):
        db_ok, db_error = _check_database()
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
            {T["admin_health_component_col"]: T["admin_health_component_database"], T["admin_health_status_col"]: _status_badge(db_ok, "admin_health_healthy_label", "admin_health_unreachable_label")},
            {T["admin_health_component_col"]: T["admin_health_component_qdrant"], T["admin_health_status_col"]: _status_badge(qdrant_ok, "admin_status_connected", "admin_status_not_connected")},
            {T["admin_health_component_col"]: T["admin_health_component_embedding"], T["admin_health_status_col"]: _status_badge(embed_ok, "admin_health_available_label", "admin_health_not_configured_label")},
            {T["admin_health_component_col"]: T["admin_health_component_retrieval"], T["admin_health_status_col"]: T["admin_health_operational_label"] if retrieval_ok else T["admin_health_fallback_label"]},
            {T["admin_health_component_col"]: T["admin_health_component_reflection"], T["admin_health_status_col"]: _status_badge(reflection_ok, "admin_health_operational_label", "admin_health_not_configured_label")},
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

    # =============================================================================
    # 6. Configuration
    # =============================================================================
    with st.expander(T["admin_config_header"]):
        st.markdown(f"""
- **{T['admin_rag_embedding_model']}:** {EMBEDDING_MODEL}
- **{T['admin_rag_embedding_dims']}:** {EMBEDDING_DIMENSIONS}
- **{T.get('historical_docs_used_label', 'Retrieval limit')}:** {DEFAULT_HISTORY_LIMIT}
- **{T['admin_rag_collection']}:** {QDRANT_COLLECTION_NAME}
    """)

    # =============================================================================
    # 7. Administrative Tools
    # =============================================================================
    with st.expander(T["admin_tools_header"]):
        st.subheader(T["admin_tools_anon_test_header"])
        st.caption(T["admin_anon_caption"])
        sample = st.text_area(T["admin_sample_label"], key="admin_anon_sample")
        if st.button(T["admin_run_button"]):
            st.code(anonymize(sample))

        st.divider()
        st.caption(T["admin_tools_future"])

    # =============================================================================
    # 8. Error Log -> AI Diagnostic Centre (Phase 2)
    # =============================================================================
    # Phase 1 (services/diagnostics.py) already builds a complete AI
    # Diagnostic Package behind the scenes for every error_log row
    # (see services/error_log.py:log_error). Phase 2 does NOT re-collect
    # any of that evidence -- it only DISPLAYS the Diagnostic Package
    # that already exists, plus a small, honest completeness score
    # ("AI Readiness Score" -- NOT an AI judgement, just a count of
    # which evidence categories are present) and a manual status field
    # (New / Investigating / Fixed / Closed) so Leon can track what
    # he's already looked at.
    #
    # Records logged BEFORE the Phase 1 Diagnostic Engine existed have
    # no diagnostic_package -- parse_diagnostic_package() (see
    # services/error_log.py) returns None for those, and every section
    # below falls back gracefully to the older, plainer fields already
    # stored directly on the error_log row (message / traceback /
    # context), exactly as the page displayed them before this phase.

    def _issue_status_badge(status):
        colors = {
            "New": "#e67e22",
            "Investigating": "#2980b9",
            "Fixed": "#27ae60",
            "Closed": "#7f8c8d",
            # Phase 4 (reopening): a previously Fixed/Closed issue that
            # has just recurred -- deliberately distinct from "New" so
            # it's immediately clear this came back, not a fresh bug.
            "Recurred": "#8e44ad",
        }
        color = colors.get(status, "#7f8c8d")
        return (
            f'<span style="background-color:{color};color:white;padding:2px 10px;'
            f'border-radius:10px;font-size:0.78rem;font-weight:600;">{status}</span>'
        )

    def _readiness_badge(score):
        if score >= 80:
            color = "#27ae60"
        elif score >= 50:
            color = "#e67e22"
        else:
            color = "#c0392b"
        return (
            f'<span style="background-color:{color};color:white;padding:2px 10px;'
            f'border-radius:10px;font-size:0.78rem;font-weight:600;">'
            f'{T.get("admin_error_log_readiness_label", "AI Readiness")}: {score}%</span>'
        )

    # NOTE: an earlier version of this page used a hand-rolled HTML/JS
    # button here (navigator.clipboard.writeText(...) via st.markdown
    # unsafe_allow_html) to copy the AI prompt. That approach turned
    # out to be unreliable in practice (it depends on the browser
    # treating a raw injected <button onclick=...> exactly like a
    # normal click-triggered script, which isn't guaranteed, and one
    # bug in it was already fixed once). It's been removed entirely in
    # favor of st.code() below, which Streamlit gives a native,
    # built-in copy icon for -- no custom JavaScript involved, so it
    # can't break the same way.

    with st.expander(T.get("admin_error_log_header", "🩺 AI Diagnostic Centre"), expanded=False):
        st.caption(T.get(
            "admin_error_log_caption",
            "Every problem recorded in the app -- crashes, failed AI companion calls, or "
            "problems people reported -- shown as a full diagnostic workspace: what happened, "
            "how serious it is, and a ready-made prompt you can copy straight into a chat with "
            "Claude to get it diagnosed and fixed.",
        ))

        errors = get_recent_errors(limit=50)

        if not errors:
            st.success(T.get("admin_error_log_empty", "No errors recorded. Everything looks clean."))
        else:
            issues = group_errors_by_signature(errors)

            # --- Filters (keeps the log searchable; extended for the
            # richer information Phase 2 adds) ---------------------------
            search_term = st.text_input(
                T.get("admin_error_log_search_label", "🔍 Search (page, error type, or message)"),
                key="admin_error_log_search",
            )
            status_filter = st.selectbox(
                T.get("admin_error_log_status_filter_label", "Filter by status"),
                options=["All", "New", "Investigating", "Recurred", "Fixed", "Closed"],
                key="admin_error_log_status_filter",
            )
            severity_filter = st.selectbox(
                T.get("admin_error_log_severity_filter_label", "Filter by severity"),
                options=["All", "error", "warning", "user_reported"],
                key="admin_error_log_severity_filter",
            )

            def _normalize_ref_text(text):
                # Keeps only letters/digits, lowercased -- so "REF-000124",
                # "ref 000124", and "REF000124" all normalize the same way.
                return "".join(ch for ch in str(text or "").lower() if ch.isalnum())

            def _ref_candidates(issue):
                # Same reference number shown on screen for this issue
                # (see display_ref below, in the render loop) -- computed
                # here too so search matches exactly what the admin sees.
                latest = issue["latest"]
                ref_num = issue.get("issue_id")
                if ref_num is None:
                    ref_num = latest.get("id")
                if ref_num is None:
                    return ""
                # Zero-padded to 6 digits so a partial search like "124"
                # still matches "REF-000124" (it's a substring of the
                # padded form). Both the padded and plain form are
                # included so "ref124" (no padding) also matches.
                if isinstance(ref_num, int):
                    return _normalize_ref_text(f"ref{ref_num:06d}ref{ref_num}")
                return _normalize_ref_text(f"ref{ref_num}")

            def _matches_filters(issue):
                latest = issue["latest"]
                current_status = latest.get("status") or "New"
                if status_filter != "All" and current_status != status_filter:
                    return False
                if severity_filter != "All" and latest.get("severity") != severity_filter:
                    return False
                if search_term:
                    haystack = " ".join(
                        str(latest.get(f) or "") for f in ("page", "error_type", "message")
                    ).lower()
                    term_matches_haystack = search_term.lower() in haystack
                    # Additional field: Reference Number (e.g. "REF-000124",
                    # "000124", or "124" all match) -- purely additive, does
                    # not change how the existing fields above are matched.
                    normalized_term = _normalize_ref_text(search_term)
                    term_matches_ref = bool(normalized_term) and normalized_term in _ref_candidates(issue)
                    if not (term_matches_haystack or term_matches_ref):
                        return False
                return True

            visible_issues = [issue for issue in issues if _matches_filters(issue)]

            st.caption(
                T.get("admin_error_log_count_caption", "Showing {n} of {total} issue(s).").format(
                    n=len(visible_issues), total=len(issues)
                )
            )

            if not visible_issues:
                st.info(T.get("admin_error_log_no_matches", "No errors match the current filters."))

            severity_icons = {"error": "🔴", "warning": "🟡", "user_reported": "🗣️"}

            for issue in visible_issues:
                err = issue["latest"]
                package = parse_diagnostic_package(err.get("diagnostic_package"))
                score, presence = compute_ai_readiness(package)
                current_status = err.get("status") or "New"

                icon = severity_icons.get(err.get("severity"), "⚪")
                occurred = (err.get("occurred_at") or "")[:19].replace("T", " ")
                occ_suffix = f" ×{issue['occurrences']}" if issue["occurrences"] > 1 else ""
                # Phase 2.1 (Stable Issue References): show the same
                # stable issue_id the person saw on screen when this
                # happened to them, not the raw row id -- so the
                # number here always matches what they'd tell you.
                # Falls back to the row id only for records from
                # before this phase (issue_id is None) or
                # user-submitted reports (never issue-linked).
                display_ref = issue.get("issue_id") if issue.get("issue_id") is not None else err["id"]
                title = (
                    f"{icon} #{display_ref}{occ_suffix} -- {occurred} -- "
                    f"{err.get('page') or 'unknown page'} -- {err.get('error_type') or 'Error'} -- "
                    f"{current_status}"
                )

                with st.expander(title):
                    # --- Summary -------------------------------------------------
                    st.markdown(
                        _issue_status_badge(current_status) + "&nbsp;&nbsp;" + _readiness_badge(score),
                        unsafe_allow_html=True,
                    )
                    summary_text = (package or {}).get("summary") or err.get("message") or "(no message)"
                    st.markdown(f"**{T.get('admin_error_log_summary_label', 'Summary')}:** {summary_text}")
                    st.markdown(
                        f"**{T.get('admin_error_log_category_label', 'Category')}:** "
                        f"{(package or {}).get('category', '—')}  \n"
                        f"**{T.get('admin_error_log_severity_label', 'Severity')}:** {err.get('severity') or '—'}  \n"
                        f"**{T.get('admin_error_log_when_label', 'When')}:** {occurred}  \n"
                        f"**{T.get('admin_error_log_page_label', 'Page')}:** {err.get('page') or '—'}  \n"
                        f"**{T.get('admin_error_log_user_label', 'User')}:** "
                        f"{err.get('user_name') or '—'} ({err.get('user_role') or 'unknown role'})"
                    )

                    # --- Status (manual lifecycle) --------------------------------
                    status_options = ["New", "Investigating", "Recurred", "Fixed", "Closed"]
                    safe_status = current_status if current_status in status_options else "New"
                    new_status = st.selectbox(
                        T.get("admin_error_log_status_label", "Status"),
                        options=status_options,
                        index=status_options.index(safe_status),
                        key=f"admin_error_status_{err['id']}",
                    )
                    if new_status != safe_status:
                        # Phase 2.1: an issue-linked record's status
                        # lives on the shared error_issues row, so
                        # every occurrence moves together -- and
                        # marking it Fixed/Closed is exactly what
                        # makes the NEXT occurrence (if it recurs)
                        # start a brand-new issue with a new number,
                        # instead of silently reopening this one.
                        # Records from before Phase 2.1 (issue_id is
                        # None) fall back to the old per-row update.
                        if issue.get("issue_id") is not None:
                            update_issue_status(issue["issue_id"], new_status)
                        else:
                            update_error_status(err["id"], new_status)
                        st.rerun()

                    # --- Occurrences -------------------------------------------------
                    if issue["occurrences"] > 1:
                        first_seen = (issue["first_seen"] or "")[:19].replace("T", " ")
                        last_seen = (issue["last_seen"] or "")[:19].replace("T", " ")
                        st.markdown(
                            f"**{T.get('admin_error_log_occurrences_label', 'Occurrences')}:** "
                            f"{issue['occurrences']}  \n"
                            f"**{T.get('admin_error_log_first_seen_label', 'First seen')}:** {first_seen}  \n"
                            f"**{T.get('admin_error_log_last_seen_label', 'Last seen')}:** {last_seen}"
                        )

                        # --- Who experienced this (Phase 2.1) ------------------------
                        # Expandable, on-demand -- not shown by default, so an
                        # issue with 70 occurrences doesn't dump 70 lines into
                        # the page. Built from whichever occurrences happen to
                        # be in the current fetch batch (get_recent_errors'
                        # limit=50), so for very old, very frequent issues this
                        # list may show fewer entries than the true count above
                        # -- the count itself is always the real, full total.
                        occ_list = issue.get("occurrence_list") or []
                        with st.expander(
                            T.get(
                                "admin_error_log_who_experienced_label",
                                "👥 Who experienced this ({n} shown)",
                            ).format(n=len(occ_list))
                        ):
                            if len(occ_list) < issue["occurrences"]:
                                st.caption(T.get(
                                    "admin_error_log_who_experienced_partial",
                                    "Showing the occurrences currently loaded; the total "
                                    "count above reflects every occurrence recorded.",
                                ))
                            for occ in occ_list:
                                occ_when = (occ.get("occurred_at") or "")[:19].replace("T", " ")
                                who = occ.get("user_name") or "—"
                                role = occ.get("user_role") or "unknown role"
                                st.markdown(f"- `{occ_when}` — {who} ({role})")

                    st.divider()

                    # =================================================================
                    # Phase 4: Case Knowledge (resolution, AI investigation history,
                    # possible similar issues, export). Everything below EXTENDS this
                    # issue -- it never re-collects evidence already in the Diagnostic
                    # Package above, and it's only available for records that have a
                    # stable issue reference (issue_id). Records from before Phase 2.1
                    # never got one, so they fall back to a short explanatory caption.
                    # =================================================================
                    stable_issue_id = issue.get("issue_id")
                    if stable_issue_id is None:
                        st.caption(T.get(
                            "admin_case_knowledge_no_issue_id",
                            "This record predates stable issue references, so case "
                            "knowledge (resolution tracking, AI investigation history, "
                            "similar issues, export) isn't available for it.",
                        ))
                    else:
                        # --- Resolution Workflow + Case Knowledge ---------------------
                        st.markdown(f"**{T.get('admin_case_resolution_header', '✅ Resolution & Case Knowledge')}**")
                        existing_resolution = case_knowledge.get_resolution(stable_issue_id) or {}
                        if existing_resolution.get("updated_at"):
                            st.caption(
                                T.get("admin_case_resolution_last_updated", "Last updated {when} by {who}").format(
                                    when=(existing_resolution.get("updated_at") or "")[:16].replace("T", " "),
                                    who=existing_resolution.get("updated_by") or "—",
                                )
                            )

                        with st.form(key=f"admin_case_resolution_form_{stable_issue_id}"):
                            r_summary = st.text_area(
                                T.get("admin_case_field_resolution_summary", "Resolution summary"),
                                value=existing_resolution.get("resolution_summary") or "",
                                key=f"case_resolution_summary_{stable_issue_id}",
                            )
                            r_root_cause = st.text_area(
                                T.get("admin_case_field_root_cause", "Root cause (administrator's conclusion)"),
                                value=existing_resolution.get("root_cause") or "",
                                key=f"case_root_cause_{stable_issue_id}",
                            )
                            r_fix_applied = st.text_area(
                                T.get("admin_case_field_fix_applied", "Fix applied"),
                                value=existing_resolution.get("fix_applied") or "",
                                key=f"case_fix_applied_{stable_issue_id}",
                            )
                            col_a, col_b = st.columns(2)
                            with col_a:
                                r_version_fixed = st.text_input(
                                    T.get("admin_case_field_version_fixed", "Version fixed"),
                                    value=existing_resolution.get("version_fixed") or "",
                                    key=f"case_version_fixed_{stable_issue_id}",
                                )
                            with col_b:
                                r_deployment_date = st.text_input(
                                    T.get("admin_case_field_deployment_date", "Deployment date (if applicable)"),
                                    value=existing_resolution.get("deployment_date") or "",
                                    key=f"case_deployment_date_{stable_issue_id}",
                                )
                            r_lessons_learned = st.text_area(
                                T.get("admin_case_field_lessons_learned", "Lessons learned"),
                                value=existing_resolution.get("lessons_learned") or "",
                                key=f"case_lessons_learned_{stable_issue_id}",
                            )
                            r_prevention_notes = st.text_area(
                                T.get("admin_case_field_prevention_notes", "Future prevention notes"),
                                value=existing_resolution.get("prevention_notes") or "",
                                key=f"case_prevention_notes_{stable_issue_id}",
                            )

                            st.markdown(f"_{T.get('admin_case_knowledge_subheader', 'Case knowledge (all optional)')}_")
                            r_common_cause = st.text_input(
                                T.get("admin_case_field_common_cause", "Common cause"),
                                value=existing_resolution.get("common_cause") or "",
                                key=f"case_common_cause_{stable_issue_id}",
                            )
                            r_known_fix = st.text_input(
                                T.get("admin_case_field_known_fix", "Known fix"),
                                value=existing_resolution.get("known_fix") or "",
                                key=f"case_known_fix_{stable_issue_id}",
                            )
                            r_known_workaround = st.text_input(
                                T.get("admin_case_field_known_workaround", "Known workaround"),
                                value=existing_resolution.get("known_workaround") or "",
                                key=f"case_known_workaround_{stable_issue_id}",
                            )
                            col_c, col_d = st.columns(2)
                            with col_c:
                                r_doc_link = st.text_input(
                                    T.get("admin_case_field_documentation_link", "Documentation link"),
                                    value=existing_resolution.get("documentation_link") or "",
                                    key=f"case_doc_link_{stable_issue_id}",
                                )
                            with col_d:
                                r_git_commit = st.text_input(
                                    T.get("admin_case_field_git_commit", "Git commit"),
                                    value=existing_resolution.get("git_commit") or "",
                                    key=f"case_git_commit_{stable_issue_id}",
                                )
                            r_external_ref = st.text_input(
                                T.get("admin_case_field_external_reference", "External reference"),
                                value=existing_resolution.get("external_reference") or "",
                                key=f"case_external_ref_{stable_issue_id}",
                            )

                            if st.form_submit_button(T.get("admin_case_resolution_save", "💾 Save resolution & case knowledge")):
                                saved = case_knowledge.save_resolution(
                                    stable_issue_id,
                                    {
                                        "resolution_summary": r_summary,
                                        "root_cause": r_root_cause,
                                        "fix_applied": r_fix_applied,
                                        "version_fixed": r_version_fixed,
                                        "deployment_date": r_deployment_date,
                                        "lessons_learned": r_lessons_learned,
                                        "prevention_notes": r_prevention_notes,
                                        "common_cause": r_common_cause,
                                        "known_fix": r_known_fix,
                                        "known_workaround": r_known_workaround,
                                        "documentation_link": r_doc_link,
                                        "git_commit": r_git_commit,
                                        "external_reference": r_external_ref,
                                    },
                                    actor_name=st.session_state.get("user_name", ""),
                                    actor_role=st.session_state.get("user_role", ""),
                                )
                                if saved:
                                    st.success(T.get("admin_case_resolution_saved", "Saved."))
                                    st.rerun()
                                else:
                                    st.error(T.get("admin_case_resolution_save_failed", "Could not save -- please try again."))

                        # --- Previous Resolution History (Phase 4 reopening) -----------
                        resolution_history = case_knowledge.get_resolution_history(stable_issue_id)
                        if resolution_history:
                            with st.expander(
                                T.get(
                                    "admin_case_resolution_history_header",
                                    "📜 Previous resolution history ({n} preserved)",
                                ).format(n=len(resolution_history))
                            ):
                                st.caption(T.get(
                                    "admin_case_resolution_history_caption",
                                    "This issue was previously marked Fixed or Closed and has since "
                                    "recurred. The resolution recorded before each recurrence is "
                                    "preserved below, even though the form above now reflects the "
                                    "current investigation.",
                                ))
                                for snap in resolution_history:
                                    when = (snap.get("reopened_at") or "")[:16].replace("T", " ")
                                    st.markdown(
                                        f"**{T.get('admin_case_resolution_history_reopened_at', 'Reopened at')} "
                                        f"{when}** "
                                        f"({T.get('admin_case_resolution_history_occurrence', 'occurrence')} "
                                        f"#{snap.get('occurrence_count_at_reopen') or '—'})"
                                    )
                                    snap_data = snap.get("snapshot_data") or {}
                                    for label, key in case_knowledge.RESOLUTION_LABELS:
                                        if snap_data.get(key):
                                            st.markdown(f"- **{label}:** {snap_data[key]}")
                                    st.markdown("---")

                        st.divider()

                        # --- AI Investigation History -----------------------------------
                        st.markdown(f"**{T.get('admin_case_investigations_header', '🧠 AI Investigation History')}**")
                        st.caption(T.get(
                            "admin_case_investigations_caption",
                            "Reflection Space never calls an AI automatically here -- this is "
                            "simply a place to preserve investigations you've already done "
                            "elsewhere (ChatGPT, Claude, Gemini, or a manual investigation), so "
                            "the next person doesn't have to redo the work.",
                        ))
                        investigations = case_knowledge.get_investigations(stable_issue_id)
                        if investigations:
                            for inv in investigations:
                                inv_when = (inv.get("investigated_at") or "")[:16].replace("T", " ")
                                with st.expander(f"{inv.get('tool_used') or 'Investigation'} — {inv_when}"):
                                    if inv.get("prompt"):
                                        st.markdown(f"**{T.get('admin_case_investigation_prompt', 'Prompt')}:**")
                                        st.code(inv["prompt"], language=None, wrap_lines=True)
                                    if inv.get("ai_response"):
                                        st.markdown(f"**{T.get('admin_case_investigation_response', 'AI response')}:**")
                                        st.code(inv["ai_response"], language=None, wrap_lines=True)
                                    if inv.get("admin_notes"):
                                        st.markdown(f"**{T.get('admin_case_investigation_notes', 'Administrator notes')}:**")
                                        st.write(inv["admin_notes"])
                                    st.caption(f"{T.get('admin_case_investigation_by', 'Added by')}: {inv.get('created_by') or '—'}")
                                    if st.button(
                                        T.get("admin_case_investigation_delete", "🗑️ Remove this entry"),
                                        key=f"delete_investigation_{inv['id']}",
                                    ):
                                        case_knowledge.delete_investigation(inv["id"])
                                        st.rerun()
                        else:
                            st.caption(T.get("admin_case_investigations_empty", "No investigations preserved yet."))

                        with st.form(key=f"admin_case_investigation_form_{stable_issue_id}", clear_on_submit=True):
                            st.markdown(f"_{T.get('admin_case_investigation_add', 'Preserve a new investigation')}_")
                            inv_tool = st.selectbox(
                                T.get("admin_case_investigation_tool", "Tool used"),
                                options=["ChatGPT", "Claude", "Gemini", "Manual Investigation", "Other"],
                                key=f"case_inv_tool_{stable_issue_id}",
                            )
                            inv_prompt = st.text_area(
                                T.get("admin_case_investigation_prompt_input", "Prompt"),
                                key=f"case_inv_prompt_{stable_issue_id}",
                            )
                            inv_response = st.text_area(
                                T.get("admin_case_investigation_response_input", "AI response"),
                                key=f"case_inv_response_{stable_issue_id}",
                            )
                            inv_notes = st.text_area(
                                T.get("admin_case_investigation_notes_input", "Administrator notes"),
                                key=f"case_inv_notes_{stable_issue_id}",
                            )
                            if st.form_submit_button(T.get("admin_case_investigation_save", "💾 Save investigation")):
                                added = case_knowledge.add_investigation(
                                    stable_issue_id,
                                    tool_used=inv_tool,
                                    prompt=inv_prompt,
                                    ai_response=inv_response,
                                    admin_notes=inv_notes,
                                    actor_name=st.session_state.get("user_name", ""),
                                    actor_role=st.session_state.get("user_role", ""),
                                )
                                if added:
                                    st.success(T.get("admin_case_investigation_saved", "Investigation preserved."))
                                    st.rerun()
                                else:
                                    st.error(T.get("admin_case_investigation_save_failed", "Could not save -- please try again."))

                        st.divider()

                        # --- Possible Similar Issues -------------------------------------
                        st.markdown(f"**{T.get('admin_case_similar_header', '🔍 Possible Similar Issues')}**")
                        st.caption(T.get(
                            "admin_case_similar_caption",
                            "Simple heuristics only (same exception, same page, same file, or a "
                            "similar message) -- not AI clustering. You decide whether these are "
                            "actually related.",
                        ))
                        similar = case_knowledge.find_similar_issues(
                            stable_issue_id,
                            page=err.get("page"),
                            error_type=(package or {}).get("exception_type") or err.get("error_type"),
                            message=(package or {}).get("exception_message") or err.get("message"),
                            traceback_text=(package or {}).get("traceback") or err.get("traceback") or "",
                        )
                        if similar:
                            for s in similar:
                                s_when = (s.get("last_seen") or "")[:16].replace("T", " ")
                                st.markdown(
                                    f"- **#{s['issue_id']}** — {s.get('page') or '—'} — "
                                    f"{s.get('error_type') or '—'} — {s.get('status') or '—'} "
                                    f"(×{s.get('occurrence_count') or 1}, last seen {s_when})  \n"
                                    f"  _{', '.join(s.get('reasons') or [])}_"
                                )
                        else:
                            st.caption(T.get("admin_case_similar_empty", "No similar issues found."))

                        st.divider()

                        # --- Export --------------------------------------------------------
                        st.markdown(f"**{T.get('admin_case_export_header', '📤 Export this case')}**")
                        export_format = st.selectbox(
                            T.get("admin_case_export_format", "Format"),
                            options=["Markdown", "JSON", "Plain Text"],
                            key=f"case_export_format_{stable_issue_id}",
                        )
                        fmt_map = {"Markdown": "markdown", "JSON": "json", "Plain Text": "text"}
                        ext_map = {"Markdown": "md", "JSON": "json", "Plain Text": "txt"}
                        export_text = case_knowledge.build_case_export(stable_issue_id, fmt=fmt_map[export_format])
                        if export_text:
                            st.download_button(
                                T.get("admin_case_export_download", "Download case #{n}").format(n=stable_issue_id),
                                data=export_text,
                                file_name=f"case_{stable_issue_id}.{ext_map[export_format]}",
                                mime="text/plain",
                                key=f"case_export_download_{stable_issue_id}_{export_format}",
                            )
                        else:
                            st.caption(T.get("admin_case_export_failed", "Could not build export."))

                    st.divider()

                    # --- Human Explanation ------------------------------------------
                    st.markdown(f"**{T.get('admin_error_log_explanation_label', '🗣️ What happened, in plain language')}**")
                    if package:
                        st.write(package.get("summary") or "—")
                    else:
                        st.caption(T.get(
                            "admin_error_log_no_package",
                            "No AI Diagnostic Package was generated for this record -- it was logged "
                            "before the Diagnostic Engine existed. The technical details below are "
                            "still available.",
                        ))

                    st.divider()

                    # --- Technical Details --------------------------------------------
                    st.markdown(f"**{T.get('admin_error_log_technical_label', '🔧 Technical Details')}**")
                    exc_type = (package or {}).get("exception_type") or err.get("error_type")
                    exc_msg = (package or {}).get("exception_message") or err.get("message")
                    tb = (package or {}).get("traceback") or err.get("traceback")
                    is_user_report = exc_type == "UserReport"
                    st.markdown(f"**{T.get('admin_error_log_exception_type_label', 'Exception type')}:** `{exc_type or '—'}`")
                    st.markdown(f"**{T.get('admin_error_log_exception_message_label', 'Exception message')}:** {exc_msg or '—'}")
                    if err.get("context"):
                        st.markdown(f"**{T.get('admin_error_log_context_label', 'Context')}:**")
                        st.code(err["context"], language="json")
                    if is_user_report:
                        # User reports carry a fixed placeholder string in the
                        # traceback field (see services/error_log.py:
                        # log_user_report) -- that's not a real traceback, so
                        # it's never shown as one here.
                        st.caption(T.get(
                            "admin_error_log_no_traceback",
                            "No traceback -- this was a user-submitted report, not an automatic exception.",
                        ))
                    elif tb:
                        st.markdown(f"**{T.get('admin_error_log_traceback_label', 'Full technical traceback')}:**")
                        st.code(tb, language="python")

                    # --- Evidence Timeline --------------------------------------------
                    timeline = (package or {}).get("navigation_timeline") or []
                    if timeline:
                        st.markdown(f"**{T.get('admin_error_log_timeline_label', '🕒 Evidence Timeline')}**")
                        timeline_lines = []
                        for entry in timeline:
                            at_full = entry.get("at") or ""
                            at = at_full[11:19] if len(at_full) >= 19 else at_full
                            line = f"`{at}` {entry.get('event', '')}"
                            if entry.get("page"):
                                line += f" _(page: {entry['page']})_"
                            if entry.get("detail"):
                                line += f" — {entry['detail']}"
                            timeline_lines.append(line)
                        st.markdown("  \n".join(timeline_lines))

                    # --- Session Context --------------------------------------------
                    session_ctx = (package or {}).get("session_context") or {}
                    if session_ctx:
                        st.markdown(f"**{T.get('admin_error_log_session_label', '🧭 Session Context')}**")
                        st.markdown("  \n".join(f"- `{k}`: {v}" for k, v in session_ctx.items()))

                    # --- Environment --------------------------------------------
                    if package:
                        st.markdown(f"**{T.get('admin_error_log_environment_label', '💻 Environment')}**")
                        env_lines = [
                            f"- {T.get('admin_error_log_env_app_version', 'App version')}: {package.get('app_version', '—')}",
                            f"- {T.get('admin_error_log_env_python', 'Python version')}: {package.get('python_version', '—')}",
                            f"- {T.get('admin_error_log_env_os', 'Operating system')}: {package.get('operating_system', '—')}",
                            f"- {T.get('admin_error_log_env_browser', 'Browser')}: {package.get('browser') or T.get('admin_error_log_not_available', 'not available')}",
                        ]
                        for k, v in (package.get("environment") or {}).items():
                            if k in ("python_version",):
                                continue
                            env_lines.append(f"- {k}: {v}")
                        st.markdown("  \n".join(env_lines))

                    # --- Evidence Collected + AI Readiness Score -----------------------
                    st.markdown(f"**{T.get('admin_error_log_evidence_label', '📋 Evidence Collected')}**")
                    st.caption(T.get(
                        "admin_error_log_readiness_explainer",
                        "The AI Readiness Score is not AI-generated -- it's a simple completeness "
                        "count of how many of the 7 evidence categories below are present for this "
                        "record.",
                    ))
                    checklist_lines = [
                        f"{'✅' if is_present else '⬜'} {label}" for label, is_present in presence
                    ]
                    st.markdown("  \n".join(checklist_lines))
                    st.progress(score / 100)

                    # --- Screenshot (legacy only) --------------------------------
                    # Phase 3 retired the screenshot subsystem entirely --
                    # no new record can have a value here. This block only
                    # ever renders for older rows logged before Phase 3,
                    # so those reports continue to display correctly.
                    if err.get("screenshot"):
                        st.markdown(f"**{T.get('admin_error_log_screenshot_label', 'Screenshot')}:**")
                        try:
                            _hdr, _, _b64data = err["screenshot"].partition(",")
                            st.image(base64.b64decode(_b64data))
                        except Exception:
                            st.caption(T.get("admin_error_log_screenshot_error", "(could not display screenshot)"))

                    st.divider()

                    # --- AI Prompt --------------------------------------------
                    # Prefer the ready-made prompt already built by the Phase 1
                    # Diagnostic Engine (services/diagnostics.py) -- fall back to
                    # the older services/error_log.py:build_ai_prompt() only for
                    # records that predate it, so nothing here ever breaks for
                    # older data.
                    st.markdown(f"**{T.get('admin_error_log_prompt_label', '🤖 AI Prompt')}**")
                    ai_prompt_text = (package or {}).get("ai_prompt") or build_ai_prompt(err)
                    st.caption(T.get(
                        "admin_error_log_copy_hint",
                        "Hover over the box below and click the copy icon in the top-right corner.",
                    ))
                    st.code(ai_prompt_text, language=None, wrap_lines=True)

    # =============================================================================
    # 9. Case Knowledge Search (Phase 4)
    # =============================================================================
    # Searches across everything Phase 4 adds -- root cause, resolution,
    # lessons learned, AI tool used, status, version fixed, occurrence
    # count, page, exception, and user -- without re-reading every issue
    # above. See services/case_knowledge.py:search_cases.
    with st.expander(T.get("admin_case_search_header", "🔎 Case Knowledge Search"), expanded=False):
        st.caption(T.get(
            "admin_case_search_caption",
            "Search resolved and unresolved cases by what you know about them, not just "
            "when they happened. Fill in any combination of fields below -- results match "
            "ALL fields you provide.",
        ))

        col1, col2, col3 = st.columns(3)
        with col1:
            s_root_cause = st.text_input(T.get("admin_case_search_root_cause", "Root cause contains"), key="admin_case_search_root_cause")
            s_resolution = st.text_input(T.get("admin_case_search_resolution", "Resolution contains"), key="admin_case_search_resolution")
            s_lesson = st.text_input(T.get("admin_case_search_lesson", "Lesson learned contains"), key="admin_case_search_lesson")
        with col2:
            s_ai_tool = st.text_input(T.get("admin_case_search_ai_tool", "AI tool used"), key="admin_case_search_ai_tool")
            s_status = st.selectbox(
                T.get("admin_case_search_status", "Status"),
                options=["Any", "New", "Investigating", "Recurred", "Fixed", "Closed"],
                key="admin_case_search_status",
            )
            s_version_fixed = st.text_input(T.get("admin_case_search_version_fixed", "Version fixed"), key="admin_case_search_version_fixed")
        with col3:
            s_page = st.text_input(T.get("admin_case_search_page", "Page"), key="admin_case_search_page")
            s_exception = st.text_input(T.get("admin_case_search_exception", "Exception type"), key="admin_case_search_exception")
            s_user = st.text_input(T.get("admin_case_search_user", "User"), key="admin_case_search_user")

        s_min_occurrences = st.number_input(
            T.get("admin_case_search_min_occurrences", "Minimum occurrence count"),
            min_value=0, value=0, step=1, key="admin_case_search_min_occurrences",
        )

        if st.button(T.get("admin_case_search_button", "Search"), key="admin_case_search_go"):
            results = case_knowledge.search_cases(
                root_cause=s_root_cause or None,
                resolution=s_resolution or None,
                lesson=s_lesson or None,
                ai_tool=s_ai_tool or None,
                status=None if s_status == "Any" else s_status,
                version_fixed=s_version_fixed or None,
                min_occurrences=s_min_occurrences or None,
                page=s_page or None,
                exception_type=s_exception or None,
                user=s_user or None,
            )
            if not results:
                st.info(T.get("admin_case_search_no_results", "No cases match those filters. Try fewer fields."))
            else:
                st.caption(T.get("admin_case_search_result_count", "{n} case(s) found.").format(n=len(results)))
                for r in results:
                    when = (r.get("last_seen") or "")[:16].replace("T", " ")
                    st.markdown(
                        f"**#{r['issue_id']}** — {r.get('page') or '—'} — {r.get('error_type') or '—'} — "
                        f"{r.get('status') or '—'} (×{r.get('occurrence_count') or 1}, last seen {when})"
                    )
                    if r.get("resolution_summary"):
                        st.caption(f"{T.get('admin_case_search_resolution_label', 'Resolution')}: {r['resolution_summary']}")
                    if r.get("root_cause"):
                        st.caption(f"{T.get('admin_case_search_root_cause_label', 'Root cause')}: {r['root_cause']}")
                    st.markdown("---")
                st.caption(T.get(
                    "admin_case_search_find_hint",
                    "Open the matching case above in AI Diagnostic Centre (by its # reference) "
                    "for the full record.",
                ))