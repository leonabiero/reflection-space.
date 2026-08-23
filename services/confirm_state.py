"""
Confirm State
=============

A tiny, shared helper for the "are you sure?" pattern used on several
screens (deleting a draft, deleting a case document, resetting the search
index): warn the user, show Yes/Cancel, and only act if they say Yes.

This module does NOT decide what warning text or button labels to show,
and does NOT know what action is being confirmed -- each page still
writes its own st.warning(...) message and its own st.button(...) calls,
in its own language via services/language.py, exactly as before.

All this module does is the small, identical bookkeeping that used to be
copy-pasted in three different files: remembering that a confirmation is
in progress, and forgetting it again once the user picks Yes or Cancel.
"""

import streamlit as st


def is_confirming(confirm_key):
    """True if the user has already clicked the initial action button
    and is now being asked to confirm it."""
    return bool(st.session_state.get(confirm_key, False))


def start_confirming(confirm_key):
    """Call this when the user clicks the initial action button, to move
    into the "please confirm" state."""
    st.session_state[confirm_key] = True


def clear_confirming(confirm_key):
    """Call this once the user has clicked either Yes or Cancel, to leave
    the "please confirm" state."""
    st.session_state.pop(confirm_key, None)
