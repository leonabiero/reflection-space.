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
from services.db_time import now_utc, get_logger, get_recent_log_entries
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
    Returns a small list of {"issue_id", "status"} dicts for issues that
    look similar to this one -- or an empty list if there's no stable
    issue_id yet (e.g. user-submitted reports, which are never grouped),
    or if anything about the lookup fails. Never raises.
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
            {"issue_id": c["issue_id"], "status": c.get("status")}
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


def _is_sensitive_key(key):
    lowered = key.lower()
    return any(marker in lowered for marker in _SENSITIVE_KEY_MARKERS)


def collect_session_context():
    """
    Returns a small, flat dict of the CURRENT Streamlit session_state,
    filtered down to values that are actually useful for diagnosing a
    problem -- never the raw, complete session_state.

    Exclusion rules (a key is left out entirely if any apply):
      - its name contains a sensitive marker (password, api_key,
        token, secret, auth, cookie, etc. -- see
        _SENSITIVE_KEY_MARKERS above)
      - it matches a known structurally-unhelpful key (e.g. internal
        diagnostic-timeline bookkeeping)
      - its value can't be safely turned into a short string at all

    Every value that IS included is stringified and truncated to
    _MAX_SESSION_VALUE_LENGTH characters, so this can never smuggle a
    large amount of text (e.g. full case/draft content) into a
    diagnostic package.

    Never raises -- returns an empty dict if session_state isn't
    available for any reason.
    """
    clean = {}
    try:
        for key, value in st.session_state.items():
            if _is_sensitive_key(key):
                continue
            if any(key.startswith(p) for p in _EXCLUDED_KEY_PREFIXES):
                continue
            try:
                text = str(value)
            except Exception:
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
            "voyage_api_key_configured": bool(getattr(config, "VOYAGE_API_KEY", "")),
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
    if "qdrant" in haystack or "voyage" in haystack or "embedding" in haystack:
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
    config_values: dict = field(default_factory=dict)
    environment: dict = field(default_factory=dict)
    recent_log_entries: list = field(default_factory=list)
    navigation_timeline: list = field(default_factory=list)
    additional_context: Optional[dict] = None
    similar_issues: list = field(default_factory=list)
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
    from an already-assembled DiagnosticPackage. This is a NEW,
    separate prompt from services/error_log.py:build_ai_prompt() (the
    one used TODAY on the System Administration > Error Log page) --
    that function is untouched, and this one is not used anywhere
    visible yet. It exists now so a later phase can surface it without
    any change to how it's built.
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
    lines.append(pkg.summary)
    lines.append(f"Category: {pkg.category}")
    lines.append(f"Severity: {pkg.severity}")
    lines.append(f"When: {pkg.timestamp}")
    lines.append(f"Page: {pkg.page}")
    lines.append(f"User: {pkg.user or 'unknown'} (role: {pkg.role or 'unknown'})")

    if pkg.exception_type or pkg.exception_message:
        lines.append("")
        lines.append("=== Exception ===")
        lines.append(f"Type: {pkg.exception_type}")
        lines.append(f"Message: {pkg.exception_message}")

    if pkg.traceback:
        lines.append("")
        lines.append("=== Full traceback ===")
        lines.append(pkg.traceback)

    lines.append("")
    lines.append("=== Environment ===")
    lines.append(f"App version: {pkg.app_version}")
    lines.append(f"Python version: {pkg.python_version}")
    lines.append(f"Operating system: {pkg.operating_system}")
    lines.append(f"Browser: {pkg.browser or 'not available'}")
    for k, v in (pkg.environment or {}).items():
        lines.append(f"{k}: {v}")

    if pkg.config_values:
        lines.append("")
        lines.append("=== Relevant configuration (no secrets included) ===")
        for k, v in pkg.config_values.items():
            lines.append(f"{k}: {v}")

    if pkg.session_context:
        lines.append("")
        lines.append("=== Relevant session state (filtered, no secrets) ===")
        for k, v in pkg.session_context.items():
            lines.append(f"{k}: {v}")

    if pkg.navigation_timeline:
        lines.append("")
        lines.append("=== Recent activity leading up to this (oldest first) ===")
        for entry in pkg.navigation_timeline:
            piece = f"- {entry.get('at')}: {entry.get('event')}"
            if entry.get("page"):
                piece += f" (page: {entry['page']})"
            if entry.get("detail"):
                piece += f" -- {entry['detail']}"
            lines.append(piece)

    if pkg.recent_log_entries:
        lines.append("")
        lines.append("=== Recent application log lines ===")
        lines.extend(pkg.recent_log_entries)

    if pkg.additional_context:
        lines.append("")
        lines.append("=== Additional context ===")
        for k, v in pkg.additional_context.items():
            lines.append(f"{k}: {v}")

    if pkg.similar_issues:
        lines.append("")
        lines.append("=== Similar previous issues ===")
        for s in pkg.similar_issues:
            lines.append(f"#{s['issue_id']} -- {s.get('status') or 'unknown status'}")
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
):
    """
    The one entry point every other part of the app should use:
    "Build me a diagnostic package."

    Gathers technical evidence, sanitizes it (see
    collect_session_context above), and returns a fully-populated
    DiagnosticPackage -- including a ready-to-paste AI prompt
    (package.ai_prompt).

    issue_id: the stable issue reference for this problem, if one
    already exists (services/error_log.py:log_error resolves this
    BEFORE calling here). Optional and additive -- used only to look
    up "Similar Previous Issues" via the existing
    services/case_knowledge.py:find_similar_issues() heuristics
    (Phase 5). None for user-submitted reports, which are never
    grouped into a stable issue and so never get a similar-issues
    list here -- same as the existing System Administration panel.

    Never raises. If anything here fails, a minimal-but-valid package
    describing the failure is returned instead, so a broken diagnostic
    build can never be the reason logging an error fails.
    """
    try:
        category = _categorize(error_type, message, traceback_text)
        environment = _collect_environment()
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
            config_values=_collect_config_values(),
            environment=environment,
            recent_log_entries=get_recent_log_entries(limit=20),
            navigation_timeline=get_timeline(),
            additional_context=context if isinstance(context, dict) else None,
            similar_issues=_collect_similar_issues(
                issue_id, page, error_type, message, traceback_text
            ),
        )
        pkg.ai_prompt = _build_ai_prompt(pkg)
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
        )
        fallback.ai_prompt = _build_ai_prompt(fallback)
        return fallback