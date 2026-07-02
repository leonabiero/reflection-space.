import streamlit as st
from services.draft_storage import init_db
from services.language import init_language
from services.visit_log import log_visit

st.set_page_config(page_title="Reflection Space", layout="centered")
init_db()

T = init_language()
log_visit("home", st.session_state.lang)

st.title(T["title"])
st.write(T["home_subtitle"])
st.markdown(T["nav_hint"])

st.sidebar.success(T["nav_header"])
st.sidebar.page_link("pages/documentation.py", label=T["nav_doc"])
st.sidebar.page_link("pages/reflection_space.py", label=T["nav_reflection"])
st.sidebar.page_link("pages/learning.py", label=T["nav_learning"])