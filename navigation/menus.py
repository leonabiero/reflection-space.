import streamlit as st


def render_workspace_menu(T):
    """Renders the page links for whichever work mode is currently
    active. Reads active_work_mode (NOT the authenticated role) so the
    links shown always match what the person is actually looking at
    right now."""
    workspace = st.session_state.get("active_work_mode", "Practitioner")

    if workspace == "Practitioner":
        st.sidebar.subheader(T.get("workmode_practitioner", "Practitioner"))
        st.sidebar.page_link("pages/documentation.py", label=T.get("nav_doc", "Documentation"))
        st.sidebar.page_link("pages/reflection_space.py", label=T.get("nav_reflection", "Reflection Space"))
        st.sidebar.page_link("pages/growth_dashboard.py", label=T.get("nav_growth", "My Reflection"))
    elif workspace == "Manager":
        st.sidebar.subheader(T.get("workmode_manager", "Manager"))
        st.sidebar.page_link("pages/learning.py", label=T.get("nav_learning", "Learning"))
        st.sidebar.page_link("pages/case_history.py", label=T.get("nav_case_history", "Case History"))
        st.sidebar.page_link("pages/research_metrics_PAGE.py", label=T.get("nav_research_metrics", "Research Metrics"))
    elif workspace == "System Administration":
        st.sidebar.subheader(T.get("workmode_admin", "System Administration"))
        st.sidebar.page_link("pages/system_administration.py", label=T.get("nav_system_admin", "System Administration"))