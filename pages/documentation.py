import streamlit as st
from services.draft_storage import save_draft
from services.context_prefetch import trigger_prefetch
from services.language import init_language
from navigation.router import render_nav
from services.identity import init_identity, render_identity_footer, require_work_mode
from services.error_log import error_boundary

T = init_language()
user_name, user_role = init_identity(T)
require_work_mode(T, "Practitioner")
render_nav(T, page_name="documentation")
render_identity_footer(T)

with error_boundary(
    "documentation", T=T, user_name=user_name, user_role=user_role,
):

    st.title(T["doc"])

    if "doc_reset" not in st.session_state:
        st.session_state.doc_reset = 0

    if "doc_type_idx" not in st.session_state:
        st.session_state.doc_type_idx = 0

    case_ref = st.text_input(T["case_ref"], key=f"case_ref_{st.session_state.doc_reset}")
    doc_type = st.selectbox(
        T["doc_type"],
        T["doc_types"],
        index=st.session_state.doc_type_idx,
        key=f"doc_type_{st.session_state.doc_reset}_{st.session_state.lang}",
    )
    st.session_state.doc_type_idx = T["doc_types"].index(doc_type)
    language = st.selectbox(T["language"], ["Español", "Euskera", "English"], key=f"lang_field_{st.session_state.doc_reset}")
    text = st.text_area(T["text"], key=f"text_{st.session_state.doc_reset}")

    if st.button(T["save"]):
        if text.strip():
            new_draft_id = save_draft(case_ref, doc_type, language, text, user_name, user_role)
            # Performance: kick off historical-context retrieval for this
            # draft in the background now, instead of making the
            # practitioner wait for it later at "Begin Reflection" -- see
            # services/context_prefetch.py for the full design.
            trigger_prefetch(new_draft_id, case_ref, text)
            st.session_state.doc_reset += 1
            st.session_state.doc_type_idx = 0
            st.session_state.save_status = "success"
            st.rerun()
        else:
            st.session_state.save_status = "empty"

    if "save_status" not in st.session_state:
        st.session_state.save_status = ""

    if st.session_state.save_status == "success":
        st.success(T["success"])
        # Clear immediately after showing once, so this message doesn't
        # linger on screen while the next case note is being written.
        st.session_state.save_status = ""
    elif st.session_state.save_status == "empty":
        st.warning(T["empty"])
        st.session_state.save_status = ""