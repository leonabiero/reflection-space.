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
every PRACTITIONER-FACING search MUST filter on it. search_similar()
below takes case_ref as a required, non-optional argument specifically
so there is no way to call it without a case scope -- there is no
"search everything" method built on top of search_similar() at all.
This is the mechanism, not just a convention: even a semantic
near-duplicate from a different client's case can never be returned to
a practitioner reflecting on a case, because Qdrant discards it at the
filter stage before scoring is even considered for ranking.

search_similar() ALSO filters (must_not) on `document_id`, to exclude
today's own document(s) from its own historical-context suggestions
(see the `exclude_ids` argument).

ONE DELIBERATE, CASE-UNSCOPED EXCEPTION -- search_global()
------------------------------------------------------------
search_global() (added alongside the System Administration page's
Retrieval Test "global mode") is the single exception to the rule
above. It runs the exact same semantic search but WITHOUT a case_ref
filter, on purpose, so organisation-wide retrieval is possible when
that is genuinely what's needed -- validating the RAG system as a
whole (System Administration's Retrieval Test) or answering an
organisational question that spans every case (the Knowledge
Assistant, see services/knowledge_assistant.py).

This function must NEVER be called from any practitioner-facing code
path -- not rdi/context_engine.py, not rdi/retrieval_service.py's
retrieve_historical_context() (used by the real Reflection Context
screen), not services/reflection_service.py. Those must keep using
search_similar(), which remains unchanged and still hard-scoped to one
case_ref. search_global() is only ever called from
rdi.retrieval_service.retrieve_global_context(), which in turn is
intentionally called from two authorised, management-tier entry
points: pages/system_administration.py's Retrieval Test panel (System
Administrator role only) and services/knowledge_assistant.py's ask()
(Supervisor / Programme Manager / System Administrator, via the
Learning page's Knowledge Assistant tab). Both are gated to
management/administrative roles -- this is never reachable from any
Practitioner-facing page or work mode.

Payload indexes (required for filtering)
-----------------------------------------
Qdrant will not execute a payload filter on a field unless a payload
index exists for that field -- filtering without an index raises
"Index required but not found for <field>" (400 Bad Request). Since
search_similar() filters on BOTH case_ref (must) and document_id
(must_not), payload indexes for BOTH fields must exist before
search_similar() is ever called:

    - "case_ref"     -> KEYWORD index
    - "document_id"  -> INTEGER index

search_global() only ever filters on document_id (must_not, for
exclude_ids), so it only depends on the document_id index -- but both
indexes are always ensured together by _ensure_payload_indexes(), so
this is never a practical concern.

REQUIRED_PAYLOAD_INDEXES (below) is the single source of truth for
which fields need an index and what schema type each needs.
_ensure_payload_indexes() creates whichever of these are missing,
automatically, once, right after the collection itself is confirmed to
exist (see _ensure_collection() below) -- so no manual Qdrant Console
step is ever needed, on a fresh collection or an existing one created
before this fix. It is idempotent by construction:
  - It first asks Qdrant for the collection's current payload schema
    and does nothing for any field whose index is already listed
    there (logs "[RAG] Payload index exists: <field>").
  - For any field not yet listed, it creates an index of the
    configured type. Qdrant's create_payload_index call is itself safe
    to call more than once for the same field (it does not duplicate
    or error on a field that already has an index of the same type),
    so even the rare race where two app instances start at the same
    moment is harmless.
This never changes what gets filtered or how -- it only makes the
existing case_ref / document_id filters (which were always part of the
design) actually executable.

Graceful degradation
------------------------
If QDRANT_URL isn't configured, or Gemini embeddings aren't available
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

# The payload field every practitioner-facing search filters on for
# confidentiality (see module docstring, "Confidentiality boundary").
# Kept as a constant so search_similar() and anything referencing it by
# name stay in sync.
CASE_REF_FIELD = "case_ref"

# The payload field both search_similar() and search_global() use to
# exclude today's own document(s) from their own suggestions.
DOCUMENT_ID_FIELD = "document_id"

# Single source of truth for every payload field that needs an index
# before search_similar() / search_global() can filter on it, and what
# schema type each one needs. Add a new entry here (and nowhere else)
# if a future filter field is introduced -- _ensure_payload_indexes()
# below picks it up automatically.
REQUIRED_PAYLOAD_INDEXES = {
    CASE_REF_FIELD: qmodels.PayloadSchemaType.KEYWORD,
    DOCUMENT_ID_FIELD: qmodels.PayloadSchemaType.INTEGER,
}


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


def _ensure_payload_indexes(client):
    """
    Idempotently make sure a payload index exists for EVERY field in
    REQUIRED_PAYLOAD_INDEXES (currently "case_ref" -> KEYWORD and
    "document_id" -> INTEGER), so filtering by any of them (
    search_similar()'s query_filter, which filters on case_ref and
    excludes on document_id; search_global()'s query_filter, which
    excludes on document_id only) never fails with Qdrant's "Index
    required but not found" error.

    Idempotent in two layers, per field:
      1. It first reads back the collection's current payload schema
         and does nothing for a field whose index is already present
         -- the common case on every app start after the first. Logs
         "[RAG] Payload index exists: <field>" in that case.
      2. Even if that check is skipped or races with another process,
         Qdrant's create_payload_index() itself does not error or
         duplicate when called again for a field that already has an
         index of the same type -- so calling this twice is always
         safe.

    Never raises upward: an indexing problem here must not block the
    app from starting or a page from loading (same graceful-degradation
    contract as every other function in this module). If it fails,
    search_similar() / search_global() will surface the underlying
    Qdrant error the next time they actually try to filter -- which is
    exactly the failure this function exists to prevent, so it's
    logged loudly here.
    """
    try:
        collection_info = client.get_collection(collection_name=QDRANT_COLLECTION_NAME)
        payload_schema = getattr(collection_info, "payload_schema", None) or {}
    except Exception as e:
        # Couldn't read the schema back (e.g. brand-new collection with
        # an eventually-consistent schema listing) -- treat as "nothing
        # confirmed yet" and attempt to create every required index
        # anyway; create_payload_index is itself safe to call
        # redundantly (see docstring above).
        _log(f"_ensure_payload_indexes: could not read existing payload schema ({e!r}), attempting create for all required fields anyway")
        payload_schema = {}

    for field_name, field_schema in REQUIRED_PAYLOAD_INDEXES.items():
        if field_name in payload_schema:
            _log(f"Payload index exists: {field_name}")
            continue

        try:
            client.create_payload_index(
                collection_name=QDRANT_COLLECTION_NAME,
                field_name=field_name,
                field_schema=field_schema,
            )
            _log(f"_ensure_payload_indexes: created/confirmed {field_schema} payload index for {field_name!r}")
            _log(f"Payload index exists: {field_name}")
        except Exception as e:
            _log(
                f"_ensure_payload_indexes FAILED: could not create payload index for "
                f"{field_name!r} exception={e!r}\n{traceback.format_exc()}"
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
    # "Index required but not found for case_ref" / "...document_id"
    # errors. Cheap and idempotent (see _ensure_payload_indexes
    # docstring), so doing this unconditionally here (rather than only
    # right after create_collection) is what makes existing deployments
    # self-heal on next startup with no manual Qdrant Console step.
    _ensure_payload_indexes(client)
    _collection_ready = True


def upsert_document(draft_id, case_ref, doc_type, content, language="",
                     created_at="", completed_at="", created_by_role="", was_edited=False):
    """
    Embed and index one COMPLETED document. Call this right after a
    document is finalized (services.draft_storage.finalize_draft), and
    also from the admin backfill for documents completed before this
    feature existed.

    The content sent to Gemini embeddings is anonymized first -- the same
    anonymize() function and the same boundary already used before any
    text reaches Claude (see services/anonymizer.py, reflection_service.py).
    The raw/original content is never sent to Qdrant or Gemini embeddings.

    No-ops silently in terms of BEHAVIOR (raises nothing -- indexing is
    best-effort and must never block a practitioner's submission) if
    Qdrant or embeddings aren't configured, or if embedding fails. It
    DOES, however, log every attempt and its outcome (see module
    docstring) so this is fully observable during development/testing,
    and it now also reports the outcome back to the caller (see
    Returns below) so callers -- services/draft_storage.py's
    finalize_draft() in particular -- can track and surface failures
    instead of assuming success. See that function's docstring for the
    full story on why this changed.

    `draft_id` is used directly as the Qdrant point id, so re-submitting
    (e.g. re-running a backfill) simply overwrites the same point rather
    than creating duplicates.

    Returns a (success, reason) tuple:
      - (True, "ok") on a successful upsert.
      - (False, "not_configured") if Qdrant or Gemini embeddings aren't set up
        -- an expected, deliberate skip, not a failure a caller should
        treat as actionable or show to an administrator.
      - (False, "missing_case_ref") if `case_ref` is blank -- indicates
        a data problem with the draft itself, distinct from a
        transient indexing failure.
      - (False, "embedding_failed") if Gemini embeddings didn't return a vector
        (rate limit, timeout, outage, network error, etc).
      - (False, "qdrant_error: <exception repr>") if the Qdrant upsert
        call itself raised.
    """
    _log(
        f"upsert_document start: draft_id={draft_id} case_ref={case_ref!r} "
        f"doc_type={doc_type!r} embedding_model={EMBEDDING_MODEL} "
        f"embedding_dimensions={EMBEDDING_DIMENSIONS} collection={QDRANT_COLLECTION_NAME}"
    )

    client = _get_client()
    if client is None:
        _log(f"upsert_document SKIPPED: draft_id={draft_id} reason='Qdrant not configured (QDRANT_URL missing)'")
        return False, "not_configured"
    if not case_ref or not (case_ref or "").strip():
        _log(f"upsert_document SKIPPED: draft_id={draft_id} reason='missing case_ref'")
        return False, "missing_case_ref"

    safe_text = anonymize(content or "")
    vector = embed_document(safe_text)
    if vector is None:
        _log(f"upsert_document FAILED: draft_id={draft_id} case_ref={case_ref!r} reason='embedding returned None (Gemini not configured or call failed)'")
        return False, "embedding_failed"

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
        return True, "ok"
    except Exception as e:
        _log(
            f"upsert_document FAILED: draft_id={draft_id} case_ref={case_ref!r} "
            f"exception={e!r}\n{traceback.format_exc()}"
        )
        return False, f"qdrant_error: {e!r}"


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
    Semantic search, ALWAYS scoped to one case. This is the ONLY search
    entry point this module exposes for practitioner-facing code --
    case_ref is a required argument, not an optional filter, so there
    is no way to call this without confidentiality scoping. (The one
    exception in this module is search_global(), below, which is
    reserved for authorised, management-tier features -- see the
    module docstring, "ONE DELIBERATE, CASE-UNSCOPED EXCEPTION".)

    Filters used (both require a payload index -- see
    _ensure_payload_indexes()):
      - must:     case_ref == case_ref               (KEYWORD index)
      - must_not: document_id in exclude_ids          (INTEGER index)

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
        qmodels.FieldCondition(key=CASE_REF_FIELD, match=qmodels.MatchValue(value=case_ref))
    ]
    must_not_conditions = []
    if exclude_ids:
        must_not_conditions.append(
            qmodels.FieldCondition(
                key=DOCUMENT_ID_FIELD,
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


def search_global(query_text, exclude_ids=None, limit=5):
    """
    Semantic search across the ENTIRE Qdrant collection -- NO case_ref
    filter is applied. This is the one deliberate exception to this
    module's confidentiality boundary (see module docstring, "ONE
    DELIBERATE, CASE-UNSCOPED EXCEPTION").

    DO NOT call this from any practitioner-facing path. It exists to
    back two authorised, management-tier features via
    rdi.retrieval_service.retrieve_global_context(): the System
    Administration page's Retrieval Test "global mode" (System
    Administrator role only), so an administrator can validate the RAG
    system's retrieval quality across the whole knowledge base rather
    than one case at a time; and the Knowledge Assistant on the
    Learning page (services/knowledge_assistant.py), which intentionally
    answers organisation-wide questions for Supervisors and Programme
    Managers by searching across every case, not just one.

    Filters used (requires the document_id payload index -- see
    _ensure_payload_indexes()):
      - must_not: document_id in exclude_ids          (INTEGER index)

    No case_ref filter is applied at all -- results can come from any
    case in the collection.

    Returns a list of {"id": draft_id, "score": float} dicts, most
    similar first, or [] if semantic search isn't available/configured
    or embedding the query failed. Callers are responsible for joining
    these ids back to full document rows in Postgres (including which
    case_ref each one belongs to, since results may span cases).
    """
    client = _get_client()
    if client is None:
        _log("search_global SKIPPED: reason='Qdrant not configured'")
        return []

    safe_query = anonymize(query_text or "")
    vector = embed_query(safe_query)
    query_embedding_created = vector is not None
    _log(f"search_global: collection={QDRANT_COLLECTION_NAME} query_embedding_created={query_embedding_created}")

    if vector is None:
        _log("search_global FAILED: reason='query embedding returned None'")
        return []

    exclude_ids = exclude_ids or set()
    must_not_conditions = []
    if exclude_ids:
        must_not_conditions.append(
            qmodels.FieldCondition(
                key=DOCUMENT_ID_FIELD,
                match=qmodels.MatchAny(any=list(exclude_ids)),
            )
        )
    query_filter = qmodels.Filter(must_not=must_not_conditions) if must_not_conditions else None

    _log(
        f"search_global payload_filter: (no case_ref filter -- global) "
        f"exclude_document_ids={sorted(exclude_ids) if exclude_ids else []} limit={limit}"
    )

    try:
        _ensure_collection(client)
        _log("Starting global semantic search (no case_ref filter)...")
        results = client.search(
            collection_name=QDRANT_COLLECTION_NAME,
            query_vector=vector,
            query_filter=query_filter,
            limit=limit,
        )
        out = [{"id": point.id, "score": point.score} for point in results]
        _log(f"search_global RESULT: retrieved={out}")
        return out
    except Exception as e:
        _log(f"search_global FAILED: exception={e!r}\n{traceback.format_exc()}")
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
            "configured": bool,                  # QDRANT_URL set at all
            "connected": bool,                    # a live call to Qdrant succeeded
            "collection_name": str,
            "embedding_model": str,
            "embedding_dimensions": int,
            "points_count": int | None,
            "case_ref_index_present": bool | None,
            "document_id_index_present": bool | None,
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
        "document_id_index_present": None,
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
            diagnostics["document_id_index_present"] = DOCUMENT_ID_FIELD in payload_schema
            for field_name in REQUIRED_PAYLOAD_INDEXES:
                if field_name in payload_schema:
                    _log(f"Payload index exists: {field_name}")
        except Exception:
            diagnostics["case_ref_index_present"] = None
            diagnostics["document_id_index_present"] = None

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
