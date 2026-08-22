"""
Shared Database Time & Logging Helpers
=========================================

Centralizes timestamp helpers and the stdout-safe operational logger used by
storage/service modules.

Security hardening: log output is treated as an untrusted data sink. Before a
record reaches stdout or the in-memory diagnostic ring buffer, its fully
formatted text is passed through the same privacy anonymizer used at the
external-AI boundary. This is defense in depth for database/SDK exceptions,
tracebacks, and future log statements that accidentally contain case data.
The ring buffer is process-wide, so retaining unsanitized records there would
otherwise create a second sensitive-data store.
"""

import logging
import sys
from collections import deque
from datetime import datetime, timezone

from services.anonymizer import anonymize

_configured_loggers = set()
_LOG_BUFFER_MAXLEN = 200
_log_buffer = deque(maxlen=_LOG_BUFFER_MAXLEN)


class _PrivacyFormatter(logging.Formatter):
    """Format a record and redact likely identifiers before storage/output."""

    def format(self, record):
        raw = super().format(record)
        try:
            return anonymize(raw)
        except Exception:
            # Logging must remain available even if the privacy helper itself
            # has a defect. The safer fallback is to emit a fixed marker rather
            # than the potentially sensitive original record.
            return "[LOG_MESSAGE_REDACTION_FAILED]"


class _RingBufferHandler(logging.Handler):
    """Append only privacy-sanitized formatted log lines to the buffer."""

    def emit(self, record):
        try:
            self.acquire()
            try:
                self.format(record)
                _log_buffer.append(self.format(record))
            finally:
                self.release()
        except Exception:
            pass


def get_recent_log_entries(limit=20):
    """Return up to `limit` recent privacy-sanitized log lines."""
    try:
        entries = list(_log_buffer)
        if limit:
            entries = entries[-limit:]
        return entries
    except Exception:
        return []


def now_utc():
    """Single source of truth for timezone-aware UTC now."""
    return datetime.now(timezone.utc)


def iso(value):
    """Normalize a TIMESTAMPTZ value to the historical ISO string shape."""
    if value is None:
        return None
    if isinstance(value, str):
        return value
    return value.isoformat()


def iso_row(row, date_indexes):
    """Apply iso() to selected positions in a fetched row tuple."""
    row = list(row)
    for i in date_indexes:
        row[i] = iso(row[i])
    return tuple(row)


def get_logger(name):
    """Return a stdout-safe logger whose output is privacy-sanitized.

    Idempotent per logger name. Both the live stdout handler and the
    process-wide diagnostic ring buffer use _PrivacyFormatter, so sensitive
    content cannot reach either sink through this logger factory.
    """
    logger = logging.getLogger(name)

    if name not in _configured_loggers:
        logger.setLevel(logging.INFO)
        logger.propagate = False

        for existing_handler in list(logger.handlers):
            logger.removeHandler(existing_handler)

        privacy_formatter = _PrivacyFormatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
        )

        handler = logging.StreamHandler(stream=sys.stdout)
        handler.setLevel(logging.INFO)
        handler.setFormatter(privacy_formatter)
        logger.addHandler(handler)

        buffer_handler = _RingBufferHandler()
        buffer_handler.setLevel(logging.INFO)
        buffer_handler.setFormatter(privacy_formatter)
        logger.addHandler(buffer_handler)

        _configured_loggers.add(name)

    return logger
