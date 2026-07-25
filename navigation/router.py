import streamlit as st
from navigation.permissions import available_workspaces
from navigation.menus import render_workspace_menu


def render_nav(T):
    role = st.session_state.get("user_role", "")
    options = available_workspaces(role)

    if not options:
        render_workspace_menu(T)
        return

    current = st.session_state.get("active_workspace", options[0])
    if current not in options:
        current = options[0]

    # Only seed session_state directly when the key is missing or
    # invalid. Once it exists, the selectbox's `key=` alone controls
    # the value on every subsequent rerun -- we must NOT also pass an
    # `index=` default for the same key, since setting a widget's
    # session_state value both via the Session State API (e.g. on
    # login, in services/identity.py) and via a widget default
    # (index=) in the same run is exactly what triggers Streamlit's
    # "widget was created with a default value but also had its value
    # set via the Session State API" warning.
    if "active_workspace" not in st.session_state or st.session_state.active_workspace not in options:
        st.session_state.active_workspace = current

    st.sidebar.selectbox("Workspace", options, key="active_workspace")
    render_workspace_menu(T)