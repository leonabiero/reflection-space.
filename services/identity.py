import streamlit as st

# FR-001/NFR-011 (authentication) + FR-002/FR-003 (identity, roles),
# now implemented together: each professional has their own username
# and password, defined in Streamlit Cloud Secrets (never in the
# repository). On successful login, the verified name and role are
# stored in session_state and used everywhere identity is needed —
# draft attribution, role-gated navigation, etc.

ROLES = ["Social Worker", "Supervisor", "Programme Manager", "System Administrator"]

LEARNING_VISIBLE_ROLES = {"Supervisor", "Programme Manager", "System Administrator"}


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


def init_identity():
    if "authed" not in st.session_state:
        st.session_state.authed = False
    if "user_name" not in st.session_state:
        st.session_state.user_name = ""
    if "user_role" not in st.session_state:
        st.session_state.user_role = ""

    if st.session_state.authed:
        with st.sidebar:
            st.markdown("---")
            st.caption(f"Logged in as **{st.session_state.user_name}** ({st.session_state.user_role})")
            if st.button("Log out"):
                st.session_state.authed = False
                st.session_state.user_name = ""
                st.session_state.user_role = ""
                st.rerun()
        return st.session_state.user_name, st.session_state.user_role

    # Not logged in: block this page with a login form until a valid
    # username/password is entered.
    st.title("🔒 Reflection Space")
    users = _load_users()

    if not users:
        st.error(
            "No user accounts are configured yet. Add them under "
            "Settings → Secrets in Streamlit Cloud, using a [users] "
            "section as described in the deployment notes."
        )
        st.stop()

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Log in"):
        user = _check_login(username, password, users)
        if user:
            st.session_state.authed = True
            st.session_state.user_name = user.get("name", username)
            st.session_state.user_role = user.get("role", ROLES[0])
            st.rerun()
        else:
            st.error("Incorrect username or password.")

    st.stop()


def get_identity():
    return st.session_state.get("user_name", ""), st.session_state.get("user_role", "")


def can_see_learning(role: str) -> bool:
    return role in LEARNING_VISIBLE_ROLES