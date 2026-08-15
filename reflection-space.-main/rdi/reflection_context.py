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
carrying three additive fields: "score", "match_reason" (primary reason,
back-compat), and "match_reasons" (the full list of every retrieval
strategy that proposed this document -- see rdi/retrieval_service.py,
"Multi-reason merge"). strength_summary() below factors the average
semantic score of included documents into its Context Confidence
classification (see classify_context_strength()), and now looks at
`match_reasons` (rather than the old single `match_reason`) so a
document that is BOTH a must-include document AND a semantic match still
has its semantic score counted towards confidence. Everything else
(set_historical_included, included_historical, combined_text,
save/get_active/clear) is unchanged.

Development logging
----------------------
Logging goes through the shared services.rag_logging.rag_log() helper
(see that module's docstring) rather than a local, ad-hoc print()-based
helper, so "[RAG]" trace lines are reliably written to stdout on
Streamlit Cloud instead of possibly being lost to output buffering.
"""

import streamlit as st
from rdi.context_engine import classify_context_strength
from services.rag_logging import rag_log


def _log(msg):
    """Thin wrapper kept for call-site compatibility -- delegates to the
    shared, properly configured logger in services.rag_logging."""
    rag_log(f"[RAG] {msg}")


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

    def _semantic_scores(self, docs):
        """Average similarity score among the given docs that were
        proposed (at least in part) by the SemanticRetriever. A
        document is counted here if "semantic" appears anywhere in its
        match_reasons list, so a must-include document that ALSO came
        back as a semantic match still contributes its score."""
        scores = []
        for h in docs:
            reasons = h.get("match_reasons")
            if reasons is None:
                # Back-compat: older/plain callers that only set the
                # singular match_reason.
                reasons = [h.get("match_reason")] if h.get("match_reason") else []
            if "semantic" in reasons and h.get("score") is not None:
                scores.append(h["score"])
        return scores

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

        semantic_scores = self._semantic_scores(included)
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

    def log_pre_orchestrator_summary(self, T):
        """Temporary development logging: emits one detailed "[RAG]"
        trace of exactly what is about to be sent into the Reflection
        Orchestrator -- the current document(s), every included
        historical document with its reasons and score, and the
        resulting Context Confidence sentence. Call this once, right
        before rdi.orchestrator.run_reflection(), so the full context
        that produced a given reflection is always visible in the logs.
        Purely observational -- never changes what gets sent."""
        included = self.included_historical()
        summary_text = self.strength_summary(T)

        current_lines = [f"id={d[0]} doc_type={d[2]!r}" for d in self.selected]
        historical_lines = [
            f"id={h['id']} doc_type={h['doc_type']!r} reasons={h.get('match_reasons', [h.get('match_reason')])} score={h.get('score')}"
            for h in included
        ]

        _log(
            "Reflection Context (pre-orchestrator): "
            f"case_ref={self.case_ref!r} | "
            f"current_documents=[{'; '.join(current_lines)}] | "
            f"historical_documents=[{'; '.join(historical_lines) if historical_lines else 'none'}] | "
            f"context_confidence={summary_text!r}"
        )

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