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
"""

import streamlit as st


class ReflectionSession:
    """A single reflection session for one case: what came back from the
    orchestrator, which draft(s) it's for, and how far through
    editing/feedback the practitioner has gotten."""

    _SESSION_KEY = "reflection_session"

    def __init__(self, result, reflected_drafts, case_ref):
        # result is whatever rdi.orchestrator.run_reflection() returned:
        # either {"error": ..., "raw": ...} or
        # {"opportunities": [...], "raw": ..., "failed_count": ..., "failed_labels": [...]}
        self.error = result.get("error")
        self.error_raw = result.get("raw") if self.error else None
        self.opportunities = result.get("opportunities", [])
        self.raw = result.get("raw")
        self.failed_count = result.get("failed_count", 0)

        self.reflected_drafts = reflected_drafts
        self.case_ref = case_ref
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