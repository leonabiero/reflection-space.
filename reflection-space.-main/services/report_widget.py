"""
"Report a problem" sidebar widget
=====================================

Available on EVERY page (rendered once, at the end of
navigation.router.render_nav(), which every page already calls). Lets
anyone using the app -- not just administrators -- flag something that
looks wrong, right when it happens, without needing to describe it
technically.

What happens when someone submits a report:
  1. It is written to the same error_log table the automatic crash
     detector uses (see services/error_log.py), tagged
     severity="user_reported", so it shows up in System Administration
     -> AI Diagnostic Centre exactly like an automatic error would,
     complete with its own ready-to-copy AI prompt.
  2. A complete AI Diagnostic Package is built automatically behind
     the scenes (services/diagnostics.py) -- page, session context,
     environment, recent navigation timeline, and more -- so the
     person reporting only ever has to describe WHAT happened, not
     gather any technical detail themselves.
  3. A Diagnostic Report email alert is sent immediately (see
     services/email_alert.py), if email alerting is configured -- so
     the administrator can see it even while not actively looking at
     the app.

Phase 3: the screenshot capture step has been retired entirely (see
the Phase 3 implementation notes). The workflow is now just a
description box and a send button -- no capture step, no waiting, no
preview. The Diagnostic Engine collects everything else automatically.

Design choice: this widget deliberately does its own thing independent
of error_boundary (services/error_log.py) -- it's for a person noticing
something looks wrong (a confusing result, something that seems off)
even when nothing actually raised a Python exception, which
error_boundary alone would never catch.
"""

import streamlit as st

from services.error_log import log_user_report


def render_report_button(T, page_name, user_name="", user_role=""):
    """
    Renders the "Report a problem" expander in the sidebar. Call once,
    near the end of navigation.router.render_nav() -- never call this
    directly from individual pages.
    """
    with st.sidebar.expander(T.get("report_problem_header", "🚩 Report a problem"), expanded=False):
        st.caption(T.get(
            "report_problem_caption",
            "Something look wrong? Describe it below. Your administrator will "
            "be notified right away.",
        ))

        reset_ctr = st.session_state.get("_report_reset_ctr", 0)

        description = st.text_area(
            T.get("report_problem_description_label", "What happened?"),
            key=f"_report_description_{reset_ctr}",
            height=100,
        )

        send_clicked = st.button(
            T.get("report_problem_send_button", "Send Report"),
            key="_report_send_button",
            type="primary",
        )

        if send_clicked:
            if not description.strip():
                st.warning(T.get(
                    "report_problem_empty_warning",
                    "Please add a short description before sending.",
                ))
            else:
                log_user_report(
                    page=page_name,
                    description=description.strip(),
                    user_name=user_name,
                    user_role=user_role,
                )
                st.session_state["_report_reset_ctr"] = reset_ctr + 1
                st.session_state["_report_just_sent"] = True
                st.rerun()

        if st.session_state.pop("_report_just_sent", False):
            st.success(T.get("report_problem_sent", "Report sent. Thank you -- your administrator has been notified."))