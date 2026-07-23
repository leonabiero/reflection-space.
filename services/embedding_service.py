"""
Embedding Service
===================

Thin wrapper around Voyage AI's embedding endpoint -- the single place in
the app that turns text into a vector. Nothing outside this module
should import voyageai directly.

Why Voyage AI: Anthropic does not run its own embedding endpoint, and
Voyage AI is Anthropic's recommended embedding partner (used e.g. by
Claude Code's own retrieval features). Using a separate small, cheap
model for embeddings -- rather than asking Claude itself to embed -- is
both the standard approach and far cheaper (see cost note below).

Same anonymization boundary as reflection_service.py
-------------------------------------------------------
Anonymization already happens once per document, in
rdi.orchestrator.run_reflection() (via services.anonymizer.anonymize),
and the ANONYMIZED text is what gets stored as ReflectionSession.safe_text.
For embeddings, this module receives whatever text the caller passes in
and does NOT re-decide anonymization itself -- callers (draft_storage,
retrieval_service) are responsible for passing already-anonymized text,
exactly like every other call site that talks to an external AI API in
this codebase. See services/qdrant_service.py, which anonymizes before
calling embed_text().

Graceful degradation
----------------------
If VOYAGE_API_KEY is not configured, every function here returns None
instead of raising. Callers (qdrant_service, retrieval_service) treat
None as "semantic retrieval unavailable right now" and fall back to the
recency-based behavior the app already had, rather than crashing the
Reflection Space page.

Cost note (pilot volume, 70-100 reflections/month)
-----------------------------------------------------
voyage-4-lite is priced at $0.02 per 1M tokens, with a 200-million-token
free allocation per Voyage account. A typical case note/report runs
roughly 300-800 tokens. Each completed document is embedded exactly
once (at submission), and each reflection run embeds the current
document's text once more as the semantic query -- so ~2 embedding
calls per reflection, worst case ~1,600 tokens total.

At 100 reflections/month that is roughly 160,000 tokens/month, which is
entirely inside the 200M free allocation -- i.e. **$0.00/month at this
pilot's volume**, likely for its entire lifetime unless volume grows by
several orders of magnitude. This is separate from, and does not change,
Claude API (Anthropic) usage/cost in any way.
"""

import voyageai
from config import VOYAGE_API_KEY, EMBEDDING_MODEL, EMBEDDING_DIMENSIONS

_client = None


def is_available():
    """True if a Voyage API key is configured. Callers should check this
    (or just handle a None return from embed_text/embed_query) before
    relying on semantic retrieval being active."""
    return bool(VOYAGE_API_KEY)


def _get_client():
    global _client
    if not VOYAGE_API_KEY:
        return None
    if _client is None:
        _client = voyageai.Client(api_key=VOYAGE_API_KEY)
    return _client


def embed_document(text: str):
    """
    Embed one document for STORAGE (input_type="document"). Voyage's
    models are trained asymmetrically -- documents and queries use
    slightly different instructions internally -- so it matters which
    of embed_document / embed_query you call.

    Returns a list[float] of length EMBEDDING_DIMENSIONS, or None if
    embeddings aren't configured or the call fails for any reason
    (network, quota, etc.) -- callers must treat None as "skip
    semantic indexing this time", never raise it upward and block the
    practitioner's document submission.
    """
    return _embed(text, input_type="document")


def embed_query(text: str):
    """Embed one piece of text as a SEARCH QUERY (input_type="query").
    Used when generating the semantic-search vector for the current
    document at the start of a reflection. Same failure behavior as
    embed_document()."""
    return _embed(text, input_type="query")


def _embed(text: str, input_type: str):
    if not text or not text.strip():
        return None

    client = _get_client()
    if client is None:
        return None

    try:
        result = client.embed(
            texts=[text],
            model=EMBEDDING_MODEL,
            input_type=input_type,
            output_dimension=EMBEDDING_DIMENSIONS,
        )
        return result.embeddings[0]
    except Exception:
        # Never let an embedding-provider hiccup break the app -- the
        # practitioner's document is already safe in Postgres regardless.
        return None