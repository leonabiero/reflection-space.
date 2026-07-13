import streamlit as st
from services.visit_log import get_visits, clear_visits
from services.anonymizer import anonymize
from services.language import get_lang
from config import ADMIN_PASSWORD

st.set_page_config(page_title="Visit Log", layout="centered")

# Deliberately NOT calling init_language() here (its sidebar selectbox
# reliably segfaults this specific page — confirmed by testing).
# Falls back to Spanish if this tab hasn't set a language yet, matching
# the same "always defaults to Spanish" behavior as every other page.
current_lang = st.session_state.get("lang", "Español")
T = get_lang(current_lang)

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

    rows_html = "".join(
        f"<tr><td>{page}</td><td>{lang}</td><td>{ts}</td></tr>"
        for page, lang, ts in visits
    )
    page_h = T["admin_table_page"]
    lang_h = T["admin_table_language"]
    visited_h = T["admin_table_visited"]
    table_html = f"""
    <table style="width:100%; border-collapse: collapse;">
        <thead>
            <tr style="text-align:left; border-bottom: 1px solid #444;">
                <th style="padding:6px;">{page_h}</th>
                <th style="padding:6px;">{lang_h}</th>
                <th style="padding:6px;">{visited_h}</th>
            </tr>
        </thead>
        <tbody>
            {rows_html}
        </tbody>
    </table>
    """
    st.markdown(table_html, unsafe_allow_html=True)

st.write("")
if st.button(T["admin_clear_log"]):
    clear_visits()
    st.rerun()

st.divider()

st.header(T["admin_anon_header"])
st.caption(T["admin_anon_caption"])

sample_default = T["admin_sample_default"]

demo_text = st.text_area(T["admin_sample_label"], value=sample_default, height=150)

if st.button(T["admin_run_button"]):
    result = anonymize(demo_text)
    st.markdown(f"**{T['admin_output_label']}**")
    st.code(result, language=None, wrap_lines=True)