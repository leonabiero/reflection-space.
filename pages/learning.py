import streamlit as st
from services.language import init_language, render_nav
from services.visit_log import log_visit
from services.identity import init_identity, render_identity_footer
from services.reflection_log import get_recent_theme_counts, THEME_KEYS

T = init_language()
log_visit("learning", st.session_state.lang)
init_identity(T)
render_nav(T)
render_identity_footer(T)

st.title(T["nav_learning"])
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