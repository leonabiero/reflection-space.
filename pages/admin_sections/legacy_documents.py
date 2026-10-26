"""System Administration -- Erase old stored documents.

Reflection-only redesign (October 2026, agreed with the EDE team -- see
REFLECTIONS.md). Reflection Space no longer stores case documents; the
EDE decision was to erase the ones saved before the change. This panel
lets a System Administrator do that deliberately, once, after typing a
confirmation word. Nothing is ever erased automatically.

What is erased (services/draft_storage.erase_all_stored_documents):
every old document, its edit history, every reflection generated from
those old documents (with their observations and notes) and their search
copies. Reflections created with the new screen are not touched.
"""
import streamlit as st

from services.draft_storage import count_all_stored_documents, erase_all_stored_documents


def render(T):
    with st.expander(T["admin_legacy_docs_header"]):
        try:
            remaining = count_all_stored_documents()
        except Exception:
            st.error(T["admin_legacy_docs_count_failed"])
            return

        flash = st.session_state.pop("_legacy_docs_flash", None)
        if flash:
            st.success(flash)

        if remaining == 0:
            st.success(T["admin_legacy_docs_none"])
            return

        st.warning(T["admin_legacy_docs_count"].format(count=remaining))
        st.caption(T["admin_legacy_docs_caption"])

        confirm_word = T["admin_legacy_docs_confirm_word"]
        typed = st.text_input(
            T["admin_legacy_docs_confirm_label"].format(word=confirm_word),
            key="legacy_docs_confirm_input",
        )
        if st.button(
            T["admin_legacy_docs_button"],
            type="primary",
            disabled=(typed or "").strip().upper() != confirm_word.upper(),
            key="legacy_docs_erase_btn",
        ):
            erased = erase_all_stored_documents(
                st.session_state.get("user_name", ""),
                st.session_state.get("user_role", ""),
            )
            if erased is None:
                st.error(T["admin_legacy_docs_refused"])
            else:
                st.session_state.pop("legacy_docs_confirm_input", None)
                st.session_state["_legacy_docs_flash"] = T["admin_legacy_docs_done"].format(count=erased)
                st.rerun()
