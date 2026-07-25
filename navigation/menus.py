import streamlit as st


def render_workspace_menu(T):
    role = st.session_state.get("user_role", "")
    workspace = st.session_state.get("active_workspace", "Practitioner")
    st.sidebar.subheader(workspace)
    if workspace == "Practitioner":
        st.sidebar.page_link("pages/documentation.py", label=T.get("nav_doc", "Documentation"))
        st.sidebar.page_link("pages/reflection_space.py", label=T.get("nav_reflection", "Reflection Space"))
        st.sidebar.page_link("pages/growth_dashboard.py", label=T.get("nav_growth", "My Reflection"))
    elif workspace == "Manager":
        st.sidebar.page_link("pages/learning.py", label=T.get("nav_learning", "Learning"))
        st.sidebar.page_link("pages/case_history.py", label=T.get("nav_case_history", "Case History"))
        st.sidebar.page_link("pages/research_metrics_PAGE.py", label=T.get("nav_research_metrics", "Research Metrics"))
    elif workspace == "System Administration":
        st.sidebar.page_link("pages/system_administration.py", label="System Administration")
