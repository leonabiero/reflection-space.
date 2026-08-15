import streamlit as st
from datetime import datetime, timedelta
from services.language import init_language
from navigation.router import render_nav
from services.identity import init_identity, render_identity_footer, require_work_mode, can_see_learning
from services.error_log import error_boundary, render_application_error_screen
from services.reflection_log import get_recent_theme_counts, THEME_KEYS
from services.exploration_log import get_aggregated_theme_counts
from services.presence import get_active_social_workers
from services.knowledge_assistant import ask as ask_knowledge_assistant

T = init_language()
user_name, user_role = init_identity(T)

# Guard BEFORE render_nav(): this both rejects direct/unauthorized access
# to the Learning page (authenticated role, not just active work mode)
# and keeps active_work_mode in sync with the page actually being
# viewed -- see services.identity.require_work_mode()'s docstring for
# why the ordering (guard, then render_nav) matters.
require_work_mode(T, "Manager")

render_nav(T, page_name="learning")
render_identity_footer(T)

with error_boundary(
    "learning", T=T, user_name=user_name, user_role=user_role,
):

    if not can_see_learning(user_role):
        st.info(T.get("learning_no_data", "No access."))
        st.stop()

    st.title(T["nav_learning"])

    # ---------------------------------------------------------------------
    # Sprint 12: Learning is now the organisational learning hub. Everything
    # below is organised into tabs rather than one long scroll, so the page
    # stays coherent even as more organisational-learning capability is
    # added to it -- per the product requirement that new capability (Team
    # Presence, the Knowledge Assistant) must live INSIDE this page, never
    # as a new top-level page.
    # ---------------------------------------------------------------------

    tab_presence, tab_knowledge, tab_insights, tab_team = st.tabs([
        T["learning_tab_presence"],
        T["learning_tab_knowledge"],
        T["learning_tab_insights"],
        T["learning_tab_team"],
    ])

    # --- Tab 1: Team Presence ------------------------------------------------
    with tab_presence:
        st.subheader(T["presence_header"])
        st.caption(T["presence_intro"])

        presence_rows = get_active_social_workers()
        visible_rows = [r for r in presence_rows if r["status"] in {"active", "recent"}]

        if not presence_rows:
            st.info(T["presence_no_data"])
        else:
            st.write(f"**{T['presence_active_count'].format(count=len(visible_rows))}**")
            if not visible_rows:
                st.caption(T["presence_status_offline"])
            for row in visible_rows:
                if row["status"] == "active":
                    status_line = T["presence_status_active"]
                else:
                    minutes = int(row["minutes_ago"]) if row["minutes_ago"] is not None else 0
                    status_line = T["presence_status_recent"].format(minutes=minutes)
                st.write(f"{status_line} — **{row['name']}**")

    # --- Tab 2: Knowledge Assistant (Organisational Learning) ---------------
    with tab_knowledge:
        st.subheader(T["ka_header"])
        st.caption(T["ka_intro"])

        question = st.text_area(
            T["ka_question_label"],
            placeholder=T["ka_question_placeholder"],
            key="ka_question_input",
            height=80,
        )

        if st.button(T["ka_ask_button"], type="primary"):
            if not question or not question.strip():
                st.warning(T["ka_empty_question"])
            else:
                with st.spinner(T["ka_thinking"]):
                    result = ask_knowledge_assistant(question.strip(), lang=st.session_state.lang)

                if "error" in result:
                    render_application_error_screen(
                        T,
                        result.get("issue_id"),
                        result.get("error_id"),
                        friendly_message=T["ka_error"],
                    )
                else:
                    st.session_state["ka_last_result"] = result
                    st.session_state["ka_last_question"] = question.strip()

        last_result = st.session_state.get("ka_last_result")
        if last_result:
            st.divider()
            st.markdown(f"**{st.session_state.get('ka_last_question', '')}**")
            st.write(last_result["answer"])

            confidence_key = {
                "strong": "ka_confidence_strong",
                "limited": "ka_confidence_limited",
                "insufficient": "ka_confidence_insufficient",
            }.get(last_result["confidence"], "ka_confidence_limited")
            st.write(f"{T['ka_confidence_label']} {T[confidence_key]}")

            if last_result.get("limitations"):
                st.caption(f"{T['ka_limitations_label']} {last_result['limitations']}")

            with st.expander(T["ka_evidence_header"], expanded=False):
                st.caption(T["ka_evidence_count"].format(count=last_result["evidence_count"]))
                evidence = last_result.get("evidence") or []
                if not evidence:
                    st.caption(T["ka_evidence_none"])
                else:
                    for item in evidence:
                        relevance = item.get("relevance")
                        relevance_display = f"{relevance:.2f}" if relevance is not None else "—"
                        st.write(
                            f"**{item.get('doc_type', '')}** — "
                            f"{T['ka_evidence_date_col']}: {item.get('date', '') or '—'} — "
                            f"{T['ka_evidence_case_col']}: {item.get('case_ref', '') or '—'} — "
                            f"{T['ka_evidence_relevance_col']}: {relevance_display}"
                        )

    # --- Tab 3: Learning Insights (existing per-professional/practice data) --
    with tab_insights:
        st.subheader(T.get("learning_phase2", "Learning Insights"))
        counts, total = get_recent_theme_counts(limit=10)
        if total == 0:
            st.info(T.get("learning_no_data", "No learning data available."))
        else:
            st.caption(T.get("learning_preview_caption", "Themes from recent reflections.").format(total=total))
            for key in THEME_KEYS:
                label = T.get("section_labels", {}).get(key, key.replace("_", " ").title())
                count = counts.get(key, 0)
                if count:
                    st.write(f"**{label}**")
                    st.progress(count / total)
                    st.caption(T.get("learning_flagged_caption", "{count} of {total}").format(count=count, total=total))

    # --- Tab 4: Team Learning (existing aggregated, anonymous org themes) ---
    with tab_team:
        st.subheader(T.get("team_learning_title", "Team Learning"))
        st.caption(T.get("team_learning_intro", "Aggregated anonymous organisational themes."))

        window_days = 182
        since_iso = (datetime.now() - timedelta(days=window_days)).isoformat()
        team_counts = get_aggregated_theme_counts(since_iso=since_iso)
        total_team = sum(team_counts.get(k, 0) for k in THEME_KEYS)

        if total_team == 0:
            st.info(T.get("team_learning_no_data", "No organisational learning data available."))
        else:
            st.caption(T.get("team_learning_period_caption", "{total} themes identified.").format(total=total_team))
            ranked = sorted((k for k in THEME_KEYS if team_counts.get(k, 0)), key=lambda k: team_counts[k], reverse=True)
            for rank, key in enumerate(ranked, start=1):
                label = T.get("section_labels", {}).get(key, key.replace("_", " ").title())
                count = team_counts[key]
                st.write(T.get("team_learning_rank_line", "#{rank}: {theme} ({count})").format(rank=rank, theme=label, count=count))
                st.progress(count / total_team)