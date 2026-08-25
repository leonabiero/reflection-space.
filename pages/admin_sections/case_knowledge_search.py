"""System Administration -- Section 9: Case Knowledge Search.

Extracted unchanged from the original system_administration.py file.
"""
import streamlit as st

from services import case_knowledge
from pages.admin_sections._shared import format_when

def render(T):
    with st.expander(T.get("admin_case_search_header", "🔎 Case Knowledge Search"), expanded=False):
        st.caption(T.get(
            "admin_case_search_caption",
            "Search resolved and unresolved cases by what you know about them, not just "
            "when they happened. Fill in any combination of fields below -- results match "
            "ALL fields you provide.",
        ))

        s_root_cause = st.text_input(T.get("admin_case_search_root_cause", "Root cause contains"), key="admin_case_search_root_cause")
        s_resolution = st.text_input(T.get("admin_case_search_resolution", "Resolution contains"), key="admin_case_search_resolution")
        s_lesson = st.text_input(T.get("admin_case_search_lesson", "Lesson learned contains"), key="admin_case_search_lesson")
        s_ai_tool = st.text_input(T.get("admin_case_search_ai_tool", "AI tool used"), key="admin_case_search_ai_tool")
        s_status = st.selectbox(
            T.get("admin_case_search_status", "Status"),
            options=["Any", "New", "Investigating", "Recurred", "Fixed", "Closed"],
            format_func=lambda s: T.get("status_labels", {}).get(s, s),
            key="admin_case_search_status",
        )
        s_version_fixed = st.text_input(T.get("admin_case_search_version_fixed", "Version fixed"), key="admin_case_search_version_fixed")
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
                    when = format_when(r.get("last_seen"))
                    st.markdown(
                        f"**#{r['issue_id']}** — {r.get('page') or '—'} — {r.get('error_type') or '—'} — "
                        f"{T.get('status_labels', {}).get(r.get('status'), r.get('status')) or '—'} (×{r.get('occurrence_count') or 1}, last seen {when})"
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

