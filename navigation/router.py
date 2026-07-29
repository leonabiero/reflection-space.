import streamlit as st
from navigation.permissions import (
    available_workspaces,
    can_switch_work_mode,
    landing_page_for_workspace,
)
from navigation.menus import render_workspace_menu
from services.report_widget import render_report_button

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


# ---------------------------------------------------------------------
# Bugfix -- work-mode selection reverting immediately after being chosen
# ---------------------------------------------------------------------
#
# ROOT CAUSE (for anyone maintaining this later):
#
# The work-mode switcher selectbox used to be bound directly to
# st.session_state["active_work_mode"] (key="active_work_mode"), with
# an on_change callback (_on_switch_select) that read that same key and
# called st.switch_page() from INSIDE the callback.
#
# That key is ALSO written, unconditionally, on every single page load,
# by services.identity.require_work_mode(T, workspace) -- with
# `workspace` being a hard-coded string belonging to whichever page
# file is currently running (e.g. "Manager" on pages/learning.py,
# "Practitioner" on pages/documentation.py). require_work_mode() runs
# BEFORE render_nav() on every page, by design (see its docstring --
# this is what protects direct-URL access).
#
# Streamlit updates a widget's session_state value, and fires its
# on_change callback, BEFORE the main script body reruns. So the actual
# sequence when someone picked a new work mode from the dropdown was:
#
#   1. Streamlit sets active_work_mode = <newly picked value> (because
#      that was the widget's own key) and fires the on_change callback,
#      which reads that value and calls st.switch_page().
#   2. The CURRENT page's own script body (the one the person was
#      already on) still runs its require_work_mode(T, <this page's
#      fixed workspace>) call -- which unconditionally OVERWRITES
#      active_work_mode back to this page's own (old) workspace,
#      stomping the selection that was just made.
#   3. The selectbox -- bound to that same, now-reverted key -- renders
#      the OLD value again.
#
# Two different pieces of code ("what page am I actually on" vs. "what
# did the user just pick") were writing to the SAME session_state key,
# with no ordering guarantee between them. That produced the
# intermittent "briefly changes, then reverts" behaviour, and is the
# same class of bug that produces Streamlit's "calling st.rerun()
# within a callback is a no-op" warning -- driving navigation from
# inside a widget callback fights with Streamlit's own automatic
# post-callback rerun.
#
# THE FIX:
#   - The selector no longer shares a key with active_work_mode. It
#     gets its own key, derived from the CURRENT authoritative state
#     (f"workmode_selector_{active}"), so if active_work_mode ever
#     changes through any other path (a direct page link, the "back to
#     my workspace" button, a permissions change), Streamlit is forced
#     to create a brand-new widget instance next render instead of
#     reusing a stale leftover value from a different page/work mode.
#   - There is no on_change callback anymore, and st.rerun()/
#     st.switch_page() are only ever called from the plain script body
#     (after the widget has rendered), exactly like every other
#     button-triggered action already in this codebase (e.g. the
#     logout button in services/identity.py). Nothing here is
#     triggered from inside a registered callback, so the "st.rerun()
#     is a no-op inside a callback" situation can no longer arise.
#   - active_work_mode remains the single, authoritative piece of
#     state. The selector's own key is pure UI bookkeeping that is
#     reconciled against it on every render -- it is never read by
#     anything else in the app.
#   - previous_work_mode (used by the "back to my workspace" button)
#     is now captured at the correct moment for BOTH ways of entering
#     Practitioner mode: via this switcher (captured here, right
#     before the state changes) and via a direct Practitioner page
#     link (still captured by services.identity.require_work_mode(),
#     unchanged). Previously the switcher path never recorded it
#     correctly, because by the time require_work_mode() ran on the
#     destination page, active_work_mode had already been flipped to
#     "Practitioner" by the old callback, so its "did this just change
#     into Practitioner" check could never fire.
#
# Nothing about WHO can access WHICH workspace, or which page a work
# mode lands on, has changed -- only how the current selection is
# tracked and applied.
# ---------------------------------------------------------------------


def render_nav(T, page_name="app"):
    """
    Renders the sidebar: the work-mode switcher (only when appropriate
    -- see below) and the current work mode's page links.

    IMPORTANT ordering requirement for callers
    ----------------------------------------------
    Pages must call services.identity.require_work_mode(T, workspace)
    BEFORE calling render_nav(T) -- require_work_mode() is what keeps
    active_work_mode in sync with whichever page was actually navigated
    to (direct-URL access protection), and it must run before this
    function reads active_work_mode for this rerun.

    Role / work-mode separation
    ------------------------------
    - The AUTHENTICATED role (st.session_state.user_role) determines
      WHICH work modes this person is even allowed to choose from
      (navigation.permissions.available_workspaces()) -- re-derived
      from the authenticated role on every render, so the switcher can
      never offer a work mode this person isn't authorized for.
    - The ACTIVE work mode (st.session_state.active_work_mode) is the
      single source of truth for what's shown right now. This function
      only writes to it in response to an explicit action taken in the
      PLAIN script body below (never inside a widget callback): picking
      a new work mode from the selector, or pressing the "back to my
      workspace" button.

    Practitioner mode hides the switcher (per product requirement): if
    active_work_mode == "Practitioner", no dropdown/selector is shown
    at all, even for a Supervisor/Programme Manager/System
    Administrator who is only temporarily working in Practitioner mode.
    Instead, if that person is authorized for more than one work mode,
    a single, minimal "back to my workspace" button is shown so they
    are never stranded in Practitioner mode.

    "Back to my workspace" remembers where the person actually came
    from
    ------------------------------------------------------------------
    previous_work_mode is recorded right before active_work_mode
    changes TO "Practitioner" -- whether that happens via the selector
    below, or via services.identity.require_work_mode() when a
    Practitioner-mode page link is clicked directly. This button reads
    that value back, falling back to the first other available
    workspace only if no previous work mode was recorded, or if the
    recorded one is no longer a workspace this role can access (e.g.
    permissions changed mid-session) -- so the button can never send
    someone somewhere they're not authorized for.
    """
    role = st.session_state.get("user_role", "")
    options = available_workspaces(role)
    active = st.session_state.get("active_work_mode", "Practitioner")

    if not options:
        render_workspace_menu(T)
        render_report_button(T, page_name, user_name=st.session_state.get("user_name", ""), user_role=role)
        return
    if active not in options:
        active = options[0]
        st.session_state.active_work_mode = active

    if active == "Practitioner":
        if can_switch_work_mode(role):
            other_options = [w for w in options if w != "Practitioner"]
            previous = st.session_state.get("previous_work_mode")
            back_target = previous if previous in other_options else (
                other_options[0] if other_options else None
            )
            if back_target:
                # Plain button + inline check, run in the normal script
                # body -- not a registered on_click callback -- exactly
                # the same pattern already used for the logout button
                # in services/identity.py. st.switch_page() here is
                # safe: it's the script body deciding to navigate, not
                # a callback fighting with Streamlit's own rerun cycle.
                if st.sidebar.button(
                    f"⬅ {_label(T, back_target)}",
                    key="workmode_back_button",
                ):
                    st.session_state.active_work_mode = back_target
                    st.switch_page(landing_page_for_workspace(back_target))
    else:
        # The widget's key is deliberately NOT "active_work_mode" (see
        # the bugfix note above). It's derived from the current
        # authoritative state, so a stale value left over from a
        # different page/work mode can never leak into this render --
        # any time `active` changes via another path, this key changes
        # too, forcing Streamlit to create a fresh widget seeded from
        # `index=`, rather than resurrecting an old stored value.
        widget_key = f"workmode_selector_{active}"

        selected = st.sidebar.selectbox(
            T.get("workmode_switch_label", "Work mode"),
            options,
            format_func=lambda w: _label(T, w),
            index=options.index(active),
            key=widget_key,
        )

        # Navigation decision happens HERE, in the plain script body,
        # AFTER the widget has already rendered/updated its own key --
        # never inside an on_change callback. This is what removes the
        # race with services.identity.require_work_mode()'s own write
        # to active_work_mode, and what eliminates any reliance on
        # st.rerun()/st.switch_page() being called from a callback.
        if selected != active:
            if selected == "Practitioner" and active != "Practitioner":
                st.session_state["previous_work_mode"] = active
            st.session_state.active_work_mode = selected
            st.switch_page(landing_page_for_workspace(selected))

    render_workspace_menu(T)
    render_report_button(T, page_name, user_name=st.session_state.get("user_name", ""), user_role=role)