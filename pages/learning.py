import streamlit as st
from services.language import init_language, render_nav
from services.visit_log import log_visit
from services.identity import init_identity, render_identity_footer

T = init_language()
log_visit("learning", st.session_state.lang)
init_identity(T)
render_nav(T)
render_identity_footer(T)

st.title(T["nav_learning"])
st.write(T["learning_phase2"])
st.caption("Preview — illustrative data, not yet live")

mock_values = [7, 9, 4, 6, 3, 8, 5, 6]
mock_counts = {T["themes"][i]: mock_values[i] for i in range(len(T["themes"]))}

for theme, count in mock_counts.items():
    st.write(f"**{theme}**")
    st.progress(count / 10)
    st.caption(f"Flagged in {count} of the last 10 reflections")