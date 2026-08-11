"""
Historical Context Prefetch Cache
=====================================

Performance pass: moves the Hybrid RAG historical-context retrieval
(rdi/retrieval_service.py -- must-include key documents + Qdrant
semantic search + recency fallback) OFF the critical path of "Begin
Reflection" for the common case, so the practitioner doesn't have to
wait on it.

The problem this solves
---------------------------
Before this module existed, retrieval only ever happened the instant a
practitioner clicked "Begin Reflection" on pages/reflection_space.py --
a live Postgres + Qdrant round trip, on the critical path, blocking the
screen from rendering (previously ~5 seconds).

How this fixes it
----------------------
The moment a draft is saved (services.draft_storage.save_draft(), called
from pages/documentation.py), trigger_prefetch() below starts a
background thread that runs the EXACT SAME retrieval query
rdi.context_engine.get_historical_context() would run if that single
draft were selected on its own: same case_ref, same query_text (the
draft's own content), same default limit, same exclude_ids (a draft is
never its own historical context). The result is cached, keyed by
draft_id.

Later, when the practitioner actually clicks "Begin Reflection":
  - If EXACTLY ONE draft is selected, pages/reflection_space.py calls
    get_cached_context() first. A cache hit (the common case -- there's
    normally at least some time between saving a note and starting a
    reflection session on it) returns instantly, no live retrieval
    needed.
  - If the cache missed (background job still running, failed, or this
    draft predates the feature), or more than one draft was selected
    at once, the original live rdi.context_engine.get_historical_context()
    call runs exactly as it always has. This can only ever be as slow
    as before -- never slower, never less correct.

Why multi-draft selections are never prefetched
-----------------------------------------------------
When a practitioner selects several drafts together (e.g. same-day
multiples for one case), the live retrieval combines ALL of their text
into one semantic query. Prefetching happens per-draft, at save time,
before anyone knows which future combination of drafts (if any) will
be selected together -- there's no single query to precompute for that
case. Multi-draft selections always take the live path. This is
deliberately the simpler, always-exact choice: it costs a live retrieval
(a few seconds) only in the less common combined case, rather than
serving an approximate merged result for every combined session.

Freshness trade-off (worth knowing about)
----------------------------------------------
Because the cached result is computed at save time, it reflects the
case's history AS OF THAT MOMENT. If another practitioner completes a
new document for the same case_ref in the window between the prefetch
running and "Begin Reflection" being clicked, that brand-new document
will not appear in the served cached result (it would have appeared in
a fresh live call). This window is normally short. CONTEXT_PREFETCH_CACHE_TTL_HOURS
(config.py) bounds how stale an UNCONSUMED cache entry is allowed to
get before purge_stale_prefetch_cache() removes it outright, but does
not itself refresh a cache entry that's about to be read -- if this
staleness ever becomes a real practical problem at pilot scale, the fix
would be re-triggering prefetch on every new completed document for a
case, not something this pass attempts.

Storage
-----------
Cached results live in Postgres (context_prefetch_cache table -- see
services/db_schema.py), not in-process memory: this survives an app
restart/redeploy and works correctly even if the app is ever scaled to
more than one worker process, unlike an in-memory dict, which would
silently lose all pending prefetches on every restart and wouldn't be
visible across workers at all.

Lifecycle / cleanup
------------------------
- get_cached_context() DELETES the row the moment it's read (consumed)
  -- a cached result is only ever meant to be served once.
- context_prefetch_cache.draft_id has ON DELETE CASCADE against
  drafts.id (see services/db_schema.py), so deleting a draft (pending-
  draft deletion, or the GDPR erasure purge of a completed case)
  automatically removes any leftover cache row for it -- no extra
  cleanup call needed at either of those existing call sites.
- purge_stale_prefetch_cache() is the safety net for a draft that WAS
  prefetched but never turned into a reflection (abandoned, or the
  practitioner came back much later) -- see CONTEXT_PREFETCH_CACHE_TTL_HOURS
  above. Called at the top of pages/reflection_space.py, the same "no
  background scheduler on this hosting setup, purge opportunistically
  on next real page visit" pattern services/draft_storage.py's
  purge_expired_deletions() already uses.

Never on the critical path
-------------------------------
Every function in this module is fail-soft: trigger_prefetch() never
blocks the caller and never raises (a prefetch failure must never
prevent a draft from saving), and get_cached_context() returns None --
never an exception -- on any miss or storage error, which callers treat
exactly like "no cache, retrieve live."
"""

import json
import threading
from datetime import timedelta

from config import CONTEXT_PREFETCH_ENABLED, CONTEXT_PREFETCH_CACHE_TTL_HOURS
from services.db_pool import get_conn as _get_conn
from services.db_time import now_utc, get_logger
from services.rag_logging import rag_log
from rdi.context_engine import DEFAULT_HISTORY_LIMIT

logger = get_logger(__name__)


def _log(msg):
    """Thin wrapper kept for call-site/style consistency with the rest
    of the Hybrid RAG pipeline -- delegates to the shared logger in
    services.rag_logging."""
    rag_log(f"[RAG] {msg}")


def trigger_prefetch(draft_id, case_ref, content):
    """
    Fire-and-forget: starts a background thread that precomputes
    historical context for a just-saved draft. Called from
    pages/documentation.py immediately after services.draft_storage.save_draft()
    returns the new draft's id.

    Never blocks the caller and never raises -- if CONTEXT_PREFETCH_ENABLED
    is false, or draft_id/case_ref/content is missing or blank, this is
    simply a no-op (mirrors the same "blank case_ref -> nothing to do"
    guard already used by rdi.context_engine.get_historical_context()).
    """
    if not CONTEXT_PREFETCH_ENABLED:
        return
    if not draft_id or not (case_ref or "").strip() or not (content or "").strip():
        return

    thread = threading.Thread(
        target=_prefetch_worker,
        args=(draft_id, case_ref, content),
        daemon=True,
        name=f"context-prefetch-{draft_id}",
    )
    thread.start()


def _prefetch_worker(draft_id, case_ref, content):
    """
    Runs on the background thread started by trigger_prefetch(). Import
    of rdi.retrieval_service is deliberately local to this function
    rather than at module load time -- rdi/retrieval_service.py itself
    imports services.draft_storage, and keeping that import local here
    means a problem resolving it can only ever affect this one
    background call, never module import for anything else that imports
    services.context_prefetch (e.g. pages/reflection_space.py).
    """
    from rdi.retrieval_service import retrieve_historical_context

    try:
        historical = retrieve_historical_context(
            case_ref, exclude_ids={draft_id}, limit=DEFAULT_HISTORY_LIMIT, query_text=content,
        )
        _store_cache(draft_id, case_ref, historical)
        _log(
            f"context_prefetch: cached {len(historical)} document(s) for "
            f"draft_id={draft_id} case_ref={case_ref!r}"
        )
    except Exception:
        logger.exception(
            "context_prefetch worker FAILED for draft_id=%r case_ref=%r", draft_id, case_ref,
        )
        # Best-effort only. No cache row means get_cached_context() below
        # simply misses, and pages/reflection_space.py falls back to its
        # existing live retrieval -- exactly as if this feature didn't
        # run for this draft.


def _store_cache(draft_id, case_ref, historical):
    conn = _get_conn()
    try:
        with conn.cursor() as c:
            c.execute("""
                INSERT INTO context_prefetch_cache (draft_id, case_ref, historical_json, computed_at)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (draft_id) DO UPDATE SET
                    case_ref = EXCLUDED.case_ref,
                    historical_json = EXCLUDED.historical_json,
                    computed_at = EXCLUDED.computed_at
            """, (draft_id, case_ref, json.dumps(historical), now_utc()))
        conn.commit()
    except Exception:
        conn.rollback()
        # Most likely cause: the draft was deleted in the moment between
        # being saved and this background write finishing (a foreign key
        # violation against drafts.id) -- not an error worth surfacing.
        # There is nothing to cache for a draft that no longer exists;
        # get_cached_context() will miss and the app falls back to live
        # retrieval, same as if prefetch had never run for it.
        logger.warning(
            "context_prefetch: could not store cache for draft_id=%r "
            "(draft may have been deleted before prefetch finished)", draft_id,
        )
    finally:
        conn.close()


def get_cached_context(draft_id):
    """
    Public entry point used by pages/reflection_space.py's "Begin
    Reflection" handler, ONLY when exactly one draft is selected.

    Returns the previously precomputed historical-context list (same
    shape rdi.context_engine.get_historical_context() returns) on a
    cache hit, or None on a miss -- background job hasn't finished yet,
    failed, prefetching is disabled, or this draft predates the
    feature. Callers must treat None exactly like "no cache, retrieve
    live" -- never as an error.

    Consumes the entry: once read, the row is deleted immediately. A
    reflection context is only ever built once per draft, so there is
    nothing left to serve after this call.
    """
    if not CONTEXT_PREFETCH_ENABLED:
        return None

    conn = _get_conn()
    try:
        with conn.cursor() as c:
            c.execute(
                "SELECT historical_json FROM context_prefetch_cache WHERE draft_id=%s",
                (draft_id,),
            )
            row = c.fetchone()
            if not row:
                return None
            c.execute("DELETE FROM context_prefetch_cache WHERE draft_id=%s", (draft_id,))
        conn.commit()
    except Exception:
        conn.rollback()
        logger.exception("get_cached_context FAILED for draft_id=%r", draft_id)
        return None
    finally:
        conn.close()

    try:
        return json.loads(row[0])
    except Exception:
        logger.exception("get_cached_context: stored JSON was unreadable for draft_id=%r", draft_id)
        return None


def purge_stale_prefetch_cache():
    """
    Safety-net cleanup for cache entries that were computed but never
    consumed (e.g. a draft was prefetched but the practitioner never
    began a reflection with it). Without this, those rows would sit in
    Postgres indefinitely -- draft deletion alone doesn't catch this
    case, since the draft itself may still exist and simply never get
    selected.

    No background scheduler on this hosting setup (same reasoning as
    services.draft_storage.purge_expired_deletions()), so this is
    called opportunistically at the top of pages/reflection_space.py --
    the page every practitioner visits to begin a reflection -- rather
    than firing at an exact scheduled time.
    """
    if not CONTEXT_PREFETCH_ENABLED:
        return

    cutoff = now_utc() - timedelta(hours=CONTEXT_PREFETCH_CACHE_TTL_HOURS)
    conn = _get_conn()
    try:
        with conn.cursor() as c:
            c.execute("DELETE FROM context_prefetch_cache WHERE computed_at < %s", (cutoff,))
        conn.commit()
    except Exception:
        conn.rollback()
        logger.exception("purge_stale_prefetch_cache FAILED")
    finally:
        conn.close()