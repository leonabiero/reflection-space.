"""
Shared Schema Migration Helper
=================================

Engineering-quality pass (see accompanying handoff notes, "Change 6" --
Centralize schema migration helper).

Every storage module in services/ previously carried its OWN,
byte-for-byte-nearly-identical copy of two things:

    1. A module-level `_schema_migrated = False` flag, so the (fairly
       expensive) TEXT -> TIMESTAMPTZ column migration only ever ran
       once per running process, not on every _get_conn() call.
    2. A `_ensure_timestamp_columns(conn)` function that checked
       information_schema.columns for each target column's current
       data_type, and ran `ALTER TABLE ... ALTER COLUMN ... TYPE
       TIMESTAMPTZ USING NULLIF(col, '')::timestamptz` for any column
       not already migrated.

This module replaces all of those with one shared, reusable helper:
ensure_timestamptz_columns(conn, table, columns). It is idempotent in
the exact same two layers the original per-module versions were:

    - Per-process: guarded by a module-level set of (table) names
      already confirmed migrated in THIS process, so the expensive
      information_schema check + potential ALTER TABLE only ever runs
      once per table per process, exactly like the old per-module
      `_schema_migrated` flag did for that module's own table(s).
    - Per-deployment: even if called again (a fresh process restart,
      or a second module happening to target the same table), it first
      reads back each column's current data_type and skips any column
      already 'timestamp with time zone' -- so this is always safe to
      call, on a brand-new database or one already migrated by an
      earlier deploy.

Behavior is completely unchanged from the previous per-module
implementations -- this is a pure de-duplication, not a schema or
migration-strategy change.

A note on `table` / `columns` and SQL injection (Change 3)
------------------------------------------------------------
`table` and `columns` are NEVER accepted from user input anywhere in
this codebase -- every call site below passes a hard-coded Python
string literal (e.g. "drafts", ["created_at", "completed_at"]), the
same way the original per-module versions did. psycopg2 cannot
parameterize identifiers (table/column names) the way it parameterizes
values, so this remains the one place in the app where an f-string is
used to build DDL -- exactly as it always was, just centralized. Every
actual VALUE in every query in this codebase (this module included)
continues to use %s parameter placeholders; see each calling module's
docstring for confirmation that no user-controlled value is ever
interpolated into SQL.
"""

from services.db_time import get_logger

logger = get_logger(__name__)

# Per-process guard: table names already confirmed migrated in this
# running process. Keyed by table name alone (table names are unique
# across this application's schema), so multiple modules calling this
# for different tables never collide, and calling it twice for the
# SAME table (e.g. a second module happening to touch the same table)
# is a cheap no-op after the first call.
_migrated_tables = set()


def ensure_timestamptz_columns(conn, table, columns):
    """
    Idempotently migrate `columns` on `table` from TEXT to TIMESTAMPTZ,
    if any of them aren't already.

    Parameters
    ----------
    conn : an open psycopg2 connection (NOT closed by this function --
        callers remain responsible for closing their own connection,
        per the connection-management pattern used throughout
        services/).
    table : str -- a hard-coded, trusted internal table name (never
        user input).
    columns : list[str] -- hard-coded, trusted internal column names
        (never user input).

    Commits its own transaction internally (the ALTER TABLE, if any,
    must be committed before the caller's own subsequent statements on
    that connection could rely on the new column type) -- matching the
    exact commit behavior every original per-module
    `_ensure_timestamp_columns()` already had.

    Never raises upward past a genuine database error -- if the
    information_schema check or the ALTER TABLE itself fails, that
    failure is logged (Change 7) and re-raised, since a failed schema
    migration is not something calling code can safely paper over; the
    original per-module implementations had the same behavior (an
    uncaught exception here would previously have surfaced as an
    uncaught exception from _get_conn()), this just makes the failure
    visible in the log before it propagates.
    """
    if table in _migrated_tables:
        return

    try:
        with conn.cursor() as c:
            c.execute(
                """
                SELECT column_name, data_type FROM information_schema.columns
                WHERE table_name = %s AND column_name = ANY(%s)
                """,
                (table, columns),
            )
            current_types = dict(c.fetchall())

            for col in columns:
                if current_types.get(col) == "timestamp with time zone":
                    continue
                # table/col are trusted, hard-coded internal identifiers
                # only (see module docstring) -- never user input.
                c.execute(
                    f"""
                    ALTER TABLE {table}
                    ALTER COLUMN {col} TYPE TIMESTAMPTZ
                    USING NULLIF({col}, '')::timestamptz
                    """
                )
        conn.commit()
    except Exception:
        logger.exception(
            "ensure_timestamptz_columns FAILED: table=%s columns=%s", table, columns
        )
        raise

    _migrated_tables.add(table)
    logger.info("Schema migration ensured: table=%s columns=%s", table, columns)