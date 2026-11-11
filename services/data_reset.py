"""
Erase all data ("start from zero")
====================================

November 2026, product owner's decision: everything saved in the app up
to now was synthetic (the EDE team was only trying the tool out), so the
real pilot must start from a clean slate, with every count across the
app showing 0.

`erase_all_data()` permanently empties EVERY data table in one database
transaction: reflections and their original texts, observations and
private notes, feedback, pattern reviews, old stored documents, activity
history, recorded problems and their case knowledge, cost and usage
records, and rate-limit / login-attempt counters. Number sequences are
restarted, so the next reflection, problem or pattern starts again from
number 1.

What is deliberately KEPT:
  - user accounts (they live in Streamlit secrets, not in the database);
  - sign-in sessions (`auth_sessions`) -- so nobody is thrown out of the
    app, including the administrator pressing the button;
  - application settings (`app_settings`), EXCEPT the remembered
    cost-alert levels, which are cleared so that alerts start afresh
    together with the emptied cost records.

It also removes the left-over tables of features that no longer exist
(Text analysis, Knowledge Assistant, Team Presence). They are no longer
created by services/db_schema.py, so dropping them here keeps an
existing database identical to a freshly created one.

Safety
------
- System Administrator only. The check is made HERE, not just in the
  page (pages/admin_sections/data_reset.py), which additionally asks the
  administrator to type a confirmation word.
- Never runs automatically: nothing calls this at startup.
- One transaction: either everything is erased or nothing is.
- Table names below are fixed constants (never user input), and only
  tables that actually exist are touched, so the action also works on a
  database created before or after any given feature.
- One line is written to the audit log afterwards, recording who did it
  and when (the audit log is not displayed anywhere in the app).
"""

from services.audit_log import log_action
from services.db_pool import get_conn as _acquire_pooled_conn
from services.db_time import get_logger

logger = get_logger(__name__)

ADMIN_ROLE = "System Administrator"

# Every table that holds data created by using the app. Emptied, never
# dropped. Keep in step with services/db_schema.py.
DATA_TABLES = (
    # Reflections, their texts, observations and notes
    "reflection_runs",
    "reflection_run_sources",
    "reflection_findings",
    "finding_feedback",
    "finding_embeddings",
    "reflections",
    "reflection_explorations",
    # Usefulness feedback
    "feedback",
    # Pattern Review
    "pattern_runs",
    "patterns",
    "pattern_findings",
    "pattern_events",
    # Documents stored before the reflection-only redesign
    "drafts",
    "draft_history",
    # Activity history
    "audit_log",
    "user_activity",
    # Recorded problems and their case knowledge
    "error_log",
    "error_issues",
    "error_issue_users",
    "case_resolutions",
    "case_resolution_history",
    "case_investigations",
    # Cost and usage records
    "service_usage",
    # Short-lived counters
    "reflection_rate_log",
    "login_failure_log",
    "idempotent_requests",
)

# Tables of features removed in November 2026. Dropped if still present.
RETIRED_TABLES = (
    "corpus_pattern_events",
    "corpus_pattern_passages",
    "corpus_patterns",
    "corpus_pattern_runs",
    "corpus_passage_embeddings",
    "corpus_passages",
    "corpus_readings",
    "corpus_reading_jobs",
    "corpus_terms",
    "corpus_documents",
    "corpora",
    "ka_rate_log",
    "user_presence",
)

# Remembered cost-alert levels (services/usage_alerts.py).
_USAGE_ALERT_SETTING_PREFIX = "usage_alert_last_tier__"


def _existing_tables(cursor, names):
    cursor.execute(
        """
        SELECT table_name FROM information_schema.tables
        WHERE table_schema = current_schema() AND table_name = ANY(%s)
        """,
        (list(names),),
    )
    found = {row[0] for row in cursor.fetchall()}
    return [name for name in names if name in found]


def erase_all_data(actor_name, actor_role):
    """
    Permanently erase all data saved in the app (see the module
    docstring for exactly what is erased and what is kept).

    Returns {"emptied": [table, ...], "removed": [table, ...]} on
    success, or None if refused (not a System Administrator, or no
    name). Raises if the database fails -- in which case nothing was
    erased (single transaction, rolled back).
    """
    if actor_role != ADMIN_ROLE or not actor_name:
        return None

    conn = _acquire_pooled_conn()
    emptied, removed = [], []
    try:
        with conn.cursor() as c:
            emptied = _existing_tables(c, DATA_TABLES)
            if emptied:
                # Constant, pre-checked identifiers -- never user input.
                c.execute(
                    "TRUNCATE TABLE " + ", ".join(emptied) + " RESTART IDENTITY CASCADE"
                )
            removed = _existing_tables(c, RETIRED_TABLES)
            for table in removed:
                c.execute("DROP TABLE IF EXISTS " + table + " CASCADE")
            if _existing_tables(c, ("app_settings",)):
                c.execute(
                    "DELETE FROM app_settings WHERE key LIKE %s",
                    (_USAGE_ALERT_SETTING_PREFIX + "%",),
                )
        conn.commit()
    except Exception:
        conn.rollback()
        logger.exception("erase_all_data FAILED (rolled back, nothing erased)")
        raise
    finally:
        conn.close()

    logger.warning(
        "erase_all_data: all application data erased (%d table(s) emptied, %d retired table(s) removed)",
        len(emptied), len(removed),
    )
    try:
        log_action(
            "purged", None, "", "all data", actor_name, actor_role,
            details=(
                f"erased all application data: {len(emptied)} table(s) emptied, "
                f"{len(removed)} retired table(s) removed"
            ),
        )
    except Exception:
        # The erase itself succeeded; a failed audit line must not make
        # it look as if it had not.
        logger.exception("erase_all_data: could not write the audit line")
    return {"emptied": emptied, "removed": removed}
