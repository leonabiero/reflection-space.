import streamlit as st
from collections import defaultdict
from services.draft_storage import (
    get_completed_drafts, get_completed_draft_dates, get_draft_history,
    soft_delete_draft, restore_draft, get_pending_deletions,
    purge_expired_deletions,
)
from services.feedback_store import get_all_feedback
from services.language import init_language
from navigation.router import render_nav
from services.identity import init_identity, render_identity_footer, can_see_case_history, require_work_mode
from services.error_log import error_boundary

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

    purge_expired_deletions()

    is_admin = user_role == "System Administrator"

    st.subheader(T["feedback_section_header"])
    all_feedback = get_all_feedback()

    if not all_feedback:
        st.info(T["feedback_no_items"])
    else:
        ratings = [row[2] for row in all_feedback if row[2] is not None]
        if ratings:
            average = sum(ratings) / len(ratings)
            st.write(f"**{T['feedback_average_label']}:** {average:.1f} / 5  ({len(ratings)})")

        for row in all_feedback:
            fb_id, draft_ids, rating, comment, submitted_by, submitted_by_role, submitted_at = row
            role_label = T.get("role_labels", {}).get(submitted_by_role, submitted_by_role)
            stars = "⭐" * (rating or 0)
            line = f"{stars} ({rating}/5) — {submitted_by or T['unknown_label']}, {role_label} — {submitted_at[:16] if submitted_at else ''}"
            st.write(line)
            if comment:
                st.caption(comment)

    st.divider()

    if is_admin:
        st.subheader(T["case_history_pending_deletion_header"])
        pending = get_pending_deletions()

        if not pending:
            st.info(T["case_history_pending_deletion_no_items"])
        else:
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

    # Scalability pass: the date filter's options are now computed with
    # a SQL aggregation (get_completed_draft_dates(), `SELECT DISTINCT
    # completed_at::date`) instead of first fetching every completed
    # document's full content org-wide just to compute this list in
    # Python. If there are no completed-document dates at all, there
    # are no completed documents -- same empty state as before.
    all_dates = get_completed_draft_dates()

    if not all_dates:
        st.info(T["case_history_no_items"])
        st.stop()

    date_options = [T["case_history_all_dates"]] + all_dates
    selected_date = st.selectbox(T["case_history_date_filter_label"], date_options)

    # "All dates" still needs the full org-wide set (this page's
    # grouped-by-worker view is intentionally org-wide, unlike the
    # per-case retrieval paths in rdi/retrieval_service.py). Selecting
    # one date now filters in SQL (`date_filter=`) instead of loading
    # every completed document and discarding everything that doesn't
    # match the selected date in Python.
    if selected_date == T["case_history_all_dates"]:
        filtered = get_completed_drafts()
    else:
        filtered = get_completed_drafts(date_filter=selected_date)

    if not filtered:
        st.info(T["case_history_no_items_for_filter"])
        st.stop()

    by_worker = defaultdict(list)
    for row in filtered:
        worker = row[5] or T["unknown_label"]
        by_worker[worker].append(row)

    for worker in sorted(by_worker.keys(), key=lambda s: s.lower()):
        worker_rows = by_worker[worker]
        role_label = T.get("role_labels", {}).get(worker_rows[0][6], worker_rows[0][6])

        with st.expander(f"📁 {worker} ({role_label}) — {len(worker_rows)}"):
            toggle = st.radio(
                T["case_history_toggle_label"],
                [T["case_history_edited_option"], T["case_history_not_edited_option"]],
                horizontal=True,
                key=f"toggle_{worker}",
            )
            show_edited = toggle == T["case_history_edited_option"]
            subset = [r for r in worker_rows if r[7] == show_edited]

            if not subset:
                st.info(T["case_history_no_items_for_filter"])
            else:
                for row in subset:
                    draft_id, case_ref, doc_type, content, created_at, created_by, created_by_role, was_edited, completed_at = row
                    badge = "🖊️" if was_edited else "✅"
                    timestamp = completed_at[:16] if completed_at else ""

                    st.markdown(f"**{badge} {case_ref} - {doc_type}** _({T['case_history_completed_label']} {timestamp})_")
                    st.markdown(f"*{T['case_history_current_label']}*")
                    st.write(content)

                    if was_edited:
                        history = get_draft_history(draft_id)
                        if history:
                            st.markdown(f"*{T['case_history_original_label']}*")
                            original_content, saved_at = history[0]
                            st.write(original_content)

                    if is_admin:
                        confirm_key = f"confirm_delete_{draft_id}"
                        if st.session_state.get(confirm_key, False):
                            st.warning(T["case_history_delete_confirm"])
                            c1, c2 = st.columns(2)
                            with c1:
                                if st.button(T["case_history_delete_yes"], key=f"yes_delete_{draft_id}"):
                                    soft_delete_draft(draft_id, user_name, user_role)
                                    st.session_state.pop(confirm_key, None)
                                    st.success(T["case_history_deleted_success"])
                                    st.rerun()
                            with c2:
                                if st.button(T["case_history_delete_cancel"], key=f"cancel_delete_{draft_id}"):
                                    st.session_state.pop(confirm_key, None)
                                    st.rerun()
                        else:
                            if st.button(T["case_history_delete_button"], key=f"delete_{draft_id}"):
                                st.session_state[confirm_key] = True
                                st.rerun()

                    st.divider()