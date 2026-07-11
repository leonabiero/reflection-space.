import streamlit as st
from services.visit_log import get_visits, clear_visits
from services.anonymizer import anonymize
from services.language import init_language
from config import ADMIN_PASSWORD

st.set_page_config(page_title="Visit Log", layout="centered")

T = init_language()

st.title(T["admin_title"])

if "admin_authed" not in st.session_state:
    st.session_state.admin_authed = False

if not st.session_state.admin_authed:
    pw = st.text_input(T["admin_password_label"], type="password")
    if st.button(T["admin_enter_button"]):
        if ADMIN_PASSWORD and pw == ADMIN_PASSWORD:
            st.session_state.admin_authed = True
            st.rerun()
        else:
            st.error(T["admin_incorrect_password"])
    st.stop()

st.header(T["admin_visit_log"])
visits = get_visits()

if not visits:
    st.info(T["admin_no_visits"])
else:
    st.write(f"**{len(visits)} {T['admin_total_views_label']}**")
    st.dataframe(
        [{"Page": p, "Language": lang, "Visited at": ts} for p, lang, ts in visits],
        use_container_width=True,
        hide_index=True,
    )

if st.button(T["admin_clear_log"]):
    clear_visits()
    st.rerun()

st.divider()

st.header(T["admin_anon_header"])
st.caption(T["admin_anon_caption"])

sample_default = (
    "On 15/02/2026 the client, Sarah Kimani, of ID number 9988776655, "
    "attended a follow-up meeting. She can be reached at "
    "+254 722 334 455 or sarah.kimani@testmail.com. "
    "Mr. David Otieno was the assigned caseworker."
)

demo_text = st.text_area(T["admin_sample_label"], value=sample_default, height=150)

if st.button(T["admin_run_button"]):
    result = anonymize(demo_text)
    st.markdown(f"**{T['admin_output_label']}**")
    st.code(result, language=None, wrap_lines=True)