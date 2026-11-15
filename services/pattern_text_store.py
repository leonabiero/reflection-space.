"""
Pattern Review texts and reports (15 November 2026)
=====================================================

Product owner's decision (see PATTERNS.md): Pattern Review looks for
patterns in what social workers WRITE, not in what the AI says back to
them. This module is the only place that stores and reads the material
for that.

pattern_texts -- one ANONYMISED copy of each text
--------------------------------------------------
- Saved straight after the text is anonymised on the reflection screen
  (pages/reflection_space.py), before the reflection itself is written.
- Holds only: the anonymised text, the date, the reflection language
  and the reflection code. NO author name and NO role are stored.
- The reflection code is used for one thing only: deleting a reflection
  (by its author or the System Administrator) also deletes its copy
  (delete_for_codes, called from services/reflection_records.py), and a
  reflection waiting in its 48-hour bin is left out of the analysis.
  The code is never selected for the analysis and never shown.
- Deleted automatically after config.PATTERN_TEXT_RETENTION_MONTHS
  (purge_expired_pattern_texts).
- Only Supervisors and Programme Managers (services/pattern_access.py)
  can have the texts READ for an analysis (texts_for_period), and only
  the AI receives them: no function here returns a text to a page for
  display.
- Never logged: only counts and ids are.

pattern_reports -- the reports managers asked for
---------------------------------------------------
- The period (months), the number of texts read, the language, and the
  AI's written report (JSON). Never a text, a quotation or a name of a
  text's author.
- Kept until "Erase all data". Deleting a reflection later does not
  rewrite a report already made (the report never names texts).
"""

import json

from services.db_pool import get_conn as _acquire_pooled_conn
from services.db_time import now_utc, iso, get_logger
from services.pattern_access import can_review_patterns

logger = get_logger(__name__)

MAX_TEXT_CHARS = 60_000
MAX_REPORT_LIST = 50


def _get_conn():
    return _acquire_pooled_conn()


def _retention_months():
    from config import PATTERN_TEXT_RETENTION_MONTHS
    return int(PATTERN_TEXT_RETENTION_MONTHS)


def _clean_period(months):
    from config import PATTERN_PERIOD_CHOICES
    months = int(months)
    if months not in PATTERN_PERIOD_CHOICES:
        raise ValueError("Unsupported period")
    return months


# A copy whose reflection is waiting in its 48-hour bin (deleted_at set)
# is left out at once, exactly like everywhere else in the app. A copy
# with no reflection row at all (the reflection could not be saved) is
# still a text a social worker wrote, so it is kept.
_USABLE = """
    p.created_at >= now() - make_interval(months => %s)
    AND p.created_at >= now() - make_interval(months => %s)
    AND NOT EXISTS (
        SELECT 1 FROM reflection_runs r
        WHERE r.reflection_code = p.reflection_code
          AND r.deleted_at IS NOT NULL
    )
"""


# ---------------------------------------------------------------------
# Saving and deleting copies
# ---------------------------------------------------------------------
def save_pattern_text(reflection_code, language, anonymised_text):
    """Save the anonymised copy of one text. Returns True if a copy was
    stored, False if there was nothing to store or this reflection code
    already has one. Raises on database failure (the reflection screen
    treats saving as best effort)."""
    text = (anonymised_text or "").strip()
    if not text or not reflection_code:
        return False
    text = text[:MAX_TEXT_CHARS]
    conn = _get_conn()
    try:
        with conn.cursor() as c:
            c.execute(
                """
                INSERT INTO pattern_texts (reflection_code, language, anonymised_text, created_at)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (reflection_code) DO NOTHING
                """,
                (str(reflection_code), language or None, text, now_utc()),
            )
            stored = (c.rowcount or 0) == 1
        conn.commit()
    except Exception:
        conn.rollback()
        logger.exception("save_pattern_text FAILED (no text logged)")
        raise
    finally:
        conn.close()
    return stored


def discard_pattern_text(reflection_code):
    """Remove the copy saved for a reflection that failed completely, so
    that trying again (which uses a new code) does not count the same text
    twice. Returns True if a copy was removed. Never raises."""
    if not reflection_code:
        return False
    conn = None
    try:
        conn = _get_conn()
        with conn.cursor() as c:
            c.execute("DELETE FROM pattern_texts WHERE reflection_code = %s", (str(reflection_code),))
            removed = (c.rowcount or 0) > 0
        conn.commit()
        return removed
    except Exception:
        if conn is not None:
            try:
                conn.rollback()
            except Exception:
                pass
        logger.exception("discard_pattern_text FAILED")
        return False
    finally:
        if conn is not None:
            conn.close()


def delete_for_codes(cursor, codes):
    """Inside the caller's transaction: delete the copies of the given
    reflections (used when reflections are erased). Safe on a database
    where the table does not exist yet."""
    codes = [str(code) for code in (codes or []) if code]
    if not codes:
        return 0
    cursor.execute("SELECT to_regclass('pattern_texts')")
    if cursor.fetchone()[0] is None:
        return 0
    cursor.execute("DELETE FROM pattern_texts WHERE reflection_code = ANY(%s)", (codes,))
    return cursor.rowcount or 0


def purge_expired_pattern_texts():
    """Delete every copy older than PATTERN_TEXT_RETENTION_MONTHS.
    Returns how many were deleted."""
    conn = _get_conn()
    try:
        with conn.cursor() as c:
            c.execute(
                "DELETE FROM pattern_texts WHERE created_at < now() - make_interval(months => %s)",
                (_retention_months(),),
            )
            removed = c.rowcount or 0
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
    if removed:
        logger.info("Expired Pattern Review texts deleted: %d", removed)
    return removed


# ---------------------------------------------------------------------
# Reading copies for an analysis (management roles only)
# ---------------------------------------------------------------------
def count_texts_for_period(actor_role, months):
    """How many texts an analysis of the last `months` months would read.
    0 for anyone who may not use Pattern Review."""
    if not can_review_patterns(actor_role):
        return 0
    months = _clean_period(months)
    conn = _get_conn()
    try:
        with conn.cursor() as c:
            c.execute(
                f"SELECT COUNT(*) FROM pattern_texts p WHERE {_USABLE}",
                (months, _retention_months()),
            )
            return c.fetchone()[0] or 0
    finally:
        conn.close()


def texts_for_period(actor_role, months):
    """The anonymised texts of the last `months` months, for the AI only:
    a list of {"language", "text"}. Deliberately no code, no date, no id
    and nothing about the author. Raises PermissionError for anyone who
    may not use Pattern Review."""
    if not can_review_patterns(actor_role):
        raise PermissionError("Not permitted to use Pattern Review")
    months = _clean_period(months)
    conn = _get_conn()
    try:
        with conn.cursor() as c:
            c.execute(
                f"""
                SELECT p.language, p.anonymised_text
                FROM pattern_texts p
                WHERE {_USABLE}
                ORDER BY p.id
                """,
                (months, _retention_months()),
            )
            rows = c.fetchall()
    finally:
        conn.close()
    return [{"language": r[0] or "", "text": r[1] or ""} for r in rows if (r[1] or "").strip()]


# ---------------------------------------------------------------------
# Reports
# ---------------------------------------------------------------------
def save_report(actor_role, actor_name, period_months, texts_count, language,
                report, model="", prompt_version=""):
    """Store one finished report. Returns its id."""
    if not can_review_patterns(actor_role):
        raise PermissionError("Not permitted to use Pattern Review")
    if not actor_name:
        raise ValueError("actor_name is required")
    period_months = _clean_period(period_months)
    conn = _get_conn()
    try:
        with conn.cursor() as c:
            c.execute(
                """
                INSERT INTO pattern_reports
                    (period_months, texts_count, language, report, model,
                     prompt_version, created_by, created_by_role, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (period_months, int(texts_count), language or None,
                 json.dumps(report, ensure_ascii=False), model or None,
                 prompt_version or None, actor_name, actor_role, now_utc()),
            )
            report_id = c.fetchone()[0]
        conn.commit()
    except Exception:
        conn.rollback()
        logger.exception("save_report FAILED")
        raise
    finally:
        conn.close()
    return report_id


def _load_report(value):
    try:
        data = json.loads(value or "{}")
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def list_reports(actor_role, limit=MAX_REPORT_LIST):
    """Saved reports, newest first: id, created_at, period_months,
    texts_count, language, report (dict). [] for anyone who may not use
    Pattern Review."""
    if not can_review_patterns(actor_role):
        return []
    limit = max(1, min(int(limit), MAX_REPORT_LIST))
    conn = _get_conn()
    try:
        with conn.cursor() as c:
            c.execute(
                """
                SELECT id, created_at, period_months, texts_count, language, report
                FROM pattern_reports
                ORDER BY created_at DESC, id DESC
                LIMIT %s
                """,
                (limit,),
            )
            rows = c.fetchall()
    finally:
        conn.close()
    return [
        {
            "id": r[0],
            "created_at": iso(r[1]),
            "period_months": r[2],
            "texts_count": r[3],
            "language": r[4] or "",
            "report": _load_report(r[5]),
        }
        for r in rows
    ]
