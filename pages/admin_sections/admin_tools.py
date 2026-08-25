"""System Administration -- Section 7: Administrative Tools.

Extracted unchanged from the original system_administration.py file.
"""
import streamlit as st

from services.anonymizer import anonymize
from services.qdrant_service import is_available as qdrant_available, admin_reset_collection
from services.confirm_state import is_confirming, start_confirming, clear_confirming

def render(T):
    with st.expander(T["admin_tools_header"]):
        st.subheader(T["admin_tools_anon_test_header"])
        st.caption(T["admin_anon_caption"])
        sample = st.text_area(T["admin_sample_label"], key="admin_anon_sample")
        if st.button(T["admin_run_button"]):
            st.code(anonymize(sample))

        st.divider()

        # --- Reset Search Index (Qdrant) ------------------------------------
        # See services/qdrant_service.py -- admin_reset_collection() is the
        # ONE deliberate exception to that module's rule of never deleting
        # or recreating the Qdrant collection on its own. It exists exactly
        # for this situation: a collection built for a previous embedding
        # provider/model (e.g. Voyage AI's 512-dimensional vectors) that is
        # incompatible with the currently configured one (e.g. Gemini's
        # 768-dimensional vectors). This is the only place in the app that
        # is allowed to call it, and only after an explicit two-step
        # confirmation, matching the same confirm/cancel pattern already
        # used for case/document deletion elsewhere (pages/case_history.py,
        # pages/reflection_space.py).
        st.subheader(T["admin_tools_reset_index_header"])
        st.caption(T["admin_tools_reset_index_caption"])

        if not qdrant_available():
            st.info(T["admin_tools_reset_index_unavailable"])
        else:
            reset_confirm_key = "confirm_reset_qdrant_index"
            if is_confirming(reset_confirm_key):
                st.warning(T["admin_tools_reset_index_warning"])
                if st.button(T["admin_tools_reset_index_yes"], key="yes_reset_qdrant_index"):
                    success, reason = admin_reset_collection(confirm=True)
                    clear_confirming(reset_confirm_key)
                    if success:
                        st.success(T["admin_tools_reset_index_success"])
                    else:
                        st.error(f"{T['admin_tools_reset_index_failed']} {reason}")
                    st.rerun()
                if st.button(T["admin_tools_reset_index_cancel"], key="cancel_reset_qdrant_index"):
                    clear_confirming(reset_confirm_key)
                    st.rerun()
            else:
                if st.button(T["admin_tools_reset_index_button"], key="reset_qdrant_index"):
                    start_confirming(reset_confirm_key)
                    st.rerun()

        st.divider()
        st.caption(T["admin_tools_future"])
