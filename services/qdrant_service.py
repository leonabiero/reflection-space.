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

Payload index on `case_ref` (required for filtering)
----------------------------------------------------
Qdrant will not execute a payload filter on a field unless a payload
index exists for that field -- filtering without an index raises
"Index required but not found for <field>" (400 Bad Request). Since
every search this module performs filters on case_ref (see
Confidentiality boundary above), a payload index for case_ref must
exist before search_similar() is ever called.

_ensure_payload_index() creates that index automatically, once, right
after the collection itself is confirmed to exist (see
_ensure_collection() below) -- so no manual Qdrant Console step is
needed, on a fresh collection or an existing one created before this
fix. It is idempotent by construction:
  - It first asks Qdrant for the collection's current payload schema
    and does nothing if an index for "case_ref" is already listed
    there.
  - If it isn't listed, it creates a KEYWORD index for "case_ref".
    Qdrant's create_payload_index call is itself safe to call more
    than once for the same field (it does not duplicate or error on a
    field that already has an index), so even the rare race where two
    app instances start at the same moment is harmless.
This never changes what gets filtered or how -- it only makes the
existing case_ref filter (which was always part of the design) actually
executable.

Graceful degradation
------------------------
If QDRANT_URL isn't configured, or Voyage embeddings aren't available
(see services/embedding_service.py), every function here is a no-op /
returns an empty result rather than raising -- so a practitioner who
hasn't set up the semantic layer yet still gets the exact same
recency-based Reflection Context behavior the app has always had.

Development logging (temporary, Hybrid RAG hardening pass)
------------------------------------------------------------
Every indexing and search operation prints a short, prefixed "[RAG]"
trace, via the shared services.rag_logging.rag_log() helper (see that
module for why logging was centralized there -- in short: stdout
buffering on Streamlit Cloud could previously swallow plain print()
calls; rag_log() writes through both a properly configured
logging.Logger AND a flushed print() so tracing is reliable). This is
intentionally verbose and intentionally temporary -- it exists so the
Hybrid RAG pipeline can be verified end-to-end without needing a
debugger attached to a live Streamlit session. Nothing here changes
retrieval behavior, ranking, or what a practitioner sees; it only adds
visibility into what already happens. Failures are logged with their
exception and full stack trace rather than silently swallowed, while
still never raising upward (indexing/search must never block a
practitioner's submission or the Reflection Space page -- see the
graceful-degradation note above).
"""

import traceback
from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels

from config import QDRANT_URL, QDRANT_API_KEY, QDRANT_COLLECTION_NAME, EMBEDDING_DIMENSIONS, EMBEDDING_MODEL
from services.anonymizer import anonymize
from services.embedding_service import embed_document, embed_query, is_available as embeddings_available
from services.rag_logging import rag_log

_client = None
_collection_ready = False

# The one payload field every search filters on (see module docstring,
# "Confidentiality boundary"). Kept as a constant so
# _ensure_payload_index() and any future caller stay in sync with
# search_similar()'s filter field by construction, not by convention.
CASE_REF_FIELD = "case_ref"


def _log(msg):
    """Thin wrapper kept for call-site compatibility -- delegates to the
    shared, properly configured logger in services.rag_logging. See
    that module's docstring for why logging was centralized there."""
    rag_log(f"[RAG] {msg}")


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


def _ensure_payload_index(client):
    """
    Idempotently make sure a payload index exists for CASE_REF_FIELD
    ("case_ref"), so filtering by it (search_similar()'s query_filter,
    always scoped to one case) never fails with Qdrant's "Index
    required but not found" error.

    Idempotent in two layers:
      1. It first reads back the collection's current payload schema
         and does nothing if an index for CASE_REF_FIELD is already
         present -- the common case on every app start after the first.
      2. Even if that check is skipped or races with another process,
         Qdrant's create_payload_index() itself does not error or
         duplicate when called again for a field that already has an
         index of the same type -- so calling this twice is always
         safe.

    Never raises upward: an indexing problem here must not block the
    app from starting or a page from loading (same graceful-degradation
    contract as every other function in this module). If it fails,
    search_similar() will surface the underlying Qdrant error the next
    time it actually tries to filter -- which is exactly the failure
    this function exists to prevent, so it's logged loudly here.
    """
    try:
        collection_info = client.get_collection(collection_name=QDRANT_COLLECTION_NAME)
        payload_schema = getattr(collection_info, "payload_schema", None) or {}
        if CASE_REF_FIELD in payload_schema:
            _log(f"_ensure_payload_index: index for {CASE_REF_FIELD!r} already exists, skipping")
            return
    except Exception as e:
        # Couldn't read the schema back (e.g. brand-new collection with
        # an eventually-consistent schema listing) -- fall through and
        # attempt to create the index anyway; create_payload_index is
        # itself safe to call redundantly (see docstring above).
        _log(f"_ensure_payload_index: could not read existing payload schema ({e!r}), attempting create anyway")

    try:
        client.create_payload_index(
            collection_name=QDRANT_COLLECTION_NAME,
            field_name=CASE_REF_FIELD,
            field_schema=qmodels.PayloadSchemaType.KEYWORD,
        )
        _log(f"_ensure_payload_index: created/confirmed KEYWORD payload index for {CASE_REF_FIELD!r}")
    except Exception as e:
        _log(
            f"_ensure_payload_index FAILED: could not create payload index for "
            f"{CASE_REF_FIELD!r} exception={e!r}\n{traceback.format_exc()}"
        )


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
    # Runs every time the collection is (re)confirmed -- including on
    # collections that already existed before this fix shipped, which
    # is exactly the case that was missing an index and triggering the
    # "Index required but not found for case_ref" error. Cheap and
    # idempotent (see _ensure_payload_index docstring), so doing this
    # unconditionally here (rather than only right after
    # create_collection) is what makes existing deployments self-heal
    # on next startup with no manual Qdrant Console step.
    _ensure_payload_index(client)
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

    No-ops silently in terms of BEHAVIOR (logs nothing sensitive, raises
    nothing) if Qdrant or embeddings aren't configured, or if embedding
    fails -- indexing is best-effort and must never block a
    practitioner's submission. It DOES, however, log every attempt and
    its outcome (see module docstring) so this is fully observable
    during development/testing.

    `draft_id` is used directly as the Qdrant point id, so re-submitting
    (e.g. re-running a backfill) simply overwrites the same point rather
    than creating duplicates.
    """
    _log(
        f"upsert_document start: draft_id={draft_id} case_ref={case_ref!r} "
        f"doc_type={doc_type!r} embedding_model={EMBEDDING_MODEL} "
        f"embedding_dimensions={EMBEDDING_DIMENSIONS} collection={QDRANT_COLLECTION_NAME}"
    )

    client = _get_client()
    if client is None:
        _log(f"upsert_document SKIPPED: draft_id={draft_id} reason='Qdrant not configured (QDRANT_URL missing)'")
        return False
    if not case_ref or not (case_ref or "").strip():
        _log(f"upsert_document SKIPPED: draft_id={draft_id} reason='missing case_ref'")
        return False

    safe_text = anonymize(content or "")
    vector = embed_document(safe_text)
    if vector is None:
        _log(f"upsert_document FAILED: draft_id={draft_id} case_ref={case_ref!r} reason='embedding returned None (Voyage not configured or call failed)'")
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
        _log(f"upsert_document SUCCESS: draft_id={draft_id} case_ref={case_ref!r} doc_type={doc_type!r} collection={QDRANT_COLLECTION_NAME}")
        return True
    except Exception as e:
        _log(
            f"upsert_document FAILED: draft_id={draft_id} case_ref={case_ref!r} "
            f"exception={e!r}\n{traceback.format_exc()}"
        )
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
        _log(f"delete_document SKIPPED: draft_id={draft_id} reason='Qdrant not configured'")
        return
    try:
        client.delete(
            collection_name=QDRANT_COLLECTION_NAME,
            points_selector=qmodels.PointIdsList(points=[draft_id]),
        )
        _log(f"delete_document SUCCESS: draft_id={draft_id} collection={QDRANT_COLLECTION_NAME}")
    except Exception as e:
        _log(f"delete_document FAILED: draft_id={draft_id} exception={e!r}\n{traceback.format_exc()}")


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
        _log("search_similar SKIPPED: reason='missing case_ref'")
        return []

    client = _get_client()
    if client is None:
        _log(f"search_similar SKIPPED: case_ref={case_ref!r} reason='Qdrant not configured'")
        return []

    safe_query = anonymize(query_text or "")
    vector = embed_query(safe_query)
    query_embedding_created = vector is not None
    _log(f"search_similar: case_ref={case_ref!r} collection={QDRANT_COLLECTION_NAME} query_embedding_created={query_embedding_created}")

    if vector is None:
        _log(f"search_similar FAILED: case_ref={case_ref!r} reason='query embedding returned None'")
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
    _log(
        f"search_similar payload_filter: case_ref=={case_ref!r} "
        f"exclude_document_ids={sorted(exclude_ids) if exclude_ids else []} limit={limit}"
    )

    try:
        _ensure_collection(client)
        _log("Starting semantic search...")
        results = client.search(
            collection_name=QDRANT_COLLECTION_NAME,
            query_vector=vector,
            query_filter=query_filter,
            limit=limit,
        )
        out = [{"id": point.id, "score": point.score} for point in results]
        _log(f"search_similar RESULT: case_ref={case_ref!r} retrieved={out}")
        return out
    except Exception as e:
        _log(f"search_similar FAILED: case_ref={case_ref!r} exception={e!r}\n{traceback.format_exc()}")
        return []


# --- RAG Diagnostics (temporary, development-only) --------------------
#
# Read-only introspection used by the "RAG Diagnostics" section of
# pages/zz_admin.py. Never called from any practitioner-facing page.
# Every field is best-effort: if Qdrant isn't configured or a call
# fails, get_diagnostics() reports that clearly rather than raising, so
# the admin page can always render something useful.

def get_diagnostics():
    """
    Returns a dict describing the current state of the semantic layer,
    for the temporary RAG Diagnostics admin panel:

        {
            "configured": bool,           # QDRANT_URL set at all
            "connected": bool,             # a live call to Qdrant succeeded
            "collection_name": str,
            "embedding_model": str,
            "embedding_dimensions": int,
            "points_count": int | None,
            "case_ref_index_present": bool | None,
            "latest_document_id": int | None,
            "latest_case_ref": str | None,
            "latest_doc_type": str | None,
            "latest_completed_at": str | None,
            "error": str | None,
        }
    """
    diagnostics = {
        "configured": bool(QDRANT_URL),
        "connected": False,
        "collection_name": QDRANT_COLLECTION_NAME,
        "embedding_model": EMBEDDING_MODEL,
        "embedding_dimensions": EMBEDDING_DIMENSIONS,
        "points_count": None,
        "case_ref_index_present": None,
        "latest_document_id": None,
        "latest_case_ref": None,
        "latest_doc_type": None,
        "latest_completed_at": None,
        "error": None,
    }

    if not QDRANT_URL:
        diagnostics["error"] = "QDRANT_URL is not configured."
        return diagnostics

    client = _get_client()
    if client is None:
        diagnostics["error"] = "Could not create a Qdrant client."
        return diagnostics

    try:
        _ensure_collection(client)

        count_result = client.count(collection_name=QDRANT_COLLECTION_NAME, exact=True)
        diagnostics["points_count"] = count_result.count
        diagnostics["connected"] = True

        try:
            collection_info = client.get_collection(collection_name=QDRANT_COLLECTION_NAME)
            payload_schema = getattr(collection_info, "payload_schema", None) or {}
            diagnostics["case_ref_index_present"] = CASE_REF_FIELD in payload_schema
        except Exception:
            diagnostics["case_ref_index_present"] = None

        # Qdrant has no built-in "most recently inserted" query, so we
        # scroll a bounded batch of points and pick the max by
        # payload.completed_at. This is a development diagnostic only
        # (bounded, not used for retrieval), so a capped scroll is fine
        # even for larger collections.
        latest = None
        next_offset = None
        scanned = 0
        SCROLL_CAP = 2000
        while scanned < SCROLL_CAP:
            points, next_offset = client.scroll(
                collection_name=QDRANT_COLLECTION_NAME,
                limit=200,
                offset=next_offset,
                with_payload=True,
                with_vectors=False,
            )
            if not points:
                break
            for p in points:
                payload = p.payload or {}
                completed_at = payload.get("completed_at") or ""
                if latest is None or completed_at > (latest.get("completed_at") or ""):
                    latest = {
                        "document_id": payload.get("document_id", p.id),
                        "case_ref": payload.get("case_ref"),
                        "document_type": payload.get("document_type"),
                        "completed_at": completed_at,
                    }
            scanned += len(points)
            if next_offset is None:
                break

        if latest:
            diagnostics["latest_document_id"] = latest["document_id"]
            diagnostics["latest_case_ref"] = latest["case_ref"]
            diagnostics["latest_doc_type"] = latest["document_type"]
            diagnostics["latest_completed_at"] = latest["completed_at"]

        _log(f"get_diagnostics: {diagnostics}")
        return diagnostics
    except Exception as e:
        diagnostics["error"] = f"{e!r}"
        _log(f"get_diagnostics FAILED: exception={e!r}\n{traceback.format_exc()}")
        return diagnostics