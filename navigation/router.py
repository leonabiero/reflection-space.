import streamlit as st
from navigation.permissions import (
    available_workspaces,
    can_switch_work_mode,
    landing_page_for_workspace,
)
from navigation.menus import render_workspace_menu

# Work-mode labels shown in the switcher -- localized via the existing
# language service (services/language.py), never a second translation
# table. Falls back to the raw work-mode name if a key is ever missing.
_WORK_MODE_LABEL_KEYS = {
    "Practitioner": "workmode_practitioner",
    "Manager": "workmode_manager",
    "System Administration": "workmode_admin",
}


def _label(T, workspace):
    return T.get(_WORK_MODE_LABEL_KEYS.get(workspace, ""), workspace)


def _on_switch_select():
    """
    on_change callback for the work-mode selectbox. By the time this
    runs, Streamlit has already updated
    st.session_state["active_work_mode"] to the newly chosen value (the
    widget's own key IS active_work_mode -- see render_nav below), so
    all this needs to do is perform the actual page navigation.

    Using st.switch_page (real, programmatic navigation) rather than
    just letting the page rerun is what makes the switch IMMEDIATE and
    complete: the browser is sent straight to the new work mode's own
    landing page, so the previous workspace's content never lingers on
    screen underneath/above the new one.
    """
    target = st.session_state["active_work_mode"]
    st.switch_page(landing_page_for_workspace(target))


def _switch_to(target_workspace):
    """Used by the minimal "back to my workspace" button shown while in
    Practitioner mode (see render_nav) -- same navigation behavior as
    the selectbox above, just triggered by a plain button instead."""
    st.session_state.active_work_mode = target_workspace
    st.switch_page(landing_page_for_workspace(target_workspace))


def render_nav(T):
    """
    Renders the sidebar: the work-mode switcher (only when appropriate
    -- see below) and the current work mode's page links.

    IMPORTANT ordering requirement for callers
    ----------------------------------------------
    Pages must call services.identity.require_work_mode(T, workspace)
    BEFORE calling render_nav(T) (see that function's docstring) --
    require_work_mode() is what keeps active_work_mode in sync with
    whichever page was actually navigated to, and it must run before
    this function instantiates the active_work_mode-keyed widget for
    this rerun, or Streamlit raises a "widget already has a value"
    exception.

    Role / work-mode separation
    ------------------------------
    - The AUTHENTICATED role (st.session_state.user_role) determines
      WHICH work modes this person is even allowed to choose from
      (navigation.permissions.available_workspaces()) -- re-derived
      from the authenticated role on every render, so the switcher can
      never offer a work mode this person isn't authorized for.
    - The ACTIVE work mode (st.session_state.active_work_mode) only
      determines what's shown right now. This function only WRITES to
      it in response to an explicit user action (selecting a new work
      mode, or the "back to my workspace" button) -- an ordinary
      rerun/page interaction never resets it back to "Practitioner".

    Practitioner mode hides the switcher (per product requirement): if
    active_work_mode == "Practitioner", no dropdown/selector is shown
    at all, even for a Supervisor/Programme Manager/System
    Administrator who is only temporarily working in Practitioner mode.
    Instead, if that person is authorized for more than one work mode,
    a single, minimal "back to my workspace" link is shown so they are
    never stranded in Practitioner mode -- this is a single button, not
    a switcher/selector, so it does not violate the "no switcher in
    Practitioner mode" rule.
    """
    role = st.session_state.get("user_role", "")
    options = available_workspaces(role)
    active = st.session_state.get("active_work_mode", "Practitioner")

    if not options:
        render_workspace_menu(T)
        return
    if active not in options:
        active = options[0]
        st.session_state.active_work_mode = active

    if active == "Practitioner":
        if can_switch_work_mode(role):
            other_options = [w for w in options if w != "Practitioner"]
            back_target = other_options[0] if other_options else None
            if back_target:
                st.sidebar.button(
                    f"⬅ {_label(T, back_target)}",
                    key="workmode_back_button",
                    on_click=_switch_to,
                    args=(back_target,),
                )
    else:
        # Manager or System Administration work mode: show the real
        # switcher. Bound directly to the "active_work_mode" key -- the
        # single source of truth -- exactly like the original
        # "active_workspace" pattern this replaces, so there is only
        # ever one variable holding this state, never a shadow copy.
        st.sidebar.selectbox(
            T.get("workmode_switch_label", "Work mode"),
            options,
            format_func=lambda w: _label(T, w),
            key="active_work_mode",
            on_change=_on_switch_select,
        )

    render_workspace_menu(T)