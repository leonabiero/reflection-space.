import streamlit as st

from services.workspace_style import render_workspace_badge


def render_workspace_menu(T):
    """Renders the page links for whichever work mode is currently
    active. Reads active_work_mode (NOT the authenticated role) so the
    links shown always match what the person is actually looking at
    right now.

    Role-aware link visibility
    ----------------------------
    Some pages inside a work mode are further gated to a SUBSET of the
    roles that can access that work mode at all (e.g. every Manager-mode
    role -- Supervisor, Programme Manager, System Administrator -- can
    open "Manager" mode, but Research Metrics itself is restricted to
    System Administrator only -- see pages/research_metrics_PAGE.py).

    Previously the sidebar link was shown to everyone in Manager mode
    regardless of this, so a Supervisor or Programme Manager would click
    through only to land on an immediate "no access" message. This
    reads the AUTHENTICATED role (st.session_state.user_role) -- the
    same source of truth already used everywhere else for authorization
    (see services.identity, navigation.permissions) -- and simply
    doesn't render that one link for roles that can't use the page.

    This changes visibility only. It does not change who is ALLOWED to
    view the page (that guard already lives inside
    pages/research_metrics_PAGE.py and is unchanged), and it does not
    change any other page's link or any work mode's availability.
    """
    workspace = st.session_state.get("active_work_mode", "Practitioner")
    role = st.session_state.get("user_role", "")

    if workspace == "Practitioner":
        render_workspace_badge(T.get("workmode_practitioner", "Practitioner"), "Practitioner")
        st.sidebar.page_link("pages/documentation.py", label=T.get("nav_doc", "Documentation"))
        st.sidebar.page_link("pages/reflection_space.py", label=T.get("nav_reflection", "Reflection Space"))
        st.sidebar.page_link("pages/growth_dashboard.py", label=T.get("nav_growth", "My Reflection"))
    elif workspace == "Manager":
        render_workspace_badge(T.get("workmode_manager", "Manager"), "Manager")
        st.sidebar.page_link("pages/learning.py", label=T.get("nav_learning", "Learning"))
        st.sidebar.page_link("pages/case_history.py", label=T.get("nav_case_history", "Case History"))
        # Research Metrics is restricted to System Administrator inside
        # the page itself -- only show the link to that role, so
        # Supervisors/Programme Managers never see a link that
        # immediately denies them.
        if role == "System Administrator":
            st.sidebar.page_link("pages/research_metrics_PAGE.py", label=T.get("nav_research_metrics", "Research Metrics"))
    elif workspace == "System Administration":
        render_workspace_badge(T.get("workmode_admin", "System Administration"), "System Administration")
        st.sidebar.page_link("pages/system_administration.py", label=T.get("nav_system_admin", "System Administration"))

    # Help is a read-only, role-aware quick guide -- not tied to any one
    # workspace, so it's shown regardless of which work mode is active
    # (unlike the workspace-specific links above). See pages/help.py.
    st.sidebar.page_link("pages/help.py", label=T.get("help", {}).get("nav_label", "❓ Help"))