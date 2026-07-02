import streamlit as st
from services.visit_log import get_visits, clear_visits
from config import ADMIN_PASSWORD

st.set_page_config(page_title="Visit Log", layout="centered")
st.title("🔒 Visit Log")

if "admin_authed" not in st.session_state:
    st.session_state.admin_authed = False

if not st.session_state.admin_authed:
    pw = st.text_input("Password", type="password")
    if st.button("Enter"):
        if ADMIN_PASSWORD and pw == ADMIN_PASSWORD:
            st.session_state.admin_authed = True
            st.rerun()
        else:
            st.error("Incorrect password.")
    st.stop()

visits = get_visits()

if not visits:
    st.info("No visits logged yet.")
else:
    st.write(f"**{len(visits)} total page views**")
    st.dataframe(
        [{"Page": p, "Language": lang, "Visited at": ts} for p, lang, ts in visits],
        use_container_width=True,
        hide_index=True,
    )

st.divider()
if st.button("Clear log"):
    clear_visits()
    st.rerun()