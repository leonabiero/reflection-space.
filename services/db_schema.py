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

September-pilot follow-up: services/rate_limiter.py and
services/login_rate_limiter.py were NOT part of the original pass
above -- they still ran their own CREATE TABLE IF NOT EXISTS on every
call, using a raw (non-pooled) psycopg2.connect(), on two of the
highest-frequency paths in the app (every reflection generation, every
login attempt). Their tables (reflection_rate_log, login_failure_log)
are now created here too, and both modules were switched to
services.db_pool.get_conn() -- see those modules' own comments.
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
                c.execute("CREATE INDEX IF NOT EXISTS idx_drafts_case_ref ON drafts (case_ref)")
                c.execute("CREATE INDEX IF NOT EXISTS idx_drafts_completed_at ON drafts (completed_at DESC)")
                c.execute("CREATE INDEX IF NOT EXISTS idx_drafts_deleted_status ON drafts (status) WHERE status = 'deleted'")
                # Scalability pass (September pilot hardening): composite,
                # sort-covering indexes for services/draft_storage.py's
                # get_completed_drafts(case_ref=..., date_filter=...) and
                # get_completed_draft_dates() -- both now filter (and, for
                # the case_ref path, order) in SQL instead of in Python,
                # per that module's docstring. idx_drafts_status_case_ref
                # above supports the equality filter but not the
                # `ORDER BY completed_at DESC`; these add completed_at so
                # that ordering can also use the index.
                c.execute("CREATE INDEX IF NOT EXISTS idx_drafts_case_ref_status_completed_at ON drafts (case_ref, status, completed_at DESC)")
                c.execute("CREATE INDEX IF NOT EXISTS idx_drafts_status_completed_at ON drafts (status, completed_at DESC)")
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

                # --- services/session_store.py: auth_sessions ---
                # Persistent login sessions (survive a browser refresh)
                # -- see config.py's "Persistent login sessions" block
                # and services/session_store.py for the full design.
                # New table, so TIMESTAMPTZ columns are used natively
                # from creation -- no ensure_timestamptz_columns() call
                # is needed for this one (compare user_presence, drafts,
                # etc. below, which started out as plain TEXT columns).
                c.execute("""
                CREATE TABLE IF NOT EXISTS auth_sessions (
                    session_id TEXT PRIMARY KEY,
                    username TEXT NOT NULL,
                    active_work_mode TEXT,
                    created_at TIMESTAMPTZ,
                    last_seen_at TIMESTAMPTZ,
                    expires_at TIMESTAMPTZ
                )
                """)
                c.execute("CREATE INDEX IF NOT EXISTS idx_auth_sessions_expires_at ON auth_sessions (expires_at)")
                c.execute("CREATE INDEX IF NOT EXISTS idx_auth_sessions_username ON auth_sessions (username)")

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
                # Phase 3: the screenshot subsystem has been retired --
                # the "screenshot" column below is kept ONLY so older
                # rows written before Phase 3 continue to load and
                # display correctly in System Administration > AI
                # Diagnostic Centre. No code writes to this column
                # anymore (see services/error_log.py:log_error); every
                # new row leaves it NULL.
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

                # Phase 2 (Issue Tracking): replaces exact-string
                # (page, error_type, message) matching with a stable
                # Diagnostic Fingerprint (see
                # services/issue_fingerprint.py) -- so the SAME
                # underlying bug is recognised as the same issue even
                # when the message text differs between occurrences.
                # `signature` (above) is kept for backward
                # compatibility with rows/reads that predate this
                # phase -- it is no longer used for matching, only as
                # a legacy display fallback.
                #
                # Additive/nullable, exactly like every other
                # cross-phase column here: existing rows read back
                # with fingerprint = NULL and simply won't be matched
                # against by the new fingerprint-based lookup -- the
                # next occurrence of an old, un-fingerprinted issue
                # gets its own new, correctly-fingerprinted issue
                # rather than risking an incorrect merge.
                c.execute("ALTER TABLE error_issues ADD COLUMN IF NOT EXISTS fingerprint TEXT")
                c.execute(
                    "CREATE INDEX IF NOT EXISTS idx_error_issues_fingerprint "
                    "ON error_issues (fingerprint)"
                )
                # A short, human-scannable title (e.g. "AI / Claude API
                # failure in generate_companion_reflection
                # (reflection_space)") -- see
                # services/error_log.py:_build_issue_title.
                c.execute("ALTER TABLE error_issues ADD COLUMN IF NOT EXISTS title TEXT")
                # The same category a reader sees on this issue's own
                # occurrences' AI prompts (see
                # services/diagnostics.py:categorize_error) -- stored
                # here too so the Issue list itself can show/filter by
                # it without re-parsing a diagnostic package.
                c.execute("ALTER TABLE error_issues ADD COLUMN IF NOT EXISTS category TEXT")
                # A more technical, mechanism-level classification (see
                # services/issue_fingerprint.py:classify_root_cause) --
                # deliberately a SEPARATE field from category: category
                # answers "which part of the system", this answers
                # "what kind of failure, mechanically".
                c.execute("ALTER TABLE error_issues ADD COLUMN IF NOT EXISTS root_cause_classification TEXT")
                # A one-line, human-readable summary of the issue (see
                # services/diagnostics.py:build_error_summary) -- the
                # same summary text shown on an occurrence's own
                # diagnostic package, but attached to the issue too so
                # the issue list can show it without opening one.
                c.execute("ALTER TABLE error_issues ADD COLUMN IF NOT EXISTS summary TEXT")
                # How many DISTINCT users have hit this issue -- kept
                # up to date by services/error_log.py:_record_affected_user
                # every time an occurrence is logged. Distinct from
                # occurrence_count (above), which counts EVENTS, not
                # people -- one person retrying the same broken action
                # five times is 5 occurrences but 1 affected user.
                c.execute("ALTER TABLE error_issues ADD COLUMN IF NOT EXISTS affected_user_count INTEGER DEFAULT 0")

                # error_issue_users: which named users have hit which
                # issue -- purely so affected_user_count (above) can be
                # computed as a true DISTINCT count rather than a
                # naive increment-every-time counter (which would
                # double-count the same person retrying repeatedly).
                # Anonymous occurrences (no user_name) are simply never
                # inserted here -- see _record_affected_user.
                c.execute("""
                CREATE TABLE IF NOT EXISTS error_issue_users (
                    id SERIAL PRIMARY KEY,
                    issue_id INTEGER NOT NULL REFERENCES error_issues(id),
                    user_name TEXT NOT NULL,
                    first_seen TIMESTAMPTZ,
                    last_seen TIMESTAMPTZ,
                    UNIQUE (issue_id, user_name)
                )
                """)
                c.execute(
                    "CREATE INDEX IF NOT EXISTS idx_error_issue_users_issue_id "
                    "ON error_issue_users (issue_id)"
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

                # --- Phase 4 (services/case_knowledge.py): Operational Knowledge Base ---
                #
                # error_issues (above) is already the stable "one distinct
                # problem" record. Phase 4 adds three additive tables on top
                # of it -- nothing here changes error_issues or error_log.
                #
                # case_resolutions: the CURRENT resolution + case-knowledge
                # fields for one issue (one row per issue_id, upserted).
                c.execute("""
                CREATE TABLE IF NOT EXISTS case_resolutions (
                    id SERIAL PRIMARY KEY,
                    issue_id INTEGER NOT NULL UNIQUE REFERENCES error_issues(id),
                    resolution_summary TEXT,
                    root_cause TEXT,
                    fix_applied TEXT,
                    version_fixed TEXT,
                    deployment_date TEXT,
                    lessons_learned TEXT,
                    prevention_notes TEXT,
                    common_cause TEXT,
                    known_fix TEXT,
                    known_workaround TEXT,
                    documentation_link TEXT,
                    git_commit TEXT,
                    external_reference TEXT,
                    updated_at TIMESTAMPTZ,
                    updated_by TEXT,
                    updated_by_role TEXT
                )
                """)

                # case_resolution_history: a snapshot of case_resolutions,
                # taken automatically the moment a Fixed/Closed issue
                # recurs (see services/error_log.py:_get_or_create_issue
                # and services/case_knowledge.py:snapshot_resolution_on_reopen)
                # -- so the PREVIOUS investigation is never lost, even
                # though case_resolutions itself is about to be edited
                # again for the new occurrence.
                c.execute("""
                CREATE TABLE IF NOT EXISTS case_resolution_history (
                    id SERIAL PRIMARY KEY,
                    issue_id INTEGER NOT NULL,
                    snapshot_data TEXT,
                    occurrence_count_at_reopen INTEGER,
                    reopened_at TIMESTAMPTZ
                )
                """)
                c.execute("""
                    CREATE INDEX IF NOT EXISTS idx_case_resolution_history_issue_id
                    ON case_resolution_history (issue_id, reopened_at DESC)
                """)

                # case_investigations: every AI (or manual) investigation
                # an administrator chooses to preserve for an issue. One
                # issue can have many rows here -- Reflection Space never
                # calls an AI on its own; this is purely a place to paste
                # work that was already done elsewhere.
                c.execute("""
                CREATE TABLE IF NOT EXISTS case_investigations (
                    id SERIAL PRIMARY KEY,
                    issue_id INTEGER NOT NULL,
                    investigated_at TIMESTAMPTZ,
                    tool_used TEXT,
                    prompt TEXT,
                    ai_response TEXT,
                    admin_notes TEXT,
                    created_by TEXT,
                    created_by_role TEXT
                )
                """)
                c.execute("""
                    CREATE INDEX IF NOT EXISTS idx_case_investigations_issue_id
                    ON case_investigations (issue_id, investigated_at DESC)
                """)

                # --- services/rate_limiter.py: reflection_rate_log ---
                # Scalability pass (September pilot hardening, "Change 9:
                # Connection pooling"): this table's CREATE TABLE IF NOT
                # EXISTS used to run inside rate_limiter.py's own
                # _get_conn(), on a RAW (non-pooled) psycopg2.connect()
                # call, on every single reflection generation -- one of
                # the highest-frequency paths in the app. Relocated here,
                # verbatim, alongside every other table's schema.
                c.execute("""
                CREATE TABLE IF NOT EXISTS reflection_rate_log (
                    id SERIAL PRIMARY KEY,
                    user_name TEXT,
                    occurred_at TEXT
                )
                """)
                c.execute("""
                    CREATE INDEX IF NOT EXISTS idx_reflection_rate_log_user_occurred
                    ON reflection_rate_log (user_name, occurred_at)
                """)

                # --- services/login_rate_limiter.py: login_failure_log ---
                # Same fix, same reasoning, applied to the login lockout
                # table -- this used to run its own raw CREATE TABLE IF
                # NOT EXISTS on every login attempt (success or failure)
                # across the whole pilot's user base.
                c.execute("""
                CREATE TABLE IF NOT EXISTS login_failure_log (
                    id SERIAL PRIMARY KEY,
                    username TEXT,
                    occurred_at TEXT
                )
                """)
                c.execute("""
                    CREATE INDEX IF NOT EXISTS idx_login_failure_log_username_occurred
                    ON login_failure_log (username, occurred_at)
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