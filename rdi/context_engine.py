"""
Reflection Context Engine
==========================

First module of the `rdi` package (Reflective Decision Intelligence).

Responsibility: before a reflection session begins, gather whatever
documentation already exists for this case that might be relevant, so the
practitioner can see it and choose what to include -- rather than the
reflection being generated from a single document in isolation.

Sprint 1 scope (superseded below)
----------------------------------
Real semantic retrieval via Qdrant was not active yet: this module
shipped a working, honest first version that retrieved this case's own
*completed* documents from Postgres, most recent first.

Hybrid RAG upgrade
--------------------
get_historical_context() now delegates to rdi.retrieval_service, which
runs several retrieval strategies (must-include key documents, Qdrant
semantic search, and the original recency fallback) and merges them --
see rdi/retrieval_service.py for the full design.

This module's PUBLIC INTERFACE is unchanged on purpose: same function
name, same return shape (list of dicts with id/doc_type/content/
created_at/was_edited/completed_at -- now with three additive keys,
"score", "match_reason" (primary reason, kept for back-compat), and
"match_reasons" (the full list of every strategy that proposed this
document -- see rdi/retrieval_service.py's "Multi-reason merge" section),
used only for the transparency label), and the same call sites
(pages/reflection_space.py, rdi/reflection_context.py) work without
needing to know retrieval got smarter. Only the internals of
get_historical_context() changed; classify_context_strength() gained one
new optional argument (avg_score) but is fully backward compatible for
any call site that doesn't pass it.

Security boundary
-------------------
The UI is not an authorization boundary. A caller must provide the
authenticated actor name and role. Before the retrieval service is called,
services.access_control.can_access_case_history() verifies that a Social
Worker owns completed documentation for the requested case, while the
existing management roles retain organisation-wide completed-history access.
Missing or invalid identity fails closed.

Development logging
----------------------
Logging goes through the shared services.rag_logging.rag_log() helper
(see that module's docstring) rather than a local, ad-hoc print()-based
helper, so "[RAG]" trace lines are reliably written to stdout on
Streamlit Cloud instead of possibly being lost to output buffering.
"""

from rdi.retrieval_service import retrieve_historical_context
from services.access_control import can_access_case_history
from services.rag_logging import rag_log

DEFAULT_HISTORY_LIMIT = 4
STRONG_CONTEXT_THRESHOLD = 3
LIMITED_CONTEXT_THRESHOLD = 1
STRONG_SIMILARITY_THRESHOLD = 0.75


def _log(msg):
    """Thin wrapper kept for call-site compatibility -- delegates to the
    shared, properly configured logger in services.rag_logging."""
    rag_log(f"[RAG] {msg}")


def get_historical_context(
    case_ref,
    exclude_ids=None,
    limit=DEFAULT_HISTORY_LIMIT,
    query_text="",
    actor_name="",
    actor_role="",
):
    """Return up to `limit` documents relevant to `case_ref`.

    Authorization is enforced against PostgreSQL before retrieval. Management
    roles may access completed history organisation-wide; a Social Worker may
    retrieve only history for a case for which they have completed
    documentation. Missing identity fails closed.

    The actor arguments are optional at the Python signature level for
    compatibility with non-user-facing tooling, but a call without them is
    denied rather than falling back to the old unscoped behaviour.
    """
    if not case_ref or not case_ref.strip():
        return []

    if not can_access_case_history(actor_name, actor_role, case_ref):
        _log("get_historical_context DENIED: case access check failed")
        return []

    exclude_ids = exclude_ids or set()
    results = retrieve_historical_context(
        case_ref, exclude_ids=exclude_ids, limit=limit, query_text=query_text,
    )

    _log(
        f"get_historical_context: returned {len(results)} document(s): "
        + (
            ", ".join(
                f"[id={d['id']} doc_type={d['doc_type']!r} reasons={d.get('match_reasons')} score={d.get('score')}"
                for d in results
            )
            if results else "(none)"
        )
    )

    return results


def classify_context_strength(count, avg_score=None):
    """Classify how much historical context is available."""
    if count >= STRONG_CONTEXT_THRESHOLD:
        strength = "strong"
    elif count >= LIMITED_CONTEXT_THRESHOLD:
        if avg_score is not None and avg_score >= STRONG_SIMILARITY_THRESHOLD:
            strength = "strong"
        else:
            strength = "limited"
    else:
        strength = "none"

    _log(f"classify_context_strength: count={count} avg_score={avg_score} -> {strength}")
    return strength
