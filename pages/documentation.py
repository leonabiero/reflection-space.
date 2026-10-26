"""
Documentation -- retired screen (kept only as a safe redirect)
================================================================

Reflection-only redesign (October 2026, agreed with the EDE team -- see
REFLECTIONS.md): there is no separate Documentation screen any more.
Writing, pasting or uploading a case now happens directly on the
Reflection Space screen, where the reflection happens on the spot, and
the case text is never stored.

This file stays so that an old bookmark, browser history entry or link
to the former Documentation address does not end in a "page not found"
error: it simply sends the person to Reflection Space. It is not linked
from any menu.
"""
import streamlit as st

from services.language import init_language
from services.identity import init_identity

T = init_language()
init_identity(T)
st.switch_page("pages/reflection_space.py")
