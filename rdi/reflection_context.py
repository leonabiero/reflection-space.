"""
Reflection Context
====================

Wraps the data behind the Reflection Context screen (Sprint 1) in a real
object instead of a loose dict passed around inside
st.session_state["context_review"].

This is a pure refactor: everything this class does was previously done
inline, by hand, in pages/reflection_space.py. Nothing about what the
practitioner sees or how the app behaves changes -- this just gives that
data a name and clear methods, so the page reads more like "ask the
context what it needs" rather than manipulating dictionary keys directly.

Hybrid RAG upgrade
--------------------
`historical` documents now arrive from rdi.context_engine.get_historical_context()
carrying two additive fields, "score" and "match_reason" (see
rdi/retrieval_service.py). strength_summary() below now factors the
average semantic score of included documents into its Context
Confidence classification (see classify_context_strength()), instead of
count alone -- everything else (set_historical_included,
included_historical, combined_text, save/get_active/clear) is unchanged.
"""

import streamlit as st
from rdi.context_engine import classify_context_strength


class ReflectionContext:
    """Holds the practitioner's in-progress choices on the Reflection
    Context screen: which current document(s) are locked in, and which
    historical documents are still included."""

    _SESSION_KEY = "reflection_context"

    def __init__(self, case_ref, selected, historical, selected_hist_ids=None):
        self.case_ref = case_ref
        self.selected = selected          # current draft(s), always included
        self.historical = historical      # candidate historical docs (dicts)
        self.selected_hist_ids = (
            set(selected_hist_ids) if selected_hist_ids is not None
            else {h["id"] for h in historical}
        )

    def set_historical_included(self, hist_id, included):
        """Update whether one historical document is included, per a
        checkbox toggle on the context screen."""
        if included:
            self.selected_hist_ids.add(hist_id)
        else:
            self.selected_hist_ids.discard(hist_id)

    def included_historical(self):
        """The historical documents currently still checked."""
        return [h for h in self.historical if h["id"] in self.selected_hist_ids]

    def strength_summary(self, T):
        """The localized transparency sentence describing how much
        historical context is included right now (Context Confidence).

        Uses both the count of included documents and, when available,
        the average semantic similarity score among the included
        documents that came from semantic matching -- see
        rdi.context_engine.classify_context_strength() for exactly how
        those two signals combine.
        """
        included = self.included_historical()
        count = len(included)

        semantic_scores = [
            h["score"] for h in included
            if h.get("match_reason") == "semantic" and h.get("score") is not None
        ]
        avg_score = (sum(semantic_scores) / len(semantic_scores)) if semantic_scores else None

        strength = classify_context_strength(count, avg_score=avg_score)
        if strength == "strong":
            return T["reflection_context_summary_strong"].format(count=count)
        elif strength == "limited":
            return T["reflection_context_summary_limited"]
        return T["reflection_context_summary_none"]

    def combined_text(self):
        """The full text to send for reflection: selected current
        document(s) followed by whichever historical documents are still
        included."""
        parts = [d[3] for d in self.selected]
        parts += [h["content"] for h in self.included_historical()]
        return "\n\n".join(parts)

    # --- session storage -------------------------------------------------
    # Kept as simple wrappers around st.session_state, in one place, so
    # the page doesn't need to know the underlying key name.

    def save(self):
        st.session_state[self._SESSION_KEY] = self
        return self

    @classmethod
    def get_active(cls):
        return st.session_state.get(cls._SESSION_KEY)

    @classmethod
    def clear(cls):
        st.session_state.pop(cls._SESSION_KEY, None)