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

Practitioner coverage behavior
------------------------------
The workspace now keeps all 8 companion dimensions present in the
session, even when a dimension has no usable reflection. This prevents a
missing tab from looking like the system forgot a dimension. A genuinely
empty dimension gets a short, neutral explanation based on that
companion's focus. A companion that failed technically after all retries
gets a neutral availability explanation instead; the technical failure
itself remains in the orchestrator's diagnostics/logging and is never
shown to the practitioner.
"""

import streamlit as st

from rdi.companions import COMPANIONS
from rdi.reflection_objects import ReflectiveOpportunity


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
        # Phase 3 (Reflection Generation): only ever set when self.error
        # is set (Complete Failure) -- see rdi/orchestrator.py:run_reflection.
        # Lets the page show the SAME numbered "Something went wrong"
        # screen as any other unexpected error -- see
        # services/error_log.py:render_application_error_screen.
        self.issue_id = result.get("issue_id") if self.error else None
        self.error_id = result.get("error_id") if self.error else None
        # September pilot hardening: only set for
        # rdi/orchestrator.py's capacity-timeout outcome -- lets the
        # "Something went wrong" screen explain (truthfully) that this
        # was a timing/capacity issue, not a bug. None for every other
        # error, which keeps that screen's normal, generic wording.
        self.friendly_message = result.get("friendly_message") if self.error else None
        self.opportunities = result.get("opportunities", [])
        self.raw = result.get("raw")
        # Keep the true technical failure count for diagnostics/inspection,
        # but do not expose it through the practitioner's old partial-failure
        # banner. The workspace itself always shows all eight dimensions.
        self.generation_failed_count = result.get("failed_count", 0)
        # Compatibility with pages/reflection_space.py: the old banner reads
        # `failed_count`. Keep that UI-facing value at zero because the
        # practitioner now sees every dimension and its neutral status/reason
        # inside the eight tabs instead of a technical generation warning.
        self.failed_count = 0
        # Phase 3 (UX): kept for diagnostic/coverage bookkeeping. The
        # practitioner UI should not be told that companions "couldn't be
        # generated"; technical details remain in orchestrator logging.
        self.failed_labels = result.get("failed_labels", [])
        self.safe_text = result.get("safe_text", "")

        # Keep all eight companion positions in the workspace. The
        # orchestrator intentionally omits empty opportunities, so rebuild
        # the display list here in the deliberate companion order. Existing
        # generated opportunities are preserved unchanged; missing ones get
        # a short neutral explanation instead of silently disappearing.
        generated_by_trigger = {o.trigger: o for o in self.opportunities}
        failed_label_set = set(self.failed_labels)
        ordered_opportunities = []

        for companion in COMPANIONS:
            key = companion["key"]
            opportunity = generated_by_trigger.get(key)
            if opportunity is not None:
                ordered_opportunities.append(opportunity)
                continue

            if companion["label"] in failed_label_set:
                # Technical/API failure after all retries. Do not expose the
                # root cause, retry count, API name, or other implementation
                # detail to the practitioner.
                reason = "No usable reflection was available for this area in this run."
            else:
                # Successful call, but the model found nothing meaningful to
                # raise for this dimension. The reason is deliberately tied
                # to the companion's focus so the practitioner can see why
                # this specific tab has no reflection without inventing a
                # case-specific claim.
                focus = (companion.get("focus") or "this area").rstrip(".")
                reason = (
                    "The available documentation did not provide enough material "
                    f"to meaningfully explore {focus}."
                )

            placeholder = ReflectiveOpportunity(
                trigger=key,
                context=companion.get("focus", ""),
                focus=reason,
                invitation=[],
            )
            ordered_opportunities.append(placeholder)

        self.opportunities = ordered_opportunities

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
