"""
Production Error Log
=======================

Purpose
---------
Leon (the product owner) is not a software developer -- Reflection
Space is built entirely with AI assistance. This module exists so that
when something breaks in production, in front of a real practitioner,
he has a reliable, non-technical way to:

  1. SEE that something broke, with plain-language context (which
     page, roughly what the person was doing, when).
  2. GET the full technical detail (exception type, message, full
     Python traceback) without needing to understand it himself.
  3. HAND that detail to an AI assistant (Claude) as a ready-made,
     copy-pasteable prompt -- so he never has to guess what
     information matters or summarize a traceback in his own words.

This module is intentionally self-contained and defensive: logging an
error must NEVER itself raise or crash the page that is already in
trouble. Every public function here swallows its own internal
failures and falls back to the stdout logger (visible in Streamlit
Cloud's "Manage app" log panel) as a last resort.

Design follows the same pattern as services/audit_log.py: a pooled
connection (services/db_pool.py), explicit commit/rollback, and
connection always returned via try/finally. The table itself is
created centrally in services/db_schema.py:ensure_schema(), exactly
like every other table in this app.

No case content (client names, case notes, document text) is ever
written here -- only operational/technical information: what broke,
where, and the traceback. Same "no sensitive content in logs" rule
already followed by services/audit_log.py.
"""

import json
import traceback
from contextlib import contextmanager

import streamlit as st

from services.db_time import now_utc, iso_row, get_logger
from services.db_pool import get_conn as _acquire_pooled_conn
from services.email_alert import send_alert_email
from services.diagnostics import build_diagnostic_package
from services.evidence_timeline import record_event

logger = get_logger(__name__)


def _get_conn():
    return _acquire_pooled_conn()


def _issue_signature(page, error_type, message):
    return f"{page}|{error_type}|{message}"


def _get_or_create_issue(page, error_type, message, severity):
    """
    Phase 2.1 (Stable Issue References): resolve the stable
    error_issues.id for one occurrence of a problem.

    If an OPEN (status not Fixed/Closed) issue already exists with the
    exact same (page, error_type, message) signature, this occurrence
    is folded into it: its occurrence_count goes up by one and
    last_seen is refreshed, and its existing id is reused -- so every
    person who hits the same unresolved bug sees the same reference
    number, and the admin sees one entry, not one per person.

    If no open issue matches (either this is a brand-new problem, or
    the previous issue with this exact signature was already marked
    Fixed/Closed), a new error_issues row is created and its new id
    becomes the stable reference number going forward -- correctly
    treating a recurrence AFTER a fix as a fresh issue to investigate.

    Never raises. Returns None if the database work fails, in which
    case the caller (log_error) simply proceeds without issue linking
    -- the individual error_log row is still written either way, so an
    issue-linking failure never loses the underlying error record.
    """
    signature = _issue_signature(page, error_type, message)
    conn = None
    try:
        conn = _get_conn()
        with conn.cursor() as c:
            c.execute(
                """
                SELECT id FROM error_issues
                WHERE signature = %s AND status NOT IN ('Fixed', 'Closed')
                ORDER BY id DESC LIMIT 1
                """,
                (signature,),
            )
            row = c.fetchone()
            now = now_utc()
            if row:
                issue_id = row[0]
                c.execute(
                    """
                    UPDATE error_issues
                    SET occurrence_count = occurrence_count + 1, last_seen = %s
                    WHERE id = %s
                    """,
                    (now, issue_id),
                )
            else:
                c.execute(
                    """
                    INSERT INTO error_issues
                        (signature, status, severity, page, error_type, message,
                         occurrence_count, first_seen, last_seen)
                    VALUES (%s, 'New', %s, %s, %s, %s, 1, %s, %s)
                    RETURNING id
                    """,
                    (signature, severity, page, error_type, message, now, now),
                )
                issue_id = c.fetchone()[0]
        conn.commit()
        return issue_id
    except Exception:
        if conn is not None:
            try:
                conn.rollback()
            except Exception:
                pass
        logger.exception("_get_or_create_issue FAILED for signature=%r", signature)
        return None
    finally:
        if conn is not None:
            conn.close()


def update_issue_status(issue_id, new_status):
    """
    Phase 2.1: set the lifecycle status of a whole ISSUE (not a single
    occurrence row). This is the authoritative status used everywhere
    an issue has a stable issue_id. Setting status to Fixed or Closed
    also stamps resolved_at -- that's what makes the NEXT occurrence
    of the same signature start a brand-new issue instead of reopening
    this one (see _get_or_create_issue above).

    Never raises. Returns True on success, False if the write failed.
    """
    conn = None
    try:
        conn = _get_conn()
        with conn.cursor() as c:
            if new_status in ("Fixed", "Closed"):
                c.execute(
                    "UPDATE error_issues SET status = %s, resolved_at = %s WHERE id = %s",
                    (new_status, now_utc(), issue_id),
                )
            else:
                c.execute(
                    "UPDATE error_issues SET status = %s, resolved_at = NULL WHERE id = %s",
                    (new_status, issue_id),
                )
        conn.commit()
        return True
    except Exception:
        if conn is not None:
            try:
                conn.rollback()
            except Exception:
                pass
        logger.exception("update_issue_status FAILED for issue_id=%s", issue_id)
        return False
    finally:
        if conn is not None:
            conn.close()


def log_error(page, error_type, message, traceback_text,
              user_name="", user_role="", context=None, severity="error",
              screenshot_b64=None):
    """
    Write one error record. Returns a (new_id, issue_id) tuple:
      - new_id: the id of this individual occurrence row, or None if
        writing to the database itself failed (in which case the
        error is still written to stdout via the logger, so it is
        never silently lost).
      - issue_id: the STABLE, shared reference number for this
        problem (Phase 2.1) -- the same number every person sees for
        as long as the issue stays unresolved, and what the admin
        should treat as "the" reference. None for user-submitted
        reports (each is its own independent case, never grouped) or
        if issue-linking itself failed (in which case new_id is still
        valid and the occurrence was still logged).

    context: an optional dict of small, non-sensitive operational
    details (e.g. {"companion": "possible_bias", "attempt": 3}) --
    stored as JSON text. Never put case/client content in here.

    screenshot_b64: optional data-URL string ("data:image/jpeg;base64,...")
    captured by components/screenshot_reporter -- only ever populated
    for user-submitted reports (see log_user_report below); automatic
    crash detection has no screenshot to attach.
    """
    # Phase 2.1 (Stable Issue References): resolve/reuse a stable
    # issue id for this exact (page, error_type, message) BEFORE
    # writing the occurrence row, so the row can store it. Skipped for
    # user-submitted reports -- those are always independent, never
    # grouped (see _get_or_create_issue's docstring and
    # group_errors_by_signature below).
    issue_id = None
    if error_type != "UserReport":
        issue_id = _get_or_create_issue(page, error_type, message, severity)

    context_json = ""
    if context:
        try:
            context_json = json.dumps(context, default=str)
        except Exception:
            context_json = str(context)

    # Phase 1 Diagnostic Engine (services/diagnostics.py): build the
    # full AI Diagnostic Package behind the scenes, every single time
    # a row is written here -- whether that's an automatic exception
    # (via error_boundary, below) or a user-submitted report
    # (log_user_report calls this same function). This is the ONE
    # place both triggers already funnel through, so hooking in here
    # covers both without touching either caller's own logic. Never
    # allowed to prevent the error itself from being logged.
    diagnostic_package_json = "{}"
    try:
        if error_type != "UserReport":
            record_event(
                "Exception occurred" if severity == "error" else "Error logged",
                detail=f"{error_type}: {message}",
                page=page,
            )
        package = build_diagnostic_package(
            page=page,
            error_type=error_type,
            message=message,
            traceback_text=traceback_text,
            user_name=user_name,
            user_role=user_role,
            severity=severity,
            context=context,
        )
        diagnostic_package_json = package.to_json()
    except Exception:
        logger.exception("Diagnostic package build failed for this error (non-fatal)")

    conn = None
    new_id = None
    try:
        conn = _get_conn()
        with conn.cursor() as c:
            c.execute("""
                INSERT INTO error_log
                    (occurred_at, page, error_type, message, traceback,
                     user_name, user_role, context, severity, screenshot,
                     diagnostic_package, issue_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (
                now_utc(), page, error_type, message, traceback_text,
                user_name, user_role, context_json, severity, screenshot_b64,
                diagnostic_package_json, issue_id,
            ))
            new_id = c.fetchone()[0]
        conn.commit()
        logger.error(
            "Logged error #%s (issue #%s) page=%r type=%r message=%r",
            new_id, issue_id, page, error_type, message,
        )
    except Exception:
        if conn is not None:
            try:
                conn.rollback()
            except Exception:
                pass
        # The database write failed -- this is the one place we fall
        # back to plain stdout logging so the error is at least
        # visible in the Streamlit Cloud log panel.
        logger.exception(
            "log_error FAILED to write to database. Original error: "
            "page=%r type=%r message=%r traceback=%s",
            page, error_type, message, traceback_text,
        )
    finally:
        if conn is not None:
            conn.close()

    # Email alerting: only for genuine errors, not routine "one
    # companion had to retry" warnings -- otherwise a single slow API
    # response could trigger an email every few minutes during a busy
    # pilot day. User reports (log_user_report, below) always email,
    # since a person deliberately flagged something.
    if severity == "error":
        record = {
            "id": new_id, "occurred_at": now_utc(), "page": page,
            "error_type": error_type, "message": message,
            "traceback": traceback_text, "user_role": user_role,
            "context": context_json,
            # BUG FIX (2026-07-30): this key was previously missing here,
            # even though screenshot_b64 is passed to send_alert_email()
            # a few lines down as the actual attachment. build_email_summary()
            # reads record["screenshot"] to decide what the email SAYS, so
            # without this key the email always claimed "no screenshot"
            # regardless of whether one was really attached. Automatic
            # errors never have a screenshot in practice (see log_error's
            # docstring), but the key is included here anyway for
            # consistency and to avoid this exact bug recurring.
            "screenshot": screenshot_b64,
        }
        ref_for_email = issue_id if issue_id is not None else new_id
        was_sent = send_alert_email(
            subject=f"[Reflection Space] Error on {page} (#{ref_for_email})",
            body_text=build_email_summary(record),
            screenshot_b64=screenshot_b64,
        )
        if was_sent:
            record_event("Email sent", detail=f"error alert for #{ref_for_email}", page=page)

    return new_id, issue_id


def log_user_report(page, description, user_name="", user_role="", screenshot_b64=None):
    """
    Records a report submitted through the "Report a problem" sidebar
    widget (services/report_widget.py). Always sends an email alert --
    a person deliberately flagged this, unlike an automatically
    detected error, which only emails for severity == "error".
    """
    record_event("User submitted report", detail=description, page=page)

    # UserReport rows are never issue-linked (see log_error), so the
    # second value here is always None -- only new_id is used below.
    new_id, _issue_id = log_error(
        page=page,
        error_type="UserReport",
        message=description,
        traceback_text="(user-submitted report -- no traceback; see description above)",
        user_name=user_name,
        user_role=user_role,
        severity="user_reported",
        screenshot_b64=screenshot_b64,
    )

    record = {
        "id": new_id, "occurred_at": now_utc(), "page": page,
        "error_type": "UserReport", "message": description,
        "traceback": "(user-submitted report)", "user_role": user_role,
        # BUG FIX (2026-07-30): this key was previously missing here, even
        # though screenshot_b64 is passed to send_alert_email() a few lines
        # down as the actual attachment. This is the main report path (the
        # "Report a problem" button always has a real chance of a
        # screenshot), so this was the record that most often produced a
        # mismatched email -- "No screenshot was captured" text next to an
        # actual attached image.
        "screenshot": screenshot_b64,
    }
    was_sent = send_alert_email(
        subject=f"[Reflection Space] Problem reported on {page}"
                + (f" (#{new_id})" if new_id else ""),
        body_text=build_email_summary(record),
        screenshot_b64=screenshot_b64,
    )
    if was_sent:
        record_event("Email sent", detail=f"report alert for #{new_id}", page=page)

    return new_id


def get_recent_errors(limit=50):
    """
    Returns the most recent error records, newest first, as a list of
    dicts. Never raises -- returns an empty list if the read itself
    fails, so the admin Error Log section always renders something.
    """
    conn = None
    try:
        conn = _get_conn()
        with conn.cursor() as c:
            # LEFT JOIN error_issues: rows written before Phase 2.1 (or
            # a UserReport row, which is never issue-linked) have
            # issue_id = NULL, so every ei.* column below comes back
            # NULL for them too -- handled explicitly in the dict
            # below, same "NULL means older/ungrouped record" pattern
            # already used for the plain error_log.status column.
            c.execute("""
                SELECT el.id, el.occurred_at, el.page, el.error_type, el.message,
                       el.traceback, el.user_name, el.user_role, el.context,
                       el.severity, el.screenshot, el.diagnostic_package,
                       el.status, el.issue_id,
                       ei.status, ei.occurrence_count, ei.first_seen, ei.last_seen
                FROM error_log el
                LEFT JOIN error_issues ei ON ei.id = el.issue_id
                ORDER BY el.occurred_at DESC
                LIMIT %s
            """, (limit,))
            rows = c.fetchall()
    except Exception:
        logger.exception("get_recent_errors FAILED")
        return []
    finally:
        if conn is not None:
            conn.close()

    records = []
    for row in iso_row_list(rows, [1, 16, 17]):
        (rid, occurred_at, page, error_type, message, tb,
         user_name, user_role, context, severity, screenshot,
         diagnostic_package, legacy_status, issue_id,
         issue_status, issue_occurrence_count,
         issue_first_seen, issue_last_seen) = row
        records.append({
            "id": rid,
            "occurred_at": occurred_at,
            "page": page,
            "error_type": error_type,
            "message": message,
            "traceback": tb,
            "user_name": user_name,
            "user_role": user_role,
            "context": context,
            "severity": severity,
            "screenshot": screenshot,
            # Phase 1 Diagnostic Engine: JSON text built by
            # services/diagnostics.py. Displayed on the System
            # Administration > Error Log page as of Phase 2 -- see
            # parse_diagnostic_package() below.
            "diagnostic_package": diagnostic_package,
            # Phase 2.1 (Stable Issue References): issue_id is the
            # number shown to the person on screen and used as the
            # admin's reference -- None only for UserReport rows and
            # for rows written before this phase existed. When
            # present, issue_status/occurrence_count/first_seen/
            # last_seen are the AUTHORITATIVE, database-tracked values
            # for the whole issue (not just what happens to be in this
            # one fetched batch of `limit` rows) -- see
            # group_errors_by_signature below, which prefers these
            # over anything counted locally.
            "issue_id": issue_id,
            "issue_status": issue_status,
            "issue_occurrence_count": issue_occurrence_count,
            "issue_first_seen": issue_first_seen,
            "issue_last_seen": issue_last_seen,
            # Phase 2 AI Diagnostic Centre: manual lifecycle status.
            # For an issue-linked row, issue_status (above) is now the
            # authoritative one -- this legacy per-row column only
            # still matters for older records that predate issue
            # linking (issue_id is None for those).
            "status": (issue_status or legacy_status or "New"),
        })
    return records


def iso_row_list(rows, date_indexes):
    """Small local helper: apply services.db_time.iso_row across a
    list of rows. Kept here (rather than importing a plural helper
    that doesn't exist in db_time.py) to avoid touching that shared
    module for a one-line convenience."""
    return [iso_row(row, date_indexes) for row in rows]


def update_error_status(error_id, new_status):
    """
    Phase 2 AI Diagnostic Centre: manually set the lifecycle status of
    one error_log row. The System Administration > Error Log page only
    ever offers "New" / "Investigating" / "Fixed" / "Closed", but this
    function itself doesn't enforce that list -- it just writes
    whatever string it's given.

    No automation, no duplicate-detection side effects -- this only
    ever touches the single row identified by error_id.

    Never raises. Returns True on success, False if the write failed
    (in which case the failure is logged, exactly like every other
    database write in this module).
    """
    conn = None
    try:
        conn = _get_conn()
        with conn.cursor() as c:
            c.execute(
                "UPDATE error_log SET status = %s WHERE id = %s",
                (new_status, error_id),
            )
        conn.commit()
        return True
    except Exception:
        if conn is not None:
            try:
                conn.rollback()
            except Exception:
                pass
        logger.exception("update_error_status FAILED for id=%s", error_id)
        return False
    finally:
        if conn is not None:
            conn.close()


def parse_diagnostic_package(diagnostic_package_json):
    """
    Phase 2 AI Diagnostic Centre: safely parse the JSON text stored in
    error_log.diagnostic_package (built by services/diagnostics.py)
    back into a plain dict for display.

    Returns None -- never raises, never returns something the caller
    would need to guard against separately -- if the value is:
      - missing / empty
      - the "{}" placeholder written when the Phase 1 diagnostic
        package build itself failed (see log_error above)
      - not valid JSON (e.g. a record logged before the Diagnostic
        Engine existed, which never wrote this column at all)

    Callers (pages/system_administration.py) treat a None return as
    "no Diagnostic Package for this record" and fall back to the
    older, plainer fields already stored directly on the row.
    """
    if not diagnostic_package_json:
        return None
    try:
        data = json.loads(diagnostic_package_json)
    except Exception:
        return None
    if not isinstance(data, dict) or not data:
        return None
    return data


# Fixed, documented order for the "Evidence Collected" checklist and
# the AI Readiness Score (see compute_ai_readiness below). Each entry
# is (internal_key, display_label).
_AI_READINESS_CATEGORIES = (
    ("exception", "Exception"),
    ("traceback_evidence", "Traceback"),
    ("timeline", "Timeline"),
    ("session_context", "Session Context"),
    ("environment", "Environment"),
    ("user_information", "User Information"),
    ("configuration", "Configuration"),
)


def compute_ai_readiness(package):
    """
    Phase 2 AI Diagnostic Centre: a plain completeness score -- NOT an
    AI judgement of anything, and NOT a measure of severity -- based
    only on how many of 7 fixed evidence categories are present in an
    already-parsed diagnostic package (see parse_diagnostic_package
    above).

    Returns (score_percent, presence):
      - score_percent: int 0-100, simply
        round(100 * present_count / total_categories)
      - presence: an ordered list of (label, is_present) tuples, in
        the fixed order defined by _AI_READINESS_CATEGORIES above,
        ready to render directly as a checklist.

    A category counts as present using a simple non-empty check on
    the corresponding diagnostic package field(s) -- nothing clever
    and nothing AI-driven:
      - Exception: exception_type or exception_message is set
      - Traceback: traceback is set AND this wasn't a user-submitted
        report. User reports (exception_type == "UserReport") always
        carry a fixed placeholder string in the traceback field
        (see services/error_log.py:log_user_report) explaining that
        no traceback exists -- that placeholder is not technical
        evidence, so it must never count toward the score or be
        confused with a genuine traceback.
      - Timeline: navigation_timeline is a non-empty list
      - Session Context: session_context is a non-empty dict
      - Environment: environment is a non-empty dict, OR
        python_version / operating_system is set
      - User Information: user or role is set
      - Configuration: config_values is a non-empty dict

    If package is None (no Diagnostic Package at all -- e.g. an older
    record), every category is False and the score is 0.
    """
    if not package:
        presence = [(label, False) for _, label in _AI_READINESS_CATEGORIES]
        return 0, presence

    is_user_report = package.get("exception_type") == "UserReport"
    checks = {
        "exception": bool(package.get("exception_type") or package.get("exception_message")),
        "traceback_evidence": bool(package.get("traceback")) and not is_user_report,
        "timeline": bool(package.get("navigation_timeline")),
        "session_context": bool(package.get("session_context")),
        "environment": bool(package.get("environment"))
        or bool(package.get("python_version"))
        or bool(package.get("operating_system")),
        "user_information": bool(package.get("user") or package.get("role")),
        "configuration": bool(package.get("config_values")),
    }
    presence = [(label, checks[key]) for key, label in _AI_READINESS_CATEGORIES]
    present_count = sum(1 for _, is_present in presence if is_present)
    score = round((present_count / len(presence)) * 100)
    return score, presence


def group_errors_by_signature(errors):
    """
    Phase 2 AI Diagnostic Centre (updated for Phase 2.1 Stable Issue
    References): groups already-fetched error records (from
    get_recent_errors -- newest first) into "issues", so the same
    problem happening repeatedly shows up once with an occurrence
    count, rather than as many separate entries.

    Grouping key: the row's stable issue_id when present (the
    database-authoritative grouping set by _get_or_create_issue at
    write time -- see services/error_log.py:log_error). Rows written
    before Phase 2.1 existed have issue_id = None and fall back to the
    old exact-match-on-(page, error_type, message) grouping so they
    still display sensibly. User-submitted reports (error_type ==
    "UserReport") are never grouped with one another, since each one
    is independent free text describing a different situation --
    every UserReport row is its own single-occurrence group.

    occurrences / first_seen / last_seen come from the AUTHORITATIVE
    error_issues counters when a row is issue-linked -- not merely
    counted within this fetched batch -- so the numbers stay correct
    even when an issue has recurred more times than the current fetch
    limit shows.

    Returns a list of dicts, in the same newest-first order as the
    input, one per distinct issue:
        {
            "signature": str,
            "issue_id": int | None,
            "occurrences": int,
            "first_seen": str (ISO timestamp, oldest occurrence),
            "last_seen": str (ISO timestamp, newest occurrence),
            "latest": dict,       # the newest record in this group --
                                   # used for all display purposes,
                                   # since it has the most complete
                                   # diagnostic package
            "all_ids": [int, ...],       # newest first
            "occurrence_list": [dict],   # newest first, from THIS fetched
                                          # batch only -- {id, occurred_at,
                                          # user_name, user_role} -- used
                                          # for the admin's expandable
                                          # "who hit this" list
        }
    """
    groups = {}
    order = []
    for err in errors:
        issue_id = err.get("issue_id")
        if err.get("error_type") == "UserReport":
            sig = f"UserReport:{err.get('id')}"
        elif issue_id is not None:
            sig = f"issue:{issue_id}"
        else:
            # Pre-Phase-2.1 record: no stable issue_id was ever
            # assigned to it, so fall back to matching on content.
            sig = f"{err.get('page')}|{err.get('error_type')}|{err.get('message')}"

        if sig not in groups:
            groups[sig] = {
                "signature": sig,
                "issue_id": issue_id,
                "occurrences": 0,
                "first_seen": err.get("occurred_at"),
                "last_seen": err.get("occurred_at"),
                "latest": err,
                "all_ids": [],
                "occurrence_list": [],
            }
            order.append(sig)

        group = groups[sig]
        group["occurrences"] += 1
        group["all_ids"].append(err.get("id"))
        group["occurrence_list"].append({
            "id": err.get("id"),
            "occurred_at": err.get("occurred_at"),
            "user_name": err.get("user_name"),
            "user_role": err.get("user_role"),
        })
        # errors is newest-first, so the LAST occurrence encountered
        # for a given signature (i.e. the final write on each loop
        # pass) is always the oldest -- that becomes first_seen.
        group["first_seen"] = err.get("occurred_at") or group["first_seen"]

    # Prefer the authoritative error_issues counters over whatever was
    # merely counted in this one fetched batch, for any group that has
    # a real issue_id.
    for sig, group in groups.items():
        latest = group["latest"]
        if latest.get("issue_id") is not None:
            if latest.get("issue_occurrence_count"):
                group["occurrences"] = latest["issue_occurrence_count"]
            if latest.get("issue_first_seen"):
                group["first_seen"] = latest["issue_first_seen"]
            if latest.get("issue_last_seen"):
                group["last_seen"] = latest["issue_last_seen"]

    return [groups[sig] for sig in order]


def build_email_summary(record):
    """
    Short, plain-language summary for the ALERT EMAIL -- distinct from
    build_ai_prompt (below), which is a long, AI-assistant-oriented
    prompt meant for the System Administration > Error Log page, not
    for an inbox. Keeping these separate means the email stays quick
    to read on a phone, while the full AI-ready prompt is still one
    click away whenever it's actually needed.
    """
    ctx_line = f"\nContext: {record['context']}" if record.get("context") else ""
    # NOTE (2026-07-30 bug fix): the actual "screenshot attached" / "no
    # screenshot" wording is intentionally NOT decided here. It used to be
    # decided here, based solely on whether a screenshot_b64 string existed
    # -- but that could still disagree with the real email, e.g. if the
    # attachment step in services/email_alert.py later failed to decode the
    # image. To guarantee the wording and the actual attachment can never
    # disagree, we leave this placeholder token and let send_alert_email()
    # (the one place that knows whether the attachment truly succeeded)
    # fill it in right before sending. See services/email_alert.py.
    return f"""A problem was reported in Reflection Space.

Page: {record.get('page')}
When: {record.get('occurred_at')}
Reported by (role): {record.get('user_role') or 'unknown'}
Description: {record.get('message')}{ctx_line}
%%SCREENSHOT_STATUS%%

For full technical detail, or to copy a ready-made prompt for Claude to help \
diagnose it, open System Administration > Error Log in the app.
"""


def build_ai_prompt(record):
    """
    Build a complete, ready-to-paste prompt describing this one error,
    written for handing directly to an AI coding assistant (Claude).

    This exists specifically so Leon never has to describe a bug in
    his own words -- he can select all of this text, paste it into a
    chat with Claude, and the AI has everything it needs to diagnose
    the problem accurately the first time.
    """
    ctx_line = ""
    if record.get("context"):
        ctx_line = f"\nAdditional context: {record['context']}\n"

    screenshot_line = ""
    if record.get("screenshot"):
        screenshot_line = (
            "\nA screenshot was attached to this report. It is not included in this text -- "
            "if you're pasting this into a chat with an AI that can see images, also attach/paste "
            "the screenshot image itself (visible on the System Administration > Error Log page, "
            "or in the alert email you received).\n"
        )

    return f"""I'm the non-developer owner of a Streamlit app called "Reflection Space" \
(GitHub repo: leonabiero/reflection-space, deployed on Streamlit Community Cloud, \
using a Neon PostgreSQL database and the Anthropic API). I don't write code myself -- \
the app was built entirely with AI assistance, so please explain what went wrong in \
plain language BEFORE giving me any fix, and if you do give me a fix, give me the \
COMPLETE contents of any file that needs to change (not a snippet or a diff), since I \
don't know how to apply a partial edit myself.

An error occurred in production. Here is everything I have on it:

- When it happened: {record.get('occurred_at')}
- Which page/area of the app: {record.get('page')}
- Who was using it (role): {record.get('user_role') or 'unknown'}
- Error type: {record.get('error_type')}
- Error message: {record.get('message')}
{ctx_line}
Full technical traceback:
{record.get('traceback')}
{screenshot_line}
Please:
1. Tell me, in plain non-technical language, what most likely caused this.
2. Tell me if you need to see the current contents of a specific file to be sure -- \
if so, tell me exactly which file(s) so I can paste them in.
3. Once you're confident, give me the complete corrected file(s), ready to save over \
the existing one(s).
"""


@contextmanager
def error_boundary(page, T=None, user_name="", user_role="",
                    context=None, reset_flags=None, severity="error"):
    """
    Wrap a block of Streamlit page code so that any unexpected
    exception is caught, logged to the Error Log (visible on the
    System Administration page), and shown to the person as a calm,
    friendly message with a reference number -- instead of Streamlit's
    default red crash screen.

    Usage:
        with error_boundary("reflection_space", T=T, user_name=user_name,
                             user_role=user_role,
                             reset_flags=["_generating_reflection"]):
            ... risky code ...

    reset_flags: session_state keys to reset to False on failure, so a
    crash mid-action doesn't permanently leave a button/spinner stuck
    (e.g. "_generating_reflection").
    """
    try:
        yield
    except Exception as e:
        tb = traceback.format_exc()
        error_id, issue_id = log_error(
            page=page,
            error_type=type(e).__name__,
            message=str(e),
            traceback_text=tb,
            user_name=user_name,
            user_role=user_role,
            context=context,
            severity=severity,
        )

        for key in (reset_flags or []):
            st.session_state[key] = False

        # Phase 2.1 (Stable Issue References): the number shown on
        # screen is the STABLE issue reference, not the raw row id --
        # every person who hits the same unresolved bug sees the same
        # number here, and it only changes once an administrator marks
        # the issue Fixed/Closed and it happens again. Falls back to
        # the row id only if issue-linking itself failed (issue_id is
        # None) but the error was still logged (error_id is not None).
        display_ref = issue_id if issue_id is not None else error_id
        ref = f"#{display_ref}" if display_ref is not None else "(not saved -- see app logs)"
        if T is not None:
            heading = T.get(
                "error_boundary_heading",
                "Something went wrong on this page.",
            )
            body = T.get(
                "error_boundary_body",
                "This has been recorded as error {ref}. Please try again -- if it "
                "keeps happening, tell your administrator the reference number above.",
            ).format(ref=ref)
        else:
            heading = "Something went wrong on this page."
            body = (
                f"This has been recorded as error {ref}. Please try again -- if it "
                "keeps happening, tell your administrator the reference number above."
            )
        st.error(f"{heading}\n\n{body}")