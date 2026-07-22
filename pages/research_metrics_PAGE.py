import streamlit as st
from services.language import init_language, render_nav
from services.visit_log import log_visit
from services.identity import init_identity, render_identity_footer
from services.research_metrics import build_research_summary, summary_to_dataframe, build_research_export_csv

# Research Metrics
# ==================
#
# Sprint 10. Prepares the app for future research/evaluation by
# surfacing organisation-wide reflection ACTIVITY -- never professional
# competence (see services/research_metrics.py for the structural
# reasoning; nothing in that module can return per-person data, so
# nothing here can render it either).
#
# Gated to System Administrator only, one tier tighter than the Team
# Learning Dashboard, because this page also offers a raw CSV export --
# even though the export itself is aggregate-only, exports are easier
# to redistribute outside the app than an on-screen dashboard, so the
# access bar is set a little higher.

T = init_language()
log_visit("research_metrics", st.session_state.lang)
user_name, user_role = init_identity(T)
render_nav(T)
render_identity_footer(T)

st.title(T["research_title"])
st.caption(T["research_intro"])

if user_role != "System Administrator":
    st.info(T["research_no_data"])
    st.stop()

WINDOW_DAYS = 182  # ~6 months, matching the Team Learning Dashboard
summary = build_research_summary(window_days=WINDOW_DAYS)

if summary["total_reflection_sessions"] == 0 and summary["feedback"]["count"] == 0:
    st.info(T["research_no_data"])
    st.stop()

st.caption(T["research_period_caption"].format(days=WINDOW_DAYS, since=summary["since"]))

# --- Activity overview ---
st.subheader(T["research_overview_header"])
col1, col2 = st.columns(2)
with col1:
    st.metric(T["research_sessions_label"], summary["total_reflection_sessions"])
with col2:
    st.metric(T["research_documents_label"], summary["total_documents_completed"])

st.divider()

# --- Theme table: flagged vs explored, side by side ---
st.subheader(T["research_theme_table_header"])
df = summary_to_dataframe(summary)
display_df = df.rename(columns={
    "theme": "theme",
    "times_flagged_by_ai": T["research_theme_flagged_col"],
    "times_explored_by_professional": T["research_theme_explored_col"],
})
display_df["theme"] = display_df["theme"].apply(
    lambda key: T["section_labels"].get(key, key.replace("_", " ").title())
)
st.dataframe(display_df, hide_index=True, use_container_width=True)

st.divider()

# --- Feedback / usefulness ratings ---
st.subheader(T["research_feedback_header"])
fb = summary["feedback"]

if fb["count"] == 0:
    st.info(T["research_feedback_no_data"])
else:
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric(T["research_feedback_count_label"], fb["count"])
    with col2:
        avg_display = f"{fb['average']:.1f} / 5" if fb["average"] is not None else "-"
        st.metric(T["research_feedback_average_label"], avg_display)
    with col3:
        st.metric(T["research_feedback_comments_label"], fb["comment_count"])

    for rating in range(5, 0, -1):
        count = fb["distribution"].get(rating, 0)
        st.write(f"{'⭐' * rating}")
        st.progress(count / fb["count"] if fb["count"] else 0)
        st.caption(str(count))

st.divider()

# --- Export ---
csv_bytes = build_research_export_csv(summary)
st.download_button(
    label=T["research_export_button"],
    data=csv_bytes,
    file_name=f"rdi_sw_research_metrics_{summary['since']}.csv",
    mime="text/csv",
)
st.caption(T["research_export_caption"])