"""
Reflect step timing (27 November 2026, Batch 1 -- measurement only)
====================================================================

Practitioners said the wait after pressing Reflect feels long. Before
anything is changed, this module measures how long each step really
takes, so the next improvements are chosen on real numbers. See
SERVICE_USAGE_MONITORING.md, "Reflection timing".

What is saved -- and nothing else
---------------------------------
One row per step: the neutral reflection code, a step name from the
fixed list STEPS below, and whole milliseconds (table `reflection_timings`,
services/db_schema.py). Never any case text, anonymised text, quote, AI
answer, name, role or language. record() only accepts a step name and a
number; anything not in STEPS is dropped.

Rows are erased with their reflection (services/reflection_records.py:
_erase_runs, services/findings_store.py:delete_runs_for_drafts), by
"Erase all data" (services/data_reset.py), and automatically after
config.REFLECTION_TIMING_RETENTION_DAYS.

Safety
------
- Switch: config.REFLECTION_TIMING_LOG. When off, a Stopwatch records
  nothing and save() makes no database call.
- Never breaks or slows a reflection: every timing action catches its own
  errors and logs a warning (never shown to the practitioner). Rows are
  kept in memory while the reflection runs and saved in ONE background
  write, through the shared connection pool, after the results are drawn.
- Thread-safe: the eight lens calls run in parallel threads and record
  into the same Stopwatch. Every change to its rows happens under one
  lock; save() takes a copy under the lock and saves only once.

Reading (System Administration -> "Reflection timing") is for the System
Administrator only: every read function checks the role itself and makes
no database call for anyone else (the page checks it too).
"""

import threading
import time
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from datetime import timedelta

from rdi.companions import COMPANION_KEYS
from services.db_pool import get_conn as _acquire_pooled_conn
from services.db_time import now_utc, get_logger

logger = get_logger(__name__)

ADMIN_ROLE = "System Administrator"

# The fixed list of steps, in the order the admin section shows them.
LENS_STEP_PREFIX = "lens_"
LENS_STEPS = tuple(LENS_STEP_PREFIX + key for key in COMPANION_KEYS)
STEPS = (
    "page_start",
    "anonymise",
    "limit_check",
    "request_guard",
    *LENS_STEPS,
    "lenses_total",
    "analysis_report",
    "save_guard_release",
    "save_reflection_log",
    "save_reflection",
    "save_cleanup",
    "save_steps",
    "results_drawn",
    "total",
)
_STEP_SET = frozenset(STEPS)

# One hour: anything longer is clamped (a reflection can never wait this
# long -- see config.CLAUDE_REQUEST_TIMEOUT_SECONDS).
MAX_DURATION_MS = 3_600_000
_CODE_MAX = 64

# AI operations recorded in service_usage (services/reflection_service.py).
LENS_OPERATION = "companion_reflection"
REPORT_OPERATION = "analysis_report"

# Small background writer, same safe pattern as services/usage_ledger.py.
_EXECUTOR = ThreadPoolExecutor(max_workers=1, thread_name_prefix="reflection-timing")
_MAX_QUEUE = 50
_queue_lock = threading.Lock()
_queue_depth = 0


def _get_conn():
    return _acquire_pooled_conn()


def timing_enabled():
    """True when config.REFLECTION_TIMING_LOG is on (read each time, so a
    test or a restart with the setting changed takes effect)."""
    try:
        import config
        return bool(getattr(config, "REFLECTION_TIMING_LOG", False))
    except Exception:
        return False


def _retention_days():
    try:
        import config
        return max(1, int(getattr(config, "REFLECTION_TIMING_RETENTION_DAYS", 30)))
    except Exception:
        return 30


def _clean_ms(value):
    """Whole milliseconds between 0 and MAX_DURATION_MS, or None."""
    try:
        ms = int(round(float(value)))
    except (TypeError, ValueError):
        return None
    return max(0, min(MAX_DURATION_MS, ms))


class Stopwatch:
    """Step times for ONE reflection, kept in memory until save()."""

    def __init__(self, reflection_code, enabled=None):
        self._lock = threading.Lock()
        self._rows = []          # [(step, ms)]
        self._saved = False
        self._code = str(reflection_code or "")[:_CODE_MAX]
        self.enabled = timing_enabled() if enabled is None else bool(enabled)
        # Moments in time (time.monotonic()) the page needs later, e.g.
        # when the Reflect click started being handled.
        self.marks = {}

    @property
    def code(self):
        return self._code

    def record(self, step, ms):
        """Add one step time. Unknown steps and bad numbers are dropped.
        Never raises."""
        try:
            if not self.enabled or step not in _STEP_SET:
                return
            clean = _clean_ms(ms)
            if clean is None:
                return
            with self._lock:
                self._rows.append((step, clean))
        except Exception:
            logger.warning("reflection_timing: could not record a step", exc_info=True)

    def record_since(self, step, started_monotonic):
        """Record the time from `started_monotonic` (time.monotonic()) until now."""
        try:
            self.record(step, (time.monotonic() - float(started_monotonic)) * 1000)
        except Exception:
            logger.warning("reflection_timing: could not record a step", exc_info=True)

    @contextmanager
    def step(self, name):
        """Time the code inside `with stopwatch.step("anonymise"):`. Errors
        from that code are NOT hidden; only timing problems are."""
        started = time.monotonic()
        try:
            yield
        finally:
            self.record_since(name, started)

    def rows(self):
        """A copy of the rows recorded so far: [(step, ms)]."""
        with self._lock:
            return list(self._rows)

    def save(self):
        """Save every row in one background write. Only the first call
        does anything. Returns True if a write was queued. Never raises."""
        global _queue_depth
        try:
            with self._lock:
                if self._saved or not self.enabled:
                    return False
                self._saved = True
                rows = list(self._rows)
            if not rows or not self._code:
                return False
            with _queue_lock:
                if _queue_depth >= _MAX_QUEUE:
                    logger.warning("reflection_timing: queue full -- timings of one reflection skipped")
                    return False
                _queue_depth += 1
            try:
                _EXECUTOR.submit(_write_rows, self._code, rows)
            except Exception:
                with _queue_lock:
                    _queue_depth = max(0, _queue_depth - 1)
                raise
            return True
        except Exception:
            logger.warning("reflection_timing: could not save timings", exc_info=True)
            return False


def _write_rows(reflection_code, rows):
    """Background: insert the rows and delete rows past their retention.
    Never raises."""
    global _queue_depth
    conn = None
    try:
        recorded_at = now_utc()
        conn = _get_conn()
        try:
            with conn.cursor() as c:
                for step, ms in rows:
                    if step not in _STEP_SET:
                        continue
                    c.execute(
                        "INSERT INTO reflection_timings (reflection_code, step, duration_ms, recorded_at) "
                        "VALUES (%s, %s, %s, %s)",
                        (reflection_code, step, int(ms), recorded_at),
                    )
                c.execute(
                    "DELETE FROM reflection_timings WHERE recorded_at < %s",
                    (recorded_at - timedelta(days=_retention_days()),),
                )
            conn.commit()
        except Exception:
            conn.rollback()
            raise
    except Exception:
        logger.warning("reflection_timing: failed to save timings", exc_info=True)
    finally:
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass
        with _queue_lock:
            _queue_depth = max(0, _queue_depth - 1)


# ---------------------------------------------------------------------
# Erasure (inside the caller's transaction)
# ---------------------------------------------------------------------

def erase_timings_for_codes(cursor, codes):
    """Delete the timing rows of these reflection codes, using the
    caller's cursor (same transaction as the reflection's erasure).
    Skipped on a database that does not have the table yet."""
    codes = [str(c) for c in (codes or []) if c]
    if not codes:
        return
    cursor.execute("SELECT to_regclass('reflection_timings')")
    row = cursor.fetchone()
    if row is not None and row[0] is not None:
        cursor.execute("DELETE FROM reflection_timings WHERE reflection_code = ANY(%s)", (codes,))


# ---------------------------------------------------------------------
# Reading -- System Administrator only
# ---------------------------------------------------------------------

def _is_admin(actor_role):
    return actor_role == ADMIN_ROLE


def _days(days):
    try:
        return max(1, min(365, int(days)))
    except (TypeError, ValueError):
        return 7


def get_step_summary(actor_role, days=7):
    """For each step with data in the last `days`: how many times it was
    measured, the average, the 90th percentile and the slowest, in
    milliseconds, in STEPS order. None for anyone but the System
    Administrator; [] if there is nothing or the database fails."""
    if not _is_admin(actor_role):
        return None
    since = now_utc() - timedelta(days=_days(days))
    conn = None
    try:
        conn = _get_conn()
        try:
            with conn.cursor() as c:
                c.execute(
                    """
                    SELECT step, COUNT(*), AVG(duration_ms),
                           PERCENTILE_CONT(0.9) WITHIN GROUP (ORDER BY duration_ms),
                           MAX(duration_ms)
                    FROM reflection_timings
                    WHERE recorded_at >= %s
                    GROUP BY step
                    """,
                    (since,),
                )
                rows = c.fetchall()
        finally:
            conn.close()
    except Exception:
        logger.warning("reflection_timing: get_step_summary FAILED", exc_info=True)
        return []
    by_step = {
        step: {"step": step, "count": int(count or 0), "avg_ms": float(avg or 0),
               "p90_ms": float(p90 or 0), "max_ms": float(mx or 0)}
        for step, count, avg, p90, mx in rows if step in _STEP_SET
    }
    return [by_step[s] for s in STEPS if s in by_step]


def get_ai_call_summary(actor_role, days=7):
    """Lens and analysis-report calls from the existing usage records
    (services/usage_ledger.py:get_call_stats). None for anyone but the
    System Administrator."""
    if not _is_admin(actor_role):
        return None
    from services import usage_ledger
    stats = usage_ledger.get_call_stats("anthropic", [LENS_OPERATION, REPORT_OPERATION], _days(days))
    return {row["operation"]: row for row in stats}


def get_measured_cost_per_reflection(actor_role, days=7):
    """The real Claude cost of lens and report calls in the period
    (retries and failed attempts included -- they are real cost), divided
    by the reflections completed in the SAME period. None for anyone but
    the System Administrator.

    Returns {"days", "reflections", "cost_usd", "avg_cost_usd" (None when
    there are no reflections)}."""
    if not _is_admin(actor_role):
        return None
    from services import usage_ledger
    from services.reflection_log import get_total_reflection_count
    window = _days(days)
    stats = usage_ledger.get_call_stats("anthropic", [LENS_OPERATION, REPORT_OPERATION], window)
    cost = sum(row["cost_usd"] for row in stats)
    try:
        since_iso = (now_utc() - timedelta(days=window)).isoformat()
        reflections = int(get_total_reflection_count(since_iso=since_iso) or 0)
    except Exception:
        logger.warning("reflection_timing: reflection count FAILED", exc_info=True)
        reflections = 0
    return {
        "days": window,
        "reflections": reflections,
        "cost_usd": cost,
        "avg_cost_usd": (cost / reflections) if reflections else None,
    }
