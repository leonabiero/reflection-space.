"""
Browser Cookie for Persistent Login (services/identity.py)
================================================================

Companion to services/session_store.py: that module is the
server-side source of truth ("is this session_id still valid, and who
does it belong to"); this module is purely the mechanics of getting
that session_id into, and out of, the person's browser as a cookie.

Why a hand-rolled cookie instead of a component/library
-------------------------------------------------------------
Streamlit (this app runs 1.47.1) exposes `st.context.cookies` as a
READ-ONLY view of whatever cookies the browser sent with the current
connection -- there is no built-in, server-side way to WRITE a cookie
(no `Set-Cookie` response-header API). The only way to set a cookie at
all from a plain Streamlit app is to run a small piece of JavaScript
(`document.cookie = ...`) in the browser -- see
https://github.com/streamlit/streamlit/issues/9421, an open Streamlit
feature request as of this writing. This module does exactly that,
via `streamlit.components.v1.html`, rather than adding a third-party
cookie-manager dependency for what is a handful of lines.

A necessary security trade-off: no HttpOnly
------------------------------------------------
Because the cookie is set by client-side JavaScript, it CANNOT be
marked `HttpOnly` -- that flag, by definition, blocks JavaScript from
ever touching the cookie (including setting it), so a JS-set cookie
and `HttpOnly` are mutually exclusive. This is a genuine, unavoidable
limitation of doing this from a plain Streamlit app -- the only way
around it would be putting a custom backend/reverse proxy in front of
Streamlit purely to inject a `Set-Cookie` header, which is a much
larger architectural change than this feature justifies. The cookie
IS still:
    - Secure (the browser refuses it over a plain http:// connection
      -- see config.SESSION_COOKIE_SECURE)
    - SameSite=Lax (never sent on a cross-site request)
    - an opaque, unguessable, meaningless-without-the-database token
      (see services/session_store.py) -- never the person's name,
      role, or anything else about them, so reading it tells an
      attacker nothing on its own
    - revoked server-side immediately on logout (the matching database
      row is deleted, so even a copied cookie value stops working
      instantly -- see services/session_store.py:delete_session())
This is the same trade-off any pure-JS "remember me" cookie makes
outside a framework with native Set-Cookie support, and is meaningfully
safer than storing anything in localStorage (no Secure/SameSite
protection at all, and just as readable by page JavaScript).
"""

import json

import streamlit as st
import streamlit.components.v1 as components

from config import SESSION_COOKIE_NAME, SESSION_LIFETIME_HOURS, SESSION_COOKIE_SECURE


def get_session_id():
    """
    Read the persistent-session cookie sent with THIS connection, if
    any. Returns "" if absent. Never raises -- falls back to "" if
    st.context is unavailable for any reason (e.g. called outside a
    real Streamlit session).
    """
    try:
        return st.context.cookies.get(SESSION_COOKIE_NAME, "") or ""
    except Exception:
        return ""


def set_session_cookie(session_id):
    """
    Write/refresh the persistent-session cookie in the browser via a
    tiny, invisible (0x0) JS snippet. Call this once right after
    login, and again on every authenticated page load (see
    services.identity._touch_auth_session()) to slide the cookie's
    expiry forward in lockstep with the server-side session
    (services.session_store.touch_session()).
    """
    if not session_id:
        return
    max_age_seconds = SESSION_LIFETIME_HOURS * 3600
    secure_flag = "; Secure" if SESSION_COOKIE_SECURE else ""
    # json.dumps(...) safely escapes the token for embedding inside the
    # <script> block -- defensive even though session_id only ever
    # contains URL-safe base64 characters (see
    # services.session_store._new_session_id()).
    safe_value = json.dumps(session_id)
    js = f"""
    <script>
    document.cookie = "{SESSION_COOKIE_NAME}=" + {safe_value} +
        "; Max-Age={max_age_seconds}; Path=/; SameSite=Lax{secure_flag}";
    </script>
    """
    components.html(js, height=0, width=0)


def clear_session_cookie():
    """
    Expire the persistent-session cookie immediately in the browser
    (Max-Age=0). Call this on logout, alongside deleting the matching
    row via services.session_store.delete_session() -- both are
    needed for logout to fully end the persistent session, not only
    the in-memory one.
    """
    secure_flag = "; Secure" if SESSION_COOKIE_SECURE else ""
    js = f"""
    <script>
    document.cookie = "{SESSION_COOKIE_NAME}=; Max-Age=0; Path=/; SameSite=Lax{secure_flag}";
    </script>
    """
    components.html(js, height=0, width=0)