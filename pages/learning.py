import streamlit as st
from datetime import datetime, timedelta
from services.language import init_language
from navigation.router import render_nav
from services.identity import init_identity, render_identity_footer, can_see_learning
from services.reflection_log import get_recent_theme_counts, THEME_KEYS
from services.exploration_log import get_aggregated_theme_counts

T = init_language()
user_name, user_role = init_identity(T)
render_nav(T)
render_identity_footer(T)

if not can_see_learning(user_role):
    st.info(T.get("learning_no_data", "No access."))
    st.stop()

st.title(T["nav_learning"])

# Practitioner/practice learning insights
st.subheader(T.get("learning_phase2", "Learning Insights"))
counts, total = get_recent_theme_counts(limit=10)
if total == 0:
    st.info(T.get("learning_no_data", "No learning data available."))
else:
    st.caption(T.get("learning_preview_caption", "Themes from recent reflections.").format(total=total))
    for i, key in enumerate(THEME_KEYS):
        # NOTE (fix): T["themes"] is a positional LIST (index 0..7, same
        # order as THEME_KEYS), not a dict -- it was never safe to call
        # .get(i, ...) on it. The old `isinstance(..., dict)` guard
        # always evaluated False against that list, so every reflection
        # theme silently fell back to its raw snake_case key (e.g.
        # "client_voice" instead of "Client's Voice" / "Voz de la
        # persona"). T["section_labels"] is a proper {theme_key: label}
        # dict -- already used correctly everywhere else in the app
        # (growth_dashboard.py, research_metrics_PAGE.py, and the Team
        # Learning section further down this same page) -- so we use it
        # here too instead of the broken positional lookup.
        label = T.get("section_labels", {}).get(key, key.replace("_", " ").title())
        count = counts.get(key, 0)
        if count:
            st.write(f"**{label}**")
            st.progress(count / total)
            st.caption(T.get("learning_flagged_caption", "{count} of {total}").format(count=count, total=total))

st.divider()

# Team Learning migration: anonymous organisational themes
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