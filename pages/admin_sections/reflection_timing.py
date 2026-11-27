"""System Administration -- Reflection timing (27 November 2026, Batch 1).

Temporary measurement: how long each step after pressing Reflect takes,
how long the AI calls take, and the MEASURED average Claude cost per
reflection (next to the earlier $0.072 estimate). Read through
services/reflection_timing.py, which checks the System Administrator role
itself and makes no database call for anyone else; the page checks the
role too.

Architectural rule kept: no st.dataframe(), st.tabs() or st.columns()
on the System Administration page -- plain text lines only.
"""
import streamlit as st

import config
from services import reflection_timing

ADMIN_ROLE = "System Administrator"
PERIOD_OPTIONS = (7, 30)


def _seconds(T, ms):
    if ms is None:
        return "–"
    return T["admin_timing_seconds"].format(value=f"{float(ms) / 1000:.1f}")


def _tokens(value):
    return "–" if value is None else f"{float(value):,.0f}"


def _step_name(T, step):
    if step.startswith(reflection_timing.LENS_STEP_PREFIX):
        key = step[len(reflection_timing.LENS_STEP_PREFIX):]
        label = T["section_labels"].get(key, key) if isinstance(T.get("section_labels"), dict) else key
        return T["admin_timing_lens_step"].format(name=label)
    return T["admin_timing_step_names"].get(step, step)


def render(T):
    with st.expander(T["admin_timing_header"], expanded=False):
        role = st.session_state.get("user_role", "")
        if role != ADMIN_ROLE:
            st.error(T["admin_timing_refused"])
            return

        st.caption(T["admin_timing_intro"])
        if getattr(config, "REFLECTION_TIMING_LOG", False):
            st.info(T["admin_timing_recording_on"].format(
                days=getattr(config, "REFLECTION_TIMING_RETENTION_DAYS", 30)))
        else:
            st.warning(T["admin_timing_recording_off"])
        st.caption(T["admin_timing_not_measured"])

        days = st.radio(
            T["admin_timing_period_label"],
            PERIOD_OPTIONS,
            format_func=lambda d: T["admin_timing_period_option"].format(days=d),
            horizontal=True,
            key="admin_timing_period",
        )

        # Cost per reflection (measured).
        st.markdown(f"#### {T['admin_timing_cost_header']}")
        cost = reflection_timing.get_measured_cost_per_reflection(role, days)
        if cost and cost.get("avg_cost_usd") is not None:
            st.write(T["admin_timing_cost_measured"].format(
                cost=f"{cost['avg_cost_usd']:.3f}", count=cost["reflections"]))
        else:
            st.write(T["admin_timing_cost_none"])
        st.caption(T["admin_timing_cost_estimate"])

        # AI calls (from the existing usage records).
        st.markdown(f"#### {T['admin_timing_ai_header']}")
        calls = reflection_timing.get_ai_call_summary(role, days) or {}
        lines = []
        for operation, name_key in ((reflection_timing.LENS_OPERATION, "admin_timing_ai_lens"),
                                    (reflection_timing.REPORT_OPERATION, "admin_timing_ai_report")):
            row = calls.get(operation)
            if not row:
                continue
            lines.append("- " + T["admin_timing_ai_line"].format(
                name=T[name_key], calls=row["calls"],
                avg=_seconds(T, row["avg_ms"]), p90=_seconds(T, row["p90_ms"]),
                max=_seconds(T, row["max_ms"]),
                tokens_in=_tokens(row["avg_input_tokens"]),
                tokens_out=_tokens(row["avg_output_tokens"]),
                failed=row["failed"], timed_out=row["timed_out"],
            ))
        st.markdown("\n".join(lines) if lines else T["admin_timing_no_data"])

        # Steps, in the order they happen.
        st.markdown(f"#### {T['admin_timing_steps_header']}")
        steps = reflection_timing.get_step_summary(role, days) or []
        if steps:
            st.markdown("\n".join(
                "- " + T["admin_timing_step_line"].format(
                    name=_step_name(T, row["step"]),
                    avg=_seconds(T, row["avg_ms"]), p90=_seconds(T, row["p90_ms"]),
                    max=_seconds(T, row["max_ms"]), count=row["count"],
                )
                for row in steps
            ))
        else:
            st.write(T["admin_timing_no_data"])
