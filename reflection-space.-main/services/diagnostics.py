"""
Diagnostic Engine (Phase 1)
==============================

Purpose
---------
This is the single, shared source of truth for turning "something went
wrong" (an automatic Python exception, or a person clicking "Report a
problem") into a complete, structured AI Diagnostic Package -- gathered
automatically, behind the scenes, every single time.

Nothing in this module is shown to anyone yet. It is deliberately
independent of:
  - the UI (nothing here calls st.error / st.write / renders anything)
  - email formatting (services/email_alert.py knows nothing about the
    shape of this module -- it just sends whatever text body it's
    given; services/error_log.py:build_diagnostic_report_email is the
    one place that turns a DiagnosticPackage into the actual email
    text)
  - the Error Log page (pages/system_administration.py is untouched --
    it still calls services/error_log.py:build_ai_prompt exactly as it
    always has)

Other parts of the app are meant to use this module in exactly one
way: ask it to build a package.

    from services.diagnostics import build_diagnostic_package

    package = build_diagnostic_package(
        page="reflection_space",
        error_type="ValueError",
        message="...",
        traceback_text="...",
        user_name="...",
        user_role="Practitioner",
        severity="error",
    )
    json_text = package.to_json()

services/error_log.py:log_error() is currently the ONLY caller (see
that module) -- because log_user_report() already routes every
user-submitted report through log_error() internally, hooking in there
is enough to cover BOTH triggers described in the Phase 1 spec
(automatic exceptions and manual reports) from one place, with no
changes needed anywhere else.

Where the package is stored
------------------------------
services/error_log.py stores the package's JSON (package.to_json())
in error_log.diagnostic_package -- a new, additive column (see
services/db_schema.py). Nothing reads that column yet; that is
intentionally left for a later phase (displaying it on the Error Log
page). This module has no knowledge of, and no dependency on, that
storage decision -- it just returns a DiagnosticPackage object that is
trivial to serialize.

What's collected, and what's deliberately excluded
-------------------------------------------------------
See collect_session_context() below for the session_state filtering
rules, and _collect_config_values() for why only non-secret,
boolean/summary config values are ever included -- never a real API
key, password, or connection string.
"""

import json
import os
import platform
import sys
from dataclasses import asdict, dataclass, field
from typing import Optional

import streamlit as st

import config
from services.db_time import now_utc, get_logger
from services.evidence_timeline import get_timeline
from services.case_knowledge import find_similar_issues

logger = get_logger(__name__)

# Similar Previous Issues (Phase 5)
# -----------------------------------
# Deliberately tiny: reuses services/case_knowledge.py:find_similar_issues()
# -- the SAME heuristic matching already used by System Administration >
# AI Diagnostic Centre -- as the one and only source of truth for "have we
# seen this before?". Nothing here re-implements or extends that matching
# logic; this module only trims the result down to the two fields (issue
# id + status) that belong in a plain-text AI prompt / email, on purpose,
# so there is never a second, different-looking list of "similar issues"
# anywhere in the app.
_SIMILAR_ISSUES_LIMIT = 5


def _collect_similar_issues(issue_id, page, error_type, message, traceback_text):
    """
    Returns a small list of {"issue_id", "status", "occurrence_count",
    "last_seen"} dicts for issues that look similar to this one -- or
    an empty list if there's no stable issue_id yet (e.g. user-
    submitted reports, which are never grouped), or if anything about
    the lookup fails. Never raises.

    occurrence_count and last_seen are carried straight through from
    services/case_knowledge.py:find_similar_issues() (which already
    computes both) so the AI prompt and email can show, at a glance,
    whether a similar-looking issue is a one-off or something that
    keeps recurring -- not just its bare reference number and status.
    """
    if not issue_id:
        return []
    try:
        candidates = find_similar_issues(
            issue_id, page, error_type, message,
            traceback_text=traceback_text or "",
            limit=_SIMILAR_ISSUES_LIMIT,
        )
        return [
            {
                "issue_id": c["issue_id"],
                "status": c.get("status"),
                "occurrence_count": c.get("occurrence_count"),
                "last_seen": c.get("last_seen"),
            }
            for c in candidates
        ]
    except Exception:
        logger.exception("_collect_similar_issues failed (non-fatal)")
        return []


# ---------------------------------------------------------------------
# session_state filtering
# ---------------------------------------------------------------------
#
# Do NOT dump the entire session_state -- only collect small, useful,
# clearly non-sensitive values. Anything whose KEY NAME contains one of
# these markers (case-insensitive substring match, deliberately broad)
# is excluded entirely, regardless of its value or type.
_SENSITIVE_KEY_MARKERS = (
    "password",
    "passwd",
    "pwd",
    "secret",
    "token",
    "api_key",
    "apikey",
    "auth",
    "credential",
    "cookie",
    "private_key",
    "connection_string",
    "database_url",
    "smtp",
)

# Streamlit-internal / structurally unhelpful keys that are never
# useful in a diagnostic prompt (large opaque objects, per-widget
# plumbing) -- excluded by exact name or prefix, separately from the
# sensitive-marker filter above.
_EXCLUDED_KEY_PREFIXES = ("_diagnostic_",)

# Any single session_state value is truncated to this many characters
# once stringified, so one large object (e.g. a full draft's text)
# can never bloat the package or leak substantial case content into an
# AI prompt.
_MAX_SESSION_VALUE_LENGTH = 200

# ---------------------------------------------------------------------
# Quality pass (post-Phase 5): what's ACTUALLY diagnostic
# ---------------------------------------------------------------------
#
# Reflection Space has hundreds of Streamlit widget keys in total --
# one per button, form field, checkbox, and expander, most of them
# scoped to one specific item with a dynamic suffix (e.g.
# "case_ref_3", "delete_pending_182", "_report_send_button",
# "save_status", "doc_reset"). None of that is ever useful for
# diagnosing a specific error: it's UI plumbing (button click flags,
# per-row toggles, form-reset counters), not information about what
# the person was doing or what state the app was in.
#
# Rather than trying to blocklist every one of those dynamic keys
# individually (an endless, fragile game of whack-a-mole as new
# widgets get added), this switches the model around: only the small,
# fixed set of SINGLETON session values below -- the ones that
# describe who the person is and what part of the app they were in,
# not which specific button they clicked -- are ever included. Every
# widget-plumbing key, by construction, is simply not on this list and
# is therefore excluded, with zero maintenance needed as new widgets
# are added elsewhere in the app.
_USEFUL_SESSION_KEYS = (
    "user_name",
    "user_role",
    "active_work_mode",
    "previous_work_mode",
    "lang",
    # True only while a reflection/companion call is actually running --
    # genuinely useful to know if an error happened mid-generation.
    "_generating_reflection",
    # True only right after the Anthropic API returned a 429 -- directly
    # relevant if the error itself turns out to be a Rate Limit.
    "_rate_limit_hit",
)


def _is_sensitive_key(key):
    lowered = key.lower()
    return any(marker in lowered for marker in _SENSITIVE_KEY_MARKERS)


def collect_session_context():
    """
    Returns a small, flat dict of CURRENT Streamlit session_state
    values that can realistically help diagnose a problem -- never the
    raw, complete session_state.

    Only keys in _USEFUL_SESSION_KEYS above are ever included (an
    allowlist, not a blocklist) -- see that constant's comment for why.
    A key is still skipped even if it's on the allowlist if:
      - its name contains a sensitive marker (password, api_key,
        token, secret, auth, cookie, etc. -- see
        _SENSITIVE_KEY_MARKERS above) -- defence in depth, since none
        of the allowlisted keys are sensitive today, but this keeps
        that guarantee even if the list changes later
      - it isn't actually present in session_state this run
      - its value is empty/blank, since an empty value never helps
        diagnose anything
      - its value can't be safely turned into a short string at all

    Every value that IS included is stringified and truncated to
    _MAX_SESSION_VALUE_LENGTH characters, so this can never smuggle a
    large amount of text into a diagnostic package.

    Never raises -- returns an empty dict if session_state isn't
    available for any reason.
    """
    clean = {}
    try:
        for key in _USEFUL_SESSION_KEYS:
            if key not in st.session_state:
                continue
            if _is_sensitive_key(key):
                continue
            if any(key.startswith(p) for p in _EXCLUDED_KEY_PREFIXES):
                continue
            value = st.session_state[key]
            try:
                text = str(value)
            except Exception:
                continue
            if not text.strip():
                continue
            if len(text) > _MAX_SESSION_VALUE_LENGTH:
                text = text[:_MAX_SESSION_VALUE_LENGTH] + "...(truncated)"
            clean[key] = text
    except Exception:
        logger.exception("collect_session_context failed (non-fatal)")
    return clean


# ---------------------------------------------------------------------
# Configuration / environment snapshots
# ---------------------------------------------------------------------
#
# Only ever booleans ("is this configured?") or small non-secret
# numbers/labels -- never an actual key, password, or connection
# string value.
def _collect_config_values():
    try:
        return {
            "app_name": getattr(config, "APP_NAME", ""),
            "app_version": getattr(config, "APP_VERSION", "unspecified"),
            "anthropic_api_key_configured": bool(getattr(config, "ANTHROPIC_API_KEY", "")),
            "gemini_api_key_configured": bool(getattr(config, "GEMINI_API_KEY", "")),
            "embedding_model": getattr(config, "EMBEDDING_MODEL", ""),
            "embedding_dimensions": getattr(config, "EMBEDDING_DIMENSIONS", None),
            "qdrant_configured": bool(getattr(config, "QDRANT_URL", "")),
            "database_configured": bool(getattr(config, "DATABASE_URL", "")),
            "email_alerts_configured": bool(getattr(config, "SMTP_HOST", "")) and bool(getattr(config, "ALERT_EMAIL_TO", "")),
            "db_pool_min_conn": getattr(config, "DB_POOL_MIN_CONN", None),
            "db_pool_max_conn": getattr(config, "DB_POOL_MAX_CONN", None),
        }
    except Exception:
        logger.exception("_collect_config_values failed (non-fatal)")
        return {}


def _collect_environment():
    try:
        return {
            "python_version": platform.python_version(),
            "os": f"{platform.system()} {platform.release()}".strip(),
            "platform_detail": platform.platform(),
            "streamlit_version": getattr(st, "__version__", "unknown"),
        }
    except Exception:
        logger.exception("_collect_environment failed (non-fatal)")
        return {}


def _detect_browser():
    """
    Best-effort browser identification. Reflection Space does not
    currently capture the browser's user agent anywhere, so this is
    None for now. Left as an explicit field/hook so a later phase can
    populate it without any change to the shape of the diagnostic
    package.
    """
    return None


# ---------------------------------------------------------------------
# Categorization
# ---------------------------------------------------------------------
def _categorize(error_type, message, traceback_text):
    if error_type == "UserReport":
        return "User-reported issue"

    haystack = " ".join(
        str(x).lower() for x in (error_type, message, traceback_text) if x
    )

    if "psycopg2" in haystack or "database" in haystack:
        return "Database"
    if "anthropic" in haystack or "claude" in haystack:
        return "AI / Claude API"
    if "qdrant" in haystack or "gemini" in haystack or "embedding" in haystack:
        return "Retrieval / Embeddings"
    if "smtp" in haystack or "email" in haystack:
        return "Email"
    if "timeout" in haystack or "connection" in haystack:
        return "Network / Connectivity"
    if "permission" in haystack or "unauthorized" in haystack or "auth" in haystack:
        return "Authentication / Permissions"
    return "Application Error"


def _build_summary(page, category, error_type, message):
    if error_type == "UserReport":
        return f"A user submitted a problem report on the '{page}' page."
    return (
        f"An automatic exception ({error_type or 'unknown type'}) occurred "
        f"on the '{page}' page. Category: {category}."
    )


# Public wrappers -- Phase 2 (Issue Tracking / services/issue_fingerprint.py)
# reuses these EXACT SAME functions for an Issue's "Category" and "Summary"
# fields, so an issue's category is always identical to the category shown
# in its own occurrences' AI prompts -- one source of truth, not two
# categorizers that could drift apart.
def categorize_error(error_type, message, traceback_text):
    return _categorize(error_type, message, traceback_text)


def build_error_summary(page, category, error_type, message):
    return _build_summary(page, category, error_type, message)


# ---------------------------------------------------------------------
# Evidence summary
# ---------------------------------------------------------------------
#
# Fixed, documented order for the "Evidence Collected" checklist and
# the AI Readiness Score. Each entry is (internal_key, display_label).
# Moved here from services/error_log.py so that evidence collection --
# including this completeness summary -- lives entirely in one place
# (this module), per the Phase 1 architecture: diagnostics.py collects
# evidence and builds the diagnostic object; error_log.py only logs/
# stores it and assigns issue information; email_alert.py only renders.
# services/error_log.py still exposes `compute_ai_readiness` (it just
# imports it from here) so nothing that already calls
# `from services.error_log import compute_ai_readiness` needs to change.
_AI_READINESS_CATEGORIES = (
    ("exception", "Exception"),
    ("traceback_evidence", "Traceback"),
    ("root_cause", "Root Cause"),
    ("timeline", "Timeline"),
    ("session_context", "Session Context"),
    ("environment", "Environment"),
    ("user_information", "User Information"),
    ("configuration", "Configuration"),
    # The AI prompt itself is part of the diagnostic package handed to
    # Claude/ChatGPT -- its presence is evidence just like a traceback
    # or a timeline is, so it belongs on the same checklist.
    ("ai_prompt", "AI Prompt Generated"),
)


def compute_ai_readiness(package):
    """
    A plain completeness score -- NOT an AI judgement of anything, and
    NOT a measure of severity -- based only on how many of 9 fixed
    evidence categories are present in an already-parsed diagnostic
    package (a dict, e.g. DiagnosticPackage.to_dict() or a package
    parsed back out of storage).

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
        explaining that no traceback exists -- that placeholder is
        not technical evidence, so it must never count toward the
        score or be confused with a genuine traceback.
      - Root Cause (Phase 5): root_cause is set AND this wasn't a
        user-submitted report -- same reasoning as Traceback above;
        there's no exception to classify a root cause from.
      - Timeline: navigation_timeline is a non-empty list
      - Session Context: session_context is a non-empty dict
      - Environment: environment is a non-empty dict, OR
        python_version / operating_system is set
      - User Information: user or role is set
      - Configuration: config_values is a non-empty dict
      - AI Prompt Generated: ai_prompt is a non-empty string -- the
        prompt itself is part of the diagnostic package, so its
        presence counts as evidence collected too

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
        "root_cause": bool(package.get("root_cause")) and not is_user_report,
        "timeline": bool(package.get("navigation_timeline")),
        "session_context": bool(package.get("session_context")),
        "environment": bool(package.get("environment"))
        or bool(package.get("python_version"))
        or bool(package.get("operating_system")),
        "user_information": bool(package.get("user") or package.get("role")),
        "configuration": bool(package.get("config_values")),
        "ai_prompt": bool(package.get("ai_prompt")),
    }
    presence = [(key, checks[key]) for key, _label in _AI_READINESS_CATEGORIES]
    present_count = sum(1 for _, is_present in presence if is_present)
    score = round((present_count / len(presence)) * 100)
    return score, presence


def _build_evidence_summary(package_dict):
    """
    Runs compute_ai_readiness() once, at build time, and reshapes it
    into the plain-dict form stored on DiagnosticPackage.evidence_summary
    (see that field's docstring). Never raises.
    """
    try:
        score, presence = compute_ai_readiness(package_dict)
        return {
            "score": score,
            "presence": [
                {"key": key, "label": T_label, "present": is_present}
                for (key, T_label), (_key2, is_present) in zip(
                    _AI_READINESS_CATEGORIES, presence
                )
            ],
        }
    except Exception:
        logger.exception("_build_evidence_summary failed (non-fatal)")
        return {}


# ---------------------------------------------------------------------
# The package itself
# ---------------------------------------------------------------------
@dataclass
class DiagnosticPackage:
    summary: str
    category: str
    severity: str
    timestamp: str
    page: str
    user: str
    role: str
    app_version: str
    python_version: str
    operating_system: str
    browser: Optional[str]
    session_context: dict = field(default_factory=dict)
    exception_type: Optional[str] = None
    exception_message: Optional[str] = None
    traceback: Optional[str] = None
    # If `traceback` is empty/None, this ALWAYS explains why -- see
    # build_diagnostic_package's docstring and _build_ai_prompt below.
    # A missing traceback must never just be silently absent; the
    # reason it's missing is itself diagnostic information.
    traceback_unavailable_reason: Optional[str] = None
    config_values: dict = field(default_factory=dict)
    environment: dict = field(default_factory=dict)
    navigation_timeline: list = field(default_factory=list)
    additional_context: Optional[dict] = None
    similar_issues: list = field(default_factory=list)
    # Root Cause Classification (see services/issue_fingerprint.py) --
    # Phase 5: previously computed for fingerprinting/issue-matching in
    # services/error_log.py:_get_or_create_issue and then discarded.
    # Now carried through here so it's part of the one canonical
    # object every consumer (AI prompt, email, admin page) reads, the
    # same way issue_number already is. None for user-submitted
    # reports (there's no exception to classify) -- the AI prompt and
    # email both say so explicitly rather than omitting the section.
    root_cause: Optional[str] = None
    # The stable issue/reference number (services/error_log.py's
    # error_issues.id) for this problem, if one exists yet -- None for
    # user-submitted reports (never issue-linked) or if issue linking
    # itself failed. Resolved by error_log.py BEFORE this package is
    # built and simply carried through here so it's part of the one
    # canonical object, instead of being bolted on separately by each
    # consumer (email, AI prompt, admin page).
    issue_number: Optional[int] = None
    # Standardized evidence-completeness summary (see
    # compute_ai_readiness below) -- computed once, here, at build
    # time, so every consumer (email, AI prompt, admin page) reads the
    # SAME evidence summary instead of each recomputing its own.
    # {"score": int 0-100, "presence": [{"key", "label", "present"}, ...]}
    evidence_summary: dict = field(default_factory=dict)
    ai_prompt: str = ""

    def to_dict(self):
        return asdict(self)

    def to_json(self):
        try:
            return json.dumps(self.to_dict(), default=str)
        except Exception:
            logger.exception("DiagnosticPackage.to_json failed (non-fatal)")
            return "{}"


def _build_ai_prompt(pkg: DiagnosticPackage):
    """
    Builds a complete, ready-to-paste-into-Claude-or-ChatGPT prompt
    from an already-assembled DiagnosticPackage. This is the ONE AI
    prompt builder used for every unexpected exception, regardless of
    where it originated -- services/error_log.py:build_ai_prompt() is
    a separate, older function kept only as a display fallback for
    records written before this engine existed (see
    pages/system_administration.py); it is never used for anything
    logged through build_diagnostic_package().

    Deliberately concise: only information that materially helps
    diagnose the error. Two things this DOES NOT include on purpose,
    even though one of them is still collected and stored on the
    package itself (for the database record and the full email
    report):
      - Environment / app version / config values -- rarely relevant
        to one specific error, and mostly unchanging noise. (Still
        collected and shown on the admin Error Log page, since it's
        occasionally useful there -- just never in the prompt.)
      - Raw recent application log lines -- Phase 1 originally
        collected up to 20 of these per error (services/db_time.py's
        process-wide rolling buffer), but that buffer mixes in
        unrelated output from anywhere in the process at the same
        moment -- schema-migration logs, startup logs, other
        sessions' activity -- none of which is scoped to THIS error.
        It was never rendered anywhere (not this prompt, not the
        email, not the admin page), so Phase 5 removed the collection
        entirely rather than just filtering it out here.

    There is NEVER a version of this prompt without a Traceback
    section -- see the "if pkg.traceback" branch below. If no
    traceback exists, the section says so explicitly, with a reason,
    instead of being silently omitted. Root Cause (below) follows the
    same rule: always its own section, with an explicit reason when
    no classification exists (e.g. user-submitted reports), never
    just omitted.
    """
    lines = []
    lines.append(
        "I'm the non-developer owner of a Streamlit app called \"Reflection "
        "Space\" (built entirely with AI assistance). Please explain what "
        "went wrong in plain language BEFORE giving me any fix, and if you "
        "do give me a fix, give me the COMPLETE contents of any file that "
        "needs to change (not a snippet or a diff)."
    )
    lines.append("")
    lines.append("=== Summary ===")
    lines.append(f"Issue Number: {pkg.issue_number if pkg.issue_number is not None else 'not yet assigned'}")
    lines.append(f"Category: {pkg.category}")
    lines.append(f"Severity: {pkg.severity}")
    lines.append(f"Page: {pkg.page}")
    lines.append(f"User: {pkg.user or 'unknown'}")
    lines.append(f"Role: {pkg.role or 'unknown'}")
    lines.append(f"Timestamp: {pkg.timestamp}")

    lines.append("")
    lines.append("=== Exception ===")
    lines.append(f"Type: {pkg.exception_type or 'unknown'}")
    lines.append(f"Message: {pkg.exception_message or 'unknown'}")

    # Full Traceback -- ALWAYS present, never silently omitted. See
    # DiagnosticPackage.traceback_unavailable_reason's docstring.
    lines.append("")
    lines.append("=== Full Traceback ===")
    if pkg.traceback:
        lines.append(pkg.traceback)
    else:
        lines.append("Not available.")
        lines.append("")
        lines.append(
            f"Reason: {pkg.traceback_unavailable_reason or 'No reason was recorded for the missing traceback.'}"
        )

    if pkg.navigation_timeline:
        lines.append("")
        lines.append("=== Recent Timeline ===")
        for entry in pkg.navigation_timeline:
            piece = f"- {entry.get('at')}: {entry.get('event')}"
            if entry.get("page"):
                piece += f" (page: {entry['page']})"
            if entry.get("detail"):
                piece += f" -- {entry['detail']}"
            lines.append(piece)

    # Relevant Context -- the filtered session state (already
    # collected non-sensitively, see collect_session_context above)
    # plus any caller-supplied additional_context, combined into one
    # section since both are "context relevant to this one error", not
    # two different kinds of thing worth separate headers.
    if pkg.session_context or pkg.additional_context:
        lines.append("")
        lines.append("=== Relevant Context ===")
        for k, v in (pkg.session_context or {}).items():
            lines.append(f"{k}: {v}")
        for k, v in (pkg.additional_context or {}).items():
            lines.append(f"{k}: {v}")

    # Root Cause -- ALWAYS present, same rule as Traceback above: never
    # silently omitted. User-submitted reports (and, rarely, a record
    # where classification itself failed) explain why no
    # classification exists instead of the section just being absent.
    lines.append("")
    lines.append("=== Root Cause ===")
    if pkg.root_cause:
        lines.append(pkg.root_cause)
    elif pkg.exception_type == "UserReport":
        lines.append("Not classified -- this is a user-submitted report, not an automatic exception.")
    else:
        lines.append("Not classified for this occurrence.")

    if pkg.similar_issues:
        lines.append("")
        lines.append("=== Similar Previous Issues ===")
        for s in pkg.similar_issues:
            lines.append(f"Issue #{s['issue_id']}")
            occ = s.get("occurrence_count")
            lines.append(f"  Occurrences: {occ if occ is not None else 'unknown'}")
            lines.append(f"  Status: {s.get('status') or 'unknown status'}")
            lines.append(f"  Last Seen: {s.get('last_seen') or 'unknown'}")
        lines.append(
            "Review these previous investigations if they appear relevant."
        )

    lines.append("")
    lines.append(
        "Please: 1) tell me in plain non-technical language what most "
        "likely caused this, 2) tell me if you need to see any specific "
        "file's current contents to be sure, and 3) once confident, give "
        "me the complete corrected file(s), ready to save over the "
        "existing one(s)."
    )
    return "\n".join(lines)


def _default_traceback_unavailable_reason(error_type):
    """
    Used only when traceback_text is empty/None AND the caller didn't
    supply its own traceback_unavailable_reason -- i.e. as a last
    resort, so the Traceback section NEVER just says "Not available"
    with no explanation at all. Callers that know exactly why a
    traceback doesn't exist (e.g. rdi/orchestrator.py, when a
    companion call failed without raising a Python exception) should
    always pass their own, more specific reason instead.
    """
    if error_type == "UserReport":
        return (
            "This is a user-submitted problem report, not an automatic "
            "exception -- no traceback exists because no Python error was "
            "raised."
        )
    return (
        "No traceback text was provided when this event was logged, and no "
        "more specific reason was recorded."
    )


def build_diagnostic_package(
    page,
    error_type=None,
    message=None,
    traceback_text=None,
    user_name="",
    user_role="",
    severity="error",
    context=None,
    issue_id=None,
    traceback_unavailable_reason=None,
    root_cause=None,
):
    """
    The one entry point every other part of the app should use:
    "Build me a diagnostic package."

    Gathers technical evidence, sanitizes it (see
    collect_session_context above), and returns a fully-populated
    DiagnosticPackage -- including a ready-to-paste AI prompt
    (package.ai_prompt) and a standardized evidence summary
    (package.evidence_summary).

    issue_id: the stable issue reference for this problem, if one
    already exists (services/error_log.py:log_error resolves this
    BEFORE calling here). Optional and additive -- used both to look
    up "Similar Previous Issues" via the existing
    services/case_knowledge.py:find_similar_issues() heuristics, and
    to populate package.issue_number so the reference number travels
    with the rest of the diagnostic evidence. None for user-submitted
    reports, which are never grouped into a stable issue.

    root_cause: the Root Cause Classification for this occurrence (see
    services/issue_fingerprint.py), also resolved by
    services/error_log.py:log_error BEFORE calling here (it's a
    byproduct of the same fingerprinting work that resolves issue_id).
    Optional -- None for user-submitted reports, since there's no
    exception to classify. Carried straight onto package.root_cause so
    it appears as its own section in the AI prompt and email, the same
    way issue_number does.

    traceback_text: pass the ACTUAL traceback (e.g.
    traceback.format_exc()) whenever one genuinely exists. If it
    doesn't -- there was no Python exception, only a failure signal --
    pass None/empty and use traceback_unavailable_reason (below) to
    say why, rather than fabricating or omitting the traceback.

    traceback_unavailable_reason: only used when traceback_text is
    empty. Should explain, specifically, why no traceback exists for
    THIS event (e.g. "the retried API call returned an unparseable
    response rather than raising an exception"). Falls back to a
    generic reason (see _default_traceback_unavailable_reason) if the
    caller doesn't know / doesn't provide one -- but the Traceback
    section itself is NEVER simply omitted (see _build_ai_prompt).

    Never raises. If anything here fails, a minimal-but-valid package
    describing the failure is returned instead, so a broken diagnostic
    build can never be the reason logging an error fails.
    """
    try:
        category = _categorize(error_type, message, traceback_text)
        environment = _collect_environment()
        tb_reason = None
        if not traceback_text:
            tb_reason = traceback_unavailable_reason or _default_traceback_unavailable_reason(error_type)
        pkg = DiagnosticPackage(
            summary=_build_summary(page, category, error_type, message),
            category=category,
            severity=severity or "error",
            timestamp=now_utc().isoformat(),
            page=page or "",
            user=user_name or "",
            role=user_role or "",
            app_version=getattr(config, "APP_VERSION", "unspecified"),
            python_version=platform.python_version(),
            operating_system=f"{platform.system()} {platform.release()}".strip(),
            browser=_detect_browser(),
            session_context=collect_session_context(),
            exception_type=error_type,
            exception_message=message,
            traceback=traceback_text,
            traceback_unavailable_reason=tb_reason,
            config_values=_collect_config_values(),
            environment=environment,
            navigation_timeline=get_timeline(),
            additional_context=context if isinstance(context, dict) else None,
            similar_issues=_collect_similar_issues(
                issue_id, page, error_type, message, traceback_text
            ),
            root_cause=root_cause,
            issue_number=issue_id,
        )
        # AI Prompt built BEFORE the evidence summary, deliberately --
        # the evidence checklist's "AI Prompt Generated" entry (see
        # _AI_READINESS_CATEGORIES) checks pkg.ai_prompt, so that field
        # must already be populated by the time _build_evidence_summary
        # inspects the package, or it would always show as missing.
        pkg.ai_prompt = _build_ai_prompt(pkg)
        pkg.evidence_summary = _build_evidence_summary(pkg.to_dict())
        return pkg
    except Exception:
        logger.exception("build_diagnostic_package failed (non-fatal)")
        fallback = DiagnosticPackage(
            summary=f"Diagnostic package could not be fully built for page '{page}'.",
            category="Diagnostic Engine Error",
            severity=severity or "error",
            timestamp=now_utc().isoformat(),
            page=page or "",
            user=user_name or "",
            role=user_role or "",
            app_version=getattr(config, "APP_VERSION", "unspecified"),
            python_version=platform.python_version(),
            operating_system=platform.system(),
            browser=None,
            exception_type=error_type,
            exception_message=message,
            traceback=traceback_text,
            traceback_unavailable_reason=(
                None if traceback_text else (
                    traceback_unavailable_reason
                    or "The diagnostic engine itself failed while building this "
                       "package, before a reason for the missing traceback could "
                       "be determined."
                )
            ),
            root_cause=root_cause,
            issue_number=issue_id,
        )
        fallback.ai_prompt = _build_ai_prompt(fallback)
        fallback.evidence_summary = _build_evidence_summary(fallback.to_dict())
        return fallback