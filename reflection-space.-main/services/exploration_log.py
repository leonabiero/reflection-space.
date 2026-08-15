from services.db_time import now_utc, iso_row, get_logger
from services.db_pool import get_conn as _acquire_pooled_conn

logger = get_logger(__name__)

# Reflection Exploration Log
# ============================
#
# Sprint 7: durable record of WHICH reflective themes a professional
# chose to explore (clicked "Explore" and exchanged at least one
# message about), and how many turns that exploration ran to.
#
# Deliberately does NOT store the conversation content itself. Session
# state already holds the live conversation for as long as the practitioner
# is working on it (see rdi/reflection_session.py); once that session
# ends, the conversation text is gone -- only the fact that this theme
# was explored, by whom, on which case, and how deeply, survives here.
#
# This follows the same minimization pattern already used by
# services/audit_log.py (which records that a case was deleted, never
# the case content). It exists specifically to give Sprint 8
# (Professional Growth Dashboard) and Sprint 9 (Team Learning Dashboard)
# real, durable data to read from -- without ever putting case dialogue
# at rest in a place a dashboard could accidentally surface it.
#
# --- Schema-hardening pass (audit Issue 1 / Issue 2) ------------------
#
# Audit Issue 1: `explored_at` used to be stored as plain TEXT
# (datetime.now().isoformat() strings) -- no timezone info, only
# string-based comparisons, no real date arithmetic in SQL. It is now
# a TIMESTAMPTZ column, populated via now_utc() (timezone-aware UTC)
# instead of the old naive isoformat() string.
#
# Audit Issue 2: no indexes existed beyond the implicit primary key,
# despite get_personal_exploration_history() filtering on explored_by
# and sorting on explored_at, and get_aggregated_theme_counts()
# filtering on explored_at. Both are now indexed (see
# idx_reflection_explorations_explored_by_at and
# idx_reflection_explorations_explored_at below).
#
# The TIMESTAMPTZ migration runs once per process, at startup, via
# services.db_schema.ensure_schema() (which calls the shared
# services.db_migration.ensure_timestamptz_columns() helper -- see
# that module's docstring). Every value read back from `explored_at`
# is normalized back to an ISO-8601 string via services.db_time.iso_row()
# before being returned, so this migration stays entirely contained to
# the database layer -- no caller outside services/exploration_log.py
# needs to change.
#
# Engineering-quality pass (see accompanying handoff notes)
# ---------------------------------------------------------------------
#   Change 1: connection always closed via try/finally.
#   Change 2: log_exploration() wraps its single INSERT with an
#     explicit commit/rollback pair.
#   Change 5 / 6: local _now_utc/_iso/_iso_row and
#     _schema_migrated/_ensure_timestamp_columns are replaced by the
#     shared services.db_time / services.db_migration modules.
#   (No pagination added here -- get_personal_exploration_history()
#   already takes an explicit `limit` parameter and is called with a
#   fixed cap (HISTORY_LIMIT = 50) from pages/growth_dashboard.py;
#   get_aggregated_theme_counts() must read every matching row to
#   compute an accurate aggregate count, so it is intentionally not
#   paginated, same reasoning as get_feedback_summary() in
#   services/feedback_store.py.)
# ---------------------------------------------------------------------


def _get_conn():
    """
    Acquire a pooled connection (services/db_pool.py). Schema
    creation/migration used to happen here, on every call -- it is now
    centralized in services/db_schema.py:ensure_schema(), called once
    at application startup (see app.py), so this is now just a pool
    checkout.
    """
    return _acquire_pooled_conn()


def log_exploration(case_ref, trigger, turn_count, explored_by="", explored_by_role=""):
    """
    Record one theme being explored within one reflection session.

    `trigger` is one of the 8 dimension keys already used everywhere
    else (see rdi.reflection_objects.ReflectiveOpportunity.trigger /
    services.reflection_log.THEME_KEYS), so this can be joined against
    the same theme vocabulary the Learning page already uses.

    `turn_count` is how many messages the professional sent in this
    opportunity's conversation before the session ended -- a simple
    depth signal, not a quality or competence measure. Call sites should
    skip calling this for opportunities with turn_count == 0 (never
    explored), so this table only ever contains genuine explorations.
    """
    conn = _get_conn()
    try:
        with conn.cursor() as c:
            c.execute("""
                INSERT INTO reflection_explorations
                    (case_ref, trigger, turn_count, explored_by, explored_by_role, explored_at)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (
                case_ref, trigger, turn_count,
                explored_by, explored_by_role,
                now_utc(),
            ))
        conn.commit()
    except Exception:
        conn.rollback()
        logger.exception(
            "log_exploration FAILED: case_ref=%r trigger=%r explored_by=%r",
            case_ref, trigger, explored_by,
        )
        raise
    finally:
        conn.close()


def get_personal_exploration_history(professional_name, limit=50):
    """
    All explorations logged by ONE named professional, most recent
    first. Used by the Professional Growth Dashboard (Sprint 8), which
    is scoped to a single practitioner looking at their own history --
    never used to compare across professionals.

    `limit` already existed as an explicit parameter before this pass
    (default 50) -- unchanged.
    """
    conn = _get_conn()
    try:
        with conn.cursor() as c:
            c.execute("""
                SELECT case_ref, trigger, turn_count, explored_at
                FROM reflection_explorations
                WHERE explored_by = %s
                ORDER BY explored_at DESC
                LIMIT %s
            """, (professional_name, limit))
            rows = c.fetchall()
    finally:
        conn.close()
    return [iso_row(row, [3]) for row in rows]


def get_aggregated_theme_counts(since_iso=None):
    """
    Theme -> total exploration count, aggregated across ALL
    professionals and cases, with no identifying information attached.
    Used by the Team Learning Dashboard (Sprint 9), which per the
    product requirements must never expose an individual professional,
    an individual case, or any one person's reflection history --
    only this kind of organisation-wide, anonymous tally.

    `since_iso`, if given, restricts to explorations at or after that
    ISO timestamp (e.g. "last 6 months"). Returns a plain dict.

    Not paginated: this must aggregate every matching row to produce a
    correct total per theme.
    """
    conn = _get_conn()
    try:
        with conn.cursor() as c:
            if since_iso:
                c.execute("""
                    SELECT trigger, COUNT(*) FROM reflection_explorations
                    WHERE explored_at >= %s
                    GROUP BY trigger
                """, (since_iso,))
            else:
                c.execute("""
                    SELECT trigger, COUNT(*) FROM reflection_explorations
                    GROUP BY trigger
                """)
            rows = c.fetchall()
    finally:
        conn.close()
    return {trigger: count for trigger, count in rows}