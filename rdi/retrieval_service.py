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

HybridRetriever runs all three, merges by document id (a document that
is proposed by more than one strategy keeps ALL of the reasons it was
proposed for -- see "Multi-reason merge" below), and truncates to
`limit`.

Multi-reason merge
----------------------
Previously, a document that happened to be proposed by more than one
strategy (e.g. it's both the case's latest Assessment AND came back as
a semantic match) silently kept only the FIRST strategy's reason,
because dict-based dedup just skipped it the second time it was seen.

Each merged document now carries a `match_reasons` list (e.g.
["must_include", "semantic"]) instead of a single reason, so the
practitioner-facing transparency label can show every reason a document
is included, not just one. `match_reason` (singular) is still populated
for backward compatibility with any code that only cares about the
single highest-priority reason (must_include > semantic > recency) --
it is now derived from `match_reasons` rather than being the only
signal.

If the SemanticRetriever proposed a document, that document's semantic
`score` is preserved on the merged record even if another strategy also
proposed it (and would otherwise have no score) -- so "this document is
also a documented semantic match, 0.81 similarity" is never lost just
because MustIncludeRetriever got to it in the same pass.

This module ONLY changes the shape of what's returned (additive keys)
and how proposals from multiple strategies for the SAME document are
combined. It does not change which documents are retrieved, their
ranking priority (must_include > semantic > recency, then score, then
recency), or the `limit` truncation behavior.

Confidentiality
-------------------
Every strategy that touches Postgres already scopes by case_ref via
services.draft_storage.get_completed_drafts() (filtered here) or
services.qdrant_service.search_similar() (filtered inside Qdrant, see
that module's docstring). This module adds no bypass -- there is no
function here that can return a document from a different case.

Development logging (temporary, Hybrid RAG hardening pass)
------------------------------------------------------------
Each strategy's raw output, and the final merged result, are printed
with a "[RAG]" prefix so the whole hybrid pipeline can be traced end to
end during testing. Purely observational -- see
services/qdrant_service.py's module docstring for the same convention
used on the indexing/search side.
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

# Priority order used both for the primary `match_reason` label and for
# ranking merged documents -- unchanged from before this pass.
_REASON_PRIORITY = {"must_include": 0, "semantic": 1, "recency": 2}


def _log(msg):
    """Temporary development logging helper, matching the convention in
    services/qdrant_service.py. Never raises."""
    try:
        print(f"[RAG] {msg}")
    except Exception:
        pass


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
    deduped by document id. Unlike before, a document proposed by more
    than one strategy now keeps ALL of the reasons it was proposed for
    (see module docstring, "Multi-reason merge"), and keeps a semantic
    score if any strategy that ran for it was the SemanticRetriever."""

    def __init__(self, strategies=None):
        self.strategies = strategies or [
            MustIncludeRetriever(),
            SemanticRetriever(),
            RecencyRetriever(),
        ]

    def retrieve(self, case_ref, query_text, exclude_ids, completed_docs, limit=4):
        merged = {}
        for strategy in self.strategies:
            strategy_name = type(strategy).__name__
            docs = strategy.retrieve(case_ref, query_text, exclude_ids, completed_docs)
            _log(
                f"{strategy_name} returned: "
                + (
                    ", ".join(
                        f"[id={d['id']} doc_type={d['doc_type']!r} reason={d['match_reason']} score={d['score']}"
                        for d in docs
                    )
                    if docs else "(none)"
                )
            )

            for doc in docs:
                doc_id = doc["id"]
                reason = doc["match_reason"]
                if doc_id not in merged:
                    entry = dict(doc)
                    entry["match_reasons"] = [reason]
                    merged[doc_id] = entry
                else:
                    entry = merged[doc_id]
                    if reason not in entry["match_reasons"]:
                        entry["match_reasons"].append(reason)
                    # Preserve a semantic score even if a later/earlier
                    # strategy proposed the same document without one.
                    if entry.get("score") is None and doc.get("score") is not None:
                        entry["score"] = doc["score"]

            if len(merged) >= limit:
                break

        # Recompute the primary `match_reason` for each merged document
        # from its full reason list, so ranking and any code that only
        # looks at the singular field still gets the highest-priority
        # reason (must_include > semantic > recency).
        for entry in merged.values():
            entry["match_reason"] = min(entry["match_reasons"], key=lambda r: _REASON_PRIORITY.get(r, 99))

        # Rank: must_include first, then by score (semantic docs) /
        # recency (completed_at), so the practitioner sees the most
        # load-bearing context first. Unchanged ranking logic -- only
        # now reads from the (possibly multi-reason) merged entry.
        def sort_key(doc):
            priority = _REASON_PRIORITY[doc["match_reason"]]
            score = -(doc["score"] or 0)
            return (priority, score, doc["completed_at"] or "")

        ordered = sorted(merged.values(), key=sort_key, reverse=False)
        result = ordered[:limit]

        _log(
            "Merged Result: "
            + (
                ", ".join(
                    f"[id={d['id']} doc_type={d['doc_type']!r} reasons={d['match_reasons']} score={d['score']}"
                    for d in result
                )
                if result else "(none)"
            )
        )

        return result


def retrieve_historical_context(case_ref, exclude_ids=None, limit=4, query_text=""):
    """
    Public entry point used by rdi.context_engine.get_historical_context().
    Fetches the case's completed documents ONCE, then runs the Hybrid
    Retriever over them.

    Returns a list of document dicts (see _doc_to_dict) -- same shape
    the Context Engine has always returned, plus "score", "match_reason"
    (primary reason, back-compat) and "match_reasons" (full list) for
    transparency, sorted most-relevant-first.
    """
    if not case_ref or not case_ref.strip():
        return []

    exclude_ids = exclude_ids or set()

    _log(f"retrieve_historical_context start: case_ref={case_ref!r} exclude_ids={sorted(exclude_ids)} limit={limit} query_text_len={len(query_text or '')}")

    all_completed = get_completed_drafts()
    completed_docs = [row for row in all_completed if row[1] == case_ref]
    completed_docs.sort(key=lambda row: row[8] or "", reverse=True)

    retriever = HybridRetriever()
    return retriever.retrieve(case_ref, query_text, exclude_ids, completed_docs, limit=limit)