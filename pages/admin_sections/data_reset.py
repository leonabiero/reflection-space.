"""System Administration -- Erase all data ("start from zero").

November 2026, product owner's decision: everything saved so far was
synthetic test data, so the real pilot starts from a clean slate with
every count in the app at 0. This panel lets a System Administrator do
that deliberately, after typing a confirmation word. Nothing is ever
erased automatically.

What is erased and what is kept is defined (and enforced) in
services/data_reset.py -- the role check lives there too, not only here.

Architectural rule kept: no st.dataframe(), st.tabs() or st.columns()
on the System Administration page.
"""
import streamlit as st

from services import data_reset


def render(T):
    with st.expander(T["admin_reset_header"], expanded=False):
        flash = st.session_state.pop("_data_reset_flash", None)
        if flash:
            st.success(flash)

        st.write(T["admin_reset_intro"])
        st.caption(T["admin_reset_kept_note"])
        st.warning(T["admin_reset_warning"])

        confirm_word = T["admin_reset_confirm_word"]
        typed = st.text_input(
            T["admin_reset_confirm_label"].format(word=confirm_word),
            key="data_reset_confirm_input",
        )
        if st.button(
            T["admin_reset_button"],
            type="primary",
            disabled=(typed or "").strip().upper() != confirm_word.upper(),
            key="data_reset_erase_btn",
        ):
            try:
                result = data_reset.erase_all_data(
                    st.session_state.get("user_name", ""),
                    st.session_state.get("user_role", ""),
                )
            except Exception:
                # Single transaction: a failure means nothing was erased.
                st.error(T["admin_reset_failed"])
                return

            if result is None:
                st.error(T["admin_reset_refused"])
                return

            # Counts shown elsewhere may be cached for a short while;
            # clear them so every screen shows 0 straight away.
            st.cache_data.clear()
            st.session_state.pop("data_reset_confirm_input", None)
            st.session_state["_data_reset_flash"] = T["admin_reset_done"]
            st.rerun()
