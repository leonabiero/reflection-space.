import streamlit as st
from services.draft_storage import (
    restore_draft, get_pending_deletions, purge_expired_deletions,
)
from services.feedback_store import get_feedback_summary
from services import reflection_records
from services.db_time import display_datetime
from services.language import init_language
from navigation.router import render_nav
from services.identity import init_identity, render_identity_footer, can_see_case_history, require_work_mode
from services.error_log import error_boundary
from services.confirm_state import is_confirming, start_confirming, clear_confirming
from config import CASE_HISTORY_MAX_RESULTS

# =====================================================================
# Case History -- now a history of REFLECTIONS
# =====================================================================
#
# Reflection-only redesign (October 2026, agreed with the EDE team --
# see REFLECTIONS.md): Reflection Space no longer stores case documents,
# so this management screen shows saved reflections instead.
#
# 15 November 2026 (product owner's decision): the AI's observations and
# questions are no longer saved, so each reflection is now one short line:
# its neutral code, the date (Bilbao time), its themes if it has any, and
# who did it. The AI summary and the folded observations were removed.
#
# It NEVER shows any text (original or anonymised) and NEVER shows a
# professional's private notes. Managers look for patterns in Pattern
# Review, which shows a report only. Access is limited to management
# roles here AND inside services/reflection_records.py.
# =====================================================================

T = init_language()
user_name, user_role = init_identity(T)
require_work_mode(T, "Manager")
render_nav(T, page_name="case_history")
render_identity_footer(T)

with error_boundary(
    "case_history", T=T, user_name=user_name, user_role=user_role,
):

    st.title(T["case_history_title"])

    if not can_see_case_history(user_role):
        st.info(T["case_history_no_items"])
        st.stop()

    # Documents stored before the redesign may still be inside their
    # 48-hour deletion window; this finishes their erasure on time.
    purge_expired_deletions()

    # Saved anonymised text past its retention period is cleared here too
    # (best effort; expired text is never shown either way).
    try:
        reflection_records.purge_expired_anonymised_text()
    except Exception:
        pass
    try:
        reflection_records.purge_expired_reflection_deletions()
    except Exception:
        pass

    is_admin = user_role == "System Administrator"

    def _tag_label(key):
        return T["case_tag_labels"].get(key, key.replace("_", " ").title())

    # -----------------------------------------------------------------
    # Usefulness feedback -- the AVERAGE rating only (November 2026,
    # product owner's decision). Individual ratings, comments and the
    # names of the people who gave them are deliberately not shown
    # here. The average is computed in PostgreSQL.
    # -----------------------------------------------------------------
    st.subheader(T["feedback_section_header"])
    feedback_summary = get_feedback_summary()
    rated_count = sum(feedback_summary["distribution"].values())

    if rated_count == 0:
        st.info(T["feedback_no_items"])
    else:
        average = feedback_summary["average"]
        st.write(f"**{T['feedback_average_label']}:** {average:.1f} / 5  ({rated_count})")

    st.divider()

    # -----------------------------------------------------------------
    # Old documents still inside their deletion window (System
    # Administrator only). Only appears while such documents exist.
    # -----------------------------------------------------------------
    if is_admin:
        pending = get_pending_deletions()
        if pending:
            st.subheader(T["case_history_pending_deletion_header"])
            for row in pending:
                draft_id, case_ref, doc_type, deleted_at, deleted_by, deleted_by_role = row
                role_label = T.get("role_labels", {}).get(deleted_by_role, deleted_by_role)
                st.write(
                    f"🗑️ {case_ref} - {doc_type} — {T['case_history_deleted_by_label']}: "
                    f"{deleted_by or T['unknown_label']}, {role_label} ({deleted_at[:16] if deleted_at else ''})"
                )
                if st.button(T["case_history_restore_button"], key=f"restore_{draft_id}"):
                    restore_draft(draft_id, user_name, user_role)
                    st.success(T["case_history_restored_success"])
                    st.rerun()
            st.divider()

    # -----------------------------------------------------------------
    # Saved reflections
    # -----------------------------------------------------------------
    st.subheader(T["ch_reflections_header"])
    st.caption(T["ch_reflections_intro"])

    flash = st.session_state.pop("_ch_flash", None)
    if flash == T["ch_delete_failed"]:
        st.error(flash)
    elif flash:
        st.success(flash)

    all_dates = reflection_records.get_reflection_dates(user_role)
    if not all_dates:
        st.info(T["case_history_no_items"])
        st.stop()

    filter_col1, filter_col2 = st.columns(2)
    with filter_col1:
        date_options = [T["case_history_all_dates"]] + all_dates
        selected_date = st.selectbox(T["case_history_date_filter_label"], date_options)
    with filter_col2:
        tag_options = [""] + list(reflection_records.CASE_TAGS)
        selected_tag = st.selectbox(
            T["ch_tag_filter_label"],
            tag_options,
            format_func=lambda k: T["ch_all_tags"] if not k else _tag_label(k),
        )

    date_filter = None if selected_date == T["case_history_all_dates"] else selected_date
    tag_filter = selected_tag or None

    # This list grows for the whole life of the pilot, so only the most
    # recent CASE_HISTORY_MAX_RESULTS matching reflections are loaded,
    # with a note when there are more (pick a date or tag to narrow).
    reflections = reflection_records.list_reflections(
        user_role, date_filter=date_filter, tag=tag_filter, limit=CASE_HISTORY_MAX_RESULTS,
    )
    total = reflection_records.count_reflections(user_role, date_filter=date_filter, tag=tag_filter)
    if total > len(reflections):
        st.caption(T["ch_showing_recent"].format(shown=len(reflections), total=total))

    if not reflections:
        st.info(T["case_history_no_items_for_filter"])
        st.stop()

    for record in reflections:
        parts = [record["code"] or T["reflection_no_case_ref"], display_datetime(record["created_at"])]
        # Themes only exist on reflections made before November 2026.
        if record["case_tags"]:
            parts.append(", ".join(_tag_label(t) for t in record["case_tags"]))
        header = "🪞 " + " — ".join(parts)

        with st.container(border=True):
            st.markdown(f"**{header}**")
            role_label = T.get("role_labels", {}).get(record["created_by_role"], record["created_by_role"])
            st.caption(f"{T['ch_author_label']}: {record['created_by'] or T['unknown_label']}, {role_label}")

            if is_admin:
                st.divider()
                confirm_key = f"confirm_delete_reflection_{record['run_id']}"
                if is_confirming(confirm_key):
                    st.warning(T["ch_delete_confirm"])
                    c1, c2 = st.columns(2)
                    with c1:
                        if st.button(T["case_history_delete_yes"], key=f"yes_delete_reflection_{record['run_id']}"):
                            deleted = reflection_records.delete_reflection(record["run_id"], user_name, user_role)
                            clear_confirming(confirm_key)
                            st.session_state["_ch_flash"] = (
                                T["ch_deleted_success"] if deleted else T["ch_delete_failed"]
                            )
                            st.rerun()
                    with c2:
                        if st.button(T["case_history_delete_cancel"], key=f"cancel_delete_reflection_{record['run_id']}"):
                            clear_confirming(confirm_key)
                            st.rerun()
                else:
                    if st.button(T["ch_delete_button"], key=f"delete_reflection_{record['run_id']}"):
                        start_confirming(confirm_key)
                        st.rerun()
