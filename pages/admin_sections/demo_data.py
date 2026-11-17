"""System Administration -- Demo data (17 November 2026, see DEMO.md).

Shown ONLY in the demo app (DEMO_MODE on). Lets the System Administrator
load the fictional texts and ratings used to demonstrate Pattern Review,
and remove them again. Every lock is enforced in services/demo_data.py,
not only here: the real app, or a demo app connected to the real
database, can never load demo texts.

Architectural rule kept: no st.dataframe(), st.tabs() or st.columns()
on the System Administration page.
"""
import streamlit as st

from services import demo_data


def render(T):
    if not demo_data.demo_mode_on():
        return
    with st.expander(T["admin_demo_header"], expanded=True):
        flash = st.session_state.pop("_demo_data_flash", None)
        if flash:
            kind, message = flash
            getattr(st, kind)(message)

        st.write(T["admin_demo_intro"])
        role = st.session_state.get("user_role", "")
        name = st.session_state.get("user_name", "")

        if not demo_data.may_use_demo_data(role):
            st.error(T["admin_demo_wrong_database"])
            return

        try:
            counts = demo_data.demo_counts()
        except Exception:
            st.error(T["admin_demo_failed"])
            return
        st.caption(T["admin_demo_counts"].format(texts=counts["texts"], ratings=counts["ratings"]))

        if st.button(T["admin_demo_load_button"], type="primary",
                     disabled=bool(counts["texts"]), key="demo_data_load_btn"):
            try:
                result = demo_data.load_demo_data(name, role)
            except Exception:
                st.error(T["admin_demo_failed"])
                return
            if result["status"] == "ok":
                message = ("success", T["admin_demo_loaded"].format(
                    texts=result["texts"], ratings=result["ratings"]))
            elif result["status"] == "already_loaded":
                message = ("info", T["admin_demo_already_loaded"])
            else:
                message = ("error", T["admin_demo_wrong_database"])
            st.cache_data.clear()
            st.session_state["_demo_data_flash"] = message
            st.rerun()

        st.caption(T["admin_demo_remove_note"])
        if st.button(T["admin_demo_remove_button"], disabled=not counts["texts"] and not counts["ratings"],
                     key="demo_data_remove_btn"):
            try:
                result = demo_data.remove_demo_data(name, role)
            except Exception:
                st.error(T["admin_demo_failed"])
                return
            if result["status"] == "ok":
                message = ("success", T["admin_demo_removed"].format(
                    texts=result["texts"], ratings=result["ratings"], reports=result["reports"]))
            else:
                message = ("error", T["admin_demo_wrong_database"])
            st.cache_data.clear()
            st.session_state["_demo_data_flash"] = message
            st.rerun()
