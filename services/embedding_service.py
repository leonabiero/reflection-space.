"""
Embedding Service
=================

Thin wrapper around Google's Gemini Embedding API. This is the single place
in the app that turns text into a vector; callers should not import the
Google GenAI SDK directly.

The service preserves the existing contract used by Qdrant: document text
is embedded with a retrieval-document task, query text with a retrieval-query
task, and provider failures return None rather than breaking document
submission or reflection.

Privacy boundary
----------------
Callers are responsible for passing already-anonymized text. This module
never logs or stores the text being embedded.
"""

from google import genai
from google.genai import types

from config import GEMINI_API_KEY, EMBEDDING_MODEL, EMBEDDING_DIMENSIONS
from services.db_time import get_logger
from services import usage_ledger
from services.cost_pricing import estimate_gemini_embedding_cost
import time

logger = get_logger(__name__)

_client = None


def is_available():
    """True when the Gemini API key is configured."""
    return bool(GEMINI_API_KEY)


def _get_client():
    global _client
    if not GEMINI_API_KEY:
        return None
    if _client is None:
        _client = genai.Client(api_key=GEMINI_API_KEY)
    return _client


def embed_document(text: str):
    """Embed one document for storage/retrieval indexing."""
    return _embed(text, task_type="RETRIEVAL_DOCUMENT", operation="embed_document")


def embed_query(text: str):
    """Embed one search query for retrieval against indexed documents."""
    return _embed(text, task_type="RETRIEVAL_QUERY", operation="embed_query")


def _embed(text: str, task_type: str, operation: str = "embed"):
    if not text or not text.strip():
        return None

    client = _get_client()
    if client is None:
        return None

    _started = time.monotonic()
    try:
        result = client.models.embed_content(
            model=EMBEDDING_MODEL,
            contents=text,
            config=types.EmbedContentConfig(
                task_type=task_type,
                output_dimensionality=EMBEDDING_DIMENSIONS,
            ),
        )
        if not result.embeddings:
            logger.warning(
                "embedding call FAILED: task_type=%r model=%r reason='no embedding returned'",
                task_type, EMBEDDING_MODEL,
            )
            _record_embedding_usage(operation, _started, success=False)
            return None

        vector = result.embeddings[0].values
        if not vector:
            logger.warning(
                "embedding call FAILED: task_type=%r model=%r reason='empty embedding returned'",
                task_type, EMBEDDING_MODEL,
            )
            _record_embedding_usage(operation, _started, success=False)
            return None

        # Service Cost & Usage Monitor: use the ACTUAL token count the
        # Google GenAI SDK reports for this embedding (statistics on the
        # returned ContentEmbedding), never an estimate from text length.
        # billable_character_count (on the response metadata) is recorded
        # too, as an additional, exact usage signal from the provider.
        _record_embedding_usage(operation, _started, success=True, result=result)
        return vector
    except Exception as e:
        # Never let an embedding-provider hiccup block a practitioner's
        # document submission or reflection. The failure is logged without
        # logging the text itself.
        logger.warning(
            "embedding call FAILED: task_type=%r model=%r exception=%r",
            task_type, EMBEDDING_MODEL, e,
        )
        _record_embedding_usage(operation, _started, success=False, error_type=type(e).__name__)
        return None


def _record_embedding_usage(operation, started_at, success=True, result=None, error_type=None):
    """
    Fire-and-forget usage recording for one Gemini embedding call -- see
    services/usage_ledger.py. Never raises, never blocks document
    submission or reflection generation on a slow/unavailable ledger
    write.
    """
    latency_ms = int((time.monotonic() - started_at) * 1000)
    input_tokens = None
    billable_characters = None
    if result is not None:
        try:
            input_tokens = result.embeddings[0].statistics.token_count
        except Exception:
            input_tokens = None
        try:
            billable_characters = result.metadata.billable_character_count
        except Exception:
            billable_characters = None

    if input_tokens is not None:
        cost, model_recognized = estimate_gemini_embedding_cost(EMBEDDING_MODEL, input_tokens=input_tokens)
        cost_is_estimate = not model_recognized
    else:
        # The SDK didn't return a token count for this call -- do not
        # fabricate a cost. Usage (call happened, succeeded/failed) is
        # still recorded; cost is simply left at 0 and flagged as an
        # estimate/unavailable rather than guessed from text length.
        cost, cost_is_estimate = 0.0, True

    usage_ledger.record_usage(
        "gemini", operation,
        input_tokens=input_tokens, units_used=billable_characters,
        estimated_cost_usd=cost, cost_is_estimate=cost_is_estimate,
        success=success, latency_ms=latency_ms, model=EMBEDDING_MODEL,
        metadata={"error_type": error_type} if error_type else None,
    )
