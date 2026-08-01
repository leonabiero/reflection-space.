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
from services.diagnostics import build_diagnostic_package, compute_ai_readiness
from services.evidence_timeline import record_event

logger = get_logger(__name__)


def _get_conn():
    return _acquire_pooled_conn()


def _issue_signature(page, error_type, message):
    # Kept only as a legacy/fallback identifier -- see
    # _get_or_create_issue's docstring. No longer the primary way
    # issues are matched; services/issue_fingerprint.py's
    # build_fingerprint() is.
    return f"{page}|{error_type}|{message}"


def _build_issue_title(category, error_type, page, operation):
    """
    A short, human-scannable title for an Issue -- shown in the admin
    Error Log list instead of a raw exception type. E.g.:
    "AI / Claude API failure in generate_companion_reflection
    (reflection_space)".
    """
    op = f" in {operation}" if operation and operation != "unknown" else ""
    pg = f" ({page})" if page else ""
    return f"{category}{op}{pg}" if category else f"{error_type or 'Unknown error'}{op}{pg}"


def _record_affected_user(c, issue_id, user_name):
    """
    Upserts (issue_id, user_name) into error_issue_users and refreshes
    error_issues.affected_user_count from the resulting distinct
    count. Runs on the SAME cursor/transaction as the caller, so it
    either commits or rolls back together with the rest of
    _get_or_create_issue's work -- never a separate, riskier write.
    No-op (and never raises) if user_name is empty, since anonymous
    occurrences can't be attributed to any one person.
    """
    if not user_name:
        return
    now = now_utc()
    c.execute(
        """
        INSERT INTO error_issue_users (issue_id, user_name, first_seen, last_seen)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (issue_id, user_name) DO UPDATE SET last_seen = EXCLUDED.last_seen
        """,
        (issue_id, user_name, now, now),
    )
    c.execute(
        """
        UPDATE error_issues
        SET affected_user_count = (
            SELECT COUNT(*) FROM error_issue_users WHERE issue_id = %s
        )
        WHERE id = %s
        """,
        (issue_id, issue_id),
    )


def _get_or_create_issue(page, error_type, message, severity,
                          traceback_text=None, user_name="",
                          title_override=None, root_cause_hint=None):
    """
    Phase 2 (Issue Tracking): resolve the stable error_issues.id for
    one OCCURRENCE of a problem -- the heart of "One Issue, Many
    Occurrences".

    MATCHING: previously (Phase 2.1), this matched on an exact string
    of (page, error_type, message) -- meaning two occurrences of the
    literal same bug, with even slightly different message text (a
    different key name, a different user's id embedded in an error,
    line numbers shifting between deployments), were treated as two
    unrelated issues, each getting its own reference number. That
    defeated the entire point of issue tracking: if 200 people hit the
    same underlying bug, they should all see the SAME reference
    number, not 200 different ones.

    Matching now uses a DIAGNOSTIC FINGERPRINT (see
    services/issue_fingerprint.py:build_fingerprint) built from Root
    Cause Classification + Exception Type + Operation (which function
    in our own code failed) + Page + a normalized Traceback Signature
    (the sequence of our own code's frames, with line numbers and all
    dynamic content stripped out). The exception message itself is
    deliberately EXCLUDED from matching -- it's the least stable part
    and comparing on it is exactly the old, fragile approach.

    Legacy rows written before this phase have no fingerprint (NULL) --
    matching NEVER falls back to comparing against those by signature
    here, so an old un-fingerprinted issue simply won't re-match a new
    occurrence; the new occurrence gets its own, correctly-fingerprinted
    issue going forward. This is intentional: silently guessing at a
    fingerprint for an old row from its stored (page, error_type,
    message) alone would risk merging two issues that only coincidentally
    share those three fields.

    REOPENING behavior (Phase 4) is unchanged: if the matched issue was
    previously Fixed/Closed, this occurrence is a genuine recurrence --
    status becomes 'Recurred' and the previous resolution is snapshotted
    (see services/case_knowledge.py:snapshot_resolution_on_reopen)
    before anything is overwritten. Otherwise the match is just folded
    in silently: occurrence_count +1, last_seen refreshed.

    Also updates the issue's Affected User Count (see
    _record_affected_user) every time, on both the match and create
    paths.

    title_override / root_cause_hint (Phase 3, Reflection Generation):
    let a caller that already knows more than a generic
    (page, error_type, message, traceback) would reveal -- e.g.
    rdi/orchestrator.py, which classifies ALL 8 companions' failures
    into one dominant Reflection-Generation-specific root cause via
    services/issue_fingerprint.py:classify_reflection_failure_root_cause
    -- supply that directly instead of it being (re)derived generically.
    Both are optional and additive; every other caller is unaffected.

    Never raises. Returns None if the database work fails, in which
    case the caller (log_error) simply proceeds without issue linking
    -- the individual error_log row is still written either way, so an
    issue-linking failure never loses the underlying error record.
    """
    from services.issue_fingerprint import build_fingerprint
    from services.diagnostics import categorize_error, build_error_summary

    fp = build_fingerprint(page, error_type, message, traceback_text, root_cause_hint=root_cause_hint)
    fingerprint = fp["fingerprint"]
    root_cause = fp["root_cause"]
    operation = fp["operation"]
    category = categorize_error(error_type, message, traceback_text)
    title = title_override or _build_issue_title(category, error_type, page, operation)
    summary = build_error_summary(page, category, error_type, message)
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
                WHERE fingerprint = %s
                ORDER BY id DESC LIMIT 1
                """,
                (fingerprint,),
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
                        (signature, fingerprint, status, severity, page, error_type, message,
                         title, category, root_cause_classification, summary,
                         occurrence_count, first_seen, last_seen)
                    VALUES (%s, %s, 'New', %s, %s, %s, %s, %s, %s, %s, %s, 1, %s, %s)
                    RETURNING id
                    """,
                    (signature, fingerprint, severity, page, error_type, message,
                     title, category, root_cause, summary, now, now),
                )
                issue_id = c.fetchone()[0]

            _record_affected_user(c, issue_id, user_name)
        conn.commit()
    except Exception:
        if conn is not None:
            try:
                conn.rollback()
            except Exception:
                pass
        logger.exception("_get_or_create_issue FAILED for fingerprint=%r", fingerprint)
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
              user_name="", user_role="", context=None, severity="error",
              traceback_unavailable_reason=None,
              title_override=None, root_cause_hint=None):
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

    traceback_unavailable_reason: pass this whenever traceback_text is
    empty AND you know specifically why (e.g. "the API call returned
    an unparseable response rather than raising an exception") -- see
    services/diagnostics.py:build_diagnostic_package for the full
    explanation. If omitted, a generic reason is used instead; the
    Traceback section of the AI prompt is never simply blank.

    title_override / root_cause_hint (Phase 3, Reflection Generation):
    optional -- see services/error_log.py:_get_or_create_issue's
    docstring. Used by rdi/orchestrator.py so that "Reflection
    Generation Failed" / "Partial Reflection Generation" issues get a
    spec-mandated title and are grouped by root cause rather than by
    which of the 8 companions happened to fail.

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
        issue_id = _get_or_create_issue(
            page, error_type, message, severity,
            traceback_text=traceback_text, user_name=user_name,
            title_override=title_override, root_cause_hint=root_cause_hint,
        )

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
            issue_id=issue_id,
            traceback_unavailable_reason=traceback_unavailable_reason,
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
                       ei.status, ei.occurrence_count, ei.first_seen, ei.last_seen,
                       ei.title, ei.category, ei.root_cause_classification,
                       ei.summary, ei.affected_user_count
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
         issue_first_seen, issue_last_seen,
         issue_title, issue_category, issue_root_cause,
         issue_summary, issue_affected_user_count) = row
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
            # Phase 2 (Issue Tracking): the rest of the Issue object --
            # None for rows that predate this phase or aren't
            # issue-linked (same NULL-means-"not available yet" pattern
            # as the fields above).
            "issue_title": issue_title,
            "issue_category": issue_category,
            "issue_root_cause": issue_root_cause,
            "issue_summary": issue_summary,
            "issue_affected_user_count": issue_affected_user_count,
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


# Evidence collection -- including compute_ai_readiness, the "how
# complete is this diagnostic evidence" score -- now lives entirely in
# services/diagnostics.py (imported above), per the diagnostic engine's
# architecture: diagnostics.py collects evidence and builds the
# diagnostic object; this module only logs/stores it and assigns issue
# information. `compute_ai_readiness` is still importable from
# services.error_log (as it always was) purely so existing callers
# (e.g. pages/system_administration.py) don't need to change.


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

    # Prefer the evidence summary already computed once, at build
    # time, by services/diagnostics.py -- fall back to recomputing it
    # only for older records logged before that field existed, so
    # this never breaks for pre-existing data.
    evidence_summary = package.get("evidence_summary")
    if evidence_summary and evidence_summary.get("presence"):
        score = evidence_summary.get("score", 0)
        evidence_lines = "\n".join(
            f"{'✓' if item.get('present') else '✗'} {item.get('label')}"
            for item in evidence_summary["presence"]
        )
    else:
        score, presence = compute_ai_readiness(package)
        evidence_lines = "\n".join(
            f"{'✓' if is_present else '✗'} {key}" for key, is_present in presence
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

    # Similar Previous Issues (Phase 5): reuses the same simplified list
    # already computed once, when the package was built (see
    # services/diagnostics.py:_collect_similar_issues), which itself just
    # calls services/case_knowledge.py:find_similar_issues() -- the same
    # heuristics used by System Administration > AI Diagnostic Centre.
    # No separate lookup happens here.
    similar_issues = package.get("similar_issues") or []
    if similar_issues:
        similar_lines = "\n".join(
            f"#{s['issue_id']} ({s.get('status') or 'unknown status'})"
            for s in similar_issues
        )
    else:
        similar_lines = "No similar previous issues found."

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
Similar Previous Issues

{similar_lines}

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


def render_application_error_screen(T, issue_id, error_id=None):
    """
    Renders the SAME calm "Something went wrong on this page" message,
    with the stable Issue Reference Number, that error_boundary()
    below shows when it catches an unexpected exception.

    Exists as its own function (Phase 3, Reflection Generation) for
    callers that detect and log a failure WITHOUT an exception ever
    being raised/caught -- e.g. rdi/orchestrator.py's Complete Failure
    case (every one of the 8 companions failed). That path already has
    everything error_boundary would want (a representative traceback,
    root cause, full evidence) and calls log_error() itself so none of
    that evidence is lost -- it just needs the exact same on-screen
    result the person would see from any other unexpected error, which
    this provides without going through error_boundary a second time
    (which would also log a SECOND, less-informative record for the
    same failure).

    issue_id: the stable issue reference to show (see log_error).
    error_id: shown only as a fallback if issue_id is None (issue
    linking itself failed, but the occurrence was still logged).
    """
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
        render_application_error_screen(T, issue_id, error_id)