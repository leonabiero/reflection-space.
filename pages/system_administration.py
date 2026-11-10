import streamlit as st

from services.language import init_language
from navigation.router import render_nav
from services.identity import init_identity, render_identity_footer, require_work_mode
from services.error_log import error_boundary

from pages.admin_sections import (
    user_management,
    legacy_documents,
    system_health,
    configuration,
    admin_tools,
    ai_diagnostic_centre,
    case_knowledge_search,
    service_usage,
)

# =============================================================================
# System Administration -- Admin Console
# =============================================================================
#
# This page is presentation-only. It reads status from existing services
# (services.embedding_service, services.draft_storage, config) and makes
# no Claude (Anthropic) API calls of its own.
#
# November 2026: the Document Indexing, Retrieval Test and RAG Status
# sections were removed together with the Qdrant search service, which
# only served the old document-based design (see REFLECTIONS.md).
#
# Sprint 12 translation audit
# -------------------------------
# Every user-facing string on this page now goes through the existing
# central language service (services/language.py, key T) -- no second
# translation table was created. See the "admin_*" / "admin_rag_*" /
# "admin_health_*" / "admin_retrieval_*" keys added there.
#
# File layout (post-reorganization)
# -------------------------------
# This page used to be a single ~1,640-line file. It has been split
# into one file per section under pages/admin_sections/, each
# exposing a render(T) function that draws exactly the same UI as
# before, in exactly the same order. This file is now just the thin
# entry point that Streamlit's page-based navigation loads (see
# navigation/menus.py's page_link("pages/system_administration.py"))
# -- it wires the pieces together but no longer contains their logic.
# Nothing about how the page looks or behaves for a System
# Administrator has changed.

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

    # 1. User Management
    user_management.render(T)

    # 1b. Erase old stored documents (reflection-only redesign,
    # REFLECTIONS.md) -- only shown while old documents remain.
    legacy_documents.render(T)

    # 5. System Health
    system_health.render(T)

    # 6. Configuration
    configuration.render(T)

    # 7. Administrative Tools
    admin_tools.render(T)

    # 8. Translation System Health + AI Diagnostic Centre (Phase 6)
    ai_diagnostic_centre.render(T)

    # 9. Case Knowledge Search (Phase 4)
    case_knowledge_search.render(T)

    # 10. Service Usage & Costs (Service Cost & Usage Monitor)
    service_usage.render(T)
