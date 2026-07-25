import streamlit as st
from navigation.permissions import available_workspaces
from navigation.menus import render_workspace_menu


def render_nav(T):
    role = st.session_state.get("user_role", "")
    options = available_workspaces(role)

    if not options or len(options) <= 1:
        render_workspace_menu(T)
        return

    current = st.session_state.get("active_workspace", options[0])
    if current not in options:
        current = options[0]

    # If in Practitioner mode, hide the switcher
    if current == "Practitioner":
        render_workspace_menu(T)
        return

    # Workspace selector for authorised users
    # We use a non-key selectbox to detect changes and then st.switch_page
    index = options.index(current) if current in options else 0
    new_workspace = st.sidebar.selectbox(
        T.get("workspace_label", "Workspace"),
        options,
        index=index
    )

    if new_workspace != current:
        st.session_state.active_workspace = new_workspace
        # Immediate navigation to landing page
        if new_workspace == "Practitioner":
            st.switch_page("pages/documentation.py")
        elif new_workspace == "Manager":
            st.switch_page("pages/learning.py")
        elif new_workspace == "System Administration":
            st.switch_page("pages/system_administration.py")
        st.rerun()

    render_workspace_menu(T)