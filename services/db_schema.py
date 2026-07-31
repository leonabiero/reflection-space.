"""
Centralized Database Schema Initialization
=============================================

Production-hardening pass (see accompanying handoff notes -- "Change
10: Centralize schema initialization").

Every storage module in services/ previously ran its own
`CREATE TABLE IF NOT EXISTS`, `ALTER TABLE ... ADD COLUMN IF NOT
EXISTS`, and `CREATE INDEX IF NOT EXISTS` statements (plus a call into
services.db_migration.ensure_timestamptz_columns()) inside its own
`_get_conn()` -- which means EVERY read or write, in every module, ran
a round trip of schema-existence checks against Postgres before doing
the actual query it was called for. Each of those checks is individually
cheap (`IF NOT EXISTS` DDL is a fast no-op once the object exists), but
they are not free, and they ran on every single database operation for
the entire lifetime of the app -- not just once at startup.

This module moves every one of those statements into ONE place,
`ensure_schema()`, which is intended to be called exactly once, at
application startup (see app.py). It is idempotent and safe to call
more than once (each individual statement is still `IF NOT EXISTS`),
but a process-local guard makes repeat calls within the same run an
instant no-op rather than re-running the checks.

Behavior is completely unchanged: this is a pure relocation of DDL
that used to live in services/draft_storage.py, feedback_store.py,
presence.py, settings_store.py, audit_log.py, reflection_log.py, and
exploration_log.py's respective `_get_conn()` functions. Table names,
column names, types, and index definitions are copied verbatim from
those modules -- see each module's own docstring/comments for the
original reasoning behind each table/index.
"""

import threading

from services.db_pool import get_conn
from services.db_migration import ensure_timestamptz_columns
from services.db_time import get_logger

logger = get_logger(__name__)

_schema_ready = False
_schema_lock = threading.Lock()


def ensure_schema():
    """
    Create every table/index this application needs, if it doesn't
    already exist, and run the one-time TEXT -> TIMESTAMPTZ column
    migrations. Call this once at startup (see app.py). Safe to call
    more than once (each statement is idempotent, and a process-local
    flag makes repeat calls in the same process an instant no-op).
    """
    global _schema_ready
    if _schema_ready:
        return

    with _schema_lock:
        if _schema_ready:
            return

        conn = get_conn()
        try:
            with conn.cursor() as c:
                # --- services/draft_storage.py: drafts / draft_history / user_activity ---
                c.execute("""
                CREATE TABLE IF NOT EXISTS drafts (
                    id SERIAL PRIMARY KEY,
                    case_ref TEXT,
                    doc_type TEXT,
                    language TEXT,
                    content TEXT,
                    created_at TEXT,
                    status TEXT,
                    created_by TEXT,
                    created_by_role TEXT
                )
                """)
                c.execute("ALTER TABLE drafts ADD COLUMN IF NOT EXISTS created_by TEXT")
                c.execute("ALTER TABLE drafts ADD COLUMN IF NOT EXISTS created_by_role TEXT")
                c.execute("ALTER TABLE drafts ADD COLUMN IF NOT EXISTS was_edited BOOLEAN DEFAULT FALSE")
                c.execute("ALTER TABLE drafts ADD COLUMN IF NOT EXISTS completed_at TEXT")
                # GDPR right-to-erasure support: soft-delete first, so an admin
                # has a short window to restore a case in case of a mistake,
                # before it is permanently purged.
                c.execute("ALTER TABLE drafts ADD COLUMN IF NOT EXISTS deleted_at TEXT")
                c.execute("ALTER TABLE drafts ADD COLUMN IF NOT EXISTS status_before_delete TEXT")
                c.execute("ALTER TABLE drafts ADD COLUMN IF NOT EXISTS deleted_by TEXT")
                c.execute("ALTER TABLE drafts ADD COLUMN IF NOT EXISTS deleted_by_role TEXT")

                c.execute("""
                CREATE TABLE IF NOT EXISTS draft_history (
                    id SERIAL PRIMARY KEY,
                    draft_id INTEGER REFERENCES drafts(id),
                    content TEXT,
                    saved_at TEXT
                )
                """)
                c.execute("""
                CREATE TABLE IF NOT EXISTS user_activity (
                    user_name TEXT PRIMARY KEY,
                    user_role TEXT,
                    last_seen TEXT
                )
                """)

                c.execute("CREATE INDEX IF NOT EXISTS idx_drafts_status_created_by ON drafts (status, created_by)")
                c.execute("CREATE INDEX IF NOT EXISTS idx_drafts_status_case_ref ON drafts (status, case_ref)")
                c.execute("CREATE INDEX IF NOT EXISTS idx_drafts_completed_at ON drafts (completed_at DESC)")
                c.execute("CREATE INDEX IF NOT EXISTS idx_drafts_deleted_status ON drafts (status) WHERE status = 'deleted'")
                c.execute("CREATE INDEX IF NOT EXISTS idx_draft_history_draft_id ON draft_history (draft_id)")
                c.execute("CREATE INDEX IF NOT EXISTS idx_user_activity_last_seen ON user_activity (last_seen DESC)")

                # --- services/feedback_store.py: feedback ---
                c.execute("""
                CREATE TABLE IF NOT EXISTS feedback (
                    id SERIAL PRIMARY KEY,
                    draft_ids TEXT,
                    rating INTEGER,
                    comment TEXT,
                    submitted_by TEXT,
                    submitted_by_role TEXT,
                    submitted_at TEXT
                )
                """)
                c.execute("CREATE INDEX IF NOT EXISTS idx_feedback_submitted_at ON feedback (submitted_at DESC)")

                # --- services/presence.py: user_presence ---
                c.execute("""
                CREATE TABLE IF NOT EXISTS user_presence (
                    professional_name TEXT PRIMARY KEY,
                    professional_role TEXT,
                    last_seen TEXT
                )
                """)
                c.execute("""
                CREATE INDEX IF NOT EXISTS idx_user_presence_role_last_seen
                ON user_presence (professional_role, last_seen DESC)
                """)

                # --- services/settings_store.py: app_settings ---
                c.execute("""
                CREATE TABLE IF NOT EXISTS app_settings (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
                """)

                # --- services/audit_log.py: audit_log ---
                c.execute("""
                CREATE TABLE IF NOT EXISTS audit_log (
                    id SERIAL PRIMARY KEY,
                    action TEXT,
                    draft_id INTEGER,
                    case_ref TEXT,
                    doc_type TEXT,
                    actor_name TEXT,
                    actor_role TEXT,
                    details TEXT,
                    occurred_at TEXT
                )
                """)
                c.execute("CREATE INDEX IF NOT EXISTS idx_audit_log_occurred_at ON audit_log (occurred_at DESC)")

                # --- services/error_log.py: error_log ---
                c.execute("""
                CREATE TABLE IF NOT EXISTS error_log (
                    id SERIAL PRIMARY KEY,
                    occurred_at TIMESTAMPTZ,
                    page TEXT,
                    error_type TEXT,
                    message TEXT,
                    traceback TEXT,
                    user_name TEXT,
                    user_role TEXT,
                    context TEXT,
                    severity TEXT,
                    screenshot TEXT
                )
                """)
                c.execute("CREATE INDEX IF NOT EXISTS idx_error_log_occurred_at ON error_log (occurred_at DESC)")
                # Phase 1 Diagnostic Engine (services/diagnostics.py):
                # holds the full structured diagnostic package (JSON
                # text) built automatically alongside every error_log
                # row. Nullable/additive -- existing rows and every
                # existing read of this table are unaffected. Nothing
                # reads this column yet (that's a later phase); it is
                # only written to, behind the scenes.
                c.execute("ALTER TABLE error_log ADD COLUMN IF NOT EXISTS diagnostic_package TEXT")
                # Phase 2 AI Diagnostic Centre (pages/system_administration.py):
                # a simple, manually-set lifecycle status per error --
                # "New" / "Investigating" / "Fixed" / "Closed". Additive and
                # nullable -- existing rows read back as NULL, and
                # services/error_log.py:get_recent_errors() treats NULL the
                # same as "New", so nothing breaks for records written before
                # this column existed.
                c.execute("ALTER TABLE error_log ADD COLUMN IF NOT EXISTS status TEXT")

                # Phase 2.1 (Stable Issue References): previously, every
                # single occurrence of the same bug got its own brand-new
                # error_log row and its own id -- so if 70 people hit the
                # identical crash, the person using the app saw 70 different
                # reference numbers, and the admin saw 70 separate-looking
                # entries (grouped only cosmetically at display time).
                #
                # error_issues is the new source of truth for "one distinct
                # problem". Every occurrence of the SAME (page, error_type,
                # message) combination, while it is still unresolved, shares
                # one row here and one stable id -- that id is what gets
                # shown to the person on screen and used as the admin's
                # reference number. Once an issue's status is set to Fixed
                # or Closed, the NEXT occurrence (if the bug isn't actually
                # fixed) no longer matches it and gets a brand-new
                # error_issues row -- a new number, as it should be, since
                # from the admin's point of view it's a fresh recurrence to
                # investigate.
                c.execute("""
                CREATE TABLE IF NOT EXISTS error_issues (
                    id SERIAL PRIMARY KEY,
                    signature TEXT NOT NULL,
                    status TEXT DEFAULT 'New',
                    severity TEXT,
                    page TEXT,
                    error_type TEXT,
                    message TEXT,
                    occurrence_count INTEGER DEFAULT 0,
                    first_seen TIMESTAMPTZ,
                    last_seen TIMESTAMPTZ,
                    resolved_at TIMESTAMPTZ
                )
                """)
                c.execute(
                    "CREATE INDEX IF NOT EXISTS idx_error_issues_signature_status "
                    "ON error_issues (signature, status)"
                )
                # Additive/nullable on error_log: old rows (written before
                # this phase) read back as NULL, and every place that reads
                # this column treats NULL exactly like the old, pre-Phase-2.1
                # behavior (falls back to the row's own id) -- so nothing
                # breaks for historical records.
                c.execute("ALTER TABLE error_log ADD COLUMN IF NOT EXISTS issue_id INTEGER")
                c.execute("CREATE INDEX IF NOT EXISTS idx_error_log_issue_id ON error_log (issue_id)")

                # --- services/reflection_log.py: reflections ---
                c.execute("""
                CREATE TABLE IF NOT EXISTS reflections (
                    id SERIAL PRIMARY KEY,
                    case_ref TEXT,
                    flags TEXT,
                    created_by TEXT,
                    created_by_role TEXT,
                    created_at TEXT
                )
                """)
                c.execute("""
                CREATE INDEX IF NOT EXISTS idx_reflections_created_at
                ON reflections (created_at DESC)
                """)

                # --- services/exploration_log.py: reflection_explorations ---
                c.execute("""
                CREATE TABLE IF NOT EXISTS reflection_explorations (
                    id SERIAL PRIMARY KEY,
                    case_ref TEXT,
                    trigger TEXT,
                    turn_count INTEGER,
                    explored_by TEXT,
                    explored_by_role TEXT,
                    explored_at TEXT
                )
                """)
                c.execute("""
                    CREATE INDEX IF NOT EXISTS idx_reflection_explorations_explored_by_at
                    ON reflection_explorations (explored_by, explored_at DESC)
                """)
                c.execute("""
                    CREATE INDEX IF NOT EXISTS idx_reflection_explorations_explored_at
                    ON reflection_explorations (explored_at)
                """)
            conn.commit()

            # One-time TEXT -> TIMESTAMPTZ migrations (see
            # services/db_migration.py). These already carry their own
            # per-table, per-process idempotency guard internally.
            ensure_timestamptz_columns(conn, "drafts", ["created_at", "completed_at", "deleted_at"])
            ensure_timestamptz_columns(conn, "draft_history", ["saved_at"])
            ensure_timestamptz_columns(conn, "user_activity", ["last_seen"])
            ensure_timestamptz_columns(conn, "feedback", ["submitted_at"])
            ensure_timestamptz_columns(conn, "user_presence", ["last_seen"])
            ensure_timestamptz_columns(conn, "audit_log", ["occurred_at"])
            ensure_timestamptz_columns(conn, "reflections", ["created_at"])
            ensure_timestamptz_columns(conn, "reflection_explorations", ["explored_at"])
        except Exception:
            conn.rollback()
            logger.exception("ensure_schema FAILED")
            raise
        finally:
            conn.close()

        _schema_ready = True
        logger.info("Database schema initialized/verified.")