"""
Evidence Timeline
====================

Phase 1 of the Diagnostic Engine redesign (see services/diagnostics.py
for the full design notes).

Purpose
---------
Keeps a short, rolling list of the last ~10-20 MEANINGFUL things that
happened in the current person's session -- which page they opened,
when they moved to a different page, when an exception was logged,
when a report was sent, when an alert email went out. When something
goes wrong, this gives the Diagnostic Engine (and, in a later phase,
the Error Log page) a small amount of "what led up to this" context,
without anything close to a full audit trail.

This is intentionally NOT:
  - a complete audit log (see services/audit_log.py for that -- this
    module has nothing to do with it and never writes to the
    database)
  - permanent history -- it lives only in st.session_state, for the
    current browser session, and is capped at _MAX_EVENTS entries
    (oldest entries fall off the front automatically)
  - a replacement for anything that already exists

Design
--------
Storage is plain st.session_state, exactly like every other piece of
per-session state already used throughout this app (e.g.
active_work_mode) -- no new infrastructure, no new database table.
Every function here is defensive: a failure to record or read the
timeline must never be the reason a page breaks, so every public
function swallows its own errors and falls back to a safe default
(recording becomes a no-op; reading returns an empty list).

Usage
-------
    from services.evidence_timeline import record_event

    record_event("Clicked Save")
    record_event("Started database operation", detail="drafts.save_draft")
    record_event("Completed database operation")

navigation/router.py already calls record_page_visit() once per page
render (inside render_nav(), which every page calls), so "Opened
page" / "Changed page" events require no per-page changes. Future
phases that want more granular events (e.g. "Clicked Save" on a
specific button) can add a single record_event(...) call at that
button's call site -- nothing here needs to change to support that.
"""

import streamlit as st

from services.db_time import now_utc, get_logger

logger = get_logger(__name__)

_TIMELINE_SESSION_KEY = "_diagnostic_evidence_timeline"
_LAST_PAGE_SESSION_KEY = "_diagnostic_evidence_last_page"

# Keep roughly the last 10-20 significant events, per the Phase 1 spec.
# Capped a little above 20 internally isn't necessary -- we trim to
# exactly this many on every write.
_MAX_EVENTS = 20


def record_event(event_type, detail=None, page=None):
    """
    Append one lightweight event to the current session's evidence
    timeline. Never raises -- if session_state isn't available for any
    reason (e.g. called outside a real Streamlit run), this is
    silently a no-op.

    event_type: short, human-readable label, e.g. "Opened page",
        "Clicked Save", "Exception occurred". Keep these consistent
        and short -- they're meant to read like a short activity log,
        not a technical message.
    detail: optional short free-text detail (truncated defensively --
        this is NOT the place for large payloads or case content).
    page: optional page name, recorded alongside the event when known.
    """
    try:
        timeline = list(st.session_state.get(_TIMELINE_SESSION_KEY, []))
        entry = {
            "at": now_utc().isoformat(),
            "event": str(event_type),
        }
        if page:
            entry["page"] = str(page)
        if detail:
            text = str(detail)
            if len(text) > 300:
                text = text[:300] + "...(truncated)"
            entry["detail"] = text

        timeline.append(entry)
        if len(timeline) > _MAX_EVENTS:
            timeline = timeline[-_MAX_EVENTS:]
        st.session_state[_TIMELINE_SESSION_KEY] = timeline
    except Exception:
        # Recording evidence must never be the reason a page breaks.
        logger.exception("evidence_timeline.record_event failed (non-fatal)")


def record_page_visit(page_name):
    """
    Call once per page render (navigation.router.render_nav() already
    does this for every page). Records "Opened page" the first time a
    page name is seen this session, or "Changed page" whenever the
    page name differs from the last recorded one. Reruns of the SAME
    page (e.g. a button press causing Streamlit to rerun the current
    page) do not add a new entry, so the timeline reflects genuine
    navigation, not every rerun.
    """
    try:
        last_page = st.session_state.get(_LAST_PAGE_SESSION_KEY)
        if last_page is None:
            record_event("Opened page", page=page_name)
        elif last_page != page_name:
            record_event("Changed page", detail=f"from {last_page}", page=page_name)
        st.session_state[_LAST_PAGE_SESSION_KEY] = page_name
    except Exception:
        logger.exception("evidence_timeline.record_page_visit failed (non-fatal)")


def get_timeline():
    """
    Returns the current session's evidence timeline as a list of
    dicts (oldest first), each with "at", "event", and optionally
    "page" / "detail" keys. Never raises -- returns an empty list if
    anything goes wrong, so a broken timeline can never prevent a
    diagnostic package from being built.
    """
    try:
        return list(st.session_state.get(_TIMELINE_SESSION_KEY, []))
    except Exception:
        logger.exception("evidence_timeline.get_timeline failed (non-fatal)")
        return []