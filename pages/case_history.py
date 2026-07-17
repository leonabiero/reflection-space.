import streamlit as st
from collections import defaultdict
from services.draft_storage import (
    get_completed_drafts, get_draft_history,
    soft_delete_draft, restore_draft, get_pending_deletions,
    purge_expired_deletions,
)
from services.feedback_store import get_all_feedback
from services.language import init_language, render_nav
from services.visit_log import log_visit
from services.identity import init_identity, render_identity_footer, can_see_case_history

T = init_language()
log_visit("case_history", st.session_state.lang)
user_name, user_role = init_identity(T)
render_nav(T)
render_identity_footer(T)

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
        line = f"{stars} ({rating}/5) — {submitted_by or 'Unknown'}, {role_label} — {submitted_at[:16] if submitted_at else ''}"
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
                f"{deleted_by or 'Unknown'}, {role_label} ({deleted_at[:16] if deleted_at else ''})"
            )
            if st.button(T["case_history_restore_button"], key=f"restore_{draft_id}"):
                restore_draft(draft_id, user_name, user_role)
                st.success(T["case_history_restored_success"])
                st.rerun()

    st.divider()

completed = get_completed_drafts()

if not completed:
    st.info(T["case_history_no_items"])
    st.stop()


def _date_only(iso_str):
    return (iso_str or "")[:10]


all_dates = sorted({_date_only(row[8]) for row in completed if row[8]}, reverse=True)
date_options = [T["case_history_all_dates"]] + all_dates
selected_date = st.selectbox(T["case_history_date_filter_label"], date_options)

if selected_date == T["case_history_all_dates"]:
    filtered = completed
else:
    filtered = [row for row in completed if _date_only(row[8]) == selected_date]

if not filtered:
    st.info(T["case_history_no_items_for_filter"])
    st.stop()

by_worker = defaultdict(list)
for row in filtered:
    worker = row[5] or "Unknown"
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

                st.markdown(f"**{badge} {case_ref} - {doc_type}** _(completed {timestamp})_")
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