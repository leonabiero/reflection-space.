import streamlit as st
from datetime import datetime, timedelta
from services.language import init_language, render_nav
from services.visit_log import log_visit
from services.identity import init_identity, render_identity_footer, can_see_case_history
from services.exploration_log import get_aggregated_theme_counts
from services.reflection_log import THEME_KEYS

# Team Learning Dashboard
# =========================
#
# Sprint 9. Lets the ORGANISATION learn from collective reflection
# patterns -- distinct from pages/learning.py (which shows themes the
# AI companions flagged) and from pages/growth_dashboard.py (which is
# one professional's own, private history).
#
# Hard privacy rules this page must never break (see Feature 3 in the
# product requirements):
#   - Must NOT expose any individual professional.
#   - Must NOT expose any individual case.
#   - Must NOT expose anyone's personal reflection history.
#   - Only aggregated, anonymous counts -- "what areas of practice
#     deserve collective attention", never "who is performing poorly".
#
# This is enforced structurally, not just by convention:
# get_aggregated_theme_counts() (services/exploration_log.py) only ever
# returns a theme -> count dict via a GROUP BY query -- there is no
# per-professional or per-case field anywhere in what it returns, so
# there's nothing here that COULD render a name or a case reference
# even by accident.
#
# Reuses can_see_case_history() for the same supervisory-role gate
# already used by Learning, Case History, and the Audit Log, rather
# than inventing a new visibility tier.

T = init_language()
log_visit("team_learning", st.session_state.lang)
user_name, user_role = init_identity(T)
render_nav(T)
render_identity_footer(T)

st.title(T["team_learning_title"])
st.caption(T["team_learning_intro"])

if not can_see_case_history(user_role):
    st.info(T["team_learning_no_data"])
    st.stop()

WINDOW_DAYS = 182  # ~6 months
since_iso = (datetime.now() - timedelta(days=WINDOW_DAYS)).isoformat()

counts = get_aggregated_theme_counts(since_iso=since_iso)
total = sum(counts.get(key, 0) for key in THEME_KEYS)

if total == 0:
    st.info(T["team_learning_no_data"])
    st.stop()

st.caption(T["team_learning_period_caption"].format(total=total))

st.subheader(T["team_learning_header"])

ranked = sorted(
    (key for key in THEME_KEYS if counts.get(key, 0) > 0),
    key=lambda k: counts[k],
    reverse=True,
)

for rank, key in enumerate(ranked, start=1):
    theme_label = T["section_labels"].get(key, key.replace("_", " ").title())
    count = counts[key]
    st.write(T["team_learning_rank_line"].format(rank=rank, theme=theme_label, count=count))
    st.progress(count / total)