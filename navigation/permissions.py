from typing import Dict

# ---------------------------------------------------------------------
# Role / Work-Mode separation
# ---------------------------------------------------------------------
# AUTHENTICATED ROLE  = the role the person actually logged in with
#                       (services.identity, st.session_state.user_role).
#                       This never changes for the duration of a session
#                       (it only changes on logout/new login).
#
# ACTIVE WORK MODE    = the workspace the authenticated user is CURRENTLY
#                       operating in (st.session_state.active_work_mode).
#                       A Supervisor, Programme Manager or System
#                       Administrator can switch into "Practitioner" work
#                       mode without ever losing their authenticated role
#                       or their permission to switch back.
#
# Work-mode values are intentionally kept identical to the workspace
# names already used throughout the app ("Practitioner", "Manager",
# "System Administration") so nothing else has to be renamed.
# ---------------------------------------------------------------------

PRACTITIONER_PAGES = {"Documentation", "Reflection Space", "My Reflection"}
MANAGER_PAGES = {"Learning", "Case History", "Research Metrics"}

WORKSPACE_ORDER = ["Practitioner", "Manager", "System Administration"]

# Where switching INTO a work mode should land the user.
WORKSPACE_LANDING_PAGE = {
    "Practitioner": "pages/documentation.py",
    "Manager": "pages/learning.py",
    "System Administration": "pages/system_administration.py",
}

# The work mode a role starts in immediately after login.
ROLE_DEFAULT_WORK_MODE = {
    "Social Worker": "Practitioner",
    "Supervisor": "Manager",
    "Programme Manager": "Manager",
    "System Administrator": "System Administration",
}


def can_access_workspace(role, workspace):
    """True if `role` (the AUTHENTICATED role) is permitted to operate in
    `workspace` (a work mode). This is the single source of truth for
    authorization -- it must be checked both for showing navigation AND
    for guarding direct page access, never just for hiding a sidebar
    link."""
    if role == "Social Worker":
        return workspace == "Practitioner"
    if role in {"Supervisor", "Programme Manager"}:
        return workspace in {"Manager", "Practitioner"}
    if role == "System Administrator":
        return workspace in {"System Administration", "Manager", "Practitioner"}
    return False


def available_workspaces(role):
    """All work modes this authenticated role is allowed to switch into,
    in a stable display order."""
    return [w for w in WORKSPACE_ORDER if can_access_workspace(role, w)]


def default_workspace_for_role(role):
    """The work mode a role should land in immediately after login."""
    return ROLE_DEFAULT_WORK_MODE.get(role, "Practitioner")


def landing_page_for_workspace(workspace):
    return WORKSPACE_LANDING_PAGE.get(workspace, "pages/documentation.py")


def can_switch_work_mode(role):
    """True if this authenticated role has more than one work mode
    available to it at all (i.e. the switcher should ever be shown for
    this person, in whichever work mode allows showing it)."""
    return len(available_workspaces(role)) > 1