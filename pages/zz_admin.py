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

tab_visits, tab_anonymizer = st.tabs(["Visit Log", "Anonymization Demo"])

with tab_visits:
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

with tab_anonymizer:
    st.subheader("See what leaves the system before it reaches Claude")
    st.caption(
        "Paste any sample text below (use fake details only — this is for "
        "demonstration, not a place to process real case notes). This runs "
        "the exact same anonymize() function that every document passes "
        "through in reflection_service.py before it is sent to the AI API."
    )

    sample_default = (
        "On 15/02/2026 the client, Sarah Kimani, of ID number 9988776655, "
        "attended a follow-up meeting. She can be reached at "
        "+254 722 334 455 or sarah.kimani@testmail.com. "
        "Mr. David Otieno was the assigned caseworker."
    )

    demo_text = st.text_area(
        "Sample text (fake details only)",
        value=sample_default,
        height=150,
    )

    if st.button("Run anonymizer"):
        result = anonymize(demo_text)
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**Before (what you typed)**")
            st.text_area("Before", value=demo_text, height=200, disabled=True, label_visibility="collapsed")
        with col2:
            st.markdown("**After (what is sent to Claude)**")
            st.text_area("After", value=result, height=200, disabled=True, label_visibility="collapsed")

        st.success(
            "This is the exact anonymized text that leaves the system. "
            "Names, ID numbers, phone numbers, emails, and dates are "
            "replaced with generic tags before any document reaches the "
            "Claude API."
        )