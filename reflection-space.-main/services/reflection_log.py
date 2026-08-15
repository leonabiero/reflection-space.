import json
from services.db_time import now_utc, iso_row, get_logger
from services.db_pool import get_conn as _acquire_pooled_conn

logger = get_logger(__name__)

# --- Schema hardening (audit Issue 1 / Issue 2) ---------------------------
#
# Issue 1: `created_at` was stored as plain TEXT
# (datetime.now().isoformat() strings) -- no timezone info, string-only
# comparisons, no real date arithmetic in SQL. It is now a proper
# TIMESTAMPTZ column. Every INSERT below now writes a timezone-aware UTC
# datetime object (via now_utc()) instead of a plain isoformat() string.
#
# Issue 2: this table had no index beyond its implicit primary key,
# despite get_recent_theme_counts() ORDER-ing by created_at DESC and
# get_theme_flag_counts()/get_total_reflection_count() filtering with
# `WHERE created_at >= %s`. An index on created_at (descending) is now
# created for exactly that access pattern.
#
# None of this changes what any function outside this file sees:
# whichever functions here select a date column still hand back the
# same ISO-8601 string shape callers (pages/, rdi/) have always
# received -- see services.db_time.iso()/iso_row(). Function signatures
# and return shapes are unchanged.
#
# Engineering-quality pass (see accompanying handoff notes)
# ---------------------------------------------------------------------
#   Change 1: connection always closed via try/finally.
#   Change 2: log_reflection() wraps its single INSERT with an explicit
#     commit/rollback pair.
#   Change 5 / 6: local _now_utc/_iso/_iso_row and
#     _schema_migrated/_ensure_timestamp_columns are replaced by the
#     shared services.db_time / services.db_migration modules.
#   (No pagination added here -- get_recent_theme_counts() already
#   takes an explicit `limit` parameter, and get_theme_flag_counts()/
#   get_total_reflection_count() must read every matching row to
#   compute a correct aggregate, so they are intentionally not
#   paginated, matching the reasoning in feedback_store.py /
#   exploration_log.py.)
# ---------------------------------------------------------------------

# Keys must match reflection_prompt.txt / reflection_service.py output,
# and are in the same order as T["themes"] / T["section_labels"] in
# language.py, so callers can zip them together directly.
THEME_KEYS = [
    "client_voice",
    "observation_vs_interpretation",
    "labels_and_language",
    "possible_bias",
    "evidence_for_decisions",
    "missing_information",
    "strengths_and_deficits",
    "continuity",
]


def _get_conn():
    """
    Acquire a pooled connection (services/db_pool.py). Schema
    creation/migration used to happen here, on every call -- it is now
    centralized in services/db_schema.py:ensure_schema(), called once
    at application startup (see app.py), so this is now just a pool
    checkout.
    """
    return _acquire_pooled_conn()


def log_reflection(case_ref, reflection_result, created_by="", created_by_role=""):
    """
    Records, for one successfully-generated reflection, which of the 8
    dimensions had a non-empty observation. Call this right after
    generate_reflection() succeeds (i.e. reflection_result has no
    "error" key) -- a failed parse has nothing meaningful to log.
    """
    flags = {}
    for key in THEME_KEYS:
        section = reflection_result.get(key)
        observation = ""
        if isinstance(section, dict):
            observation = (section.get("observation") or "").strip()
        flags[key] = bool(observation)

    conn = _get_conn()
    try:
        with conn.cursor() as c:
            c.execute("""
                INSERT INTO reflections (case_ref, flags, created_by, created_by_role, created_at)
                VALUES (%s, %s, %s, %s, %s)
            """, (case_ref, json.dumps(flags), created_by, created_by_role, now_utc()))
        conn.commit()
    except Exception:
        conn.rollback()
        # Only theme FLAGS (booleans) and operational identifiers are
        # ever logged here -- never `reflection_result` itself, which
        # can contain the actual observation/question text derived
        # from case documentation (Change 7's "no sensitive case
        # content in logs" rule).
        logger.exception(
            "log_reflection FAILED: case_ref=%r created_by=%r flags=%r",
            case_ref, created_by, flags,
        )
        raise
    finally:
        conn.close()


def get_recent_theme_counts(limit=10):
    """
    Returns (counts, total):
      - counts: {theme_key: number of the most recent `limit`
        reflections in which that dimension was flagged}
      - total: how many reflections were actually considered (<= limit,
        and 0 if none exist yet)
    """
    conn = _get_conn()
    try:
        with conn.cursor() as c:
            c.execute("""
                SELECT flags FROM reflections
                ORDER BY created_at DESC
                LIMIT %s
            """, (limit,))
            rows = c.fetchall()
    finally:
        conn.close()

    counts = {key: 0 for key in THEME_KEYS}
    for (flags_json,) in rows:
        try:
            flags = json.loads(flags_json) if flags_json else {}
        except (TypeError, ValueError):
            flags = {}
        for key in THEME_KEYS:
            if flags.get(key):
                counts[key] += 1

    return counts, len(rows)


def get_theme_flag_counts(since_iso=None):
    """
    Sprint 10 (Research Metrics): {theme_key: count} of how many
    reflections flagged that dimension, across ALL reflections in the
    given period (not just the most recent `limit` like
    get_recent_theme_counts() above) -- and, unlike that function,
    with no per-professional or per-case breakdown at all. This is
    purely an aggregate count for research/organisational-learning use,
    mirroring the same shape services.exploration_log.get_aggregated_theme_counts()
    already returns for explored (rather than flagged) themes, so the
    two can be compared side by side.

    `since_iso`, if given, restricts to reflections created at or after
    that ISO timestamp. `created_at` is now TIMESTAMPTZ (see module
    docstring), but a plain ISO-8601 string still compares correctly --
    PostgreSQL casts the untyped string literal to timestamptz for the
    comparison.

    Not paginated: must aggregate every matching row for a correct
    total per theme.
    """
    conn = _get_conn()
    try:
        with conn.cursor() as c:
            if since_iso:
                c.execute("SELECT flags FROM reflections WHERE created_at >= %s", (since_iso,))
            else:
                c.execute("SELECT flags FROM reflections")
            rows = c.fetchall()
    finally:
        conn.close()

    counts = {key: 0 for key in THEME_KEYS}
    for (flags_json,) in rows:
        try:
            flags = json.loads(flags_json) if flags_json else {}
        except (TypeError, ValueError):
            flags = {}
        for key in THEME_KEYS:
            if flags.get(key):
                counts[key] += 1

    return counts


def get_total_reflection_count(since_iso=None):
    """
    Sprint 10: total number of reflection sessions generated, org-wide,
    with no professional or case attribution -- a simple activity
    count for research purposes.
    """
    conn = _get_conn()
    try:
        with conn.cursor() as c:
            if since_iso:
                c.execute("SELECT COUNT(*) FROM reflections WHERE created_at >= %s", (since_iso,))
            else:
                c.execute("SELECT COUNT(*) FROM reflections")
            (count,) = c.fetchone()
    finally:
        conn.close()
    return count