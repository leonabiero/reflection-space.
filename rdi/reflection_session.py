"""
Reflection Session
=====================

Wraps everything about an in-progress reflection session -- the result
from the orchestrator, which draft(s) it covers, submission progress, and
whether feedback is pending -- in one object.

This replaces what used to be 5 separate, hand-managed
st.session_state[...] keys ("reflection", "reflected_drafts",
"reflection_case_ref", "submitted_ids", "awaiting_feedback") with a
single object stored under one key. Pure refactor: the page's behavior
and everything the practitioner sees is unchanged.

Sprint 6 addition
------------------
The session now also carries `safe_text` (the anonymized document text
used to generate this session's opportunities) and `context_summary`
(the transparency sentence about how much historical context was
included). Both are needed by the Reflection Workspace so that exploring
an opportunity's conversation doesn't require re-anonymizing the
document or losing the context description. Existing constructor
arguments and behavior are unchanged; both are optional.

Phase 3 (Practitioner UX) addition
-----------------------------------
`failed_labels` is now also carried over from the orchestrator result
(previously only `failed_count` was kept). This is purely additive and
purely for DISPLAY -- it lets the Reflection Coverage panel on the
Reflection Workspace page show, dimension by dimension, which of the 8
reflective areas were actually analysed this run versus which one(s)
couldn't be generated (see rdi/orchestrator.py's existing
"failed_labels" key, which was already being computed and returned --
it just wasn't being kept on the session object before now). No new
data is computed here, and nothing about how the orchestrator runs,
what it returns, or how reflections are generated has changed.
"""

import streamlit as st


class ReflectionSession:
    """A single reflection session for one case: what came back from the
    orchestrator, which draft(s) it's for, and how far through
    editing/feedback the practitioner has gotten."""

    _SESSION_KEY = "reflection_session"

    def __init__(self, result, reflected_drafts, case_ref, context_summary=""):
        # result is whatever rdi.orchestrator.run_reflection() returned:
        # either {"error": ..., "raw": ...} or
        # {"opportunities": [...], "raw": ..., "failed_count": ...,
        #  "failed_labels": [...], "safe_text": ...}
        self.error = result.get("error")
        self.error_raw = result.get("raw") if self.error else None
        self.opportunities = result.get("opportunities", [])
        self.raw = result.get("raw")
        self.failed_count = result.get("failed_count", 0)
        # Phase 3 (UX): kept purely for the Reflection Coverage display --
        # see module docstring. Falls back to [] so nothing breaks for any
        # older, already-in-memory session created before this field
        # existed.
        self.failed_labels = result.get("failed_labels", [])
        self.safe_text = result.get("safe_text", "")

        self.reflected_drafts = reflected_drafts
        self.case_ref = case_ref
        self.context_summary = context_summary
        self.submitted_ids = set()
        self.awaiting_feedback = False

    def has_error(self):
        return self.error is not None

    def mark_submitted(self, draft_id):
        self.submitted_ids.add(draft_id)

    def is_submitted(self, draft_id):
        return draft_id in self.submitted_ids

    def all_batch_submitted(self):
        """True once every draft in this session's batch has been
        submitted."""
        batch_ids = {d[0] for d in self.reflected_drafts}
        return self.submitted_ids >= batch_ids

    def draft_ids(self):
        return [d[0] for d in self.reflected_drafts]

    def get_opportunity(self, trigger):
        """Look up one opportunity by its trigger key (e.g.
        "client_voice"), for continuing its conversation. Returns None
        if not found (shouldn't normally happen, but kept defensive)."""
        for opportunity in self.opportunities:
            if opportunity.trigger == trigger:
                return opportunity
        return None

    def explored_count(self):
        """How many opportunities the practitioner has opened at all --
        used for the session progress indicator. Not a completion or
        competence measure, just a count."""
        return sum(1 for o in self.opportunities if o.explored)

    # --- session storage -------------------------------------------------

    def save(self):
        st.session_state[self._SESSION_KEY] = self
        return self

    @classmethod
    def get_active(cls):
        return st.session_state.get(cls._SESSION_KEY)

    @classmethod
    def clear(cls):
        st.session_state.pop(cls._SESSION_KEY, None)