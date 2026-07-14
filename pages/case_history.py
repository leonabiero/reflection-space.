import streamlit as st
from collections import defaultdict
from services.draft_storage import get_completed_drafts, get_draft_history
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

# --- Feedback section ---
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

# --- Case history section ---
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

                st.divider()