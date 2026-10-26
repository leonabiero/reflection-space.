import streamlit as st
from services.draft_storage import (
    restore_draft, get_pending_deletions, purge_expired_deletions,
)
from services.feedback_store import get_all_feedback, get_feedback_summary
from services import reflection_records
from services.findings_ui import render_evidence
from services.language import init_language
from navigation.router import render_nav
from services.identity import init_identity, render_identity_footer, can_see_case_history, require_work_mode
from services.error_log import error_boundary
from services.confirm_state import is_confirming, start_confirming, clear_confirming
from config import CASE_HISTORY_MAX_RESULTS, CASE_HISTORY_FEEDBACK_MAX_RESULTS

# =====================================================================
# Case History -- now a history of REFLECTIONS
# =====================================================================
#
# Reflection-only redesign (October 2026, agreed with the EDE team --
# see REFLECTIONS.md): Reflection Space no longer stores case documents,
# so this management screen shows saved reflections instead: each one by
# its neutral code, case tags, note type and date, with the AI's
# observations, questions and verified anonymised passages.
#
# It NEVER shows case text (none is stored) and NEVER shows a
# professional's private notes on an observation. Access is limited to
# management roles here AND inside services/reflection_records.py.
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

    is_admin = user_role == "System Administrator"

    def _tag_label(key):
        return T["case_tag_labels"].get(key, key.replace("_", " ").title())

    # -----------------------------------------------------------------
    # Usefulness feedback (unchanged). The average is computed in
    # PostgreSQL; the list is capped to the most recent entries.
    # -----------------------------------------------------------------
    st.subheader(T["feedback_section_header"])
    feedback_summary = get_feedback_summary()
    recent_feedback = get_all_feedback(limit=CASE_HISTORY_FEEDBACK_MAX_RESULTS)

    if feedback_summary["count"] == 0:
        st.info(T["feedback_no_items"])
    else:
        rated_count = sum(feedback_summary["distribution"].values())
        if rated_count:
            average = feedback_summary["average"]
            st.write(f"**{T['feedback_average_label']}:** {average:.1f} / 5  ({rated_count})")

        if feedback_summary["count"] > CASE_HISTORY_FEEDBACK_MAX_RESULTS:
            st.caption(T["feedback_showing_recent"].format(
                shown=len(recent_feedback), total=feedback_summary["count"],
            ))

        for row in recent_feedback:
            fb_id, reference, rating, comment, submitted_by, submitted_by_role, submitted_at = row
            role_label = T.get("role_labels", {}).get(submitted_by_role, submitted_by_role)
            stars = "⭐" * (rating or 0)
            line = f"{stars} ({rating}/5) — {submitted_by or T['unknown_label']}, {role_label} — {submitted_at[:16] if submitted_at else ''}"
            st.write(line)
            if comment:
                st.caption(comment)

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

    findings_by_run = reflection_records.get_findings_for_reflections(
        user_role, [r["run_id"] for r in reflections],
    )

    for record in reflections:
        tags_text = ", ".join(_tag_label(t) for t in record["case_tags"]) or T["rs_no_tags"]
        date_part = (record["created_at"] or "")[:16]
        header = f"🪞 {record['code'] or T['reflection_no_case_ref']} — {date_part} — {tags_text}"

        with st.expander(header):
            role_label = T.get("role_labels", {}).get(record["created_by_role"], record["created_by_role"])
            st.caption(f"{T['ch_author_label']}: {record['created_by'] or T['unknown_label']}, {role_label}")
            if record["note_type"]:
                st.caption(f"{T['rs_note_type_label']}: {record['note_type']}")
            if record["previous_code"]:
                st.caption(f"🔗 {T['ch_linked_label']}: {record['previous_code']}")

            findings = findings_by_run.get(record["run_id"], [])
            if not findings:
                st.info(T["ch_no_observations"])
            for finding in findings:
                label = T["section_labels"].get(finding["module"], finding["module"].replace("_", " ").title())
                st.markdown(f"**{label}**")
                if finding["observation"]:
                    st.write(finding["observation"])
                render_evidence(T, finding["evidence"], finding["unverified_quote_count"])
                for q in finding["questions"]:
                    st.markdown(f"- {q}")

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
