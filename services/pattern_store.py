"""
Pattern Store
===============

Stage 2 of the pattern explorer (see PATTERNS.md): the database side.

PRIVACY, in one place
----------------------
- Every function starts with require_pattern_role(): only Supervisors and
  Programme Managers get through (services/pattern_access.py).
- The pool of observations a pattern can be built from is ONLY those whose
  author chose to share them (finding_feedback.shared_with_team). An
  observation that was never shared, or whose sharing was withdrawn, is
  invisible here -- withdrawing removes it from every pattern at once,
  because membership is always re-checked against the share flag when a
  pattern is read.
- What management can read about a shared observation is: its text, its
  exact quotation, its lens, its case reference, and its reflection date.
  NEVER the author's name or role, and never the author's notes, ratings,
  alternative explanations or "AI misunderstood" flag. The SELECTs below
  do not touch those columns.
- Observations whose source documents are in the 48-hour deletion window
  are excluded, exactly as they are on the author's own page.

HISTORY
--------
Pattern content is never overwritten by a review. A reviewer's status
changes, grouping challenges and carried-over judgements are appended to
pattern_events, so the original suggestion and the full review history
both remain.
"""

import json
from datetime import timedelta

from services.db_pool import get_conn as _acquire_pooled_conn
from services.db_time import now_utc, iso, get_logger
from services.findings_store import NOT_IN_DELETION_WINDOW, FINDING_MODULES
from services.pattern_access import require_pattern_role
from services.pattern_engine import summarise_members

logger = get_logger(__name__)

PATTERN_STATUSES = (
    "candidate",
    "under_review",
    "worth_discussing",
    "not_supported",
    "archived",
)

MAX_COMMENT_CHARS = 2000

# A generation still marked "running" this long after it started is
# assumed to have been interrupted, and no longer blocks a new one.
RUN_STALE_AFTER = timedelta(minutes=15)

# Postgres advisory-lock key that serialises "is a generation already
# running? then start one" so two clicks cannot both start.
_RUN_LOCK_KEY = 7731001


def _get_conn():
    return _acquire_pooled_conn()


def _loads(value, default):
    try:
        loaded = json.loads(value) if value else default
    except (TypeError, ValueError):
        return default
    return loaded if isinstance(loaded, type(default)) else default


def _dumps(value):
    return json.dumps(value, ensure_ascii=False)


# ---------------------------------------------------------------------
# The pool of shared observations
# ---------------------------------------------------------------------

def _pool_conditions(modules, date_from, date_to):
    """SQL conditions (and parameters) for 'observations whose author
    shared them', plus the optional filters. Returns (conditions, params,
    nothing_can_match). One definition shared by every reader of the pool,
    so counts and data can never disagree about what is in it."""
    conditions = [
        "EXISTS (SELECT 1 FROM finding_feedback fb "
        "WHERE fb.finding_id = f.id AND fb.shared_with_team)",
        NOT_IN_DELETION_WINDOW,
    ]
    params = []
    if modules:
        wanted = [m for m in modules if m in FINDING_MODULES]
        if not wanted:
            return conditions, params, True
        conditions.append("f.module = ANY(%s)")
        params.append(wanted)
    if date_from:
        conditions.append("r.created_at >= %s")
        params.append(date_from)
    if date_to:
        conditions.append("r.created_at < %s")
        params.append(date_to + timedelta(days=1))
    return conditions, params, False


def get_shared_findings(role, modules=None, date_from=None, date_to=None, limit=800):
    """
    Observations whose author chose to share them, newest first.

    Filters (all optional): `modules` (list of lens keys), `date_from` /
    `date_to` (dates, inclusive, applied to the reflection date).

    Returns dicts with: id, run_id, case_ref, module, observation,
    questions, evidence, language, created_at. There is deliberately NO
    author field.
    """
    require_pattern_role(role)
    limit = max(1, min(int(limit), 5000))
    conditions, params, nothing = _pool_conditions(modules, date_from, date_to)
    if nothing:
        return []
    params = params + [limit]

    conn = _get_conn()
    try:
        with conn.cursor() as c:
            c.execute(
                f"""
                SELECT f.id, f.run_id, r.case_ref, f.module, f.observation,
                       f.questions, f.evidence, r.language, r.created_at
                FROM reflection_findings f
                JOIN reflection_runs r ON r.id = f.run_id
                WHERE {' AND '.join(conditions)}
                ORDER BY r.created_at DESC, f.id DESC
                LIMIT %s
                """,
                params,
            )
            rows = c.fetchall()
    finally:
        conn.close()

    return [
        {
            "id": r[0], "run_id": r[1], "case_ref": r[2] or "", "module": r[3],
            "observation": r[4], "questions": _loads(r[5], []),
            "evidence": _loads(r[6], []), "language": r[7],
            "created_at": iso(r[8]),
        }
        for r in rows
    ]


def get_pool_counts(role, modules=None, date_from=None, date_to=None):
    """
    Honest counts for the pool of shared observations matching the filters,
    computed in the database (no observation text is loaded):
      observations, reflections (distinct), cases (distinct recorded case
      references), reflections_without_case.
    """
    require_pattern_role(role)
    empty = {"observations": 0, "reflections": 0, "cases": 0,
             "reflections_without_case": 0}
    conditions, params, nothing = _pool_conditions(modules, date_from, date_to)
    if nothing:
        return empty

    normalised = ("NULLIF(lower(btrim(regexp_replace(COALESCE(r.case_ref, ''), "
                  "'\\s+', ' ', 'g'))), '')")
    conn = _get_conn()
    try:
        with conn.cursor() as c:
            c.execute(
                f"""
                SELECT COUNT(*),
                       COUNT(DISTINCT f.run_id),
                       COUNT(DISTINCT {normalised}),
                       COUNT(DISTINCT CASE WHEN {normalised} IS NULL THEN f.run_id END)
                FROM reflection_findings f
                JOIN reflection_runs r ON r.id = f.run_id
                WHERE {' AND '.join(conditions)}
                """,
                params,
            )
            row = c.fetchone()
    finally:
        conn.close()
    return {"observations": row[0], "reflections": row[1], "cases": row[2],
            "reflections_without_case": row[3]}


def summarise_shared_pool(role, **filters):
    """Honest counts for the pool of shared observations that match the
    filters, plus the observations themselves
    (see pattern_engine.summarise_members)."""
    require_pattern_role(role)
    findings = get_shared_findings(role, **filters)
    return summarise_members(findings), findings


# ---------------------------------------------------------------------
# Cached meaning-vectors
# ---------------------------------------------------------------------

def get_cached_embeddings(role, finding_ids, model):
    """{finding_id: vector} for observations already embedded with `model`."""
    require_pattern_role(role)
    if not finding_ids:
        return {}
    conn = _get_conn()
    try:
        with conn.cursor() as c:
            c.execute(
                "SELECT finding_id, vector FROM finding_embeddings "
                "WHERE model = %s AND finding_id = ANY(%s)",
                (model, list(finding_ids)),
            )
            return {r[0]: list(r[1]) for r in c.fetchall()}
    finally:
        conn.close()


def save_embeddings(role, vectors_by_finding_id, model):
    """Cache {finding_id: vector}. Safe to repeat. An observation that was
    erased in the meantime is skipped."""
    require_pattern_role(role)
    if not vectors_by_finding_id:
        return 0
    conn = _get_conn()
    try:
        with conn.cursor() as c:
            for finding_id, vector in vectors_by_finding_id.items():
                c.execute(
                    """
                    INSERT INTO finding_embeddings (finding_id, model, dims, vector, created_at)
                    SELECT %s, %s, %s, %s, %s
                    WHERE EXISTS (SELECT 1 FROM reflection_findings WHERE id = %s)
                    ON CONFLICT (finding_id) DO UPDATE SET
                        model = EXCLUDED.model, dims = EXCLUDED.dims,
                        vector = EXCLUDED.vector, created_at = EXCLUDED.created_at
                    """,
                    (finding_id, model, len(vector), [float(x) for x in vector],
                     now_utc(), finding_id),
                )
        conn.commit()
        return len(vectors_by_finding_id)
    except Exception:
        conn.rollback()
        logger.exception("save_embeddings FAILED (batch rolled back)")
        raise
    finally:
        conn.close()


# ---------------------------------------------------------------------
# Generation runs
# ---------------------------------------------------------------------

def start_run(role, actor, parameters, language, embedding_model,
              explanation_model, prompt_version):
    """
    Begin a pattern generation. Returns the new run id, or None if another
    generation is already running (started less than RUN_STALE_AFTER ago),
    so repeated clicks or two managers cannot launch duplicate paid work.
    """
    require_pattern_role(role)
    conn = _get_conn()
    try:
        with conn.cursor() as c:
            c.execute("SELECT pg_advisory_xact_lock(%s)", (_RUN_LOCK_KEY,))
            c.execute(
                "SELECT id FROM pattern_runs WHERE status = 'running' AND created_at > %s LIMIT 1",
                (now_utc() - RUN_STALE_AFTER,),
            )
            if c.fetchone():
                conn.rollback()
                return None
            c.execute(
                """
                INSERT INTO pattern_runs
                    (status, parameters, language, embedding_model,
                     explanation_model, prompt_version, created_by,
                     created_by_role, created_at)
                VALUES ('running', %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (_dumps(parameters), language, embedding_model, explanation_model,
                 prompt_version, actor, role, now_utc()),
            )
            run_id = c.fetchone()[0]
        conn.commit()
        return run_id
    except Exception:
        conn.rollback()
        logger.exception("start_run FAILED")
        raise
    finally:
        conn.close()


def finish_run(run_id, status, observations_considered=0, patterns_created=0,
               error_summary=""):
    """Close a generation as 'completed' or 'failed'. `error_summary` must
    be a short technical reason, never case content."""
    if status not in ("completed", "failed"):
        raise ValueError("status must be 'completed' or 'failed'")
    conn = _get_conn()
    try:
        with conn.cursor() as c:
            c.execute(
                """
                UPDATE pattern_runs
                SET status = %s, observations_considered = %s,
                    patterns_created = %s, error_summary = %s, finished_at = %s
                WHERE id = %s
                """,
                (status, observations_considered, patterns_created,
                 (error_summary or "")[:500], now_utc(), run_id),
            )
        conn.commit()
    except Exception:
        conn.rollback()
        logger.exception("finish_run FAILED: run_id=%r", run_id)
        raise
    finally:
        conn.close()


def _run_row(r):
    return {
        "id": r[0], "status": r[1], "parameters": _loads(r[2], {}),
        "language": r[3], "embedding_model": r[4], "explanation_model": r[5],
        "prompt_version": r[6], "observations_considered": r[7],
        "patterns_created": r[8], "error_summary": r[9] or "",
        "created_at": iso(r[10]), "finished_at": iso(r[11]),
    }


_RUN_COLUMNS = (
    "id, status, parameters, language, embedding_model, explanation_model, "
    "prompt_version, observations_considered, patterns_created, "
    "error_summary, created_at, finished_at"
)


def get_run(role, run_id):
    require_pattern_role(role)
    conn = _get_conn()
    try:
        with conn.cursor() as c:
            c.execute(f"SELECT {_RUN_COLUMNS} FROM pattern_runs WHERE id = %s", (run_id,))
            r = c.fetchone()
    finally:
        conn.close()
    return _run_row(r) if r else None


def list_runs(role, limit=10):
    """Recent COMPLETED generations, newest first."""
    require_pattern_role(role)
    limit = max(1, min(int(limit), 50))
    conn = _get_conn()
    try:
        with conn.cursor() as c:
            c.execute(
                f"SELECT {_RUN_COLUMNS} FROM pattern_runs WHERE status = 'completed' "
                "ORDER BY id DESC LIMIT %s",
                (limit,),
            )
            rows = c.fetchall()
    finally:
        conn.close()
    return [_run_row(r) for r in rows]


# ---------------------------------------------------------------------
# Saving and reading patterns
# ---------------------------------------------------------------------

def get_previous_patterns(role, before_run_id):
    """
    The patterns of the most recent completed generation before
    `before_run_id`, with every member id and which members the reviewer
    excluded -- used to carry a reviewer's judgement forward when a new
    generation finds "the same" pattern.
    """
    require_pattern_role(role)
    conn = _get_conn()
    try:
        with conn.cursor() as c:
            c.execute(
                """
                SELECT id FROM pattern_runs
                WHERE status = 'completed' AND id < %s AND patterns_created > 0
                ORDER BY id DESC LIMIT 1
                """,
                (before_run_id,),
            )
            row = c.fetchone()
            if not row:
                return []
            c.execute("SELECT id, status FROM patterns WHERE run_id = %s ORDER BY id", (row[0],))
            patterns = {r[0]: {"id": r[0], "status": r[1], "member_ids": [], "excluded_ids": []}
                        for r in c.fetchall()}
            if patterns:
                c.execute(
                    "SELECT pattern_id, finding_id, excluded FROM pattern_findings "
                    "WHERE pattern_id = ANY(%s)",
                    (list(patterns),),
                )
                for pattern_id, finding_id, excluded in c.fetchall():
                    patterns[pattern_id]["member_ids"].append(finding_id)
                    if excluded:
                        patterns[pattern_id]["excluded_ids"].append(finding_id)
            return list(patterns.values())
    finally:
        conn.close()


def save_patterns(role, run_id, patterns):
    """
    Save a generation's patterns, their members and their 'generated'
    history event -- all in one transaction.

    Each pattern dict: title, description, why_it_matters, modules (list),
    alternative_explanations (list), limitations (list), questions (list),
    grouping_basis (a small dict describing the settings used),
    explanation_status ('ai' | 'fallback'), member_ids (list), and
    optionally carried_from = {"pattern_id", "status", "excluded_ids"} to
    inherit a reviewer's earlier judgement.

    Returns the list of new pattern ids.
    """
    require_pattern_role(role)
    conn = _get_conn()
    new_ids = []
    try:
        with conn.cursor() as c:
            for p in patterns:
                carried = p.get("carried_from") or None
                status = "candidate"
                if carried and carried.get("status") in PATTERN_STATUSES:
                    status = carried["status"]
                c.execute(
                    """
                    INSERT INTO patterns
                        (run_id, title, description, why_it_matters, modules,
                         alternative_explanations, limitations, questions,
                         grouping_basis, explanation_status, status,
                         original_member_count, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                    """,
                    (run_id, p["title"], p.get("description", ""),
                     p.get("why_it_matters", ""), _dumps(p.get("modules", [])),
                     _dumps(p.get("alternative_explanations", [])),
                     _dumps(p.get("limitations", [])), _dumps(p.get("questions", [])),
                     _dumps(p.get("grouping_basis", {})),
                     p.get("explanation_status", "ai"), status,
                     len(p["member_ids"]), now_utc()),
                )
                pattern_id = c.fetchone()[0]
                new_ids.append(pattern_id)

                excluded_ids = set((carried or {}).get("excluded_ids") or [])
                for finding_id in p["member_ids"]:
                    c.execute(
                        "INSERT INTO pattern_findings (pattern_id, finding_id, excluded) "
                        "VALUES (%s, %s, %s) ON CONFLICT DO NOTHING",
                        (pattern_id, finding_id, finding_id in excluded_ids),
                    )

                c.execute(
                    "INSERT INTO pattern_events (pattern_id, kind, actor, actor_role, "
                    "new_value, created_at) VALUES (%s, 'generated', 'system', 'system', "
                    "'candidate', %s)",
                    (pattern_id, now_utc()),
                )
                if carried and status != "candidate":
                    c.execute(
                        "INSERT INTO pattern_events (pattern_id, kind, actor, actor_role, "
                        "old_value, new_value, comment, created_at) "
                        "VALUES (%s, 'carried_over', 'system', 'system', %s, %s, %s, %s)",
                        (pattern_id, str(carried.get("pattern_id")), status,
                         "carried over from the same pattern in an earlier generation",
                         now_utc()),
                    )
        conn.commit()
        return new_ids
    except Exception:
        conn.rollback()
        logger.exception("save_patterns FAILED (run %r rolled back)", run_id)
        raise
    finally:
        conn.close()


def list_patterns(role, run_id, statuses=None, module=None):
    """
    The patterns of one generation, each with its CURRENT members and
    honest counts.

    A member counts only while its author still shares it and its
    documents are not awaiting deletion; observations the reviewer
    excluded are listed separately. A pattern left with no current members
    is not returned.

    Each pattern dict: id, title, description, why_it_matters, modules,
    alternative_explanations, limitations, questions, grouping_basis
    (dict), explanation_status, status, created_at, lost_members (how many
    of its starting observations are no longer available -- the written
    explanation may still reflect them), members (current, not excluded),
    excluded_members (still shared, challenged by a reviewer), counts (see
    pattern_engine.summarise_members), below_minimum (True if withdrawals
    or exclusions have dropped it under the generation's own minimums).
    """
    require_pattern_role(role)
    run = get_run(role, run_id)
    if run is None:
        return []
    minimums = run["parameters"] or {}
    min_obs = int(minimums.get("min_observations", 0) or 0)
    min_refl = int(minimums.get("min_reflections", 0) or 0)

    conn = _get_conn()
    try:
        with conn.cursor() as c:
            conditions = ["p.run_id = %s"]
            params = [run_id]
            if statuses:
                conditions.append("p.status = ANY(%s)")
                params.append(list(statuses))
            c.execute(
                f"""
                SELECT p.id, p.title, p.description, p.why_it_matters, p.modules,
                       p.alternative_explanations, p.limitations, p.questions,
                       p.grouping_basis, p.explanation_status, p.status,
                       p.created_at, p.original_member_count
                FROM patterns p WHERE {' AND '.join(conditions)} ORDER BY p.id
                """,
                params,
            )
            pattern_rows = c.fetchall()
            if not pattern_rows:
                return []
            ids = [r[0] for r in pattern_rows]
            c.execute(
                f"""
                SELECT pf.pattern_id, pf.excluded, f.id, f.run_id, r.case_ref,
                       f.module, f.observation, f.questions, f.evidence,
                       r.language, r.created_at
                FROM pattern_findings pf
                JOIN reflection_findings f ON f.id = pf.finding_id
                JOIN reflection_runs r ON r.id = f.run_id
                WHERE pf.pattern_id = ANY(%s)
                  AND EXISTS (SELECT 1 FROM finding_feedback fb
                              WHERE fb.finding_id = f.id AND fb.shared_with_team)
                  AND {NOT_IN_DELETION_WINDOW}
                ORDER BY r.created_at DESC, f.id DESC
                """,
                (ids,),
            )
            member_rows = c.fetchall()
    finally:
        conn.close()

    members_by_pattern = {i: [] for i in ids}
    excluded_by_pattern = {i: [] for i in ids}
    for m in member_rows:
        member = {
            "id": m[2], "run_id": m[3], "case_ref": m[4] or "", "module": m[5],
            "observation": m[6], "questions": _loads(m[7], []),
            "evidence": _loads(m[8], []), "language": m[9],
            "created_at": iso(m[10]),
        }
        (excluded_by_pattern if m[1] else members_by_pattern)[m[0]].append(member)

    results = []
    for r in pattern_rows:
        members = members_by_pattern[r[0]]
        if not members:
            continue
        if module and module not in {m["module"] for m in members}:
            continue
        counts = summarise_members(members)
        excluded = excluded_by_pattern[r[0]]
        results.append({
            "id": r[0], "title": r[1], "description": r[2] or "",
            "why_it_matters": r[3] or "", "modules": _loads(r[4], []),
            "alternative_explanations": _loads(r[5], []),
            "limitations": _loads(r[6], []), "questions": _loads(r[7], []),
            "grouping_basis": _loads(r[8], {}), "explanation_status": r[9],
            "status": r[10], "created_at": iso(r[11]),
            "lost_members": max(0, (r[12] or 0) - len(members) - len(excluded)),
            "members": members, "excluded_members": excluded,
            "counts": counts,
            "below_minimum": bool(
                (min_obs and counts["observations"] < min_obs)
                or (min_refl and counts["reflections"] < min_refl)
            ),
        })
    return results


# ---------------------------------------------------------------------
# Review actions (all append to pattern_events; nothing is overwritten)
# ---------------------------------------------------------------------

def set_pattern_status(role, actor, pattern_id, new_status, comment=""):
    """Record a reviewer's judgement. Returns True if the status changed
    (or a comment was added), False if nothing to record / refused."""
    require_pattern_role(role)
    if not actor or new_status not in PATTERN_STATUSES:
        return False
    comment = (comment or "").strip()[:MAX_COMMENT_CHARS]

    conn = _get_conn()
    try:
        with conn.cursor() as c:
            c.execute("SELECT status FROM patterns WHERE id = %s FOR UPDATE", (pattern_id,))
            row = c.fetchone()
            if not row:
                conn.rollback()
                return False
            old_status = row[0]
            if old_status == new_status and not comment:
                conn.rollback()
                return False
            if old_status != new_status:
                c.execute("UPDATE patterns SET status = %s WHERE id = %s", (new_status, pattern_id))
            c.execute(
                "INSERT INTO pattern_events (pattern_id, kind, actor, actor_role, "
                "old_value, new_value, comment, created_at) "
                "VALUES (%s, 'status_changed', %s, %s, %s, %s, %s, %s)",
                (pattern_id, actor, role, old_status, new_status, comment, now_utc()),
            )
        conn.commit()
        return True
    except Exception:
        conn.rollback()
        logger.exception("set_pattern_status FAILED: pattern_id=%r", pattern_id)
        raise
    finally:
        conn.close()


def set_member_excluded(role, actor, pattern_id, finding_id, excluded, comment=""):
    """Challenge the grouping: mark one observation as not belonging to a
    pattern (or restore it). Returns True if changed."""
    require_pattern_role(role)
    if not actor:
        return False
    comment = (comment or "").strip()[:MAX_COMMENT_CHARS]
    excluded = bool(excluded)

    conn = _get_conn()
    try:
        with conn.cursor() as c:
            c.execute(
                "SELECT excluded FROM pattern_findings WHERE pattern_id = %s AND finding_id = %s FOR UPDATE",
                (pattern_id, finding_id),
            )
            row = c.fetchone()
            if not row or bool(row[0]) == excluded:
                conn.rollback()
                return False
            c.execute(
                "UPDATE pattern_findings SET excluded = %s WHERE pattern_id = %s AND finding_id = %s",
                (excluded, pattern_id, finding_id),
            )
            c.execute(
                "INSERT INTO pattern_events (pattern_id, kind, actor, actor_role, "
                "new_value, comment, created_at) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                (pattern_id, "member_excluded" if excluded else "member_restored",
                 actor, role, str(finding_id), comment, now_utc()),
            )
        conn.commit()
        return True
    except Exception:
        conn.rollback()
        logger.exception("set_member_excluded FAILED: pattern_id=%r", pattern_id)
        raise
    finally:
        conn.close()


def update_pattern_explanation(role, actor, pattern_id, explanation):
    """Replace the written explanation of a pattern whose explanation is
    still the plain fallback (used to retry a failed one). Recorded in the
    pattern's history. Returns True if replaced."""
    require_pattern_role(role)
    conn = _get_conn()
    try:
        with conn.cursor() as c:
            c.execute(
                "SELECT explanation_status FROM patterns WHERE id = %s FOR UPDATE",
                (pattern_id,),
            )
            row = c.fetchone()
            if not row or row[0] != "fallback":
                conn.rollback()
                return False
            c.execute(
                """
                UPDATE patterns SET title = %s, description = %s,
                    why_it_matters = %s, alternative_explanations = %s,
                    limitations = %s, questions = %s, explanation_status = 'ai'
                WHERE id = %s
                """,
                (explanation["title"], explanation["description"],
                 explanation["why_it_matters"],
                 _dumps(explanation["alternative_explanations"]),
                 _dumps(explanation["limitations"]), _dumps(explanation["questions"]),
                 pattern_id),
            )
            c.execute(
                "INSERT INTO pattern_events (pattern_id, kind, actor, actor_role, "
                "created_at) VALUES (%s, 'explanation_regenerated', %s, %s, %s)",
                (pattern_id, actor, role, now_utc()),
            )
        conn.commit()
        return True
    except Exception:
        conn.rollback()
        logger.exception("update_pattern_explanation FAILED: pattern_id=%r", pattern_id)
        raise
    finally:
        conn.close()


def get_pattern_events(role, pattern_id):
    """A pattern's review history, oldest first."""
    require_pattern_role(role)
    conn = _get_conn()
    try:
        with conn.cursor() as c:
            c.execute(
                """
                SELECT kind, actor, actor_role, old_value, new_value, comment, created_at
                FROM pattern_events WHERE pattern_id = %s ORDER BY id
                """,
                (pattern_id,),
            )
            rows = c.fetchall()
    finally:
        conn.close()
    return [
        {"kind": r[0], "actor": r[1] or "", "actor_role": r[2] or "",
         "old_value": r[3] or "", "new_value": r[4] or "",
         "comment": r[5] or "", "created_at": iso(r[6])}
        for r in rows
    ]
