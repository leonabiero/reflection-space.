"""
Findings UI helpers
=====================

Small Streamlit pieces shared by the two places a saved finding is shown:
the Reflection Space workspace (pages/reflection_space.py) and the
personal journal (pages/growth_dashboard.py). Keeping them here means a
quotation and a professional's notes look and behave the same in both.

Nothing here talks to the AI. The only database call is saving a
professional's own notes and sharing choice
(services/findings_store.py:upsert_feedback), which the store restricts
to the person who ran the reflection.
"""

import re

import streamlit as st

from services.findings_store import (
    upsert_feedback, FEEDBACK_LABELS, MAX_NOTE_CHARS, MAX_ALTERNATIVE_CHARS,
)


def md_escape(text):
    """Show a saved quotation exactly as written: markdown characters
    inside it must display as themselves, not be interpreted. Line
    breaks are shown as spaces (display only -- the saved quotation is
    unchanged)."""
    flattened = re.sub(r"\s+", " ", text or "").strip()
    return re.sub(r"([\\`*_\[\]<>#~|])", r"\\\1", flattened)


def render_evidence(T, evidence, unverified_count=0):
    """The exact passage(s) an observation is based on, as quotations,
    plus an honest note if some proposed passages could not be matched to
    the text and were therefore not shown."""
    if evidence:
        st.caption(T["findings_evidence_caption"])
        for item in evidence:
            st.markdown("> " + md_escape(item.get("quote", "")))
    if unverified_count:
        st.caption(T["findings_unverified_notice"].format(count=unverified_count))


def render_notes_form(T, finding_id, user_name, saved, key_prefix):
    """
    The professional's OWN response to one finding: a label, a flag if
    the AI seems to have misunderstood, an alternative explanation, and a
    note. Saved apart from the AI's text and private to this person.

    `saved` is this person's existing notes ({} if none). `key_prefix`
    keeps widget keys unique when the same finding could appear on one
    page more than once.

    Returns the newly saved notes dict if the person pressed Save and it
    worked this run, otherwise None.
    """
    saved = saved or {}
    label_options = [""] + list(FEEDBACK_LABELS)
    saved_label = saved.get("label") or ""
    if saved_label not in label_options:
        saved_label = ""

    st.caption(T["findings_notes_privacy"])
    with st.form(key=f"{key_prefix}_form_{finding_id}"):
        label = st.radio(
            T["findings_label_prompt"],
            options=label_options,
            index=label_options.index(saved_label),
            format_func=lambda v: T["findings_labels"].get(v, T["findings_label_none"]),
            horizontal=True,
            key=f"{key_prefix}_label_{finding_id}",
        )
        misread = st.checkbox(
            T["findings_misread_label"],
            value=bool(saved.get("flagged_misread", False)),
            key=f"{key_prefix}_misread_{finding_id}",
        )
        alternative = st.text_area(
            T["findings_alternative_label"],
            value=saved.get("alternative_explanation", ""),
            max_chars=MAX_ALTERNATIVE_CHARS,
            key=f"{key_prefix}_alt_{finding_id}",
        )
        note = st.text_area(
            T["findings_note_label"],
            value=saved.get("note", ""),
            max_chars=MAX_NOTE_CHARS,
            key=f"{key_prefix}_note_{finding_id}",
        )
        # Stage 2: sharing is the author's explicit, per-observation
        # choice. Off unless they tick it; unticking withdraws it at once.
        # What is shared is the observation and its exact quotation only --
        # never their name, their notes or their ratings.
        share = st.checkbox(
            T["findings_share_label"],
            value=bool(saved.get("shared_with_team", False)),
            help=T["findings_share_help"],
            key=f"{key_prefix}_share_{finding_id}",
        )
        submitted = st.form_submit_button(T["findings_save_button"])

    if not submitted:
        return None

    try:
        ok = upsert_feedback(
            finding_id, user_name, label=label or None, note=note,
            alternative_explanation=alternative, flagged_misread=misread,
            shared_with_team=share,
        )
    except Exception:
        ok = False

    if not ok:
        st.error(T["findings_save_error"])
        return None

    st.success(T["findings_save_success"])
    return {
        "label": label or None,
        "note": (note or "").strip(),
        "alternative_explanation": (alternative or "").strip(),
        "flagged_misread": bool(misread),
        "shared_with_team": bool(share),
    }
