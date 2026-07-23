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
created_at/was_edited/completed_at -- now with two additive keys, "score"
and "match_reason", used only for the transparency label), and the same
call sites (pages/reflection_space.py, rdi/reflection_context.py) work
without needing to know retrieval got smarter. Only the internals of
get_historical_context() changed; classify_context_strength() gained one
new optional argument (avg_score) but is fully backward compatible for
any call site that doesn't pass it.
"""

from rdi.retrieval_service import retrieve_historical_context

# How many historical documents to surface by default. Kept small
# deliberately -- this is meant to orient the practitioner, not overwhelm
# them with a full case file.
DEFAULT_HISTORY_LIMIT = 4

# Thresholds used to classify how much historical context was found, for
# the transparency summary shown to the practitioner.
STRONG_CONTEXT_THRESHOLD = 3
LIMITED_CONTEXT_THRESHOLD = 1

# A semantic average similarity at/above this is considered a genuinely
# strong signal (Voyage cosine scores for same-case caseworker
# documents in the same style typically land 0.7+ when topically
# related) -- used only to let a *smaller* number of documents still
# count as "strong" context when they're clearly, closely relevant,
# never to downgrade a count that already clears STRONG_CONTEXT_THRESHOLD.
STRONG_SIMILARITY_THRESHOLD = 0.75


def get_historical_context(case_ref, exclude_ids=None, limit=DEFAULT_HISTORY_LIMIT, query_text=""):
    """
    Return up to `limit` documents relevant to `case_ref`, excluding any
    ids in `exclude_ids` (typically the draft(s) the practitioner just
    selected for this session, so they aren't shown twice).

    `query_text` (new, optional) is the text of the document(s) the
    practitioner just selected -- used as the semantic search query so
    Qdrant can find genuinely related history, not just recent history.
    Omitting it (the old call signature) still works: the semantic
    strategy simply contributes nothing that turn, and results fall
    back to must-include + recency, exactly like before this upgrade.

    Returns a list of dicts:
        {
            "id": int,
            "doc_type": str,
            "content": str,
            "created_at": str (ISO timestamp),
            "completed_at": str (ISO timestamp),
            "was_edited": bool,
            "score": float | None,      # similarity score, semantic matches only
            "match_reason": str,        # "must_include" | "semantic" | "recency"
        }

    A missing/blank case_ref returns an empty list: undated, uncategorised
    documents shouldn't be silently pulled into someone else's context.
    Confidentiality is enforced structurally inside retrieve_historical_context()
    / services.qdrant_service.search_similar() -- every retrieval path is
    scoped to this case_ref and nothing else.
    """
    if not case_ref or not case_ref.strip():
        return []

    exclude_ids = exclude_ids or set()
    return retrieve_historical_context(
        case_ref, exclude_ids=exclude_ids, limit=limit, query_text=query_text,
    )


def classify_context_strength(count, avg_score=None):
    """
    Classify how much historical context is available, for the
    transparency summary ("Context Confidence"). Returns one of
    "strong", "limited", "none".

    `avg_score` (new, optional) is the average similarity score across
    included documents that came from semantic matching (None if there
    weren't any, e.g. semantic retrieval isn't configured, or every
    included document came from must-include/recency instead). When
    given, a small number of documents that are strongly, semantically
    relevant can still be classified "strong" even below
    STRONG_CONTEXT_THRESHOLD -- reflecting genuine relevance rather than
    just raw count. It can never turn a real "strong" (by count) into
    something weaker, and it never affects the "none" case.
    """
    if count >= STRONG_CONTEXT_THRESHOLD:
        return "strong"
    elif count >= LIMITED_CONTEXT_THRESHOLD:
        if avg_score is not None and avg_score >= STRONG_SIMILARITY_THRESHOLD:
            return "strong"
        return "limited"
    return "none"