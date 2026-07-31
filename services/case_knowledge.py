"""
Case Knowledge (Phase 4)
============================

Purpose
---------
Phases 1-3 built a strong DIAGNOSTIC system: every problem, whether an
automatic exception or a user-submitted report, is captured as a
complete, structured AI Diagnostic Package the moment it happens (see
services/diagnostics.py), and Phase 2.1 gave every distinct problem a
single stable reference (error_issues -- see services/error_log.py).

Phase 4 does NOT collect more evidence. It turns the issues that
already exist into a growing operational knowledge base, so that the
next time something breaks, the administrator can answer:

    Have we seen this before?
    How was it fixed?
    Did the AI help?
    Has it happened again?

This module owns three new, additive tables (created centrally in
services/db_schema.py, exactly like every other table in this app):

    case_resolutions          -- the CURRENT resolution + case-knowledge
                                  fields for one issue (one row per
                                  issue_id, upserted every time it's
                                  saved).
    case_resolution_history   -- snapshots of case_resolutions, taken
                                  automatically the moment a Fixed/Closed
                                  issue recurs, so the previous
                                  investigation is never lost.
    case_investigations       -- every AI (or manual) investigation an
                                  administrator chooses to preserve for
                                  an issue. Reflection Space never calls
                                  an AI on its own here -- this is purely
                                  a place to paste work already done
                                  elsewhere (ChatGPT, Claude, Gemini,
                                  manual investigation).

Nothing in this module duplicates information already stored in the
AI Diagnostic Package -- it only EXTENDS an existing error_issues row
with the knowledge an administrator builds up while resolving it.

Design follows the same pattern as services/error_log.py: a pooled
connection (services/db_pool.py), explicit commit/rollback, and the
connection always returned via try/finally. Every public function here
is defensive -- it must never raise, and never prevent whatever the
caller was doing (logging an error, rendering the AI Diagnostic
Centre) from completing.
"""

import json
import re
from collections import defaultdict

from services.db_pool import get_conn as _acquire_pooled_conn
from services.db_time import now_utc, iso, get_logger

logger = get_logger(__name__)


def _get_conn():
    return _acquire_pooled_conn()


# ---------------------------------------------------------------------
# Resolution Workflow + Case Knowledge
# ---------------------------------------------------------------------
RESOLUTION_FIELDS = [
    "resolution_summary",
    "root_cause",
    "fix_applied",
    "version_fixed",
    "deployment_date",
    "lessons_learned",
    "prevention_notes",
]

CASE_KNOWLEDGE_FIELDS = [
    "common_cause",
    "known_fix",
    "known_workaround",
    "documentation_link",
    "git_commit",
    "external_reference",
]

_ALL_RESOLUTION_COLUMNS = RESOLUTION_FIELDS + CASE_KNOWLEDGE_FIELDS


def get_resolution(issue_id):
    """
    Returns the current resolution + case-knowledge dict for one issue,
    or None if nothing has been saved for it yet. Never raises.
    """
    conn = None
    try:
        conn = _get_conn()
        with conn.cursor() as c:
            c.execute(
                f"""
                SELECT {", ".join(_ALL_RESOLUTION_COLUMNS)}, updated_at, updated_by, updated_by_role
                FROM case_resolutions WHERE issue_id = %s
                """,
                (issue_id,),
            )
            row = c.fetchone()
    except Exception:
        logger.exception("get_resolution FAILED for issue_id=%s", issue_id)
        return None
    finally:
        if conn is not None:
            conn.close()

    if not row:
        return None
    data = dict(zip(_ALL_RESOLUTION_COLUMNS + ["updated_at", "updated_by", "updated_by_role"], row))
    data["updated_at"] = iso(data.get("updated_at"))
    return data


def save_resolution(issue_id, fields, actor_name="", actor_role=""):
    """
    Upserts the resolution + case-knowledge fields for one issue.
    `fields` is a dict that may contain any subset of
    RESOLUTION_FIELDS / CASE_KNOWLEDGE_FIELDS -- any key not present
    is stored as NULL (all fields are optional per the Phase 4 spec).

    Never raises. Returns True on success, False if the write failed.
    """
    clean = {key: (fields.get(key) or None) for key in _ALL_RESOLUTION_COLUMNS}
    conn = None
    try:
        conn = _get_conn()
        with conn.cursor() as c:
            columns_sql = ", ".join(_ALL_RESOLUTION_COLUMNS)
            placeholders_sql = ", ".join(["%s"] * len(_ALL_RESOLUTION_COLUMNS))
            update_sql = ", ".join(f"{col} = EXCLUDED.{col}" for col in _ALL_RESOLUTION_COLUMNS)
            c.execute(
                f"""
                INSERT INTO case_resolutions
                    (issue_id, {columns_sql}, updated_at, updated_by, updated_by_role)
                VALUES (%s, {placeholders_sql}, %s, %s, %s)
                ON CONFLICT (issue_id) DO UPDATE SET
                    {update_sql},
                    updated_at = EXCLUDED.updated_at,
                    updated_by = EXCLUDED.updated_by,
                    updated_by_role = EXCLUDED.updated_by_role
                """,
                (
                    issue_id,
                    *[clean[key] for key in _ALL_RESOLUTION_COLUMNS],
                    now_utc(),
                    actor_name,
                    actor_role,
                ),
            )
        conn.commit()
        return True
    except Exception:
        if conn is not None:
            try:
                conn.rollback()
            except Exception:
                pass
        logger.exception("save_resolution FAILED for issue_id=%s", issue_id)
        return False
    finally:
        if conn is not None:
            conn.close()


def get_resolution_history(issue_id):
    """
    Returns every preserved resolution snapshot for an issue (most
    recent reopening first), each as:
        {"reopened_at": iso str, "occurrence_count_at_reopen": int,
         "snapshot_data": {...resolution fields at that time...}}
    Never raises -- returns an empty list on failure.
    """
    conn = None
    try:
        conn = _get_conn()
        with conn.cursor() as c:
            c.execute(
                """
                SELECT snapshot_data, occurrence_count_at_reopen, reopened_at
                FROM case_resolution_history
                WHERE issue_id = %s
                ORDER BY reopened_at DESC
                """,
                (issue_id,),
            )
            rows = c.fetchall()
    except Exception:
        logger.exception("get_resolution_history FAILED for issue_id=%s", issue_id)
        return []
    finally:
        if conn is not None:
            conn.close()

    history = []
    for snapshot_json, occ_count, reopened_at in rows:
        try:
            snapshot = json.loads(snapshot_json) if snapshot_json else {}
        except Exception:
            snapshot = {}
        history.append({
            "snapshot_data": snapshot,
            "occurrence_count_at_reopen": occ_count,
            "reopened_at": iso(reopened_at),
        })
    return history


def snapshot_resolution_on_reopen(issue_id):
    """
    Phase 4 REOPENING behavior: called by
    services/error_log.py:_get_or_create_issue the moment it detects
    that an issue which was Fixed or Closed has just recurred.

    Copies whatever is currently in case_resolutions for this issue
    into case_resolution_history (tagged with the occurrence count at
    the moment of reopening), so the PREVIOUS investigation and
    resolution are preserved even though the administrator may go on
    to edit/overwrite case_resolutions with fresh information about
    the new occurrence.

    If no resolution had ever been saved for this issue, there is
    nothing to preserve -- this is a no-op (not a failure).

    Never raises. Returns True on success (including the no-op case),
    False only if the database work itself failed.
    """
    conn = None
    try:
        conn = _get_conn()
        with conn.cursor() as c:
            c.execute(
                f"SELECT {', '.join(_ALL_RESOLUTION_COLUMNS)} FROM case_resolutions WHERE issue_id = %s",
                (issue_id,),
            )
            row = c.fetchone()
            if not row:
                return True  # nothing to preserve -- not an error

            resolution = dict(zip(_ALL_RESOLUTION_COLUMNS, row))
            # If every field is empty there's genuinely nothing worth
            # preserving either (e.g. a resolution row that was
            # upserted but never actually filled in).
            if not any(resolution.values()):
                return True

            c.execute("SELECT occurrence_count FROM error_issues WHERE id = %s", (issue_id,))
            occ_row = c.fetchone()
            occurrence_count = occ_row[0] if occ_row else None

            c.execute(
                """
                INSERT INTO case_resolution_history
                    (issue_id, snapshot_data, occurrence_count_at_reopen, reopened_at)
                VALUES (%s, %s, %s, %s)
                """,
                (issue_id, json.dumps(resolution, default=str), occurrence_count, now_utc()),
            )
        conn.commit()
        return True
    except Exception:
        if conn is not None:
            try:
                conn.rollback()
            except Exception:
                pass
        logger.exception("snapshot_resolution_on_reopen FAILED for issue_id=%s", issue_id)
        return False
    finally:
        if conn is not None:
            conn.close()


# ---------------------------------------------------------------------
# AI Investigation History
# ---------------------------------------------------------------------
def add_investigation(issue_id, tool_used, prompt, ai_response, admin_notes="",
                       actor_name="", actor_role=""):
    """
    Preserves one AI (or manual) investigation for an issue. Does NOT
    call any AI itself -- this is purely a place to paste work already
    done elsewhere. Returns the new row's id, or None on failure.
    """
    conn = None
    try:
        conn = _get_conn()
        with conn.cursor() as c:
            c.execute(
                """
                INSERT INTO case_investigations
                    (issue_id, investigated_at, tool_used, prompt, ai_response,
                     admin_notes, created_by, created_by_role)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (issue_id, now_utc(), tool_used, prompt, ai_response,
                 admin_notes, actor_name, actor_role),
            )
            new_id = c.fetchone()[0]
        conn.commit()
        return new_id
    except Exception:
        if conn is not None:
            try:
                conn.rollback()
            except Exception:
                pass
        logger.exception("add_investigation FAILED for issue_id=%s", issue_id)
        return None
    finally:
        if conn is not None:
            conn.close()


def get_investigations(issue_id):
    """
    Returns every preserved investigation for an issue, newest first,
    as a list of dicts. Never raises -- returns an empty list on
    failure.
    """
    conn = None
    try:
        conn = _get_conn()
        with conn.cursor() as c:
            c.execute(
                """
                SELECT id, investigated_at, tool_used, prompt, ai_response,
                       admin_notes, created_by, created_by_role
                FROM case_investigations
                WHERE issue_id = %s
                ORDER BY investigated_at DESC
                """,
                (issue_id,),
            )
            rows = c.fetchall()
    except Exception:
        logger.exception("get_investigations FAILED for issue_id=%s", issue_id)
        return []
    finally:
        if conn is not None:
            conn.close()

    return [
        {
            "id": rid,
            "investigated_at": iso(investigated_at),
            "tool_used": tool_used,
            "prompt": prompt,
            "ai_response": ai_response,
            "admin_notes": admin_notes,
            "created_by": created_by,
            "created_by_role": created_by_role,
        }
        for (rid, investigated_at, tool_used, prompt, ai_response,
             admin_notes, created_by, created_by_role) in rows
    ]


def delete_investigation(investigation_id):
    """Removes one preserved investigation entry (e.g. added by
    mistake). Never raises. Returns True on success, False on failure."""
    conn = None
    try:
        conn = _get_conn()
        with conn.cursor() as c:
            c.execute("DELETE FROM case_investigations WHERE id = %s", (investigation_id,))
        conn.commit()
        return True
    except Exception:
        if conn is not None:
            try:
                conn.rollback()
            except Exception:
                pass
        logger.exception("delete_investigation FAILED for id=%s", investigation_id)
        return False
    finally:
        if conn is not None:
            conn.close()


# ---------------------------------------------------------------------
# Possible Similar Issues -- simple heuristics, no AI clustering
# ---------------------------------------------------------------------
_FILE_RE = re.compile(r'File "([^"]+)"')


def _extract_files(traceback_text):
    if not traceback_text:
        return set()
    return set(_FILE_RE.findall(traceback_text))


def _first_words(text, n=6):
    if not text:
        return ""
    return " ".join(str(text).split()[:n]).lower()


def find_similar_issues(issue_id, page, error_type, message, traceback_text="", limit=6):
    """
    "Possible Similar Issues": plain heuristics only, deliberately NOT
    AI clustering -- the administrator decides whether these are
    actually related. An issue is considered a candidate if it shares
    any of: the same exception type, the same page, an overlapping
    file in its traceback (same file/component), or a similar-looking
    message (same first few words -- a crude but honest proxy for
    "same traceback signature").

    Returns up to `limit` candidates, highest-scoring first, each as:
        {"issue_id", "page", "error_type", "message", "status",
         "occurrence_count", "last_seen", "score", "reasons": [str, ...]}

    Never raises -- returns an empty list on failure.
    """
    conn = None
    try:
        conn = _get_conn()
        with conn.cursor() as c:
            c.execute(
                """
                SELECT ei.id, ei.page, ei.error_type, ei.message, ei.status,
                       ei.occurrence_count, ei.last_seen,
                       (SELECT traceback FROM error_log
                        WHERE issue_id = ei.id ORDER BY occurred_at DESC LIMIT 1) AS tb
                FROM error_issues ei
                WHERE ei.id != %s
                ORDER BY ei.last_seen DESC
                LIMIT 300
                """,
                (issue_id,),
            )
            rows = c.fetchall()
    except Exception:
        logger.exception("find_similar_issues FAILED for issue_id=%s", issue_id)
        return []
    finally:
        if conn is not None:
            conn.close()

    my_files = _extract_files(traceback_text)
    my_words = _first_words(message)

    candidates = []
    for (oid, opage, oerror_type, omessage, ostatus, occ, last_seen, otb) in rows:
        score = 0
        reasons = []
        if error_type and oerror_type == error_type:
            score += 2
            reasons.append("Same exception")
        if page and opage == page:
            score += 1
            reasons.append("Same page")
        shared_files = my_files & _extract_files(otb)
        if shared_files:
            score += 2
            reasons.append("Same file / traceback signature")
        if my_words and _first_words(omessage) == my_words:
            score += 1
            reasons.append("Same component")
        if score > 0:
            candidates.append({
                "issue_id": oid,
                "page": opage,
                "error_type": oerror_type,
                "message": omessage,
                "status": ostatus,
                "occurrence_count": occ,
                "last_seen": iso(last_seen),
                "score": score,
                "reasons": reasons,
            })

    candidates.sort(key=lambda c: c["score"], reverse=True)
    return candidates[:limit]


# ---------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------
def search_cases(root_cause=None, resolution=None, lesson=None, ai_tool=None,
                  status=None, version_fixed=None, min_occurrences=None,
                  page=None, exception_type=None, user=None, limit=100):
    """
    Searches across issues + their case knowledge + their AI
    investigations. Every parameter is optional; only the ones
    provided (non-empty) are applied as filters (ANDed together).

    Returns a list of dicts (newest-last-seen first), each a light
    summary suitable for display -- NOT the full case (use
    build_case_export for that): {"issue_id", "page", "error_type",
    "message", "status", "occurrence_count", "first_seen",
    "last_seen", "resolution_summary", "root_cause",
    "lessons_learned", "version_fixed"}.

    Never raises -- returns an empty list on failure.
    """
    clauses = []
    params = []
    joins = ["LEFT JOIN case_resolutions cr ON cr.issue_id = ei.id"]

    if ai_tool:
        joins.append("LEFT JOIN case_investigations ci ON ci.issue_id = ei.id")
    if user:
        joins.append("LEFT JOIN error_log el ON el.issue_id = ei.id")

    if status:
        clauses.append("ei.status = %s")
        params.append(status)
    if page:
        clauses.append("ei.page ILIKE %s")
        params.append(f"%{page}%")
    if exception_type:
        clauses.append("ei.error_type ILIKE %s")
        params.append(f"%{exception_type}%")
    if min_occurrences:
        clauses.append("ei.occurrence_count >= %s")
        params.append(min_occurrences)
    if version_fixed:
        clauses.append("cr.version_fixed ILIKE %s")
        params.append(f"%{version_fixed}%")
    if root_cause:
        clauses.append("cr.root_cause ILIKE %s")
        params.append(f"%{root_cause}%")
    if resolution:
        clauses.append("cr.resolution_summary ILIKE %s")
        params.append(f"%{resolution}%")
    if lesson:
        clauses.append("cr.lessons_learned ILIKE %s")
        params.append(f"%{lesson}%")
    if ai_tool:
        clauses.append("ci.tool_used ILIKE %s")
        params.append(f"%{ai_tool}%")
    if user:
        clauses.append("el.user_name ILIKE %s")
        params.append(f"%{user}%")

    if not clauses:
        return []

    where_sql = " AND ".join(clauses)
    sql = f"""
        SELECT DISTINCT ei.id, ei.page, ei.error_type, ei.message, ei.status,
               ei.occurrence_count, ei.first_seen, ei.last_seen,
               cr.resolution_summary, cr.root_cause, cr.lessons_learned, cr.version_fixed
        FROM error_issues ei
        {' '.join(joins)}
        WHERE {where_sql}
        ORDER BY ei.last_seen DESC
        LIMIT %s
    """
    params.append(limit)

    conn = None
    try:
        conn = _get_conn()
        with conn.cursor() as c:
            c.execute(sql, tuple(params))
            rows = c.fetchall()
    except Exception:
        logger.exception("search_cases FAILED")
        return []
    finally:
        if conn is not None:
            conn.close()

    results = []
    for (iid, page_, error_type, message, status_, occ, first_seen, last_seen,
         res_summary, root_cause_, lessons, version) in rows:
        results.append({
            "issue_id": iid,
            "page": page_,
            "error_type": error_type,
            "message": message,
            "status": status_,
            "occurrence_count": occ,
            "first_seen": iso(first_seen),
            "last_seen": iso(last_seen),
            "resolution_summary": res_summary,
            "root_cause": root_cause_,
            "lessons_learned": lessons,
            "version_fixed": version,
        })
    return results


# ---------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------
def _gather_case_data(issue_id):
    """Pulls together everything needed to export one case: the issue
    itself, its most recent occurrence's diagnostic evidence, its
    resolution, its resolution history, and its AI investigations.
    Returns None if the issue doesn't exist. Never raises."""
    conn = None
    try:
        conn = _get_conn()
        with conn.cursor() as c:
            c.execute(
                """
                SELECT id, signature, status, severity, page, error_type, message,
                       occurrence_count, first_seen, last_seen, resolved_at
                FROM error_issues WHERE id = %s
                """,
                (issue_id,),
            )
            issue_row = c.fetchone()
            if not issue_row:
                return None

            c.execute(
                """
                SELECT occurred_at, traceback, diagnostic_package, user_name, user_role
                FROM error_log WHERE issue_id = %s
                ORDER BY occurred_at DESC LIMIT 1
                """,
                (issue_id,),
            )
            latest_row = c.fetchone()
    except Exception:
        logger.exception("_gather_case_data FAILED for issue_id=%s", issue_id)
        return None
    finally:
        if conn is not None:
            conn.close()

    issue = {
        "id": issue_row[0],
        "signature": issue_row[1],
        "status": issue_row[2],
        "severity": issue_row[3],
        "page": issue_row[4],
        "error_type": issue_row[5],
        "message": issue_row[6],
        "occurrence_count": issue_row[7],
        "first_seen": iso(issue_row[8]),
        "last_seen": iso(issue_row[9]),
        "resolved_at": iso(issue_row[10]),
        "diagnostic_summary": None,
        "traceback": None,
        "timeline": [],
        "latest_occurred_at": None,
        "latest_user": None,
        "latest_user_role": None,
    }

    if latest_row:
        occurred_at, traceback_text, diag_json, user_name, user_role = latest_row
        issue["latest_occurred_at"] = iso(occurred_at)
        issue["traceback"] = traceback_text
        issue["latest_user"] = user_name
        issue["latest_user_role"] = user_role
        if diag_json:
            try:
                pkg = json.loads(diag_json)
                issue["diagnostic_summary"] = pkg.get("summary")
                issue["timeline"] = pkg.get("navigation_timeline") or []
            except Exception:
                pass

    return {
        "issue": issue,
        "resolution": get_resolution(issue_id),
        "resolution_history": get_resolution_history(issue_id),
        "investigations": get_investigations(issue_id),
    }


_RESOLUTION_LABELS = [
    ("Resolution summary", "resolution_summary"),
    ("Root cause", "root_cause"),
    ("Fix applied", "fix_applied"),
    ("Version fixed", "version_fixed"),
    ("Deployment date", "deployment_date"),
    ("Lessons learned", "lessons_learned"),
    ("Future prevention notes", "prevention_notes"),
]
_CASE_KNOWLEDGE_LABELS = [
    ("Common cause", "common_cause"),
    ("Known fix", "known_fix"),
    ("Known workaround", "known_workaround"),
    ("Documentation link", "documentation_link"),
    ("Git commit", "git_commit"),
    ("External reference", "external_reference"),
]

# Public aliases -- pages/system_administration.py reuses these labels
# when rendering a preserved resolution-history snapshot, so the
# labels only ever need to be defined in one place.
RESOLUTION_LABELS = _RESOLUTION_LABELS
CASE_KNOWLEDGE_LABELS = _CASE_KNOWLEDGE_LABELS


def _build_export_text(data, markdown=True):
    issue = data["issue"]
    resolution = data.get("resolution") or {}
    history = data.get("resolution_history") or []
    investigations = data.get("investigations") or []

    def heading(title, level=2):
        if markdown:
            return f"{'#' * level} {title}"
        return f"--- {title} ---"

    lines = [heading(f"Case #{issue['id']}", 1), ""]

    lines.append(heading("Overview"))
    lines.append(f"- Status: {issue.get('status') or '-'}")
    lines.append(f"- Severity: {issue.get('severity') or '-'}")
    lines.append(f"- Page: {issue.get('page') or '-'}")
    lines.append(f"- Exception type: {issue.get('error_type') or '-'}")
    lines.append(f"- Message: {issue.get('message') or '-'}")
    lines.append(f"- Occurrence count: {issue.get('occurrence_count') or 0}")
    lines.append(f"- First seen: {issue.get('first_seen') or '-'}")
    lines.append(f"- Last seen: {issue.get('last_seen') or '-'}")
    lines.append(f"- Resolved at: {issue.get('resolved_at') or '-'}")
    lines.append("")

    if issue.get("diagnostic_summary"):
        lines.append(heading("Diagnostic Package Summary (most recent occurrence)"))
        lines.append(issue["diagnostic_summary"])
        lines.append("")

    if issue.get("traceback"):
        lines.append(heading("Traceback (most recent occurrence)"))
        if markdown:
            lines.append("```")
        lines.append(issue["traceback"])
        if markdown:
            lines.append("```")
        lines.append("")

    if issue.get("timeline"):
        lines.append(heading("Evidence Timeline (most recent occurrence)"))
        for entry in issue["timeline"]:
            piece = f"- {entry.get('at')}: {entry.get('event')}"
            if entry.get("page"):
                piece += f" (page: {entry['page']})"
            if entry.get("detail"):
                piece += f" -- {entry['detail']}"
            lines.append(piece)
        lines.append("")

    lines.append(heading("Resolution"))
    if resolution and any(resolution.get(k) for _, k in _RESOLUTION_LABELS):
        for label, key in _RESOLUTION_LABELS:
            if resolution.get(key):
                lines.append(f"- {label}: {resolution[key]}")
    else:
        lines.append("(not resolved yet)")
    lines.append("")

    if resolution and any(resolution.get(k) for _, k in _CASE_KNOWLEDGE_LABELS):
        lines.append(heading("Case Knowledge"))
        for label, key in _CASE_KNOWLEDGE_LABELS:
            if resolution.get(key):
                lines.append(f"- {label}: {resolution[key]}")
        lines.append("")

    if history:
        lines.append(heading("Previous Resolution History (preserved on reopening)"))
        for snap in history:
            snap_data = snap.get("snapshot_data") or {}
            lines.append(
                f"- Reopened at {snap.get('reopened_at')} "
                f"(occurrence #{snap.get('occurrence_count_at_reopen')}):"
            )
            for label, key in _RESOLUTION_LABELS:
                if snap_data.get(key):
                    lines.append(f"    - {label}: {snap_data[key]}")
        lines.append("")

    if investigations:
        lines.append(heading("AI Investigation History"))
        for inv in investigations:
            lines.append(heading(f"{inv.get('tool_used') or 'Investigation'} -- {inv.get('investigated_at')}", 3))
            if inv.get("prompt"):
                lines.append(f"Prompt: {inv['prompt']}")
            if inv.get("ai_response"):
                lines.append(f"Response: {inv['ai_response']}")
            if inv.get("admin_notes"):
                lines.append(f"Administrator notes: {inv['admin_notes']}")
            lines.append("")

    return "\n".join(lines)


def build_case_export(issue_id, fmt="markdown"):
    """
    Builds a complete export of one case (diagnostic evidence,
    resolution, case knowledge, resolution history, and every
    preserved AI investigation), suitable for pasting into ChatGPT,
    Claude, a GitHub issue, or project documentation.

    fmt: "markdown" (default), "json", or "text".

    Returns the export as a string, or None if the issue doesn't
    exist or the export itself failed. Never raises.
    """
    try:
        data = _gather_case_data(issue_id)
        if not data:
            return None
        if fmt == "json":
            return json.dumps(data, indent=2, default=str)
        if fmt == "text":
            return _build_export_text(data, markdown=False)
        return _build_export_text(data, markdown=True)
    except Exception:
        logger.exception("build_case_export FAILED for issue_id=%s", issue_id)
        return None