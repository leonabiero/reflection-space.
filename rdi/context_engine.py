"""
Reflection Context Engine
==========================

First module of the `rdi` package (Reflective Decision Intelligence).

Responsibility: before a reflection session begins, gather whatever
documentation already exists for this case that might be relevant, so the
practitioner can see it and choose what to include -- rather than the
reflection being generated from a single document in isolation.

Sprint 1 scope
--------------
Real semantic retrieval (via Qdrant) is not active yet (see
services/qdrant_service.py, "disabled in MVP"). Rather than wait for that,
this module ships a working, honest first version: it retrieves this case's
own *completed* documents from Postgres, most recent first, excluding
whatever the practitioner has already selected for this session.

This is intentionally a thin wrapper around
services.draft_storage.get_completed_drafts() -- no schema changes, no new
dependencies. When Qdrant-based retrieval is introduced in a later sprint,
only the internals of get_historical_context() need to change; its return
shape and everything that calls it can stay the same.
"""

from services.draft_storage import get_completed_drafts

# How many historical documents to surface by default. Kept small
# deliberately -- this is meant to orient the practitioner, not overwhelm
# them with a full case file.
DEFAULT_HISTORY_LIMIT = 4

# Thresholds used to classify how much historical context was found, for
# the transparency summary shown to the practitioner.
STRONG_CONTEXT_THRESHOLD = 3
LIMITED_CONTEXT_THRESHOLD = 1


def get_historical_context(case_ref, exclude_ids=None, limit=DEFAULT_HISTORY_LIMIT):
    """
    Return up to `limit` completed documents belonging to `case_ref`,
    most recently completed first, excluding any ids in `exclude_ids`
    (typically the draft(s) the practitioner just selected for this
    session, so they aren't shown twice).

    Returns a list of dicts (not raw DB tuples) so callers -- and future
    retrieval backends -- don't need to know about column ordering:
        {
            "id": int,
            "doc_type": str,
            "content": str,
            "created_at": str (ISO timestamp),
            "completed_at": str (ISO timestamp),
            "was_edited": bool,
        }

    A missing/blank case_ref returns an empty list: undated, uncategorised
    documents shouldn't be silently pulled into someone else's context.
    """
    if not case_ref or not case_ref.strip():
        return []

    exclude_ids = exclude_ids or set()

    # get_completed_drafts() columns:
    # id, case_ref, doc_type, content, created_at, created_by,
    # created_by_role, was_edited, completed_at
    all_completed = get_completed_drafts()

    matches = [
        row for row in all_completed
        if row[1] == case_ref and row[0] not in exclude_ids
    ]

    # Already ordered by completed_at DESC from the query, but sort
    # defensively here so this function's contract doesn't silently depend
    # on draft_storage's internal query order.
    matches.sort(key=lambda row: row[8] or "", reverse=True)

    context_docs = []
    for row in matches[:limit]:
        context_docs.append({
            "id": row[0],
            "doc_type": row[2],
            "content": row[3],
            "created_at": row[4],
            "was_edited": row[7],
            "completed_at": row[8],
        })
    return context_docs


def classify_context_strength(count):
    """
    Classify how much historical context is available, for the
    transparency summary. Returns one of "strong", "limited", "none".

    Kept as a separate function (rather than inlined in the page) so the
    thresholds are defined once and reusable by any future page or
    companion that needs to describe context strength the same way.
    """
    if count >= STRONG_CONTEXT_THRESHOLD:
        return "strong"
    elif count >= LIMITED_CONTEXT_THRESHOLD:
        return "limited"
    return "none"