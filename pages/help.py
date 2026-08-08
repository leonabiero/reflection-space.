import streamlit as st
from services.language import init_language
from navigation.router import render_nav
from navigation.permissions import can_access_workspace
from services.identity import init_identity, render_identity_footer
from services.error_log import error_boundary

# In-app Help / Quick Guide
# ============================
#
# A read-only, trilingual mini user guide, native to the app -- built as
# a condensed, role-aware version of the full "Reflection Space User
# Guide" (Word document) EDE staff also receive. This page changes no
# data and calls no storage function beyond what init_identity/render_nav
# already do, so it carries no privacy or RBAC risk of its own; the only
# access control that matters here is CONTENT visibility, not page
# access -- every authenticated role may open this page.
#
# Deliberately NOT gated with services.identity.require_work_mode(): that
# call forces active_work_mode to one fixed workspace, which would yank
# a Supervisor/Programme Manager/System Administrator out of whatever
# workspace they were actually in just to read the help page. Skipping
# it means this page is reachable from -- and returns the person to --
# whichever workspace they were already using (navigation/menus.py adds
# this page's link to every workspace's sidebar for exactly that reason).
#
# Content sections are shown based on the AUTHENTICATED role (never the
# active work mode alone), via navigation.permissions.can_access_workspace
# -- the same single source of truth already used everywhere else in the
# app for authorization. A Social Worker sees only the Practitioner
# section; a Supervisor/Programme Manager sees Practitioner + Manager
# (since they can work in both); a System Administrator sees everything.
# This mirrors, not duplicates, the real page-access rules -- it never
# grants access to a page a role can't actually open.

T = init_language()
user_name, user_role = init_identity(T)
render_nav(T, page_name="help")
render_identity_footer(T)

with error_boundary("help", T=T, user_name=user_name, user_role=user_role):
    H = T["help"]

    st.title(H["page_title"])

    st.subheader(H["intro_title"])
    st.write(H["intro_body"])
    st.info(H["guardrail_note"])

    st.subheader(H["journey_title"])
    for step in H["journey_steps"]:
        st.markdown(f"- {step}")

    st.divider()

    # --- Practitioner workspace: Social Worker, Supervisor, Programme
    # Manager, System Administrator can all open Practitioner mode. ---
    if can_access_workspace(user_role, "Practitioner"):
        st.header(H["practitioner_title"])

        with st.expander(H["doc_section_title"], expanded=False):
            st.write(H["doc_section_body"])

        with st.expander(H["reflection_section_title"], expanded=False):
            st.write(H["reflection_section_body"])
            st.markdown(f"**{H['dimensions_title']}**")
            for dim in H["dimensions"]:
                st.markdown(f"- **{dim['label']}** \u2014 {dim['desc']}")

        with st.expander(H["growth_section_title"], expanded=False):
            st.write(H["growth_section_body"])

        st.divider()

    # --- Manager workspace: Supervisor, Programme Manager, System
    # Administrator. ---
    if can_access_workspace(user_role, "Manager"):
        st.header(H["manager_title"])

        with st.expander(H["learning_section_title"], expanded=False):
            st.write(H["learning_section_body"])

        with st.expander(H["case_history_section_title"], expanded=False):
            st.write(H["case_history_section_body"])

        if user_role == "System Administrator":
            with st.expander(H["research_metrics_section_title"], expanded=False):
                st.write(H["research_metrics_section_body"])

        st.divider()

    # --- System Administration: System Administrator only. ---
    if can_access_workspace(user_role, "System Administration"):
        st.header(H["admin_title"])
        st.write(H["admin_section_body"])
        st.divider()

    # --- Shown to everyone, regardless of role. ---
    st.header(H["report_problem_title"])
    st.write(H["report_problem_body"])

    st.header(H["privacy_title"])
    for point in H["privacy_points"]:
        st.markdown(f"- {point}")