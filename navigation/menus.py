import streamlit as st

from services.workspace_style import render_workspace_badge
from services.pattern_access import can_review_patterns


def render_workspace_menu(T):
    """Renders the page links for whichever work mode is currently
    active. Reads active_work_mode (NOT the authenticated role) so the
    links shown always match what the person is actually looking at
    right now.

    Role-aware link visibility
    ----------------------------
    Pattern Review is limited to a SUBSET of the roles that can open
    Manager mode (Supervisor and Programme Manager -- see
    services/pattern_access.py). The link is hidden for the System
    Administrator so nobody is shown a link that would only deny them.
    This changes visibility only; the page and the data layer enforce
    the rule themselves.

    November 2026: the Learning page (Team Presence, Knowledge
    Assistant, Learning Insights), Text analysis and Research Metrics
    were removed at the product owner's request, so Manager mode now
    holds Case History and Pattern Review only.
    """
    workspace = st.session_state.get("active_work_mode", "Practitioner")
    role = st.session_state.get("user_role", "")

    if workspace == "Practitioner":
        render_workspace_badge(T.get("workmode_practitioner", "Practitioner"), "Practitioner")
        # Reflection-only redesign (REFLECTIONS.md): Documentation and
        # Reflection Space are now ONE screen -- the case is written,
        # pasted or uploaded and reflected on in the same place.
        st.sidebar.page_link("pages/reflection_space.py", label=T.get("nav_reflection", "Reflection Space"))
        st.sidebar.page_link("pages/growth_dashboard.py", label=T.get("nav_growth", "My Reflection"))
    elif workspace == "Manager":
        render_workspace_badge(T.get("workmode_manager", "Manager"), "Manager")
        st.sidebar.page_link("pages/case_history.py", label=T.get("nav_case_history", "Case History"))
        # Pattern Review is for Supervisors and Programme Managers only
        # (services/pattern_access.py). The page and the data layer
        # enforce this themselves; hiding the link just avoids showing a
        # System Administrator a link that would deny them.
        if can_review_patterns(role):
            st.sidebar.page_link("pages/pattern_explorer.py", label=T.get("nav_patterns", "Pattern Review"))
    elif workspace == "System Administration":
        render_workspace_badge(T.get("workmode_admin", "System Administration"), "System Administration")
        st.sidebar.page_link("pages/system_administration.py", label=T.get("nav_system_admin", "System Administration"))

    # Help is a read-only, role-aware quick guide -- not tied to any one
    # workspace, so it's shown regardless of which work mode is active
    # (unlike the workspace-specific links above). See pages/help.py.
    st.sidebar.page_link("pages/help.py", label=T.get("help", {}).get("nav_label", "❓ Help"))