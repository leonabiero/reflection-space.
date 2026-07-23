import streamlit as st
from services.language import init_language, render_nav
from services.visit_log import log_visit
from services.identity import init_identity, render_identity_footer, can_see_learning
from services.reflection_log import get_recent_theme_counts, THEME_KEYS

T = init_language()
log_visit("learning", st.session_state.lang)
user_name, user_role = init_identity(T)
render_nav(T)
render_identity_footer(T)

st.title(T["nav_learning"])

# Access gate: this page is meant to be visible only to Supervisor /
# Programme Manager / System Administrator (see LEARNING_VISIBLE_ROLES
# in services/identity.py). render_nav() already hides the sidebar link
# for other roles, but that alone doesn't stop someone from opening this
# page directly by URL -- this check is what actually enforces it, the
# same way every other supervisory page (case_history.py, audit_log.py,
# team_learning.py, research_metrics_PAGE.py) already does.
if not can_see_learning(user_role):
    st.info(T["learning_no_data"])
    st.stop()

st.write(T["learning_phase2"])

WINDOW = 10
counts, total = get_recent_theme_counts(limit=WINDOW)

if total == 0:
    st.info(T["learning_no_data"])
else:
    st.caption(T["learning_preview_caption"].format(total=total))

    for i, key in enumerate(THEME_KEYS):
        theme_label = T["themes"][i]
        count = counts.get(key, 0)
        st.write(f"**{theme_label}**")
        st.progress(count / total)
        st.caption(T["learning_flagged_caption"].format(count=count, total=total))