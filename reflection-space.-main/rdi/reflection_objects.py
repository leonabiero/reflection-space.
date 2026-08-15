"""
Reflection Objects
===================

Defines the shape every reflective item in the app must take: a
Reflective Opportunity.

Per the RDI philosophy, the app never issues verdicts, scores, or
recommendations. This class enforces that structurally, not just by
convention -- there is simply no field here to put a score or a verdict
in. If a future companion tries to return one, it has nowhere to go.

A Reflective Opportunity always has exactly these five parts:
    trigger              -- what in the documentation prompted this
                             (e.g. which dimension, e.g. "client_voice")
    context               -- what documentation this opportunity was
                              generated from (e.g. "today's note" or
                              "today's note + 2 historical documents")
    focus                 -- the observation itself: what was noticed,
                              written in neutral, non-judgmental language
    invitation             -- the reflective question(s) inviting the
                              professional to think further
    professional_choice    -- a fixed reminder that engaging with this
                              opportunity is optional and the
                              professional's judgment is final

Sprint 6 addition
------------------
An opportunity can now also carry a *conversation*: a back-and-forth
between the professional and the companion that generated it, so the
practitioner can explore an observation instead of only reading it.
This is purely additive -- trigger/context/focus/invitation/
professional_choice are unchanged, and is_empty()/to_dict() behave
exactly as before for anything that doesn't touch the conversation.

The conversation is intentionally NOT structured JSON. Sprint 6/7 turns
are free-text, Socratic exchanges (see
rdi.companions.prompt_builder.build_companion_conversation_prompt and
services.reflection_service.continue_companion_conversation) -- there is
still nowhere here for a verdict, score, or decision to be stored.
"""

DEFAULT_PROFESSIONAL_CHOICE = (
    "This is offered as a reflective prompt only. Whether to explore it, "
    "and whether to change anything in the documentation, is entirely "
    "the professional's decision."
)


class ReflectiveOpportunity:
    """A single reflective item shown to the practitioner."""

    def __init__(self, trigger, context, focus, invitation,
                 professional_choice=DEFAULT_PROFESSIONAL_CHOICE):
        self.trigger = trigger
        self.context = context
        self.focus = focus
        self.invitation = invitation
        self.professional_choice = professional_choice

        # Sprint 6: conversation state. `conversation` is a list of
        # {"role": "professional" | "ai", "content": str} in the order
        # they happened. `explored` just tracks whether the practitioner
        # has opened this opportunity at all, for the session-progress
        # summary -- it is not a completion/competence signal.
        self.conversation = []
        self.explored = False

    def is_empty(self):
        """True if there's nothing here worth showing (no observation
        and no questions) -- used to skip dimensions the model found
        nothing notable to raise for."""
        return not self.focus and not self.invitation

    def mark_explored(self):
        self.explored = True

    def add_professional_message(self, text):
        self.mark_explored()
        self.conversation.append({"role": "professional", "content": text})

    def add_ai_message(self, text):
        self.conversation.append({"role": "ai", "content": text})

    def has_conversation(self):
        return len(self.conversation) > 0

    def to_dict(self):
        """Plain-dict form, useful for logging/storage without needing
        callers to know about this class."""
        return {
            "trigger": self.trigger,
            "context": self.context,
            "focus": self.focus,
            "invitation": self.invitation,
            "professional_choice": self.professional_choice,
            "explored": self.explored,
            "conversation": list(self.conversation),
        }