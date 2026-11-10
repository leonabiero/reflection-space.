"""
Reflection Context Engine
==========================

First module of the `rdi` package (Reflective Decision Intelligence).

November 2026: the historical-document retrieval that used to live here
(get_historical_context(), backed by rdi/retrieval_service.py and the
Qdrant search service) was removed. It served the old document-based
design; since the reflection-only redesign the app no longer keeps case
documents to retrieve (see REFLECTIONS.md), and nothing called it any
more.

What remains is classify_context_strength(), still used by
rdi/reflection_context.py to describe how much context a reflection had.

Development logging goes through services.rag_logging.rag_log().
"""

from services.rag_logging import rag_log

DEFAULT_HISTORY_LIMIT = 4
STRONG_CONTEXT_THRESHOLD = 3
LIMITED_CONTEXT_THRESHOLD = 1
STRONG_SIMILARITY_THRESHOLD = 0.75


def _log(msg):
    """Thin wrapper kept for call-site compatibility -- delegates to the
    shared, properly configured logger in services.rag_logging."""
    rag_log(f"[RAG] {msg}")


def classify_context_strength(count, avg_score=None):
    """Classify how much historical context is available."""
    if count >= STRONG_CONTEXT_THRESHOLD:
        strength = "strong"
    elif count >= LIMITED_CONTEXT_THRESHOLD:
        if avg_score is not None and avg_score >= STRONG_SIMILARITY_THRESHOLD:
            strength = "strong"
        else:
            strength = "limited"
    else:
        strength = "none"

    _log(f"classify_context_strength: count={count} avg_score={avg_score} -> {strength}")
    return strength
