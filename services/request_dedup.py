import hashlib
from datetime import timedelta

from services.db_pool import get_conn as _acquire_pooled_conn
from services.db_time import now_utc, get_logger

logger = get_logger(__name__)

# Shared Request Deduplication (Idempotency) Helper
# =====================================================
#
# Reliability-hardening pass (September pilot). This is the single
# place that answers one question for any expensive or state-changing
# operation in the app: "has THIS EXACT request already been started
# or finished very recently?"
#
# This is a different problem from services/rate_limiter.py and
# services/ka_rate_limiter.py, which answer "has this person done too
# MANY of these lately?" -- a person can be well within their hourly
# limit and still trigger the exact same request twice (a double
# click, a slow connection causing a retry, two browser tabs open on
# the same case). This module catches THAT specific situation, not
# volume.
#
# Design, deliberately simple (same philosophy as rate_limiter.py)
# -------------------------------------------------------------------
# One small Postgres table (idempotent_requests), one row per DISTINCT
# request currently being handled or recently finished. A "request" is
# identified by a `request_id` the caller computes -- normally via
# fingerprint() below, from the pieces that make two attempts "the
# same request" for that operation (e.g. who is asking + exactly what
# they submitted). Two calls that fingerprint to the same value are,
# by definition, the same logical request.
#
# claim() is a single atomic INSERT ... ON CONFLICT DO NOTHING: only
# the FIRST caller to reach it for a given request_id gets "claimed"
# back and should proceed; every other caller (including a genuine
# concurrent duplicate) gets told the request is already "in_progress"
# or already "completed" and should NOT repeat the expensive work.
#
# Rows expire after `ttl_minutes` (opportunistically cleaned up on
# every call, same pattern as rate_limiter.py's CLEANUP_HOURS) -- this
# is intentionally short. The purpose here is only to catch
# near-simultaneous duplicates, never to permanently stop someone from
# legitimately repeating the same action later (e.g. asking the same
# Knowledge Assistant question again tomorrow, or re-running a
# reflection on the same document next week). Volume limits belong to
# the rate limiters, not to this module.
#
# Fails OPEN (claim() returns "claimed") if the database is
# unreachable for any reason -- exactly like rate_limiter.py, an
# outage of this safety net must never be the reason someone can't do
# their normal work. The UI-side in-flight lock (a plain session-state
# flag, unrelated to this module) remains the primary, always-available
# protection against a double click; this module is the backend-level
# backstop for cases the UI lock can't see (e.g. two browser tabs).

DEFAULT_TTL_MINUTES = 10


def fingerprint(*parts) -> str:
    """
    Build a stable request_id from whatever pieces of information make
    two attempts "the same request" for a given operation (e.g. the
    person's name, a case reference, and the exact text being
    submitted). Order matters -- always pass parts in the same order
    for the same operation. None values are treated as empty strings.
    Deliberately a one-way hash: this never needs to be reversed, and
    hashing keeps request_id a fixed, short size regardless of how
    long the underlying content (e.g. a full document) is.
    """
    raw = "||".join("" if p is None else str(p) for p in parts)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _get_conn():
    return _acquire_pooled_conn()


def claim(request_id: str, kind: str, ttl_minutes: int = DEFAULT_TTL_MINUTES) -> str:
    """
    Try to claim `request_id` (see fingerprint() above) as being
    handled right now, under the given `kind` (a short label such as
    "reflection", "knowledge_assistant", or "companion_conversation" --
    purely for readability if this table is ever inspected directly,
    not used in matching).

    Returns exactly one of:
        "claimed"     -- no unexpired row existed for this request_id;
                          one now does, owned by this call. The caller
                          should proceed with the expensive operation,
                          and MUST call complete() on success or
                          release() on failure when it's done.
        "in_progress" -- another attempt at this exact request is
                          already running (its claim hasn't been
                          completed or released yet). The caller must
                          NOT repeat the expensive operation.
        "completed"   -- this exact request already finished
                          successfully within the last `ttl_minutes`.
                          The caller must NOT repeat the expensive
                          operation.

    Fails OPEN -- returns "claimed" if the database is unreachable,
    so a rate-limiter/dedup outage can never be the reason someone
    can't do their normal work (see module docstring).
    """
    if not request_id:
        return "claimed"

    conn = None
    try:
        conn = _get_conn()
        try:
            with conn.cursor() as c:
                now = now_utc()
                cutoff = now - timedelta(minutes=ttl_minutes)

                # Best-effort housekeeping, same pattern as
                # rate_limiter.py -- cheap at this volume, keeps the
                # table from growing without bound.
                c.execute("DELETE FROM idempotent_requests WHERE created_at < %s", (cutoff,))

                c.execute(
                    """
                    INSERT INTO idempotent_requests (request_id, kind, status, created_at)
                    VALUES (%s, %s, 'in_progress', %s)
                    ON CONFLICT (request_id) DO NOTHING
                    """,
                    (request_id, kind, now),
                )

                if c.rowcount == 1:
                    conn.commit()
                    return "claimed"

                # Someone already holds (or held) this exact request --
                # find out whether it's still running or already done.
                c.execute(
                    "SELECT status FROM idempotent_requests WHERE request_id = %s",
                    (request_id,),
                )
                row = c.fetchone()
            conn.commit()
            if row and row[0] == "completed":
                return "completed"
            return "in_progress"
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
    except Exception:
        # Fail open -- see module docstring.
        logger.warning("request_dedup.claim FAILED (failing open): kind=%r", kind, exc_info=True)
        return "claimed"


def complete(request_id: str) -> None:
    """
    Mark a previously-claimed request as successfully finished. A
    duplicate arriving after this point (and before the row expires)
    will see "completed" from claim() instead of "in_progress".
    Best-effort -- if this fails, the claim simply expires normally
    after `ttl_minutes` instead of being marked done early, which is
    safe (never blocks anyone, at worst a genuine duplicate arriving
    in that narrow window is not caught).
    """
    if not request_id:
        return
    conn = None
    try:
        conn = _get_conn()
        try:
            with conn.cursor() as c:
                c.execute(
                    "UPDATE idempotent_requests SET status = 'completed', completed_at = %s WHERE request_id = %s",
                    (now_utc(), request_id),
                )
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
    except Exception:
        logger.warning("request_dedup.complete FAILED (non-fatal)", exc_info=True)


def release(request_id: str) -> None:
    """
    Give up a previously-claimed request entirely (the operation
    failed or was never actually run) -- deletes the claim so a
    genuine retry of the SAME request is immediately treated as brand
    new, not as a duplicate. Always call this on failure/exception, or
    a real retry could be wrongly blocked until the row expires.
    Best-effort/non-fatal, same reasoning as complete().
    """
    if not request_id:
        return
    conn = None
    try:
        conn = _get_conn()
        try:
            with conn.cursor() as c:
                c.execute("DELETE FROM idempotent_requests WHERE request_id = %s", (request_id,))
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
    except Exception:
        logger.warning("request_dedup.release FAILED (non-fatal)", exc_info=True)
