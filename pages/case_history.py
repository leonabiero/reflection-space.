import streamlit as st
from services.draft_storage import get_completed_drafts, get_draft_history
from services.language import init_language, render_nav
from services.visit_log import log_visit
from services.identity import init_identity, render_identity_footer, can_see_case_history

T = init_language()
log_visit("case_history", st.session_state.lang)
user_name, user_role = init_identity(T)
render_nav(T)
render_identity_footer(T)

# Role gate: same tier as Learning. This hides the page's content for
# unauthorized roles, but (like the Learning link) does not block
# direct URL access on its own — real access control is the login
# system in services/identity.py, this just controls what's shown.
if not can_see_case_history(user_role):
    st.title(T["case_history_title"])
    st.info(T["case_history_no_items"])
    st.stop()

st.title(T["case_history_title"])

completed = get_completed_drafts()

if not completed:
    st.info(T["case_history_no_items"])
    st.stop()

for row in completed:
    draft_id, case_ref, doc_type, content, created_at, created_by, created_by_role, was_edited = row

    role_label = T.get("role_labels", {}).get(created_by_role, created_by_role)
    edited_label = T["case_history_edited_label"] if was_edited else T["case_history_not_edited_label"]
    badge = "🖊️" if was_edited else "✅"

    with st.expander(f"{badge} {case_ref} - {doc_type} — {created_by or 'Unknown'}, {role_label} ({created_at})"):
        st.caption(edited_label)
        st.markdown(f"**{T['case_history_current_label']}**")
        st.write(content)

        if was_edited:
            history = get_draft_history(draft_id)
            if history:
                st.markdown(f"**{T['case_history_original_label']}**")
                # history is ordered oldest-first; the first entry is
                # the version that existed before any edit was made.
                original_content, saved_at = history[0]
                st.write(original_content)