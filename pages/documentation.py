import streamlit as st
from services.draft_storage import save_draft
from services.language import init_language
from navigation.router import render_nav
from services.identity import init_identity, render_identity_footer, require_work_mode
from services.error_log import error_boundary
from services import document_import

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
    # Optional: bring in an existing document. Only the TEXT is read (the file
    # itself is never stored) and it is placed in the box below so the
    # professional can check and edit it before saving.
    text_key = f"text_{st.session_state.doc_reset}"
    imported_key = f"doc_imported_{st.session_state.doc_reset}"
    uploaded = st.file_uploader(
        T["doc_import_label"],
        type=list(document_import.ALLOWED_EXTENSIONS),
        key=f"doc_import_{st.session_state.doc_reset}",
        help=T["doc_import_help"].format(
            max_mb=document_import.MAX_FILE_BYTES // (1024 * 1024),
            max_pages=document_import.MAX_PDF_PAGES,
            max_chars=document_import.MAX_CHARS,
        ),
    )
    if uploaded is None:
        st.session_state.pop(imported_key, None)
    elif st.session_state.get(imported_key, {}).get("file_id") != uploaded.file_id:
        try:
            extracted = document_import.extract_text(uploaded.name, uploaded.getvalue())
            current = st.session_state.get(text_key, "")
            st.session_state[text_key] = (current.rstrip() + "\n\n" + extracted) if current.strip() else extracted
            st.session_state[imported_key] = {"file_id": uploaded.file_id, "error": None}
        except document_import.DocumentImportError as exc:
            st.session_state[imported_key] = {"file_id": uploaded.file_id, "error": exc.reason}
    outcome = st.session_state.get(imported_key)
    if outcome:
        if outcome["error"]:
            st.error(T["doc_import_errors"].get(outcome["error"], T["doc_import_errors"]["unreadable"]).format(
                max_mb=document_import.MAX_FILE_BYTES // (1024 * 1024),
                max_pages=document_import.MAX_PDF_PAGES,
                max_chars=document_import.MAX_CHARS,
            ))
        else:
            st.success(T["doc_import_loaded"])

    text = st.text_area(T["text"], key=text_key)

    if st.button(T["save"]):
        if text.strip():
            save_draft(case_ref, doc_type, language, text, user_name, user_role)
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