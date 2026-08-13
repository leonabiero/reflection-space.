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
    return _embed(text, task_type="RETRIEVAL_DOCUMENT")


def embed_query(text: str):
    """Embed one search query for retrieval against indexed documents."""
    return _embed(text, task_type="RETRIEVAL_QUERY")


def _embed(text: str, task_type: str):
    if not text or not text.strip():
        return None

    client = _get_client()
    if client is None:
        return None

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
            return None

        vector = result.embeddings[0].values
        if not vector:
            logger.warning(
                "embedding call FAILED: task_type=%r model=%r reason='empty embedding returned'",
                task_type, EMBEDDING_MODEL,
            )
            return None
        return vector
    except Exception as e:
        # Never let an embedding-provider hiccup block a practitioner's
        # document submission or reflection. The failure is logged without
        # logging the text itself.
        logger.warning(
            "embedding call FAILED: task_type=%r model=%r exception=%r",
            task_type, EMBEDDING_MODEL, e,
        )
        return None
