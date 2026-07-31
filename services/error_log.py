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
    Phase 2.1 (Stable Issue References), updated by Phase 4
    (REOPENING -- see services/case_knowledge.py): resolve the stable
    error_issues.id for one occurrence of a problem.

    If ANY issue already exists with the exact same (page, error_type,
    message) signature -- regardless of its current status -- this
    occurrence is folded into it: its occurrence_count goes up by one
    and last_seen is refreshed, and its existing id is reused.

    This is a deliberate change from the original Phase 2.1 behavior,
    which excluded Fixed/Closed issues here and gave a recurrence a
    brand-new id. Phase 4's whole point is a growing knowledge base
    PER PROBLEM -- so a recurrence after a fix must reuse the same
    issue (and therefore the same resolution history, AI
    investigations, and case knowledge already attached to it), not
    silently start a fresh, disconnected record:

      - If the matched issue was NOT previously Fixed/Closed, this is
        just another occurrence of an already-open issue -- status is
        left untouched.
      - If the matched issue WAS previously Fixed/Closed, this is a
        genuine recurrence after resolution. Its status is set to
        'Recurred' (a clearly-flagged state distinct from 'New', so
        the administrator immediately sees "this came back" rather
        than mistaking it for a fresh problem), and whatever
        resolution/case-knowledge was recorded for it is preserved
        into case_resolution_history BEFORE any further editing (see
        services/case_knowledge.py:snapshot_resolution_on_reopen).
        The administrator can then explicitly reopen it (move it to
        Investigating) via the existing status control -- see
        update_issue_status below and pages/system_administration.py.

    If no issue at all matches this signature (a brand-new problem),
    a new error_issues row is created and its new id becomes the
    stable reference number going forward.

    Never raises. Returns None if the database work fails, in which
    case the caller (log_error) simply proceeds without issue linking
    -- the individual error_log row is still written either way, so an
    issue-linking failure never loses the underlying error record.
    """
    signature = _issue_signature(page, error_type, message)
    conn = None
    issue_id = None
    was_reopened = False
    try:
        conn = _get_conn()
        with conn.cursor() as c:
            c.execute(
                """
                SELECT id, status FROM error_issues
                WHERE signature = %s
                ORDER BY id DESC LIMIT 1
                """,
                (signature,),
            )
            row = c.fetchone()
            now = now_utc()
            if row:
                issue_id, previous_status = row
                was_reopened = previous_status in ("Fixed", "Closed")
                if was_reopened:
                    c.execute(
                        """
                        UPDATE error_issues
                        SET occurrence_count = occurrence_count + 1,
                            last_seen = %s,
                            status = 'Recurred'
                        WHERE id = %s
                        """,
                        (now, issue_id),
                    )
                else:
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

    if was_reopened and issue_id is not None:
        # Best-effort, and deliberately AFTER the commit above -- a
        # failure here must never lose the occurrence that was just
        # recorded. See services/case_knowledge.py for what this
        # preserves and why.
        try:
            from services.case_knowledge import snapshot_resolution_on_reopen
            snapshot_resolution_on_reopen(issue_id)
        except Exception:
            logger.exception(
                "snapshot_resolution_on_reopen failed for issue_id=%s (non-fatal)", issue_id
            )

    return issue_id


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
              user_name="", user_role="", context=None, severity="error"):
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

    Phase 3: screenshots have been retired entirely. Every error and
    every user-submitted report is now diagnosed from the AI
    Diagnostic Package alone (services/diagnostics.py), and every
    alert email is built from that same package (see
    build_diagnostic_report_email below) -- entirely text-based, no
    attachments.
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
    package = None
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
            # Phase 3: the "screenshot" column still exists in the
            # table (services/db_schema.py) purely for backward
            # compatibility with older rows -- new rows are never
            # written with a screenshot, so it's simply left out of
            # this INSERT (it stays NULL, which every reader already
            # treats as "no screenshot for this record").
            c.execute("""
                INSERT INTO error_log
                    (occurred_at, page, error_type, message, traceback,
                     user_name, user_role, context, severity,
                     diagnostic_package, issue_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (
                now_utc(), page, error_type, message, traceback_text,
                user_name, user_role, context_json, severity,
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

    # Email alerting (Phase 3 redesign): only for genuine errors, not
    # routine "one companion had to retry" warnings -- otherwise a
    # single slow API response could trigger an email every few
    # minutes during a busy pilot day. User-submitted reports always
    # email, since a person deliberately flagged something -- both
    # cases are handled here now, from the SAME AI Diagnostic Package
    # already built above, so there is exactly one place that builds
    # and sends this email regardless of which of the two ways it was
    # triggered.
    if severity in ("error", "user_reported"):
        ref_for_email = issue_id if issue_id is not None else new_id
        if error_type == "UserReport":
            subject = f"[Reflection Space] Problem reported on {page}" + (
                f" (#{ref_for_email})" if ref_for_email else ""
            )
        else:
            subject = f"[Reflection Space] Error on {page} (#{ref_for_email})"

        package_dict = package.to_dict() if package is not None else {}
        was_sent = send_alert_email(
            subject=subject,
            body_text=build_diagnostic_report_email(package_dict, status="New"),
        )
        if was_sent:
            kind = "report" if error_type == "UserReport" else "error"
            record_event("Email sent", detail=f"{kind} alert for #{ref_for_email}", page=page)

    return new_id, issue_id


def log_user_report(page, description, user_name="", user_role=""):
    """
    Records a report submitted through the "Report a problem" sidebar
    widget (services/report_widget.py). Always sends an email alert --
    a person deliberately flagged this, unlike an automatically
    detected error, which only emails for severity == "error".

    Phase 3: this is now a thin wrapper around log_error() -- log_error
    itself builds the Diagnostic Package and sends the Diagnostic
    Report email for BOTH automatic errors and user reports, so this
    function no longer needs (or has) any email logic of its own.
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
    )

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
    presence = [(key, checks[key]) for key, _label in _AI_READINESS_CATEGORIES]
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


def build_diagnostic_report_email(package, status="New"):
    """
    Phase 3: builds the complete, entirely text-based "Diagnostic
    Report" alert email -- sent for both automatic errors and
    user-submitted reports (see log_error above, the single place that
    calls this). Replaces the old screenshot-carrying email entirely:
    no attachments, no images, no Base64, nothing that can silently
    fail to attach.

    Built directly from the AI Diagnostic Package (services/diagnostics.py)
    that is already generated for every error_log row, so the email and
    the record shown in System Administration > AI Diagnostic Centre
    are always built from the exact same data.

    package: dict (DiagnosticPackage.to_dict()) for this occurrence --
    may be an empty dict in the rare case the diagnostic build itself
    failed, in which case every section below degrades gracefully to
    a placeholder rather than raising.

    status: the lifecycle status to show for this issue. Every email
    is sent the moment an issue is created or recurs, so this is
    always "New" today -- kept as a parameter (rather than hardcoded)
    so a future phase could pass the real current status without
    changing this function's shape.
    """
    package = package or {}
    score, presence = compute_ai_readiness(package)

    evidence_lines = "\n".join(
        f"{'✓' if is_present else '✗'} {label}" for label, is_present in presence
    )

    timeline = package.get("navigation_timeline") or []
    if timeline:
        timeline_lines = []
        for entry in timeline:
            at_full = entry.get("at") or ""
            at = at_full[11:19] if len(at_full) >= 19 else at_full
            line = f"{at}  {entry.get('event', '')}"
            if entry.get("page"):
                line += f" (page: {entry['page']})"
            if entry.get("detail"):
                line += f" -- {entry['detail']}"
            timeline_lines.append(line)
        timeline_text = "\n".join(timeline_lines)
    else:
        timeline_text = "(no recent activity recorded for this session)"

    explanation = package.get("summary") or "(no explanation available)"
    ai_prompt = package.get("ai_prompt") or "(no AI prompt available -- open System Administration > AI Diagnostic Centre in the app)"

    divider = "-" * 50

    return f"""Reflection Space Diagnostic Report

Summary
Category: {package.get('category', '-')}
Severity: {package.get('severity', '-')}
Status: {status}
Timestamp: {package.get('timestamp', '-')}
Page: {package.get('page', '-')}
User: {package.get('user') or 'unknown'}
Role: {package.get('role') or 'unknown'}

{divider}
Evidence Collected

{evidence_lines}

{divider}
AI Readiness

Score: {score}%

{divider}
Human Explanation

{explanation}

{divider}
Recent Timeline

{timeline_text}

{divider}
AI Prompt

{ai_prompt}

For status updates and the full record, open System Administration > AI Diagnostic Centre in the app.
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