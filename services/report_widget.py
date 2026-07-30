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
     -> Error Log exactly like an automatic error would, complete with
     its own ready-to-copy AI prompt.
  2. An email alert is sent immediately (see services/email_alert.py),
     if email alerting is configured -- so the administrator can see it
     even while not actively looking at the app.
  3. A best-effort screenshot is attached (see
     components/screenshot_reporter/index.html) -- this step can fail
     silently (see that file's docstring for why) and NEVER blocks
     steps 1-2 from happening.

Design choice: this widget deliberately does its own thing independent
of error_boundary (services/error_log.py) -- it's for a person noticing
something looks wrong (a confusing result, something that seems off)
even when nothing actually raised a Python exception, which
error_boundary alone would never catch.
"""

import os
import time

import streamlit as st

from services.error_log import log_user_report

_COMPONENT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "components")
_component_func = None


def _get_component_func():
    global _component_func
    if _component_func is None:
        _component_func = st.components.v1.declare_component(
            "screenshot_reporter", path=_COMPONENT_DIR
        )
    return _component_func


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
            T.get("report_problem_description_label", "What were you doing, and what went wrong?"),
            key=f"_report_description_{reset_ctr}",
            height=100,
        )

        capture_clicked = st.button(
            T.get("report_problem_capture_button", "1. Capture screenshot"),
            key="_report_capture_button",
        )
        if capture_clicked:
            st.session_state["_report_capture_active"] = True
            st.session_state["_report_capture_trigger"] = str(time.time())
            st.session_state["_report_screenshot"] = None

        screenshot_b64 = None
        if st.session_state.get("_report_capture_active"):
            st.caption(T.get("report_problem_capturing", "Capturing a screenshot of the app..."))
            component_func = _get_component_func()
            # IMPORTANT: default is a sentinel, not None. A finished
            # capture can legitimately resolve to "no screenshot"
            # (e.g. the page was skipped as too large, or it timed
            # out) -- that result is also None, which is otherwise
            # indistinguishable from "hasn't responded yet". Without
            # this sentinel, a capture that finishes with "no
            # screenshot" gets mistaken for "still in progress"
            # forever, and the report can silently go out without a
            # screenshot the person thought they'd captured.
            _PENDING = "__reflection_space_capture_pending__"
            result = component_func(
                key=f"_report_screenshot_component_{st.session_state.get('_report_capture_trigger', '0')}",
                default=_PENDING,
            )
            if result != _PENDING:
                st.session_state["_report_screenshot"] = result  # may legitimately be None
                st.session_state["_report_capture_active"] = False
            screenshot_b64 = st.session_state.get("_report_screenshot")

            if screenshot_b64:
                st.success(T.get("report_problem_captured", "Screenshot captured."))
                try:
                    import base64
                    header, _, b64data = screenshot_b64.partition(",")
                    st.image(base64.b64decode(b64data), caption=T.get("report_problem_preview", "Attached to your report"))
                except Exception:
                    pass
            elif not st.session_state.get("_report_capture_active"):
                # Capture finished (the sentinel check above resolved
                # it), but there's no image -- tell the person plainly
                # rather than leaving it ambiguous. Their report can
                # still be sent without one.
                st.info(T.get(
                    "report_problem_no_screenshot",
                    "No screenshot could be captured automatically for this page. "
                    "You can still send your report without one.",
                ))

        send_clicked = st.button(
            T.get("report_problem_send_button", "2. Send report"),
            key="_report_send_button",
            type="primary",
            # Prevents sending before a capture finishes, which used
            # to be able to send a report without the screenshot the
            # person had just seen appear on screen.
            disabled=st.session_state.get("_report_capture_active", False),
        )

        if send_clicked:
            if not description.strip() and not st.session_state.get("_report_screenshot"):
                st.warning(T.get(
                    "report_problem_empty_warning",
                    "Please add a short description (or capture a screenshot) before sending.",
                ))
            else:
                log_user_report(
                    page=page_name,
                    description=description.strip() or "(no description provided)",
                    user_name=user_name,
                    user_role=user_role,
                    screenshot_b64=st.session_state.get("_report_screenshot"),
                )
                st.session_state["_report_reset_ctr"] = reset_ctr + 1
                st.session_state["_report_screenshot"] = None
                st.session_state["_report_capture_active"] = False
                st.session_state["_report_just_sent"] = True
                st.rerun()

        if st.session_state.pop("_report_just_sent", False):
            st.success(T.get("report_problem_sent", "Report sent. Thank you -- your administrator has been notified."))