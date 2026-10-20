import streamlit as st

from services.language import init_language
from navigation.router import render_nav
from services.identity import init_identity, render_identity_footer, require_work_mode
from services.error_log import error_boundary
from services.pattern_access import can_review_patterns
from services import pattern_store, pattern_service
from services.pattern_engine import (
    SIMILARITY_LEVELS, DEFAULT_SIMILARITY_LEVEL, DEFAULT_MIN_OBSERVATIONS,
    DEFAULT_MIN_REFLECTIONS, MAX_PATTERNS_PER_RUN, MAX_OBSERVATIONS_PER_RUN,
)
from services.findings_store import FINDING_MODULES
from services.findings_ui import render_evidence

# Pattern Explorer
# ==================
#
# Stage 2 of the saved-findings work (see PATTERNS.md). For EDE's
# management team (Supervisors and Programme Managers) ONLY.
#
# Hard rules this page must never break:
#   - It shows "candidate patterns for reflection", never conclusions. No
#     wording on this page may say that bias or poor practice has been
#     found. The team records its own judgement (status), and the AI's
#     original suggestion is never overwritten.
#   - It only ever reads observations their authors chose to share, and it
#     never shows who wrote them (services/pattern_store.py enforces both
#     in the database layer, not just here).
#   - Counts of observations, reflections and cases are always shown
#     separately, and "across cases" is only claimed when case references
#     are recorded.

T = init_language()
user_name, user_role = init_identity(T)
require_work_mode(T, "Manager")
render_nav(T, page_name="pattern_explorer")
render_identity_footer(T)

with error_boundary(
    "pattern_explorer", T=T, user_name=user_name, user_role=user_role,
):

    st.title(T["patterns_title"])

    if not can_review_patterns(user_role):
        st.info(T["patterns_no_access"])
        st.stop()

    st.info(T["patterns_intro"])

    lens_labels = {k: T["section_labels"].get(k, k.replace("_", " ").title()) for k in FINDING_MODULES}

    flash_key = st.session_state.pop("_patterns_flash", None)
    if flash_key:
        st.success(T[flash_key])

    # ------------------------------------------------------------------
    # 1. What is available to look at
    # ------------------------------------------------------------------
    st.subheader(T["patterns_pool_header"])
    st.caption(T["patterns_pool_caption"])

    selected_lenses = st.multiselect(
        T["patterns_filter_lenses"],
        options=list(FINDING_MODULES),
        format_func=lambda k: lens_labels[k],
        key="patterns_filter_lenses",
    )
    date_from = st.date_input(T["patterns_filter_from"], value=None, key="patterns_filter_from")
    date_to = st.date_input(T["patterns_filter_to"], value=None, key="patterns_filter_to")

    pool = pattern_store.get_pool_counts(
        user_role, modules=selected_lenses or None, date_from=date_from, date_to=date_to,
    )

    if pool["observations"] == 0:
        st.info(T["patterns_pool_empty"])
    else:
        st.write(T["patterns_pool_counts"].format(
            observations=pool["observations"], reflections=pool["reflections"],
            cases=pool["cases"],
        ))
        if pool["reflections_without_case"]:
            st.caption(T["patterns_pool_no_case"].format(count=pool["reflections_without_case"]))

    # ------------------------------------------------------------------
    # 2. Generate
    # ------------------------------------------------------------------
    st.subheader(T["patterns_generate_header"])
    with st.expander(T["patterns_settings_header"], expanded=False):
        st.caption(T["patterns_settings_intro"])
        level = st.select_slider(
            T["patterns_similarity_label"],
            options=list(SIMILARITY_LEVELS),
            value=DEFAULT_SIMILARITY_LEVEL,
            format_func=lambda k: T["patterns_similarity_levels"][k],
            key="patterns_similarity",
        )
        st.caption(T["patterns_similarity_help"])
        min_observations = st.number_input(
            T["patterns_min_observations_label"], min_value=2, max_value=50,
            value=DEFAULT_MIN_OBSERVATIONS, step=1, key="patterns_min_obs",
        )
        min_reflections = st.number_input(
            T["patterns_min_reflections_label"], min_value=1, max_value=50,
            value=DEFAULT_MIN_REFLECTIONS, step=1, key="patterns_min_refl",
        )
        st.caption(T["patterns_threshold_not_proof"])

    st.caption(T["patterns_cost_note"].format(max_patterns=MAX_PATTERNS_PER_RUN))
    if pool["observations"] > MAX_OBSERVATIONS_PER_RUN:
        st.caption(T["patterns_pool_truncated"].format(max=MAX_OBSERVATIONS_PER_RUN))

    can_generate = pool["observations"] >= int(min_observations)
    if not can_generate and pool["observations"] > 0:
        st.caption(T["patterns_not_enough"].format(minimum=int(min_observations)))

    if st.button(T["patterns_generate_button"], type="primary", disabled=not can_generate,
                 key="patterns_generate_btn"):
        with st.spinner(T["patterns_generating"]):
            outcome = pattern_service.generate_patterns(
                user_role, user_name, st.session_state.lang, lens_labels,
                similarity_level=level, min_observations=int(min_observations),
                min_reflections=int(min_reflections),
                modules=selected_lenses or None, date_from=date_from, date_to=date_to,
            )
        if outcome["status"] == "busy":
            st.warning(T["patterns_busy"])
        elif outcome["status"] == "unavailable":
            st.error(T["patterns_unavailable"])
        else:
            st.session_state["patterns_run_id"] = outcome["run_id"]
            if outcome["patterns_created"] == 0:
                st.info(T["patterns_none_found"].format(
                    observations=outcome["observations_considered"]))
            else:
                st.success(T["patterns_generated_ok"].format(
                    patterns=outcome["patterns_created"],
                    observations=outcome["observations_considered"]))
            if outcome["not_embedded"]:
                st.warning(T["patterns_not_embedded"].format(count=outcome["not_embedded"]))
            if outcome["fallback_count"]:
                st.warning(T["patterns_fallback_notice"].format(count=outcome["fallback_count"]))

    # ------------------------------------------------------------------
    # 3. Review
    # ------------------------------------------------------------------
    st.divider()
    st.subheader(T["patterns_review_header"])

    runs = pattern_store.list_runs(user_role, limit=10)
    if not runs:
        st.info(T["patterns_no_runs"])
        st.stop()

    run_ids = [r["id"] for r in runs]
    current = st.session_state.get("patterns_run_id")
    default_index = run_ids.index(current) if current in run_ids else 0
    run_by_id = {r["id"]: r for r in runs}
    run_id = st.selectbox(
        T["patterns_run_select"], options=run_ids, index=default_index,
        format_func=lambda i: T["patterns_run_option"].format(
            date=(run_by_id[i]["created_at"] or "")[:16],
            observations=run_by_id[i]["observations_considered"],
            patterns=run_by_id[i]["patterns_created"],
        ),
        key="patterns_run_select_box",
    )
    run = run_by_id[run_id]
    params = run["parameters"] or {}
    st.caption(T["patterns_run_caption"].format(
        level=T["patterns_similarity_levels"].get(params.get("similarity_level"), "—"),
        min_obs=params.get("min_observations", "—"),
        min_refl=params.get("min_reflections", "—"),
    ))

    status_choices = list(pattern_store.PATTERN_STATUSES)
    shown_statuses = st.multiselect(
        T["patterns_filter_status"], options=status_choices,
        default=[s for s in status_choices if s != "archived"],
        format_func=lambda s: T["patterns_statuses"][s], key="patterns_filter_status",
    )

    patterns = pattern_store.list_patterns(user_role, run_id, statuses=shown_statuses or None)
    patterns.sort(key=lambda p: (-p["counts"]["reflections"], -p["counts"]["observations"], p["id"]))

    if not patterns:
        st.info(T["patterns_none_in_view"])
        st.stop()

    MAX_MEMBERS_SHOWN = 15

    def _case_message(counts):
        if counts["cases"] == 0:
            return T["patterns_cases_none"]
        if not counts["case_recurrence_known"]:
            return T["patterns_cases_incomplete"].format(
                missing=counts["reflections_without_case"], total=counts["reflections"])
        if counts["cases"] == 1:
            return T["patterns_cases_single"]
        return T["patterns_cases_multiple"].format(cases=counts["cases"])

    for pattern in patterns:
        counts = pattern["counts"]
        status_label = T["patterns_statuses"].get(pattern["status"], pattern["status"])
        header = T["patterns_item_header"].format(
            title=pattern["title"], status=status_label,
            observations=counts["observations"], reflections=counts["reflections"],
        )
        with st.expander(header, expanded=False):
            st.caption(T["patterns_candidate_label"])
            st.write(T["patterns_counts_line"].format(
                observations=counts["observations"], reflections=counts["reflections"],
                cases=counts["cases"],
            ))
            st.caption(_case_message(counts))
            st.caption(T["patterns_case_ref_caveat"])
            if counts["date_first"]:
                st.caption(T["patterns_dates_line"].format(
                    first=counts["date_first"], last=counts["date_last"]))
            lens_text = ", ".join(
                f"{lens_labels.get(k, k)} ({counts['modules'][k]})"
                for k in sorted(counts["modules"], key=lambda k: (-counts["modules"][k], k))
            )
            st.caption(T["patterns_lenses_line"].format(lenses=lens_text))

            if pattern["lost_members"]:
                st.warning(T["patterns_lost_members"].format(count=pattern["lost_members"]))
            if pattern["below_minimum"]:
                st.warning(T["patterns_below_minimum"])

            if pattern["explanation_status"] == "fallback":
                st.warning(T["patterns_explanation_failed"])
                if st.button(T["patterns_explanation_retry"], key=f"pe_retry_{pattern['id']}"):
                    with st.spinner(T["patterns_generating"]):
                        ok = pattern_service.retry_explanation(
                            user_role, user_name, pattern["id"], pattern["members"],
                            lens_labels, st.session_state.lang,
                        )
                    st.session_state["_patterns_flash"] = (
                        "patterns_retry_ok" if ok else "patterns_retry_failed")
                    st.rerun()

            st.markdown(f"**{T['patterns_what_in_common']}**")
            st.write(pattern["description"])
            st.markdown(f"**{T['patterns_why_it_matters']}**")
            st.write(pattern["why_it_matters"])
            st.markdown(f"**{T['patterns_alternatives']}**")
            for item in pattern["alternative_explanations"]:
                st.markdown(f"- {item}")
            st.markdown(f"**{T['patterns_limitations']}**")
            for item in pattern["limitations"]:
                st.markdown(f"- {item}")
            st.markdown(f"**{T['patterns_questions']}**")
            for item in pattern["questions"]:
                st.markdown(f"- {item}")

            st.divider()
            st.markdown(f"**{T['patterns_observations_header']}**")
            for member in pattern["members"][:MAX_MEMBERS_SHOWN]:
                case_text = member["case_ref"] or T["reflection_no_case_ref"]
                st.markdown(f"**{lens_labels.get(member['module'], member['module'])}** — "
                            f"{case_text} — {(member['created_at'] or '')[:10]}")
                st.write(member["observation"])
                render_evidence(T, member["evidence"], 0)
                if st.button(T["patterns_exclude_button"],
                             key=f"pe_ex_{pattern['id']}_{member['id']}"):
                    pattern_store.set_member_excluded(
                        user_role, user_name, pattern["id"], member["id"], True)
                    st.session_state["_patterns_flash"] = "patterns_excluded_ok"
                    st.rerun()
            hidden = len(pattern["members"]) - MAX_MEMBERS_SHOWN
            if hidden > 0:
                st.caption(T["patterns_more_observations"].format(count=hidden))

            if pattern["excluded_members"]:
                st.markdown(f"**{T['patterns_excluded_header']}**")
                for member in pattern["excluded_members"]:
                    st.write(member["observation"])
                    if st.button(T["patterns_restore_button"],
                                 key=f"pe_rs_{pattern['id']}_{member['id']}"):
                        pattern_store.set_member_excluded(
                            user_role, user_name, pattern["id"], member["id"], False)
                        st.session_state["_patterns_flash"] = "patterns_restored_ok"
                        st.rerun()

            st.divider()
            st.markdown(f"**{T['patterns_review_status_header']}**")
            st.caption(T["patterns_review_help"])
            with st.form(key=f"pe_form_{pattern['id']}"):
                new_status = st.selectbox(
                    T["patterns_status_label"], options=status_choices,
                    index=status_choices.index(pattern["status"]),
                    format_func=lambda s: T["patterns_statuses"][s],
                    key=f"pe_status_{pattern['id']}",
                )
                comment = st.text_area(
                    T["patterns_comment_label"], max_chars=pattern_store.MAX_COMMENT_CHARS,
                    key=f"pe_comment_{pattern['id']}",
                )
                saved = st.form_submit_button(T["patterns_save_review"])
            if saved:
                changed = pattern_store.set_pattern_status(
                    user_role, user_name, pattern["id"], new_status, comment)
                if changed:
                    st.session_state["_patterns_flash"] = "patterns_review_saved"
                    st.rerun()
                st.info(T["patterns_review_nothing"])

            events = pattern_store.get_pattern_events(user_role, pattern["id"])
            if events:
                st.markdown(f"**{T['patterns_history_header']}**")
                for event in events[-20:]:
                    kind = T["patterns_event_kinds"].get(event["kind"], event["kind"])
                    detail = ""
                    if event["kind"] == "status_changed":
                        detail = " " + T["patterns_event_status_change"].format(
                            old=T["patterns_statuses"].get(event["old_value"], event["old_value"]),
                            new=T["patterns_statuses"].get(event["new_value"], event["new_value"]))
                    who = event["actor"] if event["actor"] not in ("", "system") else T["patterns_event_system"]
                    line = f"{(event['created_at'] or '')[:16]} — {who} — {kind}{detail}"
                    st.caption(line)
                    if event["comment"]:
                        st.caption("“" + event["comment"] + "”")
