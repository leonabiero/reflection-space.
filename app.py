import streamlit as st
from services.draft_storage import init_db
from services.language import init_language, render_nav
from services.visit_log import log_visit

st.set_page_config(page_title="Reflection Space", layout="centered")
init_db()

T = init_language()
log_visit("home", st.session_state.lang)
render_nav(T)

st.title(T["title"])
st.write(T["home_subtitle"])
st.markdown(T["nav_hint"])