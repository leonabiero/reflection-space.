"""
Reflection Context
====================

Holds the practitioner's in-progress choices between "I have my case
text" and "generate the reflection" -- the second stage of the
Reflection Journey.

Reflection-only redesign (October 2026, see REFLECTIONS.md)
-------------------------------------------------------------
Reflection Space no longer stores documents, so there are no "historical
documents" to pull in any more. Instead the context for a new reflection
is:

- today's case text, written / pasted / uploaded on the spot. It lives
  ONLY in this object (in the browser session) and is never written to
  the database or to logs;
- the neutral identifiers of the new reflection: its app-generated code,
  the non-personal case tags, the note type and an optional link to an
  earlier reflection (previous_code);
- the professional's OWN earlier reflections that are linked or similar
  (services/reflection_records.find_similar_reflections), each of which
  can be included or left out with a checkbox.

The class keeps its old name and session API (save / get_active / clear,
and a `case_ref` attribute holding the reflection code) so the rest of
the app -- request de-duplication, error context, logs -- keeps working
unchanged.

Logging goes through services.rag_logging.rag_log() and never contains
case text, observation text or tags -- only codes, ids and counts.
"""

import streamlit as st
from rdi.context_engine import classify_context_strength
from services.rag_logging import rag_log
from services.reflection_records import build_context_block


def _log(msg):
    rag_log(f"[RAG] {msg}")


class ReflectionContext:
    """The practitioner's choices on the second stage of the journey."""

    _SESSION_KEY = "reflection_context"

    def __init__(self, reflection_code, case_text, case_tags=None, note_type="",
                 previous_code="", similar=None, included_ids=None):
        self.reflection_code = reflection_code
        self.case_ref = reflection_code      # back-compat name used across the app
        self.case_text = case_text or ""     # session only -- never stored
        self.case_tags = list(case_tags or [])
        self.note_type = note_type or ""
        self.previous_code = previous_code or ""
        self.similar = list(similar or [])   # earlier reflections (dicts)
        self.included_ids = (
            set(included_ids) if included_ids is not None
            else {s["run_id"] for s in self.similar}
        )

    # --- earlier reflections -------------------------------------------

    def set_similar_included(self, run_id, included):
        """Include or leave out one earlier reflection (checkbox)."""
        if included:
            self.included_ids.add(run_id)
        else:
            self.included_ids.discard(run_id)

    def included_similar(self):
        return [s for s in self.similar if s["run_id"] in self.included_ids]

    def strength_summary(self, T):
        """The localized sentence describing how much earlier context is
        included right now (Context Confidence)."""
        count = len(self.included_similar())
        linked = any("linked" in (s.get("match_reasons") or []) for s in self.included_similar())
        strength = classify_context_strength(count)
        if linked and strength == "none":
            strength = "limited"
        if strength == "strong":
            return T["reflection_context_summary_strong"].format(count=count)
        if strength == "limited":
            return T["reflection_context_summary_limited"]
        return T["reflection_context_summary_none"]

    def combined_text(self):
        """Everything sent for reflection: today's case text, followed by
        a clearly separated block with the included earlier reflections."""
        block = build_context_block(self.included_similar())
        return f"{self.case_text}\n\n{block}" if block else self.case_text

    def log_pre_orchestrator_summary(self, T):
        """One trace line (codes and counts only -- never any text) of
        what is about to be sent to the Reflection Orchestrator."""
        included = self.included_similar()
        _log(
            "Reflection Context (pre-orchestrator): "
            f"code={self.reflection_code!r} | case_text_chars={len(self.case_text)} | "
            f"tags={len(self.case_tags)} | linked={bool(self.previous_code)} | "
            f"earlier_reflections=[{', '.join(s['code'] for s in included) or 'none'}] | "
            f"context_confidence={self.strength_summary(T)!r}"
        )

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
