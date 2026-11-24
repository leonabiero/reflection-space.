"""
Pattern Review texts and reports (15 November 2026)
=====================================================

Product owner's decisions (see PATTERNS.md): Pattern Review looks for
patterns in what social workers WRITE, not in what the AI says back to
them, and it uses the ORIGINAL texts the app already keeps (agreed with
EDE; reflection_runs.original_text, 15 months). No separate copy is saved.

Reading texts for an analysis
-------------------------------
- Only Supervisors and Programme Managers (services/pattern_access.py) can
  have the texts read for an analysis (texts_for_period), and only for the
  AI: no function here returns a text to a page for display.
- texts_for_period() returns the text and language ONLY -- no name, no
  role, no reflection code, no date.
- The texts are ORIGINAL texts, so they still contain names and personal
  details. services/pattern_text_analysis.py anonymises every text again
  before the AI reads it, so the AI still only ever receives anonymised
  text -- the same rule as for a reflection.
- Texts past ORIGINAL_TEXT_RETENTION_MONTHS, and reflections waiting in
  their 48-hour bin or erased, are never used (the same rules as the rest
  of the app; services/reflection_records.py).
- The same text is read and counted only once (24 November 2026): texts
  with the same fingerprint (services/text_fingerprint.py) count as one.
- Never logged: only counts and ids are.

pattern_reports -- the reports managers asked for
---------------------------------------------------
- The period (months), the number of texts read, the language, and the
  AI's written report (JSON). Never a text, a quotation or a name of a
  text's author.
- Kept until a manager deletes it (delete_report / delete_all_reports,
  18 November 2026: "I have the file: delete report") or "Erase all
  data". Reports are shared by the whole management team, so a deleted
  report is gone for every manager. Deleting a reflection later does not
  rewrite a report already made (the report never names texts).

(A separate anonymised copy, table pattern_texts, was used for a few hours
on 15 November 2026 and then dropped by the product owner's decision; the
table is removed by "Erase all data".)
"""

import json

from services.db_pool import get_conn as _acquire_pooled_conn
from services.db_time import now_utc, iso, get_logger
from services.pattern_access import can_review_patterns
from services.findings_store import NOT_IN_DELETION_WINDOW
from services import request_dedup

logger = get_logger(__name__)

MAX_REPORT_LIST = 50
REPORT_REQUEST_KIND = "pattern_text_report"


def report_fingerprint(period_months, texts_count, language):
    """The "same report" key used to stop the same review running twice
    (services/pattern_text_analysis.run_report). Kept here so deleting a
    report can lift exactly the same lock."""
    return request_dedup.fingerprint(
        REPORT_REQUEST_KIND, int(period_months), int(texts_count), language,
    )


def _get_conn():
    return _acquire_pooled_conn()


def _retention_months():
    from config import ORIGINAL_TEXT_RETENTION_MONTHS
    return int(ORIGINAL_TEXT_RETENTION_MONTHS)


def _clean_period(months):
    """A whole number of months from PATTERN_MIN_MONTHS to
    PATTERN_MAX_MONTHS (1-15 by default; 17 November 2026). Anything else
    -- 0, 16, a fraction, text -- is refused here, not only on screen."""
    from config import PATTERN_MIN_MONTHS, PATTERN_MAX_MONTHS
    if isinstance(months, bool):
        raise ValueError("Unsupported period")
    if isinstance(months, float):
        if not months.is_integer():
            raise ValueError("Unsupported period")
    try:
        months = int(months)
    except (TypeError, ValueError):
        raise ValueError("Unsupported period")
    if not PATTERN_MIN_MONTHS <= months <= PATTERN_MAX_MONTHS:
        raise ValueError("Unsupported period")
    return months


# Saved original texts written in the chosen period, still within their
# retention time, from reflections that are not deleted.
_USABLE = f"""
    r.original_text IS NOT NULL
    AND btrim(r.original_text) <> ''
    AND r.created_at >= now() - make_interval(months => %s)
    AND r.created_at >= now() - make_interval(months => %s)
    AND {NOT_IN_DELETION_WINDOW}
"""

# 24 November 2026 (product owner's decision): the same text is never
# counted twice. Texts with the same fingerprint (services/
# text_fingerprint.py: same words in the same order, ignoring spacing,
# line breaks and capitals) count once -- the earliest one is read. A
# text without a fingerprint counts on its own. New identical texts are
# no longer saved at all; this also covers copies saved before the change
# and a reflection restored from the bin after the same text was saved
# again.
_ONE_PER_TEXT = "COALESCE(r.text_fingerprint, 'run:' || r.id::text)"


# ---------------------------------------------------------------------
# Reading texts for an analysis (management roles only)
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
                f"SELECT COUNT(DISTINCT {_ONE_PER_TEXT}) FROM reflection_runs r WHERE {_USABLE}",
                (months, _retention_months()),
            )
            return c.fetchone()[0] or 0
    finally:
        conn.close()


def texts_for_period(actor_role, months):
    """The ORIGINAL texts of the last `months` months, for the AI only
    (pattern_text_analysis anonymises each one before sending it): a list
    of {"language", "text"}. Deliberately no name, role, code or date.
    Raises PermissionError for anyone who may not use Pattern Review."""
    if not can_review_patterns(actor_role):
        raise PermissionError("Not permitted to use Pattern Review")
    months = _clean_period(months)
    conn = _get_conn()
    try:
        with conn.cursor() as c:
            c.execute(
                f"""
                SELECT DISTINCT ON ({_ONE_PER_TEXT}) r.language, r.original_text, r.id
                FROM reflection_runs r
                WHERE {_USABLE}
                ORDER BY {_ONE_PER_TEXT}, r.id
                """,
                (months, _retention_months()),
            )
            rows = c.fetchall()
    finally:
        conn.close()
    # Back into saving order (the id is only used for sorting, never returned).
    rows = sorted(rows, key=lambda r: r[2] if len(r) > 2 else 0)
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


# ---------------------------------------------------------------------
# Deleting reports (18 November 2026, product owner's decision)
# ---------------------------------------------------------------------
# Any Supervisor or Programme Manager may delete any report (reports are
# shared by the whole management team). Downloading never deletes: the
# page has a separate button with an "are you sure?" step. Deleting also
# lifts the "this report was just made" lock (run_report's duplicate
# protection), so the same review can be run again straight away.
def _release_locks(rows):
    """Best effort: lift the duplicate-protection lock of each deleted
    report. If this fails the lock simply runs out after 15 minutes."""
    for period_months, texts_count, language in rows:
        try:
            request_dedup.release(report_fingerprint(period_months, texts_count, language))
        except Exception:
            logger.warning("Could not lift a Pattern Review lock (non-fatal)", exc_info=True)


def delete_report(actor_role, actor_name, report_id):
    """Permanently delete one report. True if it was deleted, False if it
    no longer existed (for example another manager deleted it first).
    Raises PermissionError for anyone who may not use Pattern Review."""
    if not can_review_patterns(actor_role):
        raise PermissionError("Not permitted to use Pattern Review")
    if not actor_name:
        raise ValueError("actor_name is required")
    report_id = int(report_id)
    conn = _get_conn()
    try:
        with conn.cursor() as c:
            c.execute(
                """
                DELETE FROM pattern_reports WHERE id = %s
                RETURNING period_months, texts_count, language
                """,
                (report_id,),
            )
            rows = c.fetchall()
        conn.commit()
    except Exception:
        conn.rollback()
        logger.exception("delete_report FAILED")
        raise
    finally:
        conn.close()
    if rows:
        logger.info("Pattern Review report %s deleted by %s (%s)", report_id, actor_name, actor_role)
        _release_locks(rows)
    return bool(rows)


def delete_all_reports(actor_role, actor_name):
    """Permanently delete every saved report (not only the ones listed on
    screen). Returns how many were deleted. Raises PermissionError for
    anyone who may not use Pattern Review."""
    if not can_review_patterns(actor_role):
        raise PermissionError("Not permitted to use Pattern Review")
    if not actor_name:
        raise ValueError("actor_name is required")
    conn = _get_conn()
    try:
        with conn.cursor() as c:
            c.execute(
                "DELETE FROM pattern_reports RETURNING period_months, texts_count, language"
            )
            rows = c.fetchall()
        conn.commit()
    except Exception:
        conn.rollback()
        logger.exception("delete_all_reports FAILED")
        raise
    finally:
        conn.close()
    logger.info("All Pattern Review reports deleted (%d) by %s (%s)", len(rows), actor_name, actor_role)
    _release_locks(rows)
    return len(rows)
