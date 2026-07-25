import streamlit as st
from navigation.permissions import available_workspaces
from navigation.menus import render_workspace_menu


def render_nav(T):
    role = st.session_state.get("user_role", "")
    options = available_workspaces(role)
    current = st.session_state.get("active_workspace", options[0] if options else "Practitioner")
    if current not in options and options:
        current = options[0]
    if options:
        st.sidebar.selectbox("Workspace", options, index=options.index(current), key="active_workspace")
    render_workspace_menu(T)
