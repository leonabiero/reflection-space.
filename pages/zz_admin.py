import streamlit as st
from services.visit_log import get_visits, clear_visits
from services.anonymizer import anonymize
from config import ADMIN_PASSWORD

st.set_page_config(page_title="Visit Log", layout="centered")
st.title("🔒 Admin")

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

st.header("Visit Log")
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

if st.button("Clear log"):
    clear_visits()
    st.rerun()

st.divider()

st.header("Anonymization Demo")
st.caption(
    "Paste sample text (fake details only) to see what leaves the system "
    "before it reaches Claude. Runs the same anonymize() function used in "
    "reflection_service.py."
)

sample_default = (
    "On 15/02/2026 the client, Sarah Kimani, of ID number 9988776655, "
    "attended a follow-up meeting. She can be reached at "
    "+254 722 334 455 or sarah.kimani@testmail.com. "
    "Mr. David Otieno was the assigned caseworker."
)

demo_text = st.text_area("Sample text (fake details only)", value=sample_default, height=150)

if st.button("Run anonymizer"):
    result = anonymize(demo_text)
    st.markdown("**Anonymized output (what is sent to Claude):**")
    st.code(result, language=None)