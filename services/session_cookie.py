"""
Browser Cookie for Persistent Login (services/identity.py)
================================================================

Companion to services/session_store.py: that module is the
server-side source of truth ("is this session_id still valid, and who
does it belong to"); this module is purely the mechanics of getting
that session_id into, and out of, the person's browser as a cookie.

Why streamlit-cookies-manager (and not a hand-rolled `document.cookie`
script) -- ROOT CAUSE of the "cookie never gets created" bug
--------------------------------------------------------------------
The previous implementation wrote the cookie via
`streamlit.components.v1.html("<script>document.cookie = ...</script>")`.
A `components.html(...)` block is rendered inside its own <iframe>, and
running `document.cookie = ...` from INSIDE that iframe sets the
cookie against the iframe's own document/origin -- on Streamlit Cloud
this is not reliably the same origin the main app page (and therefore
the rest of the app, including `st.context.cookies` on the next
request) is served from. The cookie was therefore being set somewhere
the browser would never send back to the app -- which is exactly why
`create_session()` succeeded (the database write is unrelated) while
no `rs_session` cookie ever showed up in dev tools and every refresh
came back with an empty session id.

`streamlit-cookies-manager` (https://github.com/ktosiek/streamlit-cookies-manager)
is a maintained Streamlit *component* (a real compiled frontend
bundle, not an inline `<script>` block) built specifically to solve
this. Its frontend code writes to `(window.parent || window).document`
-- i.e. explicitly targets the top-level app document rather than its
own iframe -- and reads the cookie back the same way, then reports the
value to Python over Streamlit's normal component protocol. That
parent-document write is the actual fix; everything else in this
module is just a thin, typed wrapper around it so the rest of the
codebase (services/identity.py) doesn't need to know the library
exists.

One CookieManager instance per script run -- required
------------------------------------------------------
The component this library registers is declared under a single fixed
key. Constructing `CookieManager()` a second time within the SAME
Streamlit script run raises a duplicate-element error. Because
services/identity.py needs to read the cookie, and later possibly
write or clear it, in that same run, ownership of the single
`CookieManager()` call is centralized in `get_cookie_manager()` below.
services.identity.init_identity() calls it exactly once, at the very
top of the function, and threads the returned `manager` object into
every other function in this module for the rest of that run. Do not
call `get_cookie_manager()` anywhere else.

A necessary, unavoidable trade-off: no HttpOnly, no Secure/SameSite
attributes
------------------------------------------------------------------
Because the cookie is still ultimately set by JavaScript running in
the browser (there is no way to write a real `Set-Cookie` response
header from a plain Streamlit app -- see
https://github.com/streamlit/streamlit/issues/9421, still open as of
this writing), it cannot be marked `HttpOnly`, and this particular
library's frontend does not add `Secure` or `SameSite` attributes
either. This is a genuine limitation of doing this from a plain
Streamlit app, shared by every maintained cookie-manager library for
Streamlit (there is currently no actively-maintained alternative that
adds those flags). The cookie IS still:
    - only ever sent to this app's own domain (ordinary same-origin
      cookie behaviour; Streamlit Cloud serves exclusively over
      https://, so in practice it never travels over plain http://
      even without an explicit `Secure` flag)
    - an opaque, unguessable, meaningless-without-the-database token
      (see services/session_store.py) -- never the person's name,
      role, or anything else about them
    - revoked server-side immediately on logout (the matching database
      row is deleted, so even a copied cookie value stops working
      instantly -- see services/session_store.py:delete_session())
    - re-validated against the database on every restore, never
      trusted on its own (see services/identity.py)

Cookie lifetime vs. session lifetime
-----------------------------------
This library's `CookieManager` does not expose a way to set a custom
Max-Age/expiry per cookie (unlike the previous hand-rolled version, it
always writes a browser-side expiry of ~365 days). The ACTUAL
lifetime of a login is still governed entirely by
`config.SESSION_LIFETIME_HOURS` on the server side, unchanged:
`services.session_store.validate_session()` rejects (and
`services.identity.init_identity()` clears the cookie for) any
session_id whose database row has expired, regardless of how long the
cookie itself is willing to sit in the browser. A long-lived cookie
holding an already-expired, worthless token is not a security
regression -- it simply means the browser stops bothering to send a
cookie sooner than it otherwise could, exactly as before.
"""

import streamlit as st
from streamlit_cookies_manager import CookieManager

from config import SESSION_COOKIE_NAME


def get_cookie_manager():
    """
    Construct the ONE CookieManager for this script run. Must be
    called exactly once per run -- see the module docstring above --
    by services.identity.init_identity(), at the very top of the
    function, before anything else in this module is used. The
    returned object is then passed as the first argument to every
    other function below for the remainder of that same run.
    """
    return CookieManager()


def cookie_manager_ready(manager) -> bool:
    """
    True once the browser's current cookies have actually been read
    back over the wire for THIS manager instance. False for one brief
    instant on the very first script run of a brand-new browser
    session/tab -- the component's frontend needs one round trip to
    report back, and Streamlit automatically reruns the script the
    moment that value arrives, so this becomes True on the very next
    run without any action needed here. Never raises.
    """
    try:
        return manager is not None and manager.ready()
    except Exception:
        return False


def get_session_id(manager):
    """
    Read the persistent-session cookie sent with THIS connection, if
    any. Returns "" if absent, if the manager isn't ready yet, or on
    any error -- never raises.
    """
    try:
        if not cookie_manager_ready(manager):
            return ""
        return manager.get(SESSION_COOKIE_NAME) or ""
    except Exception:
        return ""


def set_session_cookie(manager, session_id):
    """
    Write/refresh the persistent-session cookie in the browser. Call
    this once right after login, and again on every authenticated page
    load (see services.identity._touch_auth_session()) so the browser
    keeps carrying a valid token for as long as the server-side session
    (services.session_store.touch_session()) stays alive.

    Best-effort -- silently does nothing (never raises) if `manager`
    isn't ready yet or `session_id` is empty. `.save()` forces the
    write to happen immediately in this run rather than waiting for a
    later rerun, which matters here because a successful login is
    followed straight away by `st.switch_page(...)`
    (services/identity.py).
    """
    if not session_id:
        return
    try:
        if not cookie_manager_ready(manager):
            return
        manager[SESSION_COOKIE_NAME] = session_id
        manager.save()
    except Exception:
        pass


def clear_session_cookie(manager):
    """
    Remove the persistent-session cookie from the browser immediately.
    Call this on logout, alongside deleting the matching row via
    services.session_store.delete_session() -- both are needed for
    logout to fully end the persistent session, not only the
    in-memory one. Also called whenever a restored cookie turns out to
    be invalid/expired/orphaned (see services.identity.init_identity()),
    so the browser stops sending a worthless token.

    Best-effort -- never raises.
    """
    try:
        if not cookie_manager_ready(manager):
            return
        if SESSION_COOKIE_NAME in manager:
            del manager[SESSION_COOKIE_NAME]
            manager.save()
    except Exception:
        pass