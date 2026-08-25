"""System Administration -- Section 8: Translation System Health + AI Diagnostic Centre (issue management dashboard).

Extracted unchanged from the original system_administration.py file -- this is the largest section, covering filters, Open/Fixed/Warnings/Trends views, per-issue evidence display, resolution workflow, AI investigation history, similar-issue detection, and case export.
"""
import base64

import pandas as pd
import streamlit as st

from services.error_log import (
    get_recent_errors,
    build_ai_prompt,
    update_error_status,
    update_issue_status,
    parse_diagnostic_package,
    compute_ai_readiness,
    group_errors_by_signature,
)
from services.pagination import Paginator
from services import case_knowledge
from services.translation_manager import render_translation_health_panel
from pages.admin_sections._shared import format_when

def render(T):
    # =============================================================================
    # 8. AI Diagnostic Centre -- Issue Management Dashboard (Phase 6)
    # =============================================================================
    # Phase 1 (services/diagnostics.py) already builds a complete AI
    # Diagnostic Package behind the scenes for every error_log row (see
    # services/error_log.py:log_error). Phases 2-5 added issue tracking,
    # case knowledge, and reopening. Phase 6 does NOT re-collect any
    # evidence and does NOT change how evidence is gathered or stored --
    # it only reorganizes how the existing data is DISPLAYED and
    # SEARCHED, as a true Issue Management dashboard:
    #
    #   - Open Issues / Fixed Issues / Warnings are now three separate
    #     sections (switchable via the "View" selector above the issue
    #     list) instead of one long flat list with a status dropdown.
    #     Warnings (severity == "warning", e.g. the "Partial Reflection
    #     Generation" issue raised by rdi/orchestrator.py) are never
    #     mixed into the application-error sections -- they always get
    #     their own section, using the same severity value that already
    #     existed before this phase.
    #   - One shared filter bar (Status, Severity, Root Cause, Page,
    #     Date, User) applies across all sections, so switching sections
    #     never loses a filter you've already set.
    #   - A new Trend Analysis section charts occurrence volume over time
    #     and highlights the most frequent issues -- built entirely
    #     from data already fetched below; no new queries.
    #   - Every issue's own detail view (the expander you open) is
    #     unchanged from Phases 2-5: Summary, Root Cause, Occurrences,
    #     Affected Users, Tracebacks, Evidence, Timeline, AI Prompt,
    #     Previous Investigations, Resolution History.
    #
    # FUTURE-READY EVIDENCE (see EVIDENCE_SECTIONS below): the "what
    # evidence does this issue have" part of the detail view (Technical
    # Details, Timeline, Session Context, Environment, Evidence
    # Checklist, Screenshot, AI Prompt) is driven by a small registry
    # instead of a long fixed sequence of if-blocks. Adding a brand-new
    # evidence type later (e.g. "Network Requests", "Device Logs")
    # means appending ONE entry to that list -- an `applies()` check
    # and a `render()` function -- nothing else on this page changes.
    #
    # Records logged BEFORE the Phase 1 Diagnostic Engine existed have
    # no diagnostic_package -- parse_diagnostic_package() (see
    # services/error_log.py) returns None for those, and every section
    # below falls back gracefully to the older, plainer fields already
    # stored directly on the error_log row (message / traceback /
    # context), exactly as before.

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
        display_label = T.get("status_labels", {}).get(status, status)
        return (
            f'<span style="background-color:{color};color:white;padding:2px 10px;'
            f'border-radius:10px;font-size:0.78rem;font-weight:600;">{display_label}</span>'
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

    with st.expander(T.get("admin_translation_health_header", "🌐 Translation System Health"), expanded=False):
        # Diagnostic-only panel -- never allowed to break this page, so
        # any unexpected error here is swallowed after being surfaced
        # as a small caption rather than propagating up.
        try:
            render_translation_health_panel(T)
        except Exception:
            st.caption(T.get(
                "admin_translation_panel_error",
                "Translation health panel could not be loaded right now.",
            ))

    with st.expander(T.get("admin_error_log_header", "🩺 AI Diagnostic Centre"), expanded=False):
        st.caption(T.get(
            "admin_error_log_caption",
            "Every problem recorded in the app -- crashes, failed AI companion calls, or "
            "problems people reported -- organized as an issue management workspace: what's "
            "open, what's fixed, what's just a warning, how serious each thing is, and a "
            "ready-made prompt you can copy straight into a chat with Claude to get it "
            "diagnosed and fixed.",
        ))

        errors = get_recent_errors(limit=200)

        if not errors:
            st.success(T.get("admin_error_log_empty", "No errors recorded. Everything looks clean."))
        else:
            issues = group_errors_by_signature(errors)

            # --- Shared filter bar (Phase 6) ------------------------------------
            # Status, Severity, Root Cause, Page, Date, User -- applies across
            # Open Issues, Fixed Issues, and Warnings alike, so switching sections
            # never loses a filter you've already set.
            st.markdown(f"##### {T.get('admin_diag_filters_header', '🔍 Filters')}")
            search_term = st.text_input(
                T.get("admin_error_log_search_label", "Search (page, error type, or message)"),
                key="admin_error_log_search",
            )
            page_filter = st.text_input(
                T.get("admin_diag_filter_page", "Page contains"),
                key="admin_diag_filter_page",
            )
            severity_filter = st.selectbox(
                T.get("admin_error_log_severity_filter_label", "Filter by severity"),
                options=["All", "error", "warning", "user_reported"],
                format_func=lambda s: T.get("severity_labels", {}).get(s, s),
                key="admin_error_log_severity_filter",
            )
            root_cause_filter = st.text_input(
                T.get("admin_diag_filter_root_cause", "Root cause contains"),
                key="admin_diag_filter_root_cause",
            )
            status_filter = st.selectbox(
                T.get("admin_error_log_status_filter_label", "Filter by status"),
                options=["All", "New", "Investigating", "Recurred", "Fixed", "Closed"],
                format_func=lambda s: T.get("status_labels", {}).get(s, s),
                key="admin_error_log_status_filter",
            )
            user_filter = st.text_input(
                T.get("admin_diag_filter_user", "User contains"),
                key="admin_diag_filter_user",
            )

            date_from = st.date_input(
                T.get("admin_diag_filter_date_from", "From date"),
                value=None,
                key="admin_diag_filter_date_from",
            )
            date_to = st.date_input(
                T.get("admin_diag_filter_date_to", "To date"),
                value=None,
                key="admin_diag_filter_date_to",
            )

            def _normalize_ref_text(text):
                # Keeps only letters/digits, lowercased -- so "REF-000124",
                # "ref 000124", and "REF000124" all normalize the same way.
                return "".join(ch for ch in str(text or "").lower() if ch.isalnum())

            def _ref_candidates(issue):
                # Same reference number shown on screen for this issue
                # (see display_ref below, inside _render_issue_card) --
                # computed here too so search matches exactly what the
                # admin sees.
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
                if page_filter and page_filter.lower() not in str(latest.get("page") or "").lower():
                    return False
                if user_filter and user_filter.lower() not in str(latest.get("user_name") or "").lower():
                    return False
                if root_cause_filter:
                    root_cause_haystack = " ".join(str(x or "") for x in (
                        latest.get("issue_root_cause"),
                        latest.get("issue_category"),
                        (parse_diagnostic_package(latest.get("diagnostic_package")) or {}).get("root_cause"),
                    )).lower()
                    if root_cause_filter.lower() not in root_cause_haystack:
                        return False
                if date_from:
                    occ_date = (latest.get("occurred_at") or "")[:10]
                    if not occ_date or occ_date < date_from.isoformat():
                        return False
                if date_to:
                    occ_date = (latest.get("occurred_at") or "")[:10]
                    if not occ_date or occ_date > date_to.isoformat():
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

            # --- Bucket into Open / Fixed / Warnings (Phase 6) ------------------
            # Warnings (severity == "warning") are always kept separate from
            # application errors -- e.g. "Partial Reflection Generation"
            # (rdi/orchestrator.py) never appears mixed in with crashes and
            # failures, per design.
            warning_issues = [i for i in visible_issues if i["latest"].get("severity") == "warning"]
            open_issues = [
                i for i in visible_issues
                if i["latest"].get("severity") != "warning"
                and (i["latest"].get("status") or "New") in ("New", "Investigating", "Recurred")
            ]
            fixed_issues = [
                i for i in visible_issues
                if i["latest"].get("severity") != "warning"
                and (i["latest"].get("status") or "New") in ("Fixed", "Closed")
            ]

            st.caption(
                T.get("admin_error_log_count_caption", "Showing {n} of {total} issue(s).").format(
                    n=len(visible_issues), total=len(issues)
                )
            )

            st.metric(T.get("admin_diag_metric_total", "Total issues"), len(issues))
            st.metric(T.get("admin_diag_metric_open", "🟥 Open"), len(open_issues))
            st.metric(T.get("admin_diag_metric_fixed", "✅ Fixed"), len(fixed_issues))
            st.metric(T.get("admin_diag_metric_warnings", "⚠️ Warnings"), len(warning_issues))

            severity_icons = {"error": "🔴", "warning": "🟡", "user_reported": "🗣️"}

            # --- Evidence section registry (Phase 6, FUTURE READY) --------------
            # Each entry is one category of evidence shown inside an issue's
            # detail view. To add a brand-new evidence type later, append ONE
            # entry to EVIDENCE_SECTIONS below -- an `applies` check and a
            # `render` function -- nothing else on this page needs to change.
            def _render_technical_details(T, err, package, extra):
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
                    st.caption(T.get(
                        "admin_error_log_no_traceback",
                        "No traceback -- this was a user-submitted report, not an automatic exception.",
                    ))
                elif tb:
                    st.markdown(f"**{T.get('admin_error_log_traceback_label', 'Full technical traceback')}:**")
                    st.code(tb, language="python")

            def _timeline_applies(err, package):
                return bool((package or {}).get("navigation_timeline"))

            def _render_timeline(T, err, package, extra):
                timeline = (package or {}).get("navigation_timeline") or []
                st.markdown(f"**{T.get('admin_error_log_timeline_label', '🕒 Evidence Timeline')}**")
                timeline_lines = []
                for entry in timeline:
                    at_full = entry.get("at") or ""
                    at = at_full[11:19] if len(at_full) >= 19 else at_full
                    line = f"`{at}` {T.get('event_labels', {}).get(entry.get('event', ''), entry.get('event', ''))}"
                    if entry.get("page"):
                        line += f" _(page: {entry['page']})_"
                    if entry.get("detail"):
                        line += f" — {entry['detail']}"
                    timeline_lines.append(line)
                st.markdown("  \n".join(timeline_lines))

            def _session_applies(err, package):
                return bool((package or {}).get("session_context"))

            def _render_session_context(T, err, package, extra):
                session_ctx = (package or {}).get("session_context") or {}
                st.markdown(f"**{T.get('admin_error_log_session_label', '🧭 Session Context')}**")
                st.markdown("  \n".join(f"- `{k}`: {v}" for k, v in session_ctx.items()))

            def _environment_applies(err, package):
                return bool(package)

            def _render_environment(T, err, package, extra):
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

            def _render_evidence_checklist(T, err, package, extra):
                score = extra["score"]
                presence = extra["presence"]
                st.markdown(f"**{T.get('admin_error_log_evidence_label', '📋 Evidence Collected')}**")
                st.caption(T.get(
                    "admin_error_log_readiness_explainer",
                    "The AI Readiness Score is not AI-generated -- it's a simple completeness "
                    "count of how many of the 8 evidence categories below are present for this "
                    "record.",
                ))
                checklist_lines = [
                    f"{'✅' if is_present else '⬜'} {T.get('readiness_category_' + key, key)}" for key, is_present in presence
                ]
                st.markdown("  \n".join(checklist_lines))
                st.progress(score / 100)

            def _screenshot_applies(err, package):
                return bool(err.get("screenshot"))

            def _render_screenshot(T, err, package, extra):
                st.markdown(f"**{T.get('admin_error_log_screenshot_label', 'Screenshot')}:**")
                try:
                    _hdr, _, _b64data = err["screenshot"].partition(",")
                    st.image(base64.b64decode(_b64data))
                except Exception:
                    st.caption(T.get("admin_error_log_screenshot_error", "(could not display screenshot)"))

            def _render_ai_prompt(T, err, package, extra):
                st.markdown(f"**{T.get('admin_error_log_prompt_label', '🤖 AI Prompt')}**")
                ai_prompt_text = (package or {}).get("ai_prompt") or build_ai_prompt(err)
                st.caption(T.get(
                    "admin_error_log_copy_hint",
                    "Hover over the box below and click the copy icon in the top-right corner.",
                ))
                st.code(ai_prompt_text, language=None, wrap_lines=True)

            EVIDENCE_SECTIONS = [
                {"id": "technical_details", "applies": lambda err, pkg: True, "render": _render_technical_details},
                {"id": "timeline", "applies": _timeline_applies, "render": _render_timeline},
                {"id": "session_context", "applies": _session_applies, "render": _render_session_context},
                {"id": "environment", "applies": _environment_applies, "render": _render_environment},
                {"id": "evidence_checklist", "applies": lambda err, pkg: True, "render": _render_evidence_checklist},
                {"id": "screenshot", "applies": _screenshot_applies, "render": _render_screenshot},
                {"id": "ai_prompt", "applies": lambda err, pkg: True, "render": _render_ai_prompt},
            ]

            # --- Trend Analysis (Phase 6) ---------------------------------------
            # Built entirely from `issues` and `errors` already fetched above --
            # no new queries, no new evidence collection.
            def _render_trend_analysis(T, issues, errors):
                st.caption(T.get(
                    "admin_diag_trends_caption",
                    "Built entirely from the issues already loaded above -- volume, hot spots, "
                    "and the most frequent problems, at a glance.",
                ))
                if not errors:
                    st.info(T.get("admin_diag_trends_empty", "Not enough data yet for trend analysis."))
                    return

                trend_df = pd.DataFrame(errors)
                trend_df["occurred_date"] = trend_df["occurred_at"].astype(str).str.slice(0, 10)
                trend_df["severity"] = trend_df["severity"].fillna("error")

                st.markdown(f"**{T.get('admin_diag_trends_volume_header', '📅 Occurrences over time')}**")
                by_day = (
                    trend_df.groupby(["occurred_date", "severity"]).size().unstack(fill_value=0).sort_index()
                )
                st.bar_chart(by_day)

                st.markdown(f"**{T.get('admin_diag_trends_pages_header', '📍 Most affected pages')}**")
                by_page = trend_df["page"].fillna(
                    T.get("admin_error_log_unknown_page", "unknown page")
                ).value_counts().head(10)
                st.bar_chart(by_page)

                st.markdown(f"**{T.get('admin_diag_trends_category_header', '🗂️ Occurrences by category')}**")
                categories = []
                for e in errors:
                    pkg = parse_diagnostic_package(e.get("diagnostic_package"))
                    categories.append(
                        e.get("issue_category") or (pkg or {}).get("category")
                        or T.get("admin_diag_trends_uncategorized", "Uncategorized")
                    )
                by_category = pd.Series(categories).value_counts().head(10)
                st.bar_chart(by_category)

                st.markdown(f"**{T.get('admin_diag_trends_top_issues_header', '🔁 Most frequent issues')}**")
                sorted_issues = sorted(issues, key=lambda i: i["occurrences"], reverse=True)[:10]
                if sorted_issues:
                    for i in sorted_issues:
                        latest = i["latest"]
                        display_ref = i.get("issue_id") if i.get("issue_id") is not None else latest["id"]
                        status_label = T.get("status_labels", {}).get(
                            latest.get("status") or "New", latest.get("status") or "New"
                        )
                        severity_icon = severity_icons.get(latest.get("severity"), "⚪")
                        st.markdown(
                            f"- **#{display_ref}** {severity_icon} — {latest.get('page') or '—'} — "
                            f"{latest.get('error_type') or '—'} — ×{i['occurrences']} — {status_label}"
                        )
                else:
                    st.caption(T.get("admin_diag_trends_no_issues", "No issues recorded yet."))

            def _render_issue_card(issue):
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
                    f"{err.get('page') or T.get('admin_error_log_unknown_page', 'unknown page')} -- "
                    f"{err.get('error_type') or T.get('admin_error_log_generic_error', 'Error')} -- "
                    f"{T.get('status_labels', {}).get(current_status, current_status)}"
                )

                with st.expander(title):
                    # --- Summary -------------------------------------------------
                    st.markdown(
                        _issue_status_badge(current_status) + "&nbsp;&nbsp;" + _readiness_badge(score),
                        unsafe_allow_html=True,
                    )
                    summary_text = (package or {}).get("summary") or err.get("message") or T.get("admin_error_log_no_message", "(no message)")
                    st.markdown(f"**{T.get('admin_error_log_summary_label', 'Summary')}:** {summary_text}")
                    severity_display = T.get("severity_labels", {}).get(err.get("severity"), err.get("severity")) or "—"
                    st.markdown(
                        f"**{T.get('admin_error_log_category_label', 'Category')}:** "
                        f"{(package or {}).get('category', '—')}  \n"
                        f"**{T.get('admin_error_log_severity_label', 'Severity')}:** {severity_display}  \n"
                        f"**{T.get('admin_error_log_when_label', 'When')}:** {occurred}  \n"
                        f"**{T.get('admin_error_log_page_label', 'Page')}:** {err.get('page') or '—'}  \n"
                        f"**{T.get('admin_error_log_user_label', 'User')}:** "
                        f"{err.get('user_name') or '—'} ({err.get('user_role') or T.get('admin_error_log_unknown_role', 'unknown role')})"
                    )

                    # --- Status (manual lifecycle) --------------------------------
                    status_options = ["New", "Investigating", "Recurred", "Fixed", "Closed"]
                    safe_status = current_status if current_status in status_options else "New"
                    new_status = st.selectbox(
                        T.get("admin_error_log_status_label", "Status"),
                        options=status_options,
                        format_func=lambda s: T.get("status_labels", {}).get(s, s),
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
                                role = occ.get("user_role") or T.get("admin_error_log_unknown_role", "unknown role")
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
                                    when=format_when(existing_resolution.get("updated_at")),
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
                            r_version_fixed = st.text_input(
                                T.get("admin_case_field_version_fixed", "Version fixed"),
                                value=existing_resolution.get("version_fixed") or "",
                                key=f"case_version_fixed_{stable_issue_id}",
                            )
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
                            r_doc_link = st.text_input(
                                T.get("admin_case_field_documentation_link", "Documentation link"),
                                value=existing_resolution.get("documentation_link") or "",
                                key=f"case_doc_link_{stable_issue_id}",
                            )
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
                                    when = format_when(snap.get("reopened_at"))
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
                                inv_when = format_when(inv.get("investigated_at"))
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

                        # --- Similar Previous Issues ---------------------------------------
                        # Deliberately lightweight (Phase 5): a plain memory-aid list, not a
                        # recurrence-management system. Reuses the exact same
                        # case_knowledge.find_similar_issues() heuristics as before -- only the
                        # DISPLAY is simplified (no reasons, no occurrence counts, no scores).
                        # The administrator decides whether any of these are actually related;
                        # Reflection Space never makes that call.
                        st.markdown(f"**{T.get('admin_case_similar_header', 'Similar Previous Issues')}**")
                        similar = case_knowledge.find_similar_issues(
                            stable_issue_id,
                            page=err.get("page"),
                            error_type=(package or {}).get("exception_type") or err.get("error_type"),
                            message=(package or {}).get("exception_message") or err.get("message"),
                            traceback_text=(package or {}).get("traceback") or err.get("traceback") or "",
                        )
                        if similar:
                            for s in similar:
                                status_label = T.get("status_labels", {}).get(s.get("status"), s.get("status")) or "—"
                                st.markdown(f"- #{s['issue_id']} ({status_label})")
                        else:
                            st.caption(T.get("admin_case_similar_empty", "No similar previous issues found."))

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
                    for _section in EVIDENCE_SECTIONS:
                        if _section["applies"](err, package):
                            _section["render"](T, err, package, {"score": score, "presence": presence})

            section_choice = st.radio(
                T.get("admin_diag_section_selector", "View"),
                options=["open", "fixed", "warnings", "trends"],
                format_func=lambda key: {
                    "open": T.get("admin_diag_tab_open", "🟥 Open Issues ({n})").format(n=len(open_issues)),
                    "fixed": T.get("admin_diag_tab_fixed", "✅ Fixed Issues ({n})").format(n=len(fixed_issues)),
                    "warnings": T.get("admin_diag_tab_warnings", "⚠️ Warnings ({n})").format(n=len(warning_issues)),
                    "trends": T.get("admin_diag_tab_trends", "📈 Trend Analysis"),
                }[key],
                key="admin_diag_section_choice",
                horizontal=True,
            )
            st.divider()

            if section_choice == "open":
                if not open_issues:
                    st.info(T.get("admin_diag_open_empty", "No open issues match the current filters."))
                else:
                    # Paginate open issues (20 per page)
                    paginator = Paginator("admin_open_issues", open_issues, items_per_page=20)
                    paginator.render_info()
                    for issue in paginator.current_page():
                        _render_issue_card(issue)
                    paginator.render_controls()

            elif section_choice == "fixed":
                if not fixed_issues:
                    st.info(T.get("admin_diag_fixed_empty", "No fixed issues match the current filters."))
                else:
                    # Paginate fixed issues (20 per page)
                    paginator = Paginator("admin_fixed_issues", fixed_issues, items_per_page=20)
                    paginator.render_info()
                    for issue in paginator.current_page():
                        _render_issue_card(issue)
                    paginator.render_controls()

            elif section_choice == "warnings":
                st.caption(T.get(
                    "admin_diag_warnings_caption",
                    "Warnings are non-fatal conditions worth knowing about -- like a partial "
                    "reflection generation -- kept separate from application errors above.",
                ))
                if not warning_issues:
                    st.info(T.get("admin_diag_warnings_empty", "No warnings match the current filters."))
                else:
                    # Paginate warnings (20 per page)
                    paginator = Paginator("admin_warnings", warning_issues, items_per_page=20)
                    paginator.render_info()
                    for issue in paginator.current_page():
                        _render_issue_card(issue)
                    paginator.render_controls()

            else:
                _render_trend_analysis(T, issues, errors)

