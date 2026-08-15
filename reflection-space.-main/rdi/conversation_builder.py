"""
Conversation Builder
======================

Takes the list of Reflective Opportunities produced by the orchestrator
and arranges them into a deliberate conversational order, rather than
whatever order the 8 parallel companion calls happened to finish in.

This module ONLY reorders. It never adds, removes, or edits the content
of any opportunity -- dimensions with nothing to say are already absent
from the list by the time it reaches here (see
rdi.reflection_objects.ReflectiveOpportunity.is_empty(), applied in the
orchestrator).

The sequence below is a deliberate arc, not an alphabetical or technical
ordering:
  1. Client's Voice                 -- center the person first
  2. Observation vs Interpretation
  3. Labels & Language
  4. Possible Bias
  5. Missing Information
  6. Evidence for Decisions
  7. Continuity
  8. Strengths vs Deficits           -- deliberately last, so the
                                        conversation closes on what the
                                        person/family is already doing
                                        well, not on a gap
"""

CONVERSATION_ORDER = [
    "client_voice",
    "observation_vs_interpretation",
    "labels_and_language",
    "possible_bias",
    "missing_information",
    "evidence_for_decisions",
    "continuity",
    "strengths_and_deficits",
]


def build_conversation(opportunities):
    """
    Reorder a list of ReflectiveOpportunity objects according to
    CONVERSATION_ORDER.

    Any opportunity whose trigger isn't in CONVERSATION_ORDER (shouldn't
    normally happen, but kept defensive for future companions that
    haven't been added to the sequence yet) is appended at the end, in
    whatever order it arrived in -- so nothing is ever silently dropped.
    """
    order_index = {key: i for i, key in enumerate(CONVERSATION_ORDER)}

    def sort_key(opportunity):
        return order_index.get(opportunity.trigger, len(CONVERSATION_ORDER))

    return sorted(opportunities, key=sort_key)