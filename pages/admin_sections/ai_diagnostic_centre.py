"""System Administration -- Translation System Health + Problem list.

November 2026 simplification (product owner's decision)
---------------------------------------------------------
This section used to be a full "issue management workspace": six search
filters, Open/Fixed/Warnings/Trends views, technical details, an AI
readiness score, a ready-made AI prompt, a 14-field resolution form, an
investigation log, similar-issue detection and a case export. It had
grown far beyond its purpose, which is simply:

    a problem happens in the app  ->  it is recorded  ->  the
    administrator receives an alert email (with the AI diagnosis)
    ->  the problem gets solved.

So the screen now shows the bare minimum: a list of recorded problems
with WHAT happened, WHEN, and a STATUS the administrator can change.
The AI diagnosis is not shown here any more -- it travels in the alert
email (services/email_alert.py, services/error_log.py), which is
unchanged.

Nothing about how problems are RECORDED has changed: every error is
still logged with its full diagnostic package, grouped into issues, and
emailed. The underlying services (services/error_log.py,
services/diagnostics.py, services/case_knowledge.py,
services/issue_fingerprint.py) are untouched, so the fuller views can be
brought back later without losing any history.

Architectural rule kept: no st.dataframe(), st.tabs() or st.columns()
on the System Administration page.
"""
import streamlit as st

from services.error_log import (
    get_recent_errors,
    update_error_status,
    update_issue_status,
    parse_diagnostic_package,
    group_errors_by_signature,
)
from services.pagination import Paginator
from services.translation_manager import render_translation_health_panel

STATUS_OPTIONS = ["New", "Investigating", "Recurred", "Fixed", "Closed"]
OPEN_STATUSES = ("New", "Investigating", "Recurred")
ISSUES_PER_PAGE = 20
SUMMARY_TITLE_LENGTH = 70


def _when(timestamp):
    """'2026-11-11T10:42:07+00:00' -> '2026-11-11 10:42' (UTC, as stored)."""
    return (timestamp or "")[:16].replace("T", " ")


def _what_happened(T, err):
    """Plain description of the problem: the diagnostic summary when one
    exists, otherwise the recorded message."""
    package = parse_diagnostic_package(err.get("diagnostic_package"))
    return (
        (package or {}).get("summary")
        or err.get("message")
        or T["admin_error_log_no_message"]
    )


def _shorten(text, length=SUMMARY_TITLE_LENGTH):
    text = " ".join(str(text).split())
    return text if len(text) <= length else text[: length - 1].rstrip() + "…"


def _render_issue(T, issue):
    err = issue["latest"]
    current_status = err.get("status") or "New"
    safe_status = current_status if current_status in STATUS_OPTIONS else "New"
    status_label = T["status_labels"].get(safe_status, safe_status)

    # Same stable number the person saw on screen when it happened to
    # them; falls back to the row id for older or user-reported records.
    display_ref = issue.get("issue_id") if issue.get("issue_id") is not None else err["id"]
    what = _what_happened(T, err)
    last_seen = _when(issue.get("last_seen") or err.get("occurred_at"))
    times = f" ×{issue['occurrences']}" if issue["occurrences"] > 1 else ""

    title = f"#{display_ref}{times} — {last_seen} — {_shorten(what)} — {status_label}"
    with st.expander(title):
        st.markdown(f"**{T['admin_problem_what_label']}:** {what}")
        st.markdown(
            f"**{T['admin_error_log_when_label']}:** {last_seen}  \n"
            f"**{T['admin_error_log_page_label']}:** "
            f"{err.get('page') or T['admin_error_log_unknown_page']}"
        )
        if issue["occurrences"] > 1:
            st.markdown(
                f"**{T['admin_error_log_occurrences_label']}:** {issue['occurrences']}  \n"
                f"**{T['admin_error_log_first_seen_label']}:** {_when(issue.get('first_seen'))}"
            )

        new_status = st.selectbox(
            T["admin_error_log_status_label"],
            options=STATUS_OPTIONS,
            format_func=lambda s: T["status_labels"].get(s, s),
            index=STATUS_OPTIONS.index(safe_status),
            key=f"admin_error_status_{err['id']}",
        )
        if new_status != safe_status:
            # An issue-linked record's status lives on the shared issue
            # row, so every occurrence moves together -- and marking it
            # Fixed/Closed is what makes a later recurrence show up as
            # "Recurred". Older records fall back to the per-row update.
            if issue.get("issue_id") is not None:
                update_issue_status(issue["issue_id"], new_status)
            else:
                update_error_status(err["id"], new_status)
            st.rerun()


def _render_group(T, header, issues, paginator_key):
    st.markdown(f"**{header.format(n=len(issues))}**")
    paginator = Paginator(paginator_key, issues, items_per_page=ISSUES_PER_PAGE)
    paginator.render_info()
    for issue in paginator.current_page():
        _render_issue(T, issue)
    paginator.render_controls()


def render(T):
    with st.expander(T["admin_translation_health_header"], expanded=False):
        # Diagnostic-only panel -- never allowed to break this page.
        try:
            render_translation_health_panel(T)
        except Exception:
            st.caption(T["admin_translation_panel_error"])

    with st.expander(T["admin_error_log_header"], expanded=False):
        st.caption(T["admin_error_log_caption"])

        errors = get_recent_errors(limit=200)
        if not errors:
            st.success(T["admin_error_log_empty"])
            return

        issues = group_errors_by_signature(errors)
        open_issues = [i for i in issues if (i["latest"].get("status") or "New") in OPEN_STATUSES]
        solved_issues = [i for i in issues if (i["latest"].get("status") or "New") not in OPEN_STATUSES]

        if open_issues:
            _render_group(T, T["admin_problem_open_header"], open_issues, "admin_open_issues")
        else:
            st.success(T["admin_problem_none_open"])

        if solved_issues:
            st.divider()
            _render_group(T, T["admin_problem_solved_header"], solved_issues, "admin_fixed_issues")
