import streamlit as st

from services.language import init_language
from navigation.router import render_nav
from services.identity import init_identity, render_identity_footer, require_work_mode
from services.error_log import error_boundary

from pages.admin_sections import (
    user_management,
    system_health,
    admin_tools,
    ai_diagnostic_centre,
    service_usage,
    reflection_timing,
    data_reset,
    demo_data,
)

# =============================================================================
# System Administration -- Admin Console
# =============================================================================
#
# This page is the thin entry point that Streamlit's page-based
# navigation loads (see navigation/menus.py). Each section lives in its
# own file under pages/admin_sections/ and exposes a render(T) function.
# The page makes no Claude (Anthropic) API calls of its own.
#
# Every user-facing string goes through the central language service
# (services/language.py, key T).
#
# Architectural rule: this page and its sections must never use
# st.dataframe(), st.tabs() or st.columns().
#
# November 2026 clean-up (product owner's decisions):
#   - Removed: "Erase old stored documents", "Configuration" and "Case
#     Knowledge Search" (and, earlier the same month, the Qdrant-based
#     Document Indexing / Retrieval Test / RAG Status sections).
#   - The AI Diagnostic Centre was reduced to a plain list of recorded
#     problems (what happened, when, status); the AI diagnosis travels
#     in the alert email. Since 18 November 2026 each problem also shows
#     the same Claude Code prompt as its alert email, with a copy button.
#   - Added: "Erase all data", to start the real pilot from zero.
#   - 17 November 2026: "Demo data" (load / remove fictional texts), shown
#     ONLY in the separate demo app (DEMO_MODE on) -- see DEMO.md.
#   - 27 November 2026: "Reflection timing" (temporary measurement of the
#     Reflect steps and the measured cost per reflection).

T = init_language()
init_identity(T)
require_work_mode(T, "System Administration")
render_nav(T, page_name="system_administration")
render_identity_footer(T)

if st.session_state.get("user_role") != "System Administrator":
    st.stop()

with error_boundary(
    "system_administration",
    T=T,
    user_name=st.session_state.get("user_name", ""),
    user_role=st.session_state.get("user_role", ""),
):
    st.title(T.get("nav_system_admin", "🛠️ System Administration"))
    st.caption(T.get("admin_console_caption", "Administration console for Reflection Space -- system status, indexing, and diagnostic tools."))

    # 0. Demo data -- only in the demo app (the section shows nothing
    #    when DEMO_MODE is off).
    demo_data.render(T)

    # 1. Users (view only)
    user_management.render(T)

    # 2. System Health
    system_health.render(T)

    # 3. Administrative Tools (anonymisation test)
    admin_tools.render(T)

    # 4. Translation System Health + Diagnostic Centre (problem list)
    ai_diagnostic_centre.render(T)

    # 5. Service Usage & Costs
    service_usage.render(T)

    # 5b. Reflection timing (27 November 2026, Batch 1 measurement):
    #     step times and the measured cost per reflection.
    reflection_timing.render(T)

    # 6. Erase all data (start from zero)
    data_reset.render(T)
