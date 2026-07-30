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

logger = get_logger(__name__)


def _get_conn():
    return _acquire_pooled_conn()


def log_error(page, error_type, message, traceback_text,
              user_name="", user_role="", context=None, severity="error",
              screenshot_b64=None):
    """
    Write one error record. Returns the new row's id on success, or
    None if writing to the database itself failed (in which case the
    error is still written to stdout via the logger, so it is never
    silently lost).

    context: an optional dict of small, non-sensitive operational
    details (e.g. {"companion": "possible_bias", "attempt": 3}) --
    stored as JSON text. Never put case/client content in here.

    screenshot_b64: optional data-URL string ("data:image/jpeg;base64,...")
    captured by components/screenshot_reporter -- only ever populated
    for user-submitted reports (see log_user_report below); automatic
    crash detection has no screenshot to attach.
    """
    context_json = ""
    if context:
        try:
            context_json = json.dumps(context, default=str)
        except Exception:
            context_json = str(context)

    conn = None
    new_id = None
    try:
        conn = _get_conn()
        with conn.cursor() as c:
            c.execute("""
                INSERT INTO error_log
                    (occurred_at, page, error_type, message, traceback,
                     user_name, user_role, context, severity, screenshot)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (
                now_utc(), page, error_type, message, traceback_text,
                user_name, user_role, context_json, severity, screenshot_b64,
            ))
            new_id = c.fetchone()[0]
        conn.commit()
        logger.error(
            "Logged error #%s page=%r type=%r message=%r",
            new_id, page, error_type, message,
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
        }
        send_alert_email(
            subject=f"[Reflection Space] Error on {page} (#{new_id})",
            body_text=build_email_summary(record),
            screenshot_b64=screenshot_b64,
        )

    return new_id


def log_user_report(page, description, user_name="", user_role="", screenshot_b64=None):
    """
    Records a report submitted through the "Report a problem" sidebar
    widget (services/report_widget.py). Always sends an email alert --
    a person deliberately flagged this, unlike an automatically
    detected error, which only emails for severity == "error".
    """
    new_id = log_error(
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
    }
    send_alert_email(
        subject=f"[Reflection Space] Problem reported on {page}"
                + (f" (#{new_id})" if new_id else ""),
        body_text=build_email_summary(record),
        screenshot_b64=screenshot_b64,
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
            c.execute("""
                SELECT id, occurred_at, page, error_type, message,
                       traceback, user_name, user_role, context, severity,
                       screenshot
                FROM error_log
                ORDER BY occurred_at DESC
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
    for row in iso_row_list(rows, [1]):
        (rid, occurred_at, page, error_type, message, tb,
         user_name, user_role, context, severity, screenshot) = row
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
        })
    return records


def iso_row_list(rows, date_indexes):
    """Small local helper: apply services.db_time.iso_row across a
    list of rows. Kept here (rather than importing a plural helper
    that doesn't exist in db_time.py) to avoid touching that shared
    module for a one-line convenience."""
    return [iso_row(row, date_indexes) for row in rows]


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
    screenshot_note = (
        "\nA screenshot is attached." if record.get("screenshot")
        else "\nNo screenshot was captured for this report."
    )
    return f"""A problem was reported in Reflection Space.

Page: {record.get('page')}
When: {record.get('occurred_at')}
Reported by (role): {record.get('user_role') or 'unknown'}
Description: {record.get('message')}{ctx_line}{screenshot_note}

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
        error_id = log_error(
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

        ref = f"#{error_id}" if error_id is not None else "(not saved -- see app logs)"
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