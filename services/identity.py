import streamlit as st
from navigation.permissions import (
    default_workspace_for_role,
    can_access_workspace,
    landing_page_for_workspace,
)
from services.login_security import verify_password
from services.login_rate_limiter import (
    is_locked_out,
    record_failed_attempt,
    clear_failed_attempts,
)

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
# require_work_mode() below also records, in
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
# ============================================================================
# BUGFIX (this revision): "You do not have access to this workspace" after
# logging out and logging back in as a different user, in the same tab.
# ============================================================================
#
# ROOT CAUSE
# ----------
# Logging out never changes the browser's URL/page -- it only reruns
# whatever script is currently open (via st.rerun()). The login form was
# then submitted, and validated, from INSIDE that same page. The old code
# responded to a successful login with another plain st.rerun(), which
# simply re-ran that SAME page again -- e.g. pages/system_administration.py.
# That page immediately calls require_work_mode(T, "System Administration"),
# and if the newly logged-in person's role isn't allowed into that specific
# workspace, they are instantly blocked with "You do not have access to this
# workspace," even though they just logged in correctly. Closing the tab
# "fixed" it only because a brand-new tab always starts at app.py, which
# correctly routes by role -- the bug was that login itself never did that
# redirect.
#
# FIX 1 -- Login now redirects.
# A successful login now calls st.switch_page(...) to the landing page for
# that role's default work mode (the same helper app.py already uses),
# instead of st.rerun(). This guarantees every login lands on a page the
# newly authenticated person is actually allowed to see, regardless of which
# page the login form happened to be shown on.
#
# FIX 2 -- Logout now clears the ENTIRE session, not a fixed list of keys.
# Previously, logout only reset authed/user_name/user_role/active_work_mode
# (+ previous_work_mode). Every other piece of state from the previous
# person's session -- ReflectionContext, ReflectionSession, open-tab flags,
# checkbox selections, admin-panel inputs, Knowledge Assistant results,
# delete-confirmation flags, draft-editing text boxes, and anything else --
# stayed in st.session_state and could bleed into the next person's session
# in the same tab.
#
# Rather than maintaining a hand-curated list of "things to remember to
# clear" (which is exactly how this kind of bug reappears later, whenever
# someone adds a new session_state key and forgets to add it to the
# clear-list too), logout now deletes EVERY key in st.session_state except
# an explicit, short KEEP-list of things that are genuinely meant to persist
# across different users in the same browser tab. Today that list is just
# the language preference. Anything not explicitly kept is gone the moment
# logout happens -- safe by default for any future feature.
#
# Logout ordering (unchanged from before)
# ------------------------------------------
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
# flag, "_logout_requested", and reruns. The actual reset happens at the
# very top of init_identity() instead -- which every page calls BEFORE
# render_nav() -- so the reset always runs before that widget exists
# for that run, which is allowed.

ROLES = ["Social Worker", "Supervisor", "Programme Manager", "System Administrator"]

LEARNING_VISIBLE_ROLES = {"Supervisor", "Programme Manager", "System Administrator"}

# FR-028: who can browse completed/reflected case history. Same tier
# as Learning for now — supervisory and administrative roles only.
CASE_HISTORY_VISIBLE_ROLES = {"Supervisor", "Programme Manager", "System Administrator"}

# --- Logout: explicit KEEP-list --------------------------------------------
#
# Everything in st.session_state is wiped on logout EXCEPT the keys listed
# here. This is intentionally a short, explicit allow-list (not a
# deny-list) so that any new feature added later is safe-by-default: a new
# session_state key that nobody remembers to add to a "clear on logout"
# list will simply be wiped along with everything else, rather than
# silently surviving into the next user's session.
#
# "lang" (the Español/Euskera/English language preference) is the one
# thing genuinely designed to persist regardless of who is using the
# browser tab -- it reflects a preference for that physical device/tab,
# not for a particular professional's account.
LOGOUT_KEEP_KEYS = {"lang"}

# Used only by _check_login() below, for an unknown username, so that
# checking a password always costs the same bcrypt comparison whether
# or not the username exists -- see _check_login()'s docstring. This
# is a fixed, valid bcrypt hash of an arbitrary placeholder string; it
# is not a real account and does not need to be kept secret.
_DUMMY_HASH = "$2b$12$CwTycUXWue0Thq9StjUM0uJ8i6XZg8x0N.9E6Dn3ORaTgvtdcOaWq"


def _load_users():
    """
    Reads user accounts from Streamlit Cloud Secrets, structured as:

        [users.jmwangi]
        password = "$2b$12$...."   # a bcrypt HASH, not a plain password
        name = "John Mwangi"
        role = "Social Worker"

    IMPORTANT (password hashing change): `password` must be a bcrypt
    hash, not the account holder's actual password. Use
    generate_password_hash.py (project root) to turn a chosen password
    into the hash string to paste here -- see that script for
    instructions. An account whose `password` value is not a valid
    bcrypt hash will simply be unable to log in (see _check_login()
    below), rather than falling back to a plain-text comparison.

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
    """
    Verifies a submitted username/password pair against the bcrypt
    hash stored for that account in secrets.toml (see _load_users()
    docstring). Returns the matching user dict on success, else None.

    Deliberately does the same amount of work (a bcrypt comparison)
    whether or not `username` exists, using a fixed dummy hash for
    unknown usernames -- this avoids letting someone learn which
    usernames are valid accounts purely by measuring how fast the app
    responds (an unknown username used to fail instantly, before ever
    reaching the password check).
    """
    user = users.get(username)
    stored_hash = user.get("password") if user else _DUMMY_HASH
    valid = verify_password(password, stored_hash) if password else False
    if user and valid:
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


def _wipe_session_for_logout():
    """
    Full session-state reset for logout, keeping only the keys in
    LOGOUT_KEEP_KEYS (see module docstring, "FIX 2").

    This intentionally clears far more than the old fixed list of
    identity/work-mode keys -- it clears EVERYTHING: ReflectionContext
    and ReflectionSession (rdi/reflection_context.py,
    rdi/reflection_session.py), every per-document checkbox
    (ctx_hist_*, chk_*), every open Reflection Workspace tab and its
    conversation input (workspace_open_*, convo_input_*, convo_error_*),
    delete-confirmation flags (confirm_delete_*), draft-editing text
    boxes (edit_*), the Documentation page's form-reset counters
    (doc_reset, doc_type_idx, case_ref_*, doc_type_*, text_*,
    lang_field_*), admin-panel inputs and toggles (admin_*), the
    Knowledge Assistant's last answer (ka_last_result, ka_last_question,
    ka_question_input), save_status, and anything else -- known or not
    yet invented -- that a previous person's session might have left
    behind.

    Called from init_identity() BEFORE any widget is instantiated this
    run (see module docstring, "Logout ordering"), so removing keys
    here -- including "active_work_mode" -- is always safe.
    """
    preserved = {k: st.session_state[k] for k in LOGOUT_KEEP_KEYS if k in st.session_state}
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    for k, v in preserved.items():
        st.session_state[k] = v


def init_identity(T):
    # Defensive safety net: app.py calls services.db_schema.ensure_schema()
    # once at startup, but Streamlit's classic multipage routing means a
    # bookmarked/direct URL to a page under pages/ can run that page's
    # script WITHOUT app.py ever having run first in this session. Every
    # page calls init_identity() before touching any storage function, so
    # calling ensure_schema() here too guarantees the schema always exists
    # first -- it's a no-op after the first successful call in this
    # process (see services/db_schema.py's process-local guard).
    from services.db_schema import ensure_schema
    ensure_schema()

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
    # above ("Logout ordering") for why this can't happen inside
    # render_identity_footer itself.
    if st.session_state.pop("_logout_requested", False):
        _wipe_session_for_logout()
        # Re-establish the plain defaults every page expects to find,
        # exactly as on a brand-new session -- _wipe_session_for_logout()
        # deliberately does not special-case these, so they're set here,
        # the same way they were set above for a first-ever visit.
        st.session_state.authed = False
        st.session_state.user_name = ""
        st.session_state.user_role = ""
        st.session_state.active_work_mode = "Practitioner"

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
        locked_out, retry_after_seconds = is_locked_out(username)
        if locked_out:
            minutes = max(1, (retry_after_seconds + 59) // 60)
            st.error(T["login_locked"].format(minutes=minutes))
            st.stop()

        user = _check_login(username, password, users)
        if user:
            # Successful login: forget any recent failed attempts for
            # this username, so a couple of earlier typos don't count
            # toward a future lockout.
            clear_failed_attempts(username)
            # Belt-and-braces: a login is always the start of a brand
            # new session for whoever is now authenticated. Wipe
            # anything that might still be sitting in session_state
            # (e.g. if this login form is being submitted for the very
            # first time after a logout, before this run's own wipe
            # above ever had a chance to run) so a fresh login can never
            # inherit stale, unrelated state either.
            _wipe_session_for_logout()

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

            # FIX 1 (see module docstring): redirect straight to the
            # landing page for this role's default work mode, instead of
            # merely rerunning whatever page the login form happened to
            # be shown on. This is what guarantees a newly authenticated
            # person never lands back on a page their role isn't allowed
            # into (the direct cause of the "You do not have access to
            # this workspace" bug when logging in as a different user in
            # the same tab).
            st.switch_page(landing_page_for_workspace(st.session_state.active_work_mode))
        else:
            record_failed_attempt(username)
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

    Note on the logout/login fix above: since login now always redirects
    (via st.switch_page) to the landing page for the newly authenticated
    role's default work mode, and that landing page always calls
    require_work_mode() with a workspace that role IS allowed into, this
    guard should no longer be reached with a mismatched role/workspace
    pair immediately after a login. It remains in place unchanged as the
    defense against direct/typed URL access, which is its original
    purpose.
    """
    role = st.session_state.get("user_role", "")
    if not can_access_workspace(role, workspace):
        st.error(T.get("workmode_access_denied", "You do not have access to this workspace."))
        st.stop()

    current = st.session_state.get("active_work_mode")
    if workspace == "Practitioner" and current and current != "Practitioner":
        st.session_state["previous_work_mode"] = current

    st.session_state.active_work_mode = workspace