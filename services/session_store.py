"""
Persistent Login Sessions (survive a browser refresh)
==========================================================

Server-side half of the "stay logged in after F5" feature -- see
config.py's "Persistent login sessions" block for the feature-level
overview, and services/session_cookie.py for the browser-cookie half.
services/identity.py (init_identity()) is the only caller of this
module.

Design, deliberately mirrors services/presence.py and
services/login_rate_limiter.py
-----------------------------------------------------------
A small Postgres table, one row per active browser session, keyed by
an opaque, cryptographically random session_id (never predictable,
never derived from the username or password -- see _new_session_id()
below). That random id is the ONLY thing ever stored in the browser
(as a cookie, see services/session_cookie.py); looking it up here is
what proves a returning browser still belongs to a genuine, still-
valid, previously authenticated session. Nothing in the cookie itself
needs to be signed or encrypted, because the token is unguessable
(256 bits of randomness from Python's `secrets` module) and is
meaningless without a matching row in this table -- the same trust
model as Django's or Flask's default server-side session cookie.

Why the role/name are NOT stored here
------------------------------------------
Only `username` is stored -- the same key used to look the account up
in Streamlit Cloud Secrets at login (see services/identity.py,
_load_users()). On every restore, the CURRENT name/role are re-read
fresh from secrets.toml rather than trusted from this table (see
services/identity.py). This means changing or revoking someone's role
-- or removing their account entirely -- in Secrets takes effect the
very next time their browser reloads the app, exactly as if this were
a brand new login: a stale or tampered privilege can never survive a
page refresh.

Rolling ("sliding") expiry
------------------------------
Every authenticated page load calls touch_session(), which pushes
expires_at forward by config.SESSION_LIFETIME_HOURS from *now* and
records the current active_work_mode -- mirroring
services/presence.py's touch() heartbeat. A session that is actively
being used never expires; one that is abandoned (browser closed, no
further page loads) naturally expires SESSION_LIFETIME_HOURS after
the last activity. validate_session() is the read-only counterpart,
called once at the top of a fresh script run (e.g. right after
pressing F5) to decide whether to restore a session automatically
instead of showing the login form -- it deliberately does NOT extend
the expiry itself (see its docstring).

Fails safe, not open
------------------------
Unlike services/login_rate_limiter.py (which fails OPEN, since a
lockout-tracking outage must never be the reason nobody can sign in),
validate_session() fails CLOSED: if the database is unreachable, it
returns None rather than restoring a session. An unreachable database
must never be treated as "let them in anyway" -- worst case, someone
sees the ordinary login form a little more often than
SESSION_LIFETIME_HOURS alone would require, exactly as if this
feature did not exist yet.
"""

import secrets
from datetime import timedelta

from config import SESSION_LIFETIME_HOURS
from services.db_time import now_utc, get_logger
from services.db_pool import get_conn as _acquire_pooled_conn

logger = get_logger(__name__)


def _get_conn():
    """Acquire a pooled connection (services/db_pool.py). Schema
    creation lives centrally in services/db_schema.py:ensure_schema(),
    called once at application startup -- this is just a pool
    checkout, same pattern as every other services/*.py storage
    module."""
    return _acquire_pooled_conn()


def _new_session_id():
    """A cryptographically random, URL-safe token (256 bits of
    entropy) -- unguessable, and carries no information about the
    account it belongs to on its own. Never derived from the
    username, password, or anything else predictable."""
    return secrets.token_urlsafe(32)


def create_session(username, active_work_mode=""):
    """
    Start a new persistent session for `username`, called right after
    a successful password login (services.identity.init_identity()).
    Returns the new opaque session_id to store in the browser's
    cookie, or None if the database is unreachable.

    Best-effort: a None return must be treated by the caller as
    "persistence unavailable right now" -- the person is still logged
    in for the current browser tab via st.session_state exactly as
    before this feature existed; they simply won't survive a refresh
    until the database is reachable again on a later page load.
    """
    if not username:
        return None
    session_id = _new_session_id()
    try:
        conn = _get_conn()
    except Exception:
        # Connection acquisition itself failed (e.g. the pool/database
        # is unreachable) -- there is no connection to roll back or
        # close here. Fail the same way any other database error here
        # fails: return None, never raise into the caller.
        logger.exception("create_session: could not acquire a database connection")
        return None
    try:
        with conn.cursor() as c:
            now = now_utc()
            expires = now + timedelta(hours=SESSION_LIFETIME_HOURS)
            c.execute("""
                INSERT INTO auth_sessions
                    (session_id, username, active_work_mode, created_at, last_seen_at, expires_at)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (session_id, username, active_work_mode, now, now, expires))
        conn.commit()
        return session_id
    except Exception:
        conn.rollback()
        logger.exception("create_session FAILED for username=%r", username)
        return None
    finally:
        conn.close()


def validate_session(session_id):
    """
    Look up `session_id` (as read from the browser's cookie -- see
    services/session_cookie.py). Returns
    {"username": str, "active_work_mode": str} if a matching,
    not-yet-expired row exists, else None.

    Does NOT extend the session's expiry -- that is touch_session()'s
    job, called separately by services.identity ONLY once it has also
    confirmed the restored account still exists in secrets.toml.
    Keeping "is this still valid" and "extend it" as two separate
    steps means a session that turns out to belong to a
    since-removed account is never accidentally renewed first.

    Fails CLOSED (returns None) on any database error -- see module
    docstring, "Fails safe, not open".
    """
    if not session_id:
        return None
    try:
        conn = _get_conn()
    except Exception:
        # See create_session() above: connection acquisition failing
        # is just another way this check fails CLOSED (returns None),
        # never an uncaught exception into services.identity.
        logger.exception("validate_session: could not acquire a database connection")
        return None
    try:
        with conn.cursor() as c:
            c.execute("""
                SELECT username, active_work_mode, expires_at
                FROM auth_sessions WHERE session_id = %s
            """, (session_id,))
            row = c.fetchone()
        if not row:
            return None
        username, active_work_mode, expires_at = row
        if expires_at is None or expires_at < now_utc():
            return None
        return {"username": username, "active_work_mode": active_work_mode or ""}
    except Exception:
        logger.exception("validate_session FAILED")
        return None
    finally:
        conn.close()


def touch_session(session_id, active_work_mode=""):
    """
    Extend an already-validated session's expiry by
    SESSION_LIFETIME_HOURS from now, and record the currently active
    work mode so a later refresh restores the exact workspace the
    person was in. Call this once per authenticated page load,
    alongside services.presence.touch() (see services/identity.py).

    Best-effort -- never raises. A failed heartbeat here must never
    block a page from rendering; worst case, the session simply
    expires a little earlier than SESSION_LIFETIME_HOURS of true
    inactivity would suggest.

    Also opportunistically deletes every already-expired session (not
    only this one) so this table never grows without bound -- mirrors
    services/login_rate_limiter.py's cleanup-on-write pattern.
    """
    if not session_id:
        return
    try:
        conn = _get_conn()
    except Exception:
        logger.warning("touch_session: could not acquire a database connection", exc_info=True)
        return
    try:
        with conn.cursor() as c:
            now = now_utc()
            expires = now + timedelta(hours=SESSION_LIFETIME_HOURS)
            c.execute("""
                UPDATE auth_sessions
                SET last_seen_at = %s, expires_at = %s, active_work_mode = %s
                WHERE session_id = %s
            """, (now, expires, active_work_mode, session_id))
            c.execute("DELETE FROM auth_sessions WHERE expires_at < %s", (now,))
        conn.commit()
    except Exception:
        conn.rollback()
        logger.warning("touch_session FAILED for a session", exc_info=True)
    finally:
        conn.close()


def delete_session(session_id):
    """
    Permanently end one persistent session -- called on logout (see
    services.identity.init_identity()'s logout handling). After this,
    the browser's cookie -- even before it is cleared client-side --
    is worthless: validate_session() returns None for it from this
    point on.

    Best-effort, same reasoning as touch_session() -- a failed delete
    here must never prevent the person from being logged out locally
    (st.session_state is always wiped regardless, see
    services.identity._wipe_session_for_logout()); worst case, the
    orphaned row simply expires naturally at its existing expires_at
    and is swept up by a later touch_session() cleanup elsewhere.
    """
    if not session_id:
        return
    try:
        conn = _get_conn()
    except Exception:
        logger.warning("delete_session: could not acquire a database connection", exc_info=True)
        return
    try:
        with conn.cursor() as c:
            c.execute("DELETE FROM auth_sessions WHERE session_id = %s", (session_id,))
        conn.commit()
    except Exception:
        conn.rollback()
        logger.warning("delete_session FAILED", exc_info=True)
    finally:
        conn.close()