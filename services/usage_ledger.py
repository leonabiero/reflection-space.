"""
Service Usage Ledger
========================

Service Cost & Usage Monitor (September pilot hardening) -- Phases
2-8 of the accompanying spec.

This module is the single write/read point for the `service_usage`
table (see services/db_schema.py). Every external/billable operation
in the app -- a Claude call, a Gemini embedding, a Qdrant call, an
SMTP send -- is recorded here, and every number the System
Administration "Service Usage & Costs" panel shows is read back out
through the functions below.

Design principles (see the accompanying spec for the full reasoning):

1. MONITORING MUST NEVER BREAK THE APPLICATION.
   record_usage() never raises. A failure to write a usage row --
   database unavailable, pool exhausted, anything -- is logged and
   swallowed. A reflection, an embedding, an email: none of them care
   whether their own usage row made it into the ledger.

2. MONITORING MUST NEVER ADD LATENCY TO A USER-FACING CALL.
   The actual INSERT happens on a small, bounded background thread
   pool (_USAGE_EXECUTOR below), not on the calling thread. The
   Reflection Orchestrator's 8-way parallel companion fan-out (see
   rdi/orchestrator.py) already puts up to CLAUDE_MAX_CONCURRENT_
   REFLECTIONS x 8 companion calls in flight across the app; doing a
   synchronous DB round trip for each one, ON the thread the
   practitioner is waiting on, would add real latency to something
   that has nothing to do with recording usage. Firing it
   asynchronously means the practitioner's response is never delayed
   by so much as one usage-logging write.

3. NO SENSITIVE DATA, EVER.
   record_usage() accepts only operational/billing fields -- token
   counts, a service/operation/model label, timing, success/failure.
   There is no parameter for reflection text, an AI response, a case
   reference, a name, an email address, or a secret. metadata (below)
   is a small, explicitly-allowlisted label dict -- never
   caller-supplied free text.

4. NEVER FABRICATE A NUMBER.
   Every aggregation function below returns exactly what's in the
   ledger. If a cost couldn't be computed (e.g. an unrecognized model,
   or a service with no known provider pricing -- see
   services/cost_pricing.py), the row's cost_is_estimate flag says so,
   and callers (services/cost_dashboard_service.py) surface that
   honestly rather than rounding it into a real-looking number.
"""

import json
import threading
import traceback
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta

from services.db_pool import get_conn as _acquire_pooled_conn
from services.db_time import now_utc, get_logger

logger = get_logger(__name__)

# Recognized service identifiers -- used throughout the dashboard so
# every panel iterates the same fixed list rather than whatever
# happens to already be in the table.
SERVICES = ["anthropic", "gemini", "qdrant", "postgres", "streamlit", "smtp"]

# Small, bounded pool JUST for usage-ledger writes -- deliberately
# separate from any request-serving thread pool, and deliberately
# small: usage writes are cheap, frequent, and must never be allowed
# to queue up unboundedly if the database is slow. A full queue simply
# means the newest write is skipped (logged, not raised) -- see
# _submit() below.
_USAGE_EXECUTOR = ThreadPoolExecutor(max_workers=4, thread_name_prefix="usage-ledger")
_MAX_QUEUE = 200
_queue_lock = threading.Lock()
_queue_depth = 0

# Only these keys may ever appear in the `metadata` column -- a small
# allowlist, not a place for arbitrary caller data. Values are short
# labels (a companion key, a document type, an error class name), never
# document/case content.
_METADATA_ALLOWLIST = {"companion", "doc_type", "error_type", "endpoint", "note"}


def _get_conn():
    return _acquire_pooled_conn()


def _safe_metadata(metadata):
    if not metadata:
        return None
    cleaned = {k: v for k, v in metadata.items() if k in _METADATA_ALLOWLIST and v is not None}
    if not cleaned:
        return None
    try:
        return json.dumps(cleaned)[:500]
    except Exception:
        return None


def _insert_row(service, operation, occurred_at, request_count, input_tokens,
                 output_tokens, cache_read_tokens, cache_creation_tokens,
                 units_used, estimated_cost_usd, cost_is_estimate, success,
                 retry_count, latency_ms, model, metadata_json):
    conn = None
    try:
        conn = _get_conn()
        try:
            with conn.cursor() as c:
                c.execute(
                    """
                    INSERT INTO service_usage (
                        service, operation, occurred_at, request_count,
                        input_tokens, output_tokens, cache_read_tokens,
                        cache_creation_tokens, units_used, estimated_cost_usd,
                        cost_is_estimate, success, retry_count, latency_ms,
                        model, metadata
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        service, operation, occurred_at, request_count,
                        input_tokens, output_tokens, cache_read_tokens,
                        cache_creation_tokens, units_used, estimated_cost_usd,
                        cost_is_estimate, success, retry_count, latency_ms,
                        model, metadata_json,
                    ),
                )
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
    except Exception:
        logger.warning("usage_ledger: failed to record usage row (service=%r operation=%r)",
                        service, operation, exc_info=True)
    finally:
        global _queue_depth
        with _queue_lock:
            _queue_depth = max(0, _queue_depth - 1)


def record_usage(service, operation, *, input_tokens=None, output_tokens=None,
                  cache_read_tokens=None, cache_creation_tokens=None,
                  units_used=None, estimated_cost_usd=None, cost_is_estimate=False,
                  success=True, retry_count=0, latency_ms=None, request_count=1,
                  model=None, metadata=None):
    """
    Record one usage event. Fire-and-forget: returns immediately, the
    actual write happens on a background thread, and ANY failure
    (including "the background queue is full right now") is logged and
    swallowed -- this function is safe to call from any request path,
    including inside the Reflection Orchestrator's parallel fan-out,
    and will never be the reason a reflection, embedding, or email
    fails or is delayed.
    """
    global _queue_depth
    with _queue_lock:
        if _queue_depth >= _MAX_QUEUE:
            logger.warning(
                "usage_ledger: queue full (%d pending) -- dropping one usage "
                "record for service=%r operation=%r. This affects dashboard "
                "accuracy only; no user-facing operation is affected.",
                _queue_depth, service, operation,
            )
            return
        _queue_depth += 1

    occurred_at = now_utc()
    metadata_json = _safe_metadata(metadata)

    try:
        _USAGE_EXECUTOR.submit(
            _insert_row, service, operation, occurred_at, request_count,
            input_tokens, output_tokens, cache_read_tokens, cache_creation_tokens,
            units_used, estimated_cost_usd, cost_is_estimate, success,
            retry_count, latency_ms, model, metadata_json,
        )
    except Exception:
        with _queue_lock:
            _queue_depth = max(0, _queue_depth - 1)
        logger.warning("usage_ledger: could not submit usage record", exc_info=True)


# ---------------------------------------------------------------------
# Aggregation / read side -- used by services/cost_dashboard_service.py
# ---------------------------------------------------------------------

def _fetch_summary(service, since, until=None, operation_prefix=None):
    """
    One aggregated row for `service` (optionally filtered to operations
    starting with `operation_prefix`) between `since` (inclusive) and
    `until` (exclusive, defaults to now).

    Returns a dict -- every numeric field defaults to 0/None if there
    is no matching data at all (never raises, never fabricates).
    """
    until = until or now_utc()
    conn = None
    try:
        conn = _get_conn()
        try:
            with conn.cursor() as c:
                where = ["service = %s", "occurred_at >= %s", "occurred_at < %s"]
                params = [service, since, until]
                if operation_prefix:
                    where.append("operation LIKE %s")
                    params.append(operation_prefix + "%")
                c.execute(
                    f"""
                    SELECT
                        COALESCE(SUM(request_count), 0),
                        COALESCE(SUM(CASE WHEN success THEN request_count ELSE 0 END), 0),
                        COALESCE(SUM(CASE WHEN NOT success THEN request_count ELSE 0 END), 0),
                        COALESCE(SUM(retry_count), 0),
                        COALESCE(SUM(input_tokens), 0),
                        COALESCE(SUM(output_tokens), 0),
                        COALESCE(SUM(cache_read_tokens), 0),
                        COALESCE(SUM(cache_creation_tokens), 0),
                        COALESCE(SUM(units_used), 0),
                        COALESCE(SUM(estimated_cost_usd), 0),
                        COALESCE(BOOL_OR(cost_is_estimate), FALSE)
                    FROM service_usage
                    WHERE {' AND '.join(where)}
                    """,
                    params,
                )
                row = c.fetchone()
        finally:
            conn.close()
    except Exception:
        logger.warning("usage_ledger: _fetch_summary FAILED (service=%r)", service, exc_info=True)
        row = None

    if row is None:
        return {
            "request_count": 0, "success_count": 0, "fail_count": 0,
            "retry_count": 0, "input_tokens": 0, "output_tokens": 0,
            "cache_read_tokens": 0, "cache_creation_tokens": 0,
            "units_used": 0.0, "estimated_cost_usd": 0.0,
            "cost_is_estimate": None, "unavailable": True,
        }

    (request_count, success_count, fail_count, retry_count, input_tokens,
     output_tokens, cache_read_tokens, cache_creation_tokens, units_used,
     estimated_cost_usd, cost_is_estimate) = row

    return {
        "request_count": int(request_count),
        "success_count": int(success_count),
        "fail_count": int(fail_count),
        "retry_count": int(retry_count),
        "input_tokens": int(input_tokens),
        "output_tokens": int(output_tokens),
        "cache_read_tokens": int(cache_read_tokens),
        "cache_creation_tokens": int(cache_creation_tokens),
        "units_used": float(units_used),
        "estimated_cost_usd": float(estimated_cost_usd),
        "cost_is_estimate": bool(cost_is_estimate),
        "unavailable": False,
    }


def get_today_summary(service, operation_prefix=None):
    now = now_utc()
    since = now.replace(hour=0, minute=0, second=0, microsecond=0)
    return _fetch_summary(service, since, operation_prefix=operation_prefix)


def get_month_summary(service, operation_prefix=None):
    now = now_utc()
    since = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    return _fetch_summary(service, since, operation_prefix=operation_prefix)


def get_window_summary(service, window_days, operation_prefix=None):
    since = now_utc() - timedelta(days=window_days)
    return _fetch_summary(service, since, operation_prefix=operation_prefix)


def get_operation_breakdown(service, window_days=30):
    """Per-operation totals within the window -- for the "which
    operation is driving cost" detail view."""
    since = now_utc() - timedelta(days=window_days)
    conn = None
    try:
        conn = _get_conn()
        try:
            with conn.cursor() as c:
                c.execute(
                    """
                    SELECT operation,
                           COALESCE(SUM(request_count), 0),
                           COALESCE(SUM(CASE WHEN NOT success THEN request_count ELSE 0 END), 0),
                           COALESCE(SUM(retry_count), 0),
                           COALESCE(SUM(estimated_cost_usd), 0)
                    FROM service_usage
                    WHERE service = %s AND occurred_at >= %s
                    GROUP BY operation
                    ORDER BY 5 DESC
                    """,
                    (service, since),
                )
                rows = c.fetchall()
        finally:
            conn.close()
    except Exception:
        logger.warning("usage_ledger: get_operation_breakdown FAILED", exc_info=True)
        return []

    return [
        {
            "operation": op,
            "request_count": int(req),
            "fail_count": int(fail),
            "retry_count": int(retry),
            "estimated_cost_usd": float(cost),
        }
        for op, req, fail, retry, cost in rows
    ]


def get_qdrant_operation_counts(window_days=30):
    """Success/failure counts per Qdrant operation -- Qdrant has no
    dollar cost surfaced by its API, so this is usage/health only, per
    the spec's Phase 5."""
    return get_operation_breakdown("qdrant", window_days=window_days)


def get_smtp_summary(window_days=30):
    return get_window_summary("smtp", window_days)
