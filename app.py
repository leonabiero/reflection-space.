import streamlit as st
from services.db_schema import ensure_schema
from services.language import init_language
from services.identity import init_identity, get_active_work_mode
from navigation.permissions import landing_page_for_workspace

st.set_page_config(page_title="Reflection Space", layout="centered")
# Schema creation/migration for every table this app uses now happens
# exactly once here, at startup (see services/db_schema.py) -- it no
# longer runs on every individual database call throughout the app.
ensure_schema()

T = init_language()
user_name, user_role = init_identity(T)

# Sprint 12: app.py is only ever the very first screen right after
# login. From then on, the person always lives inside one specific
# work mode's own landing page (Documentation / Learning / System
# Administration) -- see navigation.permissions.WORKSPACE_LANDING_PAGE.
# This keeps "immediate workspace switching" true everywhere, including
# the very first render after login: nobody sees a generic home page
# mixed in with (or instead of) their actual workspace.
st.switch_page(landing_page_for_workspace(get_active_work_mode()))