"""
RAG Logging
=============

Shared, centralized logging helper for the Hybrid RAG development trace.

Security note: RAG logs are operational diagnostics, not a data store. Case
references can themselves identify a client/case, so they are redacted before
anything reaches stdout or a logging handler. Retrieval results log only
opaque internal document ids, document types and scores.
"""

import logging
import re
import sys

_logger = None

# All current RAG call sites use `case_ref=<repr>` in their trace messages.
# Redacting the value centrally is defense in depth: a future call site can
# accidentally include a case reference without turning stdout into another
# sensitive-data store.
_CASE_REF_LOG_RE = re.compile(
    r"\bcase_ref\s*=\s*(?:'[^']*'|\"[^\"]*\"|[^\s,;|]+)",
    re.IGNORECASE,
)

# Also cover common prose forms used by future/legacy messages.
_CASE_PROSE_RE = re.compile(
    r"\bcase\s+(?:reference|ref|id|number)\s*[:=]\s*[^\s,;|]+",
    re.IGNORECASE,
)


def _sanitize_message(msg):
    try:
        text = str(msg)
    except Exception:
        return "[UNPRINTABLE_LOG_MESSAGE]"
    text = _CASE_REF_LOG_RE.sub("case_ref=[REDACTED]", text)
    text = _CASE_PROSE_RE.sub("case reference=[REDACTED]", text)
    return text


def get_rag_logger():
    """Return the shared "rag" logger, creating it on first use."""
    global _logger
    if _logger is not None:
        return _logger

    logger = logging.getLogger("rag")
    logger.setLevel(logging.INFO)
    logger.propagate = False

    for existing_handler in list(logger.handlers):
        logger.removeHandler(existing_handler)

    handler = logging.StreamHandler(stream=sys.stdout)
    handler.setLevel(logging.INFO)
    handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(handler)

    _logger = logger
    return logger


def rag_log(msg):
    """Log an operational RAG message after central case-reference redaction.

    Never raises -- a logging failure must never break the page it serves.
    """
    safe_msg = _sanitize_message(msg)
    try:
        get_rag_logger().info(safe_msg)
        return
    except Exception:
        pass
    try:
        print(safe_msg, flush=True)
    except Exception:
        pass


if _logger is None:
    rag_log("[RAG] Logging initialized successfully")
