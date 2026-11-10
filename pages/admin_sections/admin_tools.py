"""System Administration -- Section 7: Administrative Tools.

Extracted unchanged from the original system_administration.py file.
"""
import streamlit as st

from services.anonymizer import anonymize

def render(T):
    with st.expander(T["admin_tools_header"]):
        st.subheader(T["admin_tools_anon_test_header"])
        st.caption(T["admin_anon_caption"])
        # The result is kept in session_state (not only shown on the click
        # rerun) so it does not vanish the moment anything else on this long
        # page causes a rerun. An empty sample now shows a clear message
        # instead of doing nothing.
        sample = st.text_area(T["admin_sample_label"], key="admin_anon_sample")
        if st.button(T["admin_run_button"], key="admin_anon_run"):
            if not (sample or "").strip():
                st.session_state.pop("admin_anon_result", None)
                st.warning(T["admin_anon_empty_warning"])
            else:
                st.session_state["admin_anon_result"] = {
                    "input": sample,
                    "output": anonymize(sample),
                }

        result = st.session_state.get("admin_anon_result")
        if result:
            st.markdown(T["admin_output_label"])
            st.code(result["output"], language=None, wrap_lines=True)
            if result["output"] == result["input"]:
                st.info(T["admin_anon_no_changes"])
            if result["input"] != sample:
                st.caption(T["admin_anon_stale_note"])
            st.caption(T["admin_anon_tags_help"])

        st.divider()
        st.caption(T["admin_tools_future"])
