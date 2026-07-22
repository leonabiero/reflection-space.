import psycopg2
from datetime import datetime
from config import DATABASE_URL

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


def _get_conn():
    conn = psycopg2.connect(DATABASE_URL)
    with conn.cursor() as c:
        c.execute("""
        CREATE TABLE IF NOT EXISTS reflection_explorations (
            id SERIAL PRIMARY KEY,
            case_ref TEXT,
            trigger TEXT,
            turn_count INTEGER,
            explored_by TEXT,
            explored_by_role TEXT,
            explored_at TEXT
        )
        """)
    conn.commit()
    return conn


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
    with conn.cursor() as c:
        c.execute("""
            INSERT INTO reflection_explorations
                (case_ref, trigger, turn_count, explored_by, explored_by_role, explored_at)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (
            case_ref, trigger, turn_count,
            explored_by, explored_by_role,
            datetime.now().isoformat(),
        ))
    conn.commit()
    conn.close()


def get_personal_exploration_history(professional_name, limit=50):
    """
    All explorations logged by ONE named professional, most recent
    first. Used by the Professional Growth Dashboard (Sprint 8), which
    is scoped to a single practitioner looking at their own history --
    never used to compare across professionals.
    """
    conn = _get_conn()
    with conn.cursor() as c:
        c.execute("""
            SELECT case_ref, trigger, turn_count, explored_at
            FROM reflection_explorations
            WHERE explored_by = %s
            ORDER BY explored_at DESC
            LIMIT %s
        """, (professional_name, limit))
        rows = c.fetchall()
    conn.close()
    return rows


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
    """
    conn = _get_conn()
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
    conn.close()
    return {trigger: count for trigger, count in rows}