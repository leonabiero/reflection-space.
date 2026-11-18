import streamlit as st

from services.language import init_language
from navigation.router import render_nav
from services.identity import init_identity, render_identity_footer, require_work_mode
from services.error_log import error_boundary
from services.pattern_access import can_review_patterns
from services import pattern_text_store, pattern_text_analysis
from services.pattern_report_html import build_report_html, period_phrase
from services.db_time import display_datetime, now_utc
from services import reflection_records
from services.feedback_store import get_feedback_summary
from services.confirm_state import is_confirming, start_confirming, clear_confirming
from config import (
    PATTERN_MIN_MONTHS, PATTERN_MAX_MONTHS, PATTERN_DEFAULT_MONTHS,
    PATTERN_MIN_TEXTS, ORIGINAL_TEXT_RETENTION_MONTHS,
)

# Pattern Review
# ================
#
# Redesigned 15 November 2026 (product owner's decision -- see
# PATTERNS.md). For EDE's management team (Supervisors and Programme
# Managers) ONLY.
#
# Patterns are looked for in what social workers WROTE (the original texts
# the app already keeps, anonymised again before the AI reads them), not
# in what the AI said back to them. A manager types a period -- any whole
# number of months from 1 to 15 (17 November 2026; it used to be a choice
# of 3, 6, 9 or 12) -- and presses
# "Identify patterns"; the AI reads that period's texts and writes one
# report, which is saved with its date and period.
#
# Since 15 November 2026 this is the only page in Manager mode (Case
# History was removed), so it also shows the average usefulness rating.
#
# Hard rules this page must never break:
#   - Managers see the REPORT only: never a text, a quotation, a
#     reflection code or who wrote anything (the texts go to the AI only --
#     services/pattern_text_store.py has no function that returns them for
#     display, and services/pattern_text_analysis.py removes any part of
#     the report that repeats a passage).
#   - It speaks of candidate patterns for reflection, never conclusions.
#   - Nothing runs with fewer than PATTERN_MIN_TEXTS texts.
#
# Since 18 November 2026 a manager can delete a report once they have
# downloaded it ("I have the file: delete report", with an "are you
# sure?" step), or all saved reports at once. Downloading never deletes.

GENERATING_KEY = "_pr_generating"
FLASH_KEY = "_pr_flash"
SELECTED_KEY = "_pr_selected_report"
CONFIRM_DELETE_ALL_KEY = "_pr_confirm_delete_all"


def _after_delete(message_kind, message):
    """Forget which report was on screen (it may be gone) and show a
    short message after the page reloads."""
    st.session_state.pop(SELECTED_KEY, None)
    st.session_state.pop("pr_report_select_box", None)
    st.session_state[FLASH_KEY] = (message_kind, message)
    st.rerun()

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

    # Usefulness rating (moved here on 15 November 2026 when Case History
    # was removed): the AVERAGE only, never individual ratings, comments or
    # who gave them. Best effort -- never blocks the page.
    try:
        rating = get_feedback_summary()
        rated = sum(rating["distribution"].values())
    except Exception:
        rating, rated = None, 0
    if rated:
        st.caption(T["pr_rating_line"].format(average=f"{rating['average']:.1f}", count=rated))
    else:
        st.caption(T["pr_rating_none"])

    st.info(T["pr_intro"])

    flash = st.session_state.pop(FLASH_KEY, None)
    if flash:
        kind, message = flash
        getattr(st, kind)(message)

    # Texts past their time limit are cleared here too (best effort; an
    # expired text is never used either way).
    try:
        reflection_records.purge_expired_original_text()
    except Exception:
        pass

    # ------------------------------------------------------------------
    # 1. Identify patterns
    # ------------------------------------------------------------------
    st.subheader(T["pr_new_header"])
    st.caption(T["pr_texts_note"].format(months=ORIGINAL_TEXT_RETENTION_MONTHS))

    # A box where the manager types the number of months (whole numbers
    # only, PATTERN_MIN_MONTHS to PATTERN_MAX_MONTHS). The service layer
    # checks the same limits again (pattern_text_store._clean_period).
    period = int(st.number_input(
        T["pr_period_label"].format(minimum=PATTERN_MIN_MONTHS, maximum=PATTERN_MAX_MONTHS),
        min_value=PATTERN_MIN_MONTHS,
        max_value=PATTERN_MAX_MONTHS,
        value=PATTERN_DEFAULT_MONTHS,
        step=1,
        format="%d",
        help=T["pr_period_help"].format(maximum=PATTERN_MAX_MONTHS),
        key="pr_period_months",
    ))

    available = pattern_text_store.count_texts_for_period(user_role, period)
    st.write(T["pr_available"].format(count=available, period=period_phrase(T, period)))
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
            period=period_phrase(T, by_id[i]["period_months"]),
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
            date=created_on, period=period_phrase(T, saved["period_months"]),
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

    # ------------------------------------------------------------------
    # 3. Deleting reports (18 November 2026, product owner's decision)
    # ------------------------------------------------------------------
    # Downloading never deletes anything. Once the manager has the file,
    # a separate button deletes the report for good, after an "are you
    # sure?" step. Reports are shared by the whole management team, so the
    # warning says so. The service layer checks the role again
    # (pattern_text_store.delete_report / delete_all_reports).
    confirm_key = f"_pr_confirm_delete_{saved['id']}"
    if not is_confirming(confirm_key):
        if st.button(T["pr_delete_button"], key=f"pr_delete_{saved['id']}"):
            clear_confirming(CONFIRM_DELETE_ALL_KEY)
            start_confirming(confirm_key)
            st.rerun()
    else:
        st.warning(T["pr_delete_confirm"])
        yes_col, no_col = st.columns(2)
        with yes_col:
            if st.button(T["pr_delete_yes"], type="primary", key=f"pr_delete_yes_{saved['id']}"):
                clear_confirming(confirm_key)
                try:
                    deleted = pattern_text_store.delete_report(user_role, user_name, saved["id"])
                except Exception:
                    deleted = None
                if deleted:
                    _after_delete("success", T["pr_delete_done"])
                elif deleted is False:
                    _after_delete("info", T["pr_delete_already_gone"])
                else:
                    _after_delete("error", T["pr_delete_failed"])
        with no_col:
            if st.button(T["pr_delete_cancel"], key=f"pr_delete_cancel_{saved['id']}"):
                clear_confirming(confirm_key)
                st.rerun()

    # With two or more saved reports, all of them can be deleted at once.
    if len(reports) > 1:
        st.divider()
        if not is_confirming(CONFIRM_DELETE_ALL_KEY):
            if st.button(T["pr_delete_all_button"], key="pr_delete_all"):
                clear_confirming(confirm_key)
                start_confirming(CONFIRM_DELETE_ALL_KEY)
                st.rerun()
        else:
            st.warning(T["pr_delete_all_confirm"].format(count=len(reports)))
            yes_col, no_col = st.columns(2)
            with yes_col:
                if st.button(T["pr_delete_yes"], type="primary", key="pr_delete_all_yes"):
                    clear_confirming(CONFIRM_DELETE_ALL_KEY)
                    try:
                        count = pattern_text_store.delete_all_reports(user_role, user_name)
                    except Exception:
                        count = None
                    if count is None:
                        _after_delete("error", T["pr_delete_failed"])
                    else:
                        _after_delete("success", T["pr_delete_all_done"].format(count=count))
            with no_col:
                if st.button(T["pr_delete_cancel"], key="pr_delete_all_cancel"):
                    clear_confirming(CONFIRM_DELETE_ALL_KEY)
                    st.rerun()
