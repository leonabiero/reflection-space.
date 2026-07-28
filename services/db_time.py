"""
Shared Database Time & Logging Helpers
=========================================

Engineering-quality pass (see accompanying handoff notes, "Change 5" --
Centralize duplicated timestamp helpers).

Previously, every storage module in services/ (draft_storage.py,
reflection_log.py, audit_log.py, feedback_store.py, exploration_log.py,
presence.py) each defined its OWN private copy of three identical
helper functions:

    _now_utc()  -- a timezone-aware UTC "now", used when writing to any
                   TIMESTAMPTZ column, replacing the old
                   datetime.now().isoformat() pattern.
    _iso(value) -- normalizes a value read back from a TIMESTAMPTZ
                   column into the same ISO-8601 STRING shape every
                   caller outside services/ has always received (every
                   page in this app does string slicing on these
                   values, e.g. completed_at[:10]).
    _iso_row(row, date_indexes) -- applies _iso() to specific positions
                   in a fetched row tuple.

This module is the single, shared source of truth for all three. It
changes NOTHING about behavior -- every module that now imports from
here (now_utc/iso/iso_row) previously had byte-for-byte identical
private implementations. This purely removes duplication so a future
change to this logic (if ever needed) only has to happen once.

Logging
---------
get_logger(name) is the shared, stdout-safe logger factory used by
every storage module for Change 7 ("Logging instead of silent
failures"). This follows the exact same reasoning already documented in
services/rag_logging.py: on a hosted container process (e.g. Streamlit
Cloud), stdout is frequently NOT attached to a real terminal, so CPython
switches to full block-buffering and plain logging.basicConfig() output
can sit unflushed indefinitely. get_logger() binds a StreamHandler
directly to sys.stdout and disables propagation, so every "rdi.db.*"
logger is reliably visible in the hosting platform's log viewer,
independent of whatever the root logger happens to be configured at.

This module intentionally does NOT touch services/rag_logging.py or its
"[RAG] ..." trace lines -- that module remains the dedicated, verbose,
temporary Hybrid RAG development trace. This module is the general-
purpose, permanent operational logger for ordinary storage-layer
events (connection errors, failed writes, degraded/best-effort paths).
"""

import logging
import sys
from datetime import datetime, timezone

_configured_loggers = set()


def now_utc():
    """Single source of truth for 'now' as a timezone-aware UTC
    datetime. Pass this directly into any TIMESTAMPTZ column write --
    psycopg2 stores it natively with no ambiguity about which timezone
    it represents."""
    return datetime.now(timezone.utc)


def iso(value):
    """Normalize a value read back from a TIMESTAMPTZ column into the
    same ISO-8601 string shape every caller outside services/ has
    always received. A None passes through as None; a plain string
    (e.g. from a not-yet-migrated column, or an already-formatted
    value) passes through unchanged; anything else (a real datetime
    object) is converted via .isoformat()."""
    if value is None:
        return None
    if isinstance(value, str):
        return value
    return value.isoformat()


def iso_row(row, date_indexes):
    """Apply iso() to specific positions in a fetched row tuple,
    leaving every other value untouched. Rows from psycopg2 are plain
    tuples (immutable), so this returns a new tuple."""
    row = list(row)
    for i in date_indexes:
        row[i] = iso(row[i])
    return tuple(row)


def get_logger(name):
    """
    Return a logger configured to reliably write to stdout on hosted
    platforms (see module docstring). Idempotent per logger name --
    calling this more than once for the same `name` never stacks
    duplicate handlers.

    Usage (in any services/*.py module):

        from services.db_time import get_logger
        logger = get_logger(__name__)
        ...
        logger.warning("upsert_document failed: %s", exc)

    Never raises. Logging must never be the reason a page breaks.
    """
    logger = logging.getLogger(name)

    if name not in _configured_loggers:
        logger.setLevel(logging.INFO)
        # Never hand records up to the root logger -- that logger may
        # be configured at a different level or with different
        # handlers by the hosting platform, which could otherwise
        # silently drop or duplicate these lines.
        logger.propagate = False

        for existing_handler in list(logger.handlers):
            logger.removeHandler(existing_handler)

        handler = logging.StreamHandler(stream=sys.stdout)
        handler.setLevel(logging.INFO)
        handler.setFormatter(
            logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
        )
        logger.addHandler(handler)

        _configured_loggers.add(name)

    return logger