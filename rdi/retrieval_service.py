"""
Retrieval Service
====================

Sits between the Reflection Context Engine (rdi/context_engine.py) and
the semantic index (services/qdrant_service.py). This is where "Hybrid
RAG" actually happens: several small, independent retrieval strategies
each propose documents, and this module merges, dedupes, and ranks the
result into one list the Context Engine can hand to the practitioner.

Why this is a separate module from context_engine.py
---------------------------------------------------------
Qdrant/embedding logic must never be embedded directly inside reflection
orchestration or the context engine's own code -- both should be able to
ask this module "what's relevant for this case" without knowing HOW that
answer was produced. That separation is also what makes it easy to add
future retrieval strategies (Timeline, Reflection, Goal, Evidence,
Practice retrieval -- see the `Retriever` base class below) without
touching the context engine at all.

Retrieval strategies (each is a `Retriever`)
-------------------------------------------------
1. MustIncludeRetriever -- always surfaces the case's most recent
   Intervention Plan and most recent Assessment/Social work report, if
   they exist. These document types anchor a case's plan and are always
   worth having in view regardless of semantic similarity to today's
   note.
2. SemanticRetriever -- top-K documents from THIS case whose content is
   semantically similar to the current document, via Qdrant. Confidence
   scoped and filtered to case_ref, per services/qdrant_service.py.
3. RecencyRetriever -- the ORIGINAL Sprint 1 behavior (most recently
   completed documents for the case), used to fill in when semantic
   search isn't available/configured, or hasn't found much. This is
   what guarantees the app never regresses below its pre-RAG behavior.

HybridRetriever runs all three, merges by document id (first strategy to
propose a document wins its "why" label), and truncates to `limit`.

Confidentiality
-------------------
Every strategy that touches Postgres already scopes by case_ref via
services.draft_storage.get_completed_drafts() (filtered here) or
services.qdrant_service.search_similar() (filtered inside Qdrant, see
that module's docstring). This module adds no bypass -- there is no
function here that can return a document from a different case.
"""

from services.draft_storage import get_completed_drafts
from services.qdrant_service import search_similar, is_available as qdrant_available

# Document types that always anchor a case's context, regardless of
# semantic similarity -- these are the "must include" documents.
# Matched against T["doc_types"] labels used across all three
# languages (see services/language.py doc_types lists).
PLAN_DOC_TYPES = {"Intervention plan", "Esku-hartze plana", "Plan de intervención"}
ASSESSMENT_DOC_TYPES = {"Social work report", "Gizarte-txostena", "Informe social"}

DEFAULT_SEMANTIC_K = 4


class Retriever:
    """Base class for one retrieval strategy. Subclass and implement
    retrieve() to add a future strategy (Timeline, Reflection, Goal,
    Evidence, Practice retrieval, etc.) without changing anything else
    in this module or in the Context Engine."""

    #: short machine-readable reason, used for the "why is this here"
    #: transparency label shown in the Reflection Context screen.
    reason = "retrieved"

    def retrieve(self, case_ref, query_text, exclude_ids, completed_docs):
        """
        completed_docs is the case's completed documents from Postgres
        (already fetched once by the caller and shared across
        strategies, so no strategy needs to hit the DB itself just to
        do type/recency matching).

        Must return a list of dicts shaped like context_engine's
        historical-document dicts, each additionally carrying:
          - "score": float | None  (similarity score if applicable)
          - "match_reason": one of "must_include" | "semantic" | "recency"
        """
        raise NotImplementedError


def _doc_to_dict(row, score=None, match_reason="recency"):
    # row columns (from draft_storage.get_completed_drafts):
    # id, case_ref, doc_type, content, created_at, created_by,
    # created_by_role, was_edited, completed_at
    return {
        "id": row[0],
        "doc_type": row[2],
        "content": row[3],
        "created_at": row[4],
        "was_edited": row[7],
        "completed_at": row[8],
        "score": score,
        "match_reason": match_reason,
    }


class MustIncludeRetriever(Retriever):
    reason = "must_include"

    def retrieve(self, case_ref, query_text, exclude_ids, completed_docs):
        found = []
        for type_set in (PLAN_DOC_TYPES, ASSESSMENT_DOC_TYPES):
            candidates = [
                row for row in completed_docs
                if row[0] not in exclude_ids and row[2] in type_set
            ]
            if candidates:
                # completed_docs is already sorted most-recent-first by
                # the caller, so the first match is the latest one.
                found.append(_doc_to_dict(candidates[0], score=None, match_reason="must_include"))
        return found


class SemanticRetriever(Retriever):
    reason = "semantic"

    def __init__(self, k=DEFAULT_SEMANTIC_K):
        self.k = k

    def retrieve(self, case_ref, query_text, exclude_ids, completed_docs):
        if not qdrant_available() or not (query_text or "").strip():
            return []

        matches = search_similar(case_ref, query_text, exclude_ids=exclude_ids, limit=self.k)
        if not matches:
            return []

        by_id = {row[0]: row for row in completed_docs}
        results = []
        for match in matches:
            row = by_id.get(match["id"])
            if row is None:
                # Indexed in Qdrant but not present/completed in
                # Postgres right now (e.g. purged) -- skip rather than
                # risk showing a document that no longer exists.
                continue
            results.append(_doc_to_dict(row, score=match["score"], match_reason="semantic"))
        return results


class RecencyRetriever(Retriever):
    reason = "recency"

    def __init__(self, k=None):
        self.k = k

    def retrieve(self, case_ref, query_text, exclude_ids, completed_docs):
        candidates = [row for row in completed_docs if row[0] not in exclude_ids]
        if self.k is not None:
            candidates = candidates[: self.k]
        return [_doc_to_dict(row, score=None, match_reason="recency") for row in candidates]


class HybridRetriever(Retriever):
    """Runs a list of strategies in order and merges their results,
    deduped by document id -- first strategy to propose a document
    wins the "why" label (must_include takes priority over semantic,
    which takes priority over recency, matching the order below)."""

    def __init__(self, strategies=None):
        self.strategies = strategies or [
            MustIncludeRetriever(),
            SemanticRetriever(),
            RecencyRetriever(),
        ]

    def retrieve(self, case_ref, query_text, exclude_ids, completed_docs, limit=4):
        merged = {}
        for strategy in self.strategies:
            for doc in strategy.retrieve(case_ref, query_text, exclude_ids, completed_docs):
                if doc["id"] not in merged:
                    merged[doc["id"]] = doc
            if len(merged) >= limit:
                break

        # Rank: must_include first, then by score (semantic docs) /
        # recency (completed_at), so the practitioner sees the most
        # load-bearing context first.
        def sort_key(doc):
            priority = {"must_include": 0, "semantic": 1, "recency": 2}[doc["match_reason"]]
            score = -(doc["score"] or 0)
            return (priority, score, doc["completed_at"] or "")

        ordered = sorted(merged.values(), key=sort_key, reverse=False)
        return ordered[:limit]


def retrieve_historical_context(case_ref, exclude_ids=None, limit=4, query_text=""):
    """
    Public entry point used by rdi.context_engine.get_historical_context().
    Fetches the case's completed documents ONCE, then runs the Hybrid
    Retriever over them.

    Returns a list of document dicts (see _doc_to_dict) -- same shape
    the Context Engine has always returned, plus "score" and
    "match_reason" for transparency, sorted most-relevant-first.
    """
    if not case_ref or not case_ref.strip():
        return []

    exclude_ids = exclude_ids or set()

    all_completed = get_completed_drafts()
    completed_docs = [row for row in all_completed if row[1] == case_ref]
    completed_docs.sort(key=lambda row: row[8] or "", reverse=True)

    retriever = HybridRetriever()
    return retriever.retrieve(case_ref, query_text, exclude_ids, completed_docs, limit=limit)