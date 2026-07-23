"""
Qdrant Service
================

The semantic index for completed documents. This is the module that was
previously a disabled placeholder ("Saving to Qdrant (disabled in MVP)")
-- Phase 2 has arrived, so it's now a real, small, focused service:

    embed text  -->  store/search vectors in Qdrant, scoped to one case

PostgreSQL (services/draft_storage.py) remains the system of record for
everything: content, edit history, audit trail, GDPR erasure. Qdrant
holds nothing but vectors + small identifying payload metadata (never
document content), purely to power semantic search. If Qdrant is ever
wiped or unreachable, no data is lost -- the app degrades to the
recency-based historical context it already had, and a backfill (see
pages/zz_admin.py) can regenerate every embedding from Postgres at any
time.

Confidentiality boundary (mandatory, per case)
--------------------------------------------------
Every point stored here is tagged with a `case_ref` payload field, and
every search MUST filter on it. search_similar() below takes case_ref
as a required, non-optional argument specifically so there is no way to
call it without a case scope -- there is no "search everything" method
in this module at all. This is the mechanism, not just a convention:
even a semantic near-duplicate from a different client's case can never
be returned, because Qdrant discards it at the filter stage before
scoring is even considered for ranking.

Graceful degradation
------------------------
If QDRANT_URL isn't configured, or Voyage embeddings aren't available
(see services/embedding_service.py), every function here is a no-op /
returns an empty result rather than raising -- so a practitioner who
hasn't set up the semantic layer yet still gets the exact same
recency-based Reflection Context behavior the app has always had.
"""

from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels

from config import QDRANT_URL, QDRANT_API_KEY, QDRANT_COLLECTION_NAME, EMBEDDING_DIMENSIONS
from services.anonymizer import anonymize
from services.embedding_service import embed_document, embed_query, is_available as embeddings_available

_client = None
_collection_ready = False


def is_available():
    """True if Qdrant AND the embedding provider are both configured.
    Callers should treat a False here the same way they'd treat any
    other "semantic layer not set up yet" case: fall back gracefully."""
    return bool(QDRANT_URL) and embeddings_available()


def _get_client():
    global _client
    if not QDRANT_URL:
        return None
    if _client is None:
        _client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY or None)
    return _client


def _ensure_collection(client):
    global _collection_ready
    if _collection_ready:
        return
    existing = [c.name for c in client.get_collections().collections]
    if QDRANT_COLLECTION_NAME not in existing:
        client.create_collection(
            collection_name=QDRANT_COLLECTION_NAME,
            vectors_config=qmodels.VectorParams(
                size=EMBEDDING_DIMENSIONS,
                distance=qmodels.Distance.COSINE,
            ),
        )
    _collection_ready = True


def upsert_document(draft_id, case_ref, doc_type, content, language="",
                     created_at="", completed_at="", created_by_role="", was_edited=False):
    """
    Embed and index one COMPLETED document. Call this right after a
    document is finalized (services.draft_storage.finalize_draft), and
    also from the admin backfill for documents completed before this
    feature existed.

    The content sent to Voyage AI is anonymized first -- the same
    anonymize() function and the same boundary already used before any
    text reaches Claude (see services/anonymizer.py, reflection_service.py).
    The raw/original content is never sent to Qdrant or Voyage AI.

    No-ops silently (logs nothing sensitive, raises nothing) if Qdrant
    or embeddings aren't configured, or if embedding fails -- indexing
    is best-effort and must never block a practitioner's submission.

    `draft_id` is used directly as the Qdrant point id, so re-submitting
    (e.g. re-running a backfill) simply overwrites the same point rather
    than creating duplicates.
    """
    client = _get_client()
    if client is None or not case_ref or not (case_ref or "").strip():
        return False

    safe_text = anonymize(content or "")
    vector = embed_document(safe_text)
    if vector is None:
        return False

    try:
        _ensure_collection(client)
        client.upsert(
            collection_name=QDRANT_COLLECTION_NAME,
            points=[
                qmodels.PointStruct(
                    id=draft_id,
                    vector=vector,
                    payload={
                        "case_ref": case_ref,
                        "document_id": draft_id,
                        "document_type": doc_type,
                        "language": language,
                        "created_at": created_at,
                        "completed_at": completed_at,
                        "created_by_role": created_by_role,
                        "was_edited": bool(was_edited),
                    },
                )
            ],
        )
        return True
    except Exception:
        return False


def delete_document(draft_id):
    """
    Remove one document's vector permanently. Call this from the same
    places PostgreSQL content is permanently removed --
    draft_storage.delete_pending_draft() and
    draft_storage.purge_expired_deletions() -- so a purged case leaves
    no retrievable trace here either (mirrors the audit_log.py pattern
    of "the case is gone" being true everywhere, not just in one table).

    Deliberately NOT called from soft_delete_draft(): during the 48-hour
    restore window the case is hidden from every user-facing view
    already (status='deleted' is filtered out everywhere), but the
    vector stays so restore_draft() doesn't need to re-embed anything.
    """
    client = _get_client()
    if client is None:
        return
    try:
        client.delete(
            collection_name=QDRANT_COLLECTION_NAME,
            points_selector=qmodels.PointIdsList(points=[draft_id]),
        )
    except Exception:
        pass


def search_similar(case_ref, query_text, exclude_ids=None, limit=5):
    """
    Semantic search, ALWAYS scoped to one case. This is the only search
    entry point this module exposes -- case_ref is a required argument,
    not an optional filter, so there is no way to call this without
    confidentiality scoping.

    Returns a list of {"id": draft_id, "score": float} dicts, most
    similar first, or [] if semantic search isn't available/configured,
    the case has no indexed documents, or embedding the query failed.
    Callers (rdi.retrieval_service) are responsible for joining these
    ids back to full document rows in Postgres.
    """
    if not case_ref or not (case_ref or "").strip():
        return []

    client = _get_client()
    if client is None:
        return []

    safe_query = anonymize(query_text or "")
    vector = embed_query(safe_query)
    if vector is None:
        return []

    exclude_ids = exclude_ids or set()
    must_conditions = [
        qmodels.FieldCondition(key="case_ref", match=qmodels.MatchValue(value=case_ref))
    ]
    must_not_conditions = []
    if exclude_ids:
        must_not_conditions.append(
            qmodels.FieldCondition(
                key="document_id",
                match=qmodels.MatchAny(any=list(exclude_ids)),
            )
        )

    query_filter = qmodels.Filter(must=must_conditions, must_not=must_not_conditions)

    try:
        _ensure_collection(client)
        results = client.search(
            collection_name=QDRANT_COLLECTION_NAME,
            query_vector=vector,
            query_filter=query_filter,
            limit=limit,
        )
        return [{"id": point.id, "score": point.score} for point in results]
    except Exception:
        return []