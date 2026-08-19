"""
Reflection Session
=====================

Wraps everything about an in-progress reflection session -- the result
from the orchestrator, which draft(s) it covers, submission progress, and
whether feedback is pending -- in one object.

The workspace keeps all 8 companion dimensions present, including a
short explanation when a dimension has no usable reflection. Technical
failures are retained for diagnostics, not exposed as technical details
to the practitioner.

Manual companion recovery
-------------------------
A companion that exhausted the orchestrator's existing automatic retry
mechanism is marked retryable. The workspace exposes one practitioner
retry for that companion only. That retry makes exactly one additional
API call. If it fails, the companion becomes permanently unavailable for
that session and the failure is logged as an operational issue. No
additional retry button is rendered.
"""

import streamlit as st

from rdi.companions import COMPANIONS
from rdi.reflection_objects import ReflectiveOpportunity
from rdi.companion_retry import retry_companion_once


_COVERAGE_REASON_TEXT = {
    "English": {
        "not_applicable": "The documentation did not contain enough relevant information to meaningfully explore this reflection point.",
        "unavailable": "This reflection is temporarily unavailable.",
        "manual_failed": "This reflection is currently unavailable. The issue has been recorded for review.",
        "retry": "Retry",
    },
    "Español": {
        "not_applicable": "La documentación no contenía suficiente información relevante para explorar de forma significativa este punto de reflexión.",
        "unavailable": "Esta reflexión no está disponible temporalmente.",
        "manual_failed": "Esta reflexión no está disponible actualmente. El problema ha quedado registrado para su revisión.",
        "retry": "Reintentar",
    },
    "Euskera": {
        "not_applicable": "Dokumentazioak ez zuen nahikoa informazio garrantzitsurik hausnarketa-puntu hau zentzuz lantzeko.",
        "unavailable": "Hausnarketa hau aldi baterako ez dago erabilgarri.",
        "manual_failed": "Hausnarketa hau ez dago erabilgarri une honetan. Arazoa berrikusteko erregistratu da.",
        "retry": "Berriro saiatu",
    },
}


class _RetryInvitation:
    """Iterable used by the existing tab renderer to place the retry button
    exactly where invitation questions normally appear.

    The page already iterates `opportunity.invitation` inside each horizontal
    companion tab. Keeping the control on the placeholder avoids changing the
    tab layout or creating a second global retry area.
    """

    def __init__(self, session, trigger, label):
        self.session = session
        self.trigger = trigger
        self.label = label

    def __iter__(self):
        if not self.session.can_retry_companion(self.trigger):
            return

        lang = st.session_state.get("lang", "Español")
        text = _COVERAGE_REASON_TEXT.get(lang, _COVERAGE_REASON_TEXT["Español"])
        button_key = f"retry_companion_{self.trigger}"

        if st.button(text["retry"], key=button_key):
            with st.spinner(text["retry"] + "..."):
                result = retry_companion_once(
                    self.trigger,
                    self.session.safe_text,
                    lang,
                )

            if result.get("success"):
                generated = result["result"]
                companion = next(c for c in COMPANIONS if c["key"] == self.trigger)
                replacement = ReflectiveOpportunity(
                    trigger=self.trigger,
                    context=self.session.context_summary,
                    focus=generated.get("observation", ""),
                    invitation=generated.get("questions", []),
                )
                self.session.replace_opportunity(self.trigger, replacement)
            else:
                self.session.mark_manual_retry_failed(self.trigger)

            self.session.save()
            st.rerun()

        return


class ReflectionSession:
    """A single reflection session for one case: what came back from the
    orchestrator, which draft(s) it's for, and how far through
    editing/feedback the practitioner has gotten."""

    _SESSION_KEY = "reflection_session"

    def __init__(self, result, reflected_drafts, case_ref, context_summary=""):
        self.error = result.get("error")
        self.error_raw = result.get("raw") if self.error else None
        self.issue_id = result.get("issue_id") if self.error else None
        self.error_id = result.get("error_id") if self.error else None
        self.friendly_message = result.get("friendly_message") if self.error else None
        self.opportunities = result.get("opportunities", [])
        self.raw = result.get("raw")

        # Keep true technical failure information for diagnostics, while the
        # practitioner-facing UI remains neutral and dimension-specific.
        self.generation_failed_count = result.get("failed_count", 0)
        self.failed_count = 0
        self.failed_labels = result.get("failed_labels", [])
        self.safe_text = result.get("safe_text", "")

        # These sets define the manual-retry state machine for this session:
        # retryable -> one manual attempt -> either success or permanent
        # unavailable. A failed manual attempt is never retryable again.
        self.retryable_triggers = set()
        self.manual_retry_failed = set()

        generated_by_trigger = {o.trigger: o for o in self.opportunities}
        failed_label_set = set(self.failed_labels)
        ordered_opportunities = []
        lang = st.session_state.get("lang", "Español")
        reason_text = _COVERAGE_REASON_TEXT.get(lang, _COVERAGE_REASON_TEXT["Español"])

        for companion in COMPANIONS:
            key = companion["key"]
            opportunity = generated_by_trigger.get(key)
            if opportunity is not None:
                ordered_opportunities.append(opportunity)
                continue

            if companion["label"] in failed_label_set:
                reason = reason_text["unavailable"]
                self.retryable_triggers.add(key)
                invitation = _RetryInvitation(self, key, companion["label"])
            else:
                reason = reason_text["not_applicable"]
                invitation = []

            placeholder = ReflectiveOpportunity(
                trigger=key,
                context=companion.get("focus", ""),
                focus=reason,
                invitation=invitation,
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

    def can_retry_companion(self, trigger):
        return trigger in self.retryable_triggers and trigger not in self.manual_retry_failed

    def replace_opportunity(self, trigger, replacement):
        self.opportunities = [
            replacement if opportunity.trigger == trigger else opportunity
            for opportunity in self.opportunities
        ]
        self.retryable_triggers.discard(trigger)
        self.manual_retry_failed.discard(trigger)

    def mark_manual_retry_failed(self, trigger):
        self.retryable_triggers.discard(trigger)
        self.manual_retry_failed.add(trigger)
        lang = st.session_state.get("lang", "Español")
        text = _COVERAGE_REASON_TEXT.get(lang, _COVERAGE_REASON_TEXT["Español"])
        opportunity = self.get_opportunity(trigger)
        if opportunity is not None:
            opportunity.focus = text["manual_failed"]
            opportunity.invitation = []

    def mark_submitted(self, draft_id):
        self.submitted_ids.add(draft_id)

    def is_submitted(self, draft_id):
        return draft_id in self.submitted_ids

    def all_batch_submitted(self):
        batch_ids = {d[0] for d in self.reflected_drafts}
        return self.submitted_ids >= batch_ids

    def draft_ids(self):
        return [d[0] for d in self.reflected_drafts]

    def get_opportunity(self, trigger):
        for opportunity in self.opportunities:
            if opportunity.trigger == trigger:
                return opportunity
        return None

    def explored_count(self):
        return sum(1 for o in self.opportunities if o.explored)

    def save(self):
        st.session_state[self._SESSION_KEY] = self
        return self

    @classmethod
    def get_active(cls):
        return st.session_state.get(cls._SESSION_KEY)

    @classmethod
    def clear(cls):
        st.session_state.pop(cls._SESSION_KEY, None)
