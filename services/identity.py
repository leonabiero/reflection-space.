import streamlit as st

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
# Logout ordering fix
# ---------------------
# navigation.router.render_nav() renders a sidebar selectbox bound to
# st.session_state["active_workspace"] (key="active_workspace"). Every
# page calls render_nav(T) BEFORE render_identity_footer(T), so by the
# time the Log out button (inside render_identity_footer) is clicked,
# that widget has already been instantiated in this script run.
#
# Streamlit raises StreamlitAPIException if you assign directly to
# st.session_state["active_workspace"] after its widget has already
# been created in the same run — which is exactly what logging out
# used to do (reset active_workspace back to "Practitioner" inline,
# then st.rerun()). The assignment itself was already illegal before
# the rerun ever got a chance to run.
#
# Fix: the Log out button no longer touches session_state directly.
# It only sets a plain (non-widget) flag, "_logout_requested", and
# reruns. The actual reset (authed/user_name/user_role/active_workspace)
# now happens at the very top of init_identity() instead — which every
# page calls BEFORE render_nav() — so the reset always runs before the
# "active_workspace" widget exists for that run, which is allowed.

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


from services.draft_storage import update_user_activity


def init_identity(T):
    if "authed" not in st.session_state:
        st.session_state.authed = False
    if "user_name" not in st.session_state:
        st.session_state.user_name = ""
    if "user_role" not in st.session_state:
        st.session_state.user_role = ""
    if "active_workspace" not in st.session_state:
        st.session_state.active_workspace = ""

    # Apply any logout requested on the previous run BEFORE render_nav()
    if st.session_state.pop("_logout_requested", False):
        st.session_state.authed = False
        st.session_state.user_name = ""
        st.session_state.user_role = ""
        st.session_state.active_workspace = ""

    if st.session_state.authed:
        # Heartbeat: update last_seen on every page load while authed
        update_user_activity(st.session_state.user_name, st.session_state.user_role)
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
            # Initial active workspace based on role
            role = st.session_state.user_role
            if role == "System Administrator":
                st.session_state.active_workspace = "System Administration"
            elif role in {"Supervisor", "Programme Manager"}:
                st.session_state.active_workspace = "Manager"
            else:
                st.session_state.active_workspace = "Practitioner"
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
            # Do NOT touch st.session_state["active_workspace"] here --
            # render_nav() already instantiated that widget earlier in
            # this run. Just flag the request and rerun; init_identity()
            # performs the actual reset at the top of the NEXT run,
            # before that widget exists again. See module docstring.
            st.session_state["_logout_requested"] = True
            st.rerun()


def get_identity():
    return st.session_state.get("user_name", ""), st.session_state.get("user_role", "")


def can_see_learning(role: str) -> bool:
    return role in LEARNING_VISIBLE_ROLES


def can_see_case_history(role: str) -> bool:
    return role in CASE_HISTORY_VISIBLE_ROLES