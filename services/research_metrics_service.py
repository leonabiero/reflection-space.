import io
import pandas as pd
from datetime import datetime, timedelta

from services.reflection_log import get_theme_flag_counts, get_total_reflection_count, THEME_KEYS
from services.exploration_log import get_aggregated_theme_counts
from services.feedback_store import get_feedback_summary
from services.draft_storage import get_completed_draft_count

# Research Metrics
# ==================
#
# Sprint 10. Prepares the app for future research and evaluation by
# aggregating what Sprints 4-9 already log into one activity-based
# summary.
#
# Hard rule (Feature 5 in the product requirements): these metrics
# measure REFLECTION ACTIVITY, never professional competence. This
# module never computes or returns:
#   - a score, grade, or rating for any individual professional
#   - a ranking or leaderboard of any kind
#   - anything that could be read as "how good is this person at
#     reflecting"
#
# Every function here returns organisation-wide totals only. None of
# them accept or filter by a professional's name -- that's a
# structural choice, not just a UI omission: there is no parameter
# anywhere in this module through which per-person data could enter
# the result.


def build_research_summary(window_days=182):
    """
    Build one aggregate summary dict covering the last `window_days`
    (default ~6 months, matching the Team Learning Dashboard's window).

    Returns:
        {
            "window_days": int,
            "since": str (ISO date),
            "total_reflection_sessions": int,
            "total_documents_completed": int,
            "theme_flag_counts": {theme_key: int},      # AI raised it
            "theme_explore_counts": {theme_key: int},   # practitioner explored it
            "feedback": {
                "count": int, "average": float|None,
                "distribution": {1..5: int}, "comment_count": int,
            },
        }
    """
    since_iso = (datetime.now() - timedelta(days=window_days)).isoformat()

    return {
        "window_days": window_days,
        "since": since_iso[:10],
        "total_reflection_sessions": get_total_reflection_count(since_iso=since_iso),
        "total_documents_completed": get_completed_draft_count(since_iso=since_iso),
        "theme_flag_counts": get_theme_flag_counts(since_iso=since_iso),
        "theme_explore_counts": get_aggregated_theme_counts(since_iso=since_iso),
        "feedback": get_feedback_summary(),
    }


def summary_to_dataframe(summary):
    """
    Reshape build_research_summary()'s output into one flat,
    research-friendly table: one row per theme, with both the
    "flagged by AI" count and the "explored by a professional" count
    side by side -- useful for questions like "which flagged themes
    actually get engaged with". No professional or case columns exist
    in this table, by construction.
    """
    flag_counts = summary["theme_flag_counts"]
    explore_counts = summary["theme_explore_counts"]

    rows = []
    for key in THEME_KEYS:
        rows.append({
            "theme": key,
            "times_flagged_by_ai": flag_counts.get(key, 0),
            "times_explored_by_professional": explore_counts.get(key, 0),
        })
    return pd.DataFrame(rows)


def build_research_export_csv(summary):
    """
    Produce a downloadable CSV (as bytes) for a researcher: the per-theme
    table plus a short header block of the org-wide totals and feedback
    summary. Everything in this export is an aggregate count -- no
    document text, no case references, no professional names anywhere
    in the file.
    """
    buffer = io.StringIO()

    buffer.write("RDI-SW Research Metrics Export\n")
    buffer.write(f"window_days,{summary['window_days']}\n")
    buffer.write(f"since,{summary['since']}\n")
    buffer.write(f"total_reflection_sessions,{summary['total_reflection_sessions']}\n")
    buffer.write(f"total_documents_completed,{summary['total_documents_completed']}\n")
    fb = summary["feedback"]
    buffer.write(f"feedback_count,{fb['count']}\n")
    buffer.write(f"feedback_average,{fb['average'] if fb['average'] is not None else ''}\n")
    buffer.write(f"feedback_comment_count,{fb['comment_count']}\n")
    for rating, count in sorted(fb["distribution"].items()):
        buffer.write(f"feedback_rating_{rating}_count,{count}\n")
    buffer.write("\n")

    df = summary_to_dataframe(summary)
    buffer.write(df.to_csv(index=False))

    return buffer.getvalue().encode("utf-8")