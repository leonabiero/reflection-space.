import streamlit as st

from services.language import init_language
from navigation.router import render_nav
from services.identity import init_identity, render_identity_footer, require_work_mode
from services.error_log import error_boundary
from services.pattern_access import can_review_patterns
from services import pattern_text_store, pattern_text_analysis
from services.pattern_report_html import build_report_html
from services.db_time import display_datetime, now_utc
from config import PATTERN_PERIOD_CHOICES, PATTERN_MIN_TEXTS, PATTERN_TEXT_RETENTION_MONTHS

# Pattern Review
# ================
#
# Redesigned 15 November 2026 (product owner's decision -- see
# PATTERNS.md). For EDE's management team (Supervisors and Programme
# Managers) ONLY.
#
# Patterns are looked for in what social workers WROTE (the anonymised
# copy saved straight after anonymisation), not in what the AI said back
# to them. A manager picks a period -- 3, 6, 9 or 12 months -- and presses
# "Identify patterns"; the AI reads that period's texts and writes one
# report, which is saved with its date and period.
#
# Hard rules this page must never break:
#   - Managers see the REPORT only: never a text, a quotation, a
#     reflection code or who wrote anything (the texts go to the AI only --
#     services/pattern_text_store.py has no function that returns them for
#     display, and services/pattern_text_analysis.py removes any part of
#     the report that repeats a passage).
#   - It speaks of candidate patterns for reflection, never conclusions.
#   - Nothing runs with fewer than PATTERN_MIN_TEXTS texts.

GENERATING_KEY = "_pr_generating"
FLASH_KEY = "_pr_flash"
SELECTED_KEY = "_pr_selected_report"

T = init_language()
user_name, user_role = init_identity(T)
require_work_mode(T, "Manager")
render_nav(T, page_name="pattern_explorer")
render_identity_footer(T)

with error_boundary(
    "pattern_explorer", T=T, user_name=user_name, user_role=user_role,
):

    st.title(T["patterns_title"])

    if not can_review_patterns(user_role):
        st.info(T["patterns_no_access"])
        st.stop()

    st.info(T["pr_intro"])

    flash = st.session_state.pop(FLASH_KEY, None)
    if flash:
        kind, message = flash
        getattr(st, kind)(message)

    # Texts past their time limit are deleted here too (best effort).
    try:
        pattern_text_store.purge_expired_pattern_texts()
    except Exception:
        pass

    # ------------------------------------------------------------------
    # 1. Identify patterns
    # ------------------------------------------------------------------
    st.subheader(T["pr_new_header"])
    st.caption(T["pr_texts_note"].format(months=PATTERN_TEXT_RETENTION_MONTHS))

    period = st.radio(
        T["pr_period_label"],
        list(PATTERN_PERIOD_CHOICES),
        format_func=lambda m: T["pr_period_option"].format(months=m),
        horizontal=True,
        key="pr_period",
    )

    available = pattern_text_store.count_texts_for_period(user_role, period)
    st.write(T["pr_available"].format(count=available, months=period))
    enough = available >= PATTERN_MIN_TEXTS
    if not enough:
        st.caption(T["pr_not_enough"].format(minimum=PATTERN_MIN_TEXTS))
    st.caption(T["pr_cost_note"])

    is_generating = st.session_state.get(GENERATING_KEY, False)
    if st.button(T["pr_run_button"], type="primary", disabled=(not enough) or is_generating,
                 key="pr_run_btn"):
        st.session_state[GENERATING_KEY] = True
        try:
            with st.spinner(T["pr_running"]):
                outcome = pattern_text_analysis.run_report(
                    user_role, user_name, period, st.session_state.get("lang", "Español"),
                )
        finally:
            st.session_state[GENERATING_KEY] = False

        status = outcome["status"]
        if status == "ok":
            st.session_state[SELECTED_KEY] = outcome["report_id"]
            st.session_state[FLASH_KEY] = ("success", T["pr_done"].format(
                patterns=outcome["patterns"], texts=outcome["texts_read"]))
        elif status == "not_enough":
            st.session_state[FLASH_KEY] = ("info", T["pr_not_enough"].format(minimum=outcome["minimum"]))
        elif status == "busy":
            st.session_state[FLASH_KEY] = ("warning", T["pr_busy"])
        elif status == "recent":
            st.session_state[FLASH_KEY] = ("info", T["pr_recent"])
        else:
            st.session_state[FLASH_KEY] = ("error", T["pr_failed"])
        st.rerun()

    # ------------------------------------------------------------------
    # 2. Saved reports
    # ------------------------------------------------------------------
    st.divider()
    st.subheader(T["pr_saved_header"])

    reports = pattern_text_store.list_reports(user_role)
    if not reports:
        st.info(T["pr_no_reports"])
        st.stop()

    by_id = {r["id"]: r for r in reports}
    ids = list(by_id)
    wanted = st.session_state.get(SELECTED_KEY)
    chosen_id = st.selectbox(
        T["pr_report_select"],
        options=ids,
        index=ids.index(wanted) if wanted in by_id else 0,
        format_func=lambda i: T["pr_report_option"].format(
            date=display_datetime(by_id[i]["created_at"]),
            months=by_id[i]["period_months"],
            texts=by_id[i]["texts_count"],
        ),
        key="pr_report_select_box",
    )
    saved = by_id[chosen_id]
    report = saved["report"]
    texts_read = report.get("texts_read", saved["texts_count"])
    created_on = display_datetime(saved["created_at"])

    with st.container(border=True):
        st.caption(T["pr_report_meta"].format(
            date=created_on, months=saved["period_months"],
            texts=saved["texts_count"], read=texts_read,
        ))
        if report.get("groups_failed"):
            st.warning(T["pr_some_unread"])
        st.caption(T["pr_candidate_note"])

        if report.get("overview"):
            st.markdown(f"**{T['pr_overview_header']}**")
            st.write(report["overview"])

        st.markdown(f"**{T['pr_patterns_header']}**")
        patterns = report.get("patterns") or []
        if not patterns:
            st.info(T["pr_no_patterns"])
        for n, pattern in enumerate(patterns, start=1):
            with st.container(border=True):
                st.markdown(f"**{n}. {pattern.get('title', '')}**")
                st.caption(T["pr_seen_in"].format(count=pattern.get("texts_count", 0), total=texts_read))
                st.write(pattern.get("description", ""))
                if pattern.get("why_it_may_matter"):
                    st.markdown(f"*{T['pr_why_header']}*")
                    st.write(pattern["why_it_may_matter"])
                if pattern.get("questions"):
                    st.markdown(f"*{T['pr_questions_header']}*")
                    for question in pattern["questions"]:
                        st.markdown(f"- {question}")

        st.markdown(f"**{T['pr_limits_header']}**")
        for item in list(report.get("limitations") or []) + list(T["pr_standing_limits"]):
            st.markdown(f"- {item}")

    # Printable copy of the report shown above (nothing else is added).
    prepared_on = display_datetime(now_utc(), with_time=False)
    page = build_report_html(T, st.session_state.get("lang", "Español"), saved, prepared_on, created_on)
    st.download_button(
        T["pr_download_button"], data=page.encode("utf-8"),
        file_name=f"pattern-report-{saved['id']}.html", mime="text/html",
        key=f"pr_download_{saved['id']}",
    )
    st.caption(T["pr_how_to_print"])
