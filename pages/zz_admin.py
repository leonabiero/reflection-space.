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

    # Plain HTML table instead of st.dataframe() — avoids the pyarrow
    # code path that was causing a segfault on this page.
    rows_html = "".join(
        f"<tr><td>{page}</td><td>{lang}</td><td>{ts}</td></tr>"
        for page, lang, ts in visits
    )
    table_html = f"""
    <table style="width:100%; border-collapse: collapse;">
        <thead>
            <tr style="text-align:left; border-bottom: 1px solid #444;">
                <th style="padding:6px;">Page</th>
                <th style="padding:6px;">Language</th>
                <th style="padding:6px;">Visited at</th>
            </tr>
        </thead>
        <tbody>
            {rows_html}
        </tbody>
    </table>
    """
    st.markdown(table_html, unsafe_allow_html=True)

st.write("")
if st.button("Clear log"):
    clear_visits()
    st.rerun()

st.divider()

st.header("Anonymization Demo")
st.caption("Paste sample text (fake details only) to test the anonymizer.")

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
    st.code(result, language=None, wrap_lines=True)