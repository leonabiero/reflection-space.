import json
import psycopg2
from datetime import datetime
from config import DATABASE_URL

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
    conn = psycopg2.connect(DATABASE_URL)
    with conn.cursor() as c:
        c.execute("""
        CREATE TABLE IF NOT EXISTS reflections (
            id SERIAL PRIMARY KEY,
            case_ref TEXT,
            flags TEXT,
            created_by TEXT,
            created_by_role TEXT,
            created_at TEXT
        )
        """)
    conn.commit()
    return conn


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
    with conn.cursor() as c:
        c.execute("""
            INSERT INTO reflections (case_ref, flags, created_by, created_by_role, created_at)
            VALUES (%s, %s, %s, %s, %s)
        """, (case_ref, json.dumps(flags), created_by, created_by_role, datetime.now().isoformat()))
    conn.commit()
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
    with conn.cursor() as c:
        c.execute("""
            SELECT flags FROM reflections
            ORDER BY created_at DESC
            LIMIT %s
        """, (limit,))
        rows = c.fetchall()
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
    that ISO timestamp.
    """
    conn = _get_conn()
    with conn.cursor() as c:
        if since_iso:
            c.execute("SELECT flags FROM reflections WHERE created_at >= %s", (since_iso,))
        else:
            c.execute("SELECT flags FROM reflections")
        rows = c.fetchall()
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
    with conn.cursor() as c:
        if since_iso:
            c.execute("SELECT COUNT(*) FROM reflections WHERE created_at >= %s", (since_iso,))
        else:
            c.execute("SELECT COUNT(*) FROM reflections")
        (count,) = c.fetchone()
    conn.close()
    return count