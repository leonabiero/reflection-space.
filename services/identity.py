import streamlit as st
from navigation.permissions import default_workspace_for_role, can_access_workspace

# FR-001/NFR-011 (authentication) + FR-002/FR-003 (identity, roles).
# Each professional has their own username and password, defined in
# Streamlit Cloud Secrets (never in the repository). On successful
# login, the verified name and role are stored in session_state and
# used everywhere identity is needed — draft attribution, role-gated
# navigation, etc.
#
# init_identity(T) is the login GATE — call it near the top of every
# page, before render_nav(). It blocks the page (st.stop()) with a
# localized login form until the person logs in.
#
# render_identity_footer(T) draws the logged-in account display and
# the Log out button. Call this AFTER render_nav(T) so it ends up at
# the bottom of the sidebar, below the navigation links.
#
# Role / Work-Mode separation
# ------------------------------
# st.session_state.user_role is the AUTHENTICATED role -- it is set once
# at login and is NEVER changed while switching work modes. It only
# changes on logout/new login.
#
# st.session_state.active_work_mode is the CURRENTLY ACTIVE workspace
# the person is operating in right now. It starts at
# navigation.permissions.default_workspace_for_role(user_role) on login,
# and from then on is only ever changed by:
#   - an explicit, authorized work-mode switch (navigation/router.py)
#   - logout / a new login
# It must never silently reset back to "Practitioner" during an
# ordinary Streamlit rerun -- see navigation/router.py, which only ever
# WRITES active_work_mode on those two occasions, never reads a stale
# default back into it.
#
# "previous_work_mode" (Back to my workspace fix)
# ----------------------------------------------------
# require_work_mode() below now also records, in
# st.session_state["previous_work_mode"], whichever work mode was
# active immediately before the person entered "Practitioner" mode --
# whether that happened via the work-mode switcher (navigation/router.py)
# or simply by clicking a Practitioner-mode page link directly. Both
# paths call require_work_mode() before the page renders, so this one
# spot reliably captures it regardless of how Practitioner mode was
# entered. navigation/router.py's "back to my workspace" button reads
# this value back instead of always guessing "Manager".
#
# Presence / heartbeat (Team Presence, Sprint 12)
# ---------------------------------------------------
# Every authenticated page load "touches" services.presence with the
# logged-in professional's name/role, updating their last_seen
# timestamp. This is a lightweight heartbeat -- there is no background
# job, the timestamp simply advances every time the person interacts
# with the app (any page load, any button press causes a Streamlit
# rerun, which re-touches presence). See services/presence.py for the
# "active now / recently active / offline" classification used by the
# Team Presence panel on the Learning page.
#
# Logout ordering fix
# ---------------------
# navigation.router.render_nav() renders a sidebar control bound to
# st.session_state["active_work_mode"] (key="active_work_mode"). Every
# page calls render_nav(T) BEFORE render_identity_footer(T), so by the
# time the Log out button (inside render_identity_footer) is clicked,
# that widget has already been instantiated in this script run.
#
# Streamlit raises StreamlitAPIException if you assign directly to
# st.session_state["active_work_mode"] after its widget has already
# been created in the same run. Fix: the Log out button no longer
# touches session_state directly. It only sets a plain (non-widget)
# flag, "_logout_requested", and reruns. The actual reset
# (authed/user_name/user_role/active_work_mode) happens at the very top
# of init_identity() instead -- which every page calls BEFORE
# render_nav() -- so the reset always runs before that widget exists
# for that run, which is allowed.

ROLES = ["Social Worker", "Supervisor", "Programme Manager", "System Administrator"]

LEARNING_VISIBLE_ROLES = {"Supervisor", "Programme Manager", "System Administrator"}

# FR-028: who can browse completed/reflected case history. Same tier
# as Learning for now — supervisory and administrative roles only.
CASE_HISTORY_VISIBLE_ROLES = {"Supervisor", "Programme Manager", "System Administrator"}


def _load_users():
    """
    Reads user accounts from Streamlit Cloud Secrets, structured as:

        [users.jmwangi]
        password = "..."
        name = "John Mwangi"
        role = "Social Worker"

    Add accounts under Settings -> Secrets in the Streamlit Cloud
    dashboard for this app. Returns an empty dict (rather than raising)
    if no secrets are configured yet, e.g. when running locally without
    a secrets.toml file.
    """
    try:
        return dict(st.secrets.get("users", {}))
    except Exception:
        return {}


def _check_login(username, password, users):
    user = users.get(username)
    if user and password and user.get("password") == password:
        return user
    return None


def _touch_presence():
    """Best-effort presence heartbeat -- never blocks or breaks a page
    if the presence table/DB is unavailable for any reason."""
    try:
        from services.presence import touch
        touch(st.session_state.user_name, st.session_state.user_role)
    except Exception:
        pass


def init_identity(T):
    if "authed" not in st.session_state:
        st.session_state.authed = False
    if "user_name" not in st.session_state:
        st.session_state.user_name = ""
    if "user_role" not in st.session_state:
        st.session_state.user_role = ""
    if "active_work_mode" not in st.session_state:
        st.session_state.active_work_mode = "Practitioner"

    # Apply any logout requested on the previous run BEFORE render_nav()
    # (called right after this function returns/stops) ever instantiates
    # the "active_work_mode" widget this run. See the module docstring
    # above ("Logout ordering fix") for why this can't happen inside
    # render_identity_footer itself.
    if st.session_state.pop("_logout_requested", False):
        st.session_state.authed = False
        st.session_state.user_name = ""
        st.session_state.user_role = ""
        st.session_state.active_work_mode = "Practitioner"
        # Clear the remembered "came from" workspace too, so a fresh
        # login never accidentally inherits a stale value from a
        # previous person's session on a shared browser.
        st.session_state.pop("previous_work_mode", None)

    if st.session_state.authed:
        _touch_presence()
        return st.session_state.user_name, st.session_state.user_role

    # Not logged in: block this page with a login form until a valid
    # username/password is entered.
    st.title(T["login_heading"])
    users = _load_users()

    if not users:
        st.error(T["no_users_configured"])
        st.stop()

    username = st.text_input(T["username"])
    password = st.text_input(T["password_label"], type="password")

    if st.button(T["login_button"]):
        user = _check_login(username, password, users)
        if user:
            st.session_state.authed = True
            st.session_state.user_name = user.get("name", username).strip()
            st.session_state.user_role = user.get("role", ROLES[0]).strip()
            # Active work mode is initialised ONCE here, from the
            # authenticated role's default workspace -- see
            # navigation.permissions.default_workspace_for_role(). It is
            # a completely separate piece of state from user_role from
            # this point on.
            st.session_state.active_work_mode = default_workspace_for_role(
                st.session_state.user_role
            )
            st.rerun()
        else:
            st.error(T["login_error"])

    st.stop()


def render_identity_footer(T):
    role = st.session_state.get("user_role", "")
    name = st.session_state.get("user_name", "")
    role_label = T.get("role_labels", {}).get(role, role)

    with st.sidebar:
        st.markdown("---")
        st.caption(role_label)
        st.write(f"**{name}**")
        if st.button(T["logout"]):
            # Do NOT touch st.session_state["active_work_mode"] here --
            # render_nav() already instantiated that widget earlier in
            # this run. Just flag the request and rerun; init_identity()
            # performs the actual reset at the top of the NEXT run,
            # before that widget exists again. See module docstring.
            st.session_state["_logout_requested"] = True
            st.rerun()


def get_identity():
    return st.session_state.get("user_name", ""), st.session_state.get("user_role", "")


def get_active_work_mode():
    return st.session_state.get("active_work_mode", "Practitioner")


def can_see_learning(role: str) -> bool:
    return role in LEARNING_VISIBLE_ROLES


def can_see_case_history(role: str) -> bool:
    return role in CASE_HISTORY_VISIBLE_ROLES


def require_work_mode(T, workspace):
    """
    Authorization guard for a page whose content belongs to `workspace`
    ("Practitioner" | "Manager" | "System Administration").

    This is the enforcement point requested for direct-page-access
    protection: it checks the AUTHENTICATED role (never just the active
    work mode, and never just sidebar visibility) via
    navigation.permissions.can_access_workspace(). If the authenticated
    user isn't allowed into this workspace at all, the page is blocked
    with st.stop() -- typing the URL directly cannot bypass this.

    If the person IS authorized, this also keeps active_work_mode in
    sync with whatever page they actually landed on (e.g. following a
    direct link, or a page reload) -- so the work-mode switcher and the
    "Practitioner mode hides the switcher" rule stay consistent no
    matter how the person arrived at this page, not only when they used
    the switcher itself.

    "Back to my workspace" fix -- remembering where they came from
    ------------------------------------------------------------------
    Right before active_work_mode is (re)set, if the NEW workspace is
    "Practitioner" and the CURRENT active_work_mode is something else
    (i.e. this call is the moment of entering Practitioner mode, not
    just re-confirming it on a later Practitioner-mode page), the
    current value is saved as st.session_state["previous_work_mode"].

    This covers both ways someone can end up in Practitioner mode:
    using the work-mode switcher (navigation/router.py's selectbox,
    which calls st.switch_page -> lands on a Practitioner page ->
    require_work_mode(T, "Practitioner") runs), and clicking a
    Practitioner-mode page link directly from Manager or System
    Administration mode. Navigating between two Practitioner-mode pages
    (e.g. Documentation -> Reflection Space) does NOT overwrite the
    remembered value, since active_work_mode is already "Practitioner"
    by then -- so the true originating workspace is preserved for the
    whole time someone stays in Practitioner mode, not just the first
    click.
    """
    role = st.session_state.get("user_role", "")
    if not can_access_workspace(role, workspace):
        st.error(T.get("workmode_access_denied", "You do not have access to this workspace."))
        st.stop()

    current = st.session_state.get("active_work_mode")
    if workspace == "Practitioner" and current and current != "Practitioner":
        st.session_state["previous_work_mode"] = current

    st.session_state.active_work_mode = workspace