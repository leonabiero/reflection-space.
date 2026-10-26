"""
Findings Store
================

Stage 1 of the saved-findings feature (see FINDINGS_STORAGE.md).

Until now a reflection was shown on screen and then forgotten: the app
kept only a yes/no flag per dimension (services/reflection_log.py) and
never the observation, the questions or the passage that prompted them.
This module is where those are now kept, so they can be reopened later,
checked against their source, and (in later stages) compared across
documents.

What is stored, and what is deliberately kept apart
-----------------------------------------------------
reflection_runs         one row per reflection that was generated: which
                        case, which documents went in, which language,
                        which prompt version and model, who ran it, when.
reflection_run_sources  which documents fed that run (own table so a
                        permanent deletion of a document can find every
                        run that used it -- see delete_runs_for_drafts).
reflection_findings     the AI's output for one dimension of one run:
                        observation, questions, and the verified exact
                        passages (services/evidence.py). Never edited
                        after it is saved.
finding_feedback        the PROFESSIONAL's own response to one finding:
                        a label, a note, an alternative explanation, and
                        a flag for "the AI may have misunderstood". Kept
                        in its own table so a professional's words can
                        never overwrite or blend into the AI's.

Privacy rules this module enforces
-----------------------------------
- Only anonymized text is ever stored here (the quotes come from the
  anonymized text the model was given, never from the raw document).
- A professional's feedback is private to them. get_feedback_for_findings
  and get_my_findings filter by the person's own name IN SQL, and
  upsert_feedback refuses to write on someone else's findings. Nothing
  here lets one professional read another's notes.
- Stage 2: an author may choose to SHARE an observation with the
  management team's pattern explorer (upsert_feedback(shared_with_team=
  True)). Only the observation and its exact quote are then readable by
  management (services/pattern_store.py) -- never the author's name, notes,
  ratings or alternative explanations. Sharing can be withdrawn at any
  time and takes effect immediately.
- No finding text, quote or note is ever written to logs -- logging in
  this module uses ids and counts only.
- Deleting a document permanently deletes every run that used it,
  together with its findings and feedback (delete_runs_for_drafts),
  inside the same database transaction as the document deletion.
"""

import json

from services.db_pool import get_conn as _acquire_pooled_conn
from services.db_time import now_utc, iso, get_logger

logger = get_logger(__name__)

# The eight reflection dimensions. Must match rdi/companions/__init__.py
# and services/reflection_log.py:THEME_KEYS.
FINDING_MODULES = (
    "client_voice",
    "observation_vs_interpretation",
    "labels_and_language",
    "possible_bias",
    "evidence_for_decisions",
    "missing_information",
    "strengths_and_deficits",
    "continuity",
)

# What a professional can say about a finding. None means "no label
# chosen" -- distinct from every explicit choice below.
FEEDBACK_LABELS = ("useful", "not_relevant", "uncertain", "discuss")

MAX_NOTE_CHARS = 4000
MAX_ALTERNATIVE_CHARS = 4000


def _get_conn():
    """Pooled connection (services/db_pool.py). Tables are created once
    at startup by services/db_schema.py:ensure_schema()."""
    return _acquire_pooled_conn()


def _loads(value, default):
    try:
        loaded = json.loads(value) if value else default
    except (TypeError, ValueError):
        return default
    return loaded if isinstance(loaded, type(default)) else default


def _clean_finding(finding):
    """Validate one finding dict from the orchestrator and return the
    values to store, or None if it should not be stored."""
    if not isinstance(finding, dict):
        return None
    module = finding.get("module")
    if module not in FINDING_MODULES:
        return None
    observation = (finding.get("observation") or "").strip()
    questions = [
        q.strip() for q in (finding.get("questions") or [])
        if isinstance(q, str) and q.strip()
    ]
    if not observation and not questions:
        return None
    evidence = []
    for item in finding.get("evidence") or []:
        quote = item.get("quote") if isinstance(item, dict) else None
        if isinstance(quote, str) and quote:
            evidence.append({"quote": quote})
    try:
        unverified = max(0, int(finding.get("unverified_quote_count") or 0))
    except (TypeError, ValueError):
        unverified = 0
    return module, observation, questions, evidence, unverified


def save_reflection_run(case_ref, source_draft_ids, language, prompt_version,
                        model, module_status, findings,
                        created_by, created_by_role="",
                        reflection_code=None, case_tags=None,
                        note_type="", previous_code=""):
    """
    Save one generated reflection: the run, the documents it used, and
    every finding -- all in ONE transaction, so either everything is
    stored or nothing is (never a run without its findings, or findings
    pointing at a run that doesn't exist).

    `module_status` is {module: "finding" | "no_finding" | "failed"},
    an honest record of what happened for each of the eight dimensions,
    including the ones that produced nothing.

    Reflection-only redesign (see REFLECTIONS.md): the case text is
    never stored. A reflection is identified by `reflection_code` (a
    neutral app-generated code), `case_tags` (non-personal theme keys),
    `note_type` and an optional `previous_code`. When a reflection_code
    is given it is also used as `case_ref`, so every existing log that
    groups by case_ref keeps working. All four are optional, so older
    callers (and older rows) are unaffected.

    Returns {"run_id": int, "finding_ids": {module: finding_id}}.
    Raises on database failure (callers decide how to degrade).
    """
    if not created_by:
        raise ValueError("created_by is required")

    cleaned = [c for c in (_clean_finding(f) for f in (findings or [])) if c]
    draft_ids = sorted({int(d) for d in (source_draft_ids or [])})
    status = {
        k: v for k, v in (module_status or {}).items()
        if k in FINDING_MODULES and v in ("finding", "no_finding", "failed")
    }
    if reflection_code:
        case_ref = reflection_code
    tags_json = (
        json.dumps(sorted({str(t) for t in case_tags}), ensure_ascii=False)
        if case_tags else None
    )

    conn = _get_conn()
    try:
        with conn.cursor() as c:
            c.execute(
                """
                INSERT INTO reflection_runs
                    (case_ref, language, prompt_version, model, module_status,
                     created_by, created_by_role, created_at,
                     reflection_code, case_tags, note_type, previous_code)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (case_ref, language, prompt_version, model,
                 json.dumps(status, ensure_ascii=False),
                 created_by, created_by_role, now_utc(),
                 reflection_code or None, tags_json,
                 note_type or None, previous_code or None),
            )
            run_id = c.fetchone()[0]

            for draft_id in draft_ids:
                c.execute(
                    "INSERT INTO reflection_run_sources (run_id, draft_id) "
                    "VALUES (%s, %s) ON CONFLICT DO NOTHING",
                    (run_id, draft_id),
                )

            finding_ids = {}
            for module, observation, questions, evidence, unverified in cleaned:
                c.execute(
                    """
                    INSERT INTO reflection_findings
                        (run_id, module, observation, questions, evidence,
                         unverified_quote_count, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (run_id, module) DO NOTHING
                    RETURNING id
                    """,
                    (run_id, module, observation,
                     json.dumps(questions, ensure_ascii=False),
                     json.dumps(evidence, ensure_ascii=False),
                     unverified, now_utc()),
                )
                row = c.fetchone()
                if row:
                    finding_ids[module] = row[0]
        conn.commit()
    except Exception:
        conn.rollback()
        logger.exception(
            "save_reflection_run FAILED (run rolled back): created_by=%r findings=%d",
            created_by, len(cleaned),
        )
        raise
    finally:
        conn.close()

    return {"run_id": run_id, "finding_ids": finding_ids}


def add_finding_to_run(run_id, finding, acting_user):
    """
    Add ONE finding to an existing run -- used when a practitioner's
    one-time manual retry of a failed dimension succeeds.

    Only the person who ran the reflection may add to it. Returns the new
    finding id, or None if the run isn't theirs, doesn't exist, the
    finding is empty, or that dimension already has a finding.
    """
    if not acting_user or not run_id:
        return None
    cleaned = _clean_finding(finding)
    if cleaned is None:
        return None
    module, observation, questions, evidence, unverified = cleaned

    conn = _get_conn()
    try:
        with conn.cursor() as c:
            c.execute(
                "SELECT created_by, module_status FROM reflection_runs "
                "WHERE id = %s FOR UPDATE",
                (run_id,),
            )
            row = c.fetchone()
            if not row or row[0] != acting_user:
                conn.rollback()
                return None

            c.execute(
                """
                INSERT INTO reflection_findings
                    (run_id, module, observation, questions, evidence,
                     unverified_quote_count, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (run_id, module) DO NOTHING
                RETURNING id
                """,
                (run_id, module, observation,
                 json.dumps(questions, ensure_ascii=False),
                 json.dumps(evidence, ensure_ascii=False),
                 unverified, now_utc()),
            )
            inserted = c.fetchone()
            if not inserted:
                conn.rollback()
                return None

            status = _loads(row[1], {})
            status[module] = "finding"
            c.execute(
                "UPDATE reflection_runs SET module_status = %s WHERE id = %s",
                (json.dumps(status, ensure_ascii=False), run_id),
            )
        conn.commit()
        return inserted[0]
    except Exception:
        conn.rollback()
        logger.exception("add_finding_to_run FAILED: run_id=%r", run_id)
        raise
    finally:
        conn.close()


def upsert_feedback(finding_id, user_name, label=None, note="",
                    alternative_explanation="", flagged_misread=False,
                    shared_with_team=None):
    """
    Save (create or replace) THIS professional's response to one finding.

    Returns True if saved, False if refused. Refused when: no user, the
    finding doesn't exist, the finding belongs to a reflection run by a
    different person, or the label is not one of FEEDBACK_LABELS.

    The AI's finding is never touched -- feedback lives in its own table.

    Stage 2 -- sharing: `shared_with_team` is the AUTHOR'S choice to put
    this observation (its text and exact quote -- never their name or
    their notes) into the pool the management team's pattern explorer
    reads. True shares it, False withdraws it immediately, None (the
    default) leaves whatever was chosen before unchanged. Nothing is
    ever shared unless the author set it True.
    """
    if not user_name or not finding_id:
        return False
    if label in ("", None):
        label = None
    elif label not in FEEDBACK_LABELS:
        return False

    note = (note or "").strip()[:MAX_NOTE_CHARS]
    alternative = (alternative_explanation or "").strip()[:MAX_ALTERNATIVE_CHARS]

    conn = _get_conn()
    try:
        with conn.cursor() as c:
            c.execute(
                """
                SELECT r.created_by
                FROM reflection_findings f
                JOIN reflection_runs r ON r.id = f.run_id
                WHERE f.id = %s
                """,
                (finding_id,),
            )
            row = c.fetchone()
            if not row or row[0] != user_name:
                conn.rollback()
                return False

            if shared_with_team is None:
                c.execute(
                    """
                    INSERT INTO finding_feedback
                        (finding_id, user_name, label, note,
                         alternative_explanation, flagged_misread, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (finding_id, user_name) DO UPDATE SET
                        label = EXCLUDED.label,
                        note = EXCLUDED.note,
                        alternative_explanation = EXCLUDED.alternative_explanation,
                        flagged_misread = EXCLUDED.flagged_misread,
                        updated_at = EXCLUDED.updated_at
                    """,
                    (finding_id, user_name, label, note, alternative,
                     bool(flagged_misread), now_utc()),
                )
            else:
                share = bool(shared_with_team)
                moment = now_utc()
                c.execute(
                    """
                    INSERT INTO finding_feedback
                        (finding_id, user_name, label, note,
                         alternative_explanation, flagged_misread, updated_at,
                         shared_with_team, shared_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (finding_id, user_name) DO UPDATE SET
                        label = EXCLUDED.label,
                        note = EXCLUDED.note,
                        alternative_explanation = EXCLUDED.alternative_explanation,
                        flagged_misread = EXCLUDED.flagged_misread,
                        updated_at = EXCLUDED.updated_at,
                        shared_at = CASE
                            WHEN NOT EXCLUDED.shared_with_team THEN NULL
                            WHEN finding_feedback.shared_with_team THEN finding_feedback.shared_at
                            ELSE EXCLUDED.shared_at
                        END,
                        shared_with_team = EXCLUDED.shared_with_team
                    """,
                    (finding_id, user_name, label, note, alternative,
                     bool(flagged_misread), moment, share, moment if share else None),
                )
        conn.commit()
        return True
    except Exception:
        conn.rollback()
        logger.exception("upsert_feedback FAILED: finding_id=%r", finding_id)
        raise
    finally:
        conn.close()


def get_feedback_for_findings(user_name, finding_ids):
    """
    This professional's saved feedback for the given findings, as
    {finding_id: {"label", "note", "alternative_explanation",
    "flagged_misread", "updated_at"}}. Only ever returns the caller's
    own feedback (filtered in SQL).
    """
    if not user_name or not finding_ids:
        return {}
    conn = _get_conn()
    try:
        with conn.cursor() as c:
            c.execute(
                """
                SELECT finding_id, label, note, alternative_explanation,
                       flagged_misread, updated_at, shared_with_team
                FROM finding_feedback
                WHERE user_name = %s AND finding_id = ANY(%s)
                """,
                (user_name, list(finding_ids)),
            )
            rows = c.fetchall()
    finally:
        conn.close()
    return {
        r[0]: {
            "label": r[1],
            "note": r[2] or "",
            "alternative_explanation": r[3] or "",
            "flagged_misread": bool(r[4]),
            "updated_at": iso(r[5]),
            "shared_with_team": bool(r[6]),
        }
        for r in rows
    }


# A run is hidden from its author while ANY document that fed it is in
# the 48-hour GDPR deletion window (status='deleted'), and reappears if
# the document is restored. After the window the run is permanently
# deleted (delete_runs_for_drafts).
NOT_IN_DELETION_WINDOW = """
    NOT EXISTS (
        SELECT 1
        FROM reflection_run_sources s
        JOIN drafts d ON d.id = s.draft_id
        WHERE s.run_id = r.id AND d.status = 'deleted'
    )
"""


def count_my_findings(user_name):
    """How many saved findings this professional has (excluding any
    whose source documents are awaiting permanent deletion)."""
    if not user_name:
        return 0
    conn = _get_conn()
    try:
        with conn.cursor() as c:
            c.execute(
                f"""
                SELECT COUNT(*)
                FROM reflection_findings f
                JOIN reflection_runs r ON r.id = f.run_id
                WHERE r.created_by = %s AND {NOT_IN_DELETION_WINDOW}
                """,
                (user_name,),
            )
            return c.fetchone()[0]
    finally:
        conn.close()


def get_my_findings(user_name, limit=20, offset=0):
    """
    This professional's own saved findings, newest first, each with their
    own feedback attached (if any). Paginated.

    Returns a list of dicts: id, run_id, case_ref, module, observation,
    questions, evidence, unverified_quote_count, language, prompt_version,
    created_at, feedback ({...} or None).
    """
    if not user_name:
        return []
    limit = max(1, min(int(limit), 200))
    offset = max(0, int(offset))

    conn = _get_conn()
    try:
        with conn.cursor() as c:
            c.execute(
                f"""
                SELECT f.id, f.run_id, r.case_ref, f.module, f.observation,
                       f.questions, f.evidence, f.unverified_quote_count,
                       r.language, r.prompt_version, f.created_at,
                       fb.label, fb.note, fb.alternative_explanation,
                       fb.flagged_misread, fb.updated_at, fb.shared_with_team
                FROM reflection_findings f
                JOIN reflection_runs r ON r.id = f.run_id
                LEFT JOIN finding_feedback fb
                       ON fb.finding_id = f.id AND fb.user_name = %s
                WHERE r.created_by = %s AND {NOT_IN_DELETION_WINDOW}
                ORDER BY f.created_at DESC, f.id DESC
                LIMIT %s OFFSET %s
                """,
                (user_name, user_name, limit, offset),
            )
            rows = c.fetchall()
    finally:
        conn.close()

    results = []
    for r in rows:
        has_feedback = any([r[11], r[12], r[13], r[14], r[16]])
        results.append({
            "id": r[0],
            "run_id": r[1],
            "case_ref": r[2] or "",
            "module": r[3],
            "observation": r[4],
            "questions": _loads(r[5], []),
            "evidence": _loads(r[6], []),
            "unverified_quote_count": r[7] or 0,
            "language": r[8],
            "prompt_version": r[9],
            "created_at": iso(r[10]),
            "feedback": {
                "label": r[11],
                "note": r[12] or "",
                "alternative_explanation": r[13] or "",
                "flagged_misread": bool(r[14]),
                "updated_at": iso(r[15]),
                "shared_with_team": bool(r[16]),
            } if has_feedback else None,
        })
    return results


def delete_runs_for_drafts(cursor, draft_ids):
    """
    Permanently delete every reflection run that used any of these
    documents, with all of its findings and feedback.

    Takes the CALLER'S open cursor, so the deletion happens inside the
    same transaction as the document deletion itself: either the
    document and everything derived from it are gone, or neither is.
    Child rows (sources, findings, feedback) are removed by the database
    (ON DELETE CASCADE).

    Why whole runs, not just findings that quote the deleted document:
    a run's quotes may come from any document that fed it, including
    earlier documents added as history. Deleting the whole run is the
    conservative, erasure-safe choice.

    Returns the number of runs deleted.
    """
    ids = [int(d) for d in (draft_ids or [])]
    if not ids:
        return 0
    cursor.execute(
        """
        DELETE FROM reflection_runs
        WHERE id IN (
            SELECT run_id FROM reflection_run_sources WHERE draft_id = ANY(%s)
        )
        """,
        (ids,),
    )
    deleted_runs = cursor.rowcount
    # Stage 2: deleting the runs also removed their observations from any
    # pattern (ON DELETE CASCADE). A pattern left with NO observations at
    # all has nothing left to stand on, so its written explanation -- which
    # was derived from the erased observations -- is erased too. (A pattern
    # that keeps some observations stays, flagged on screen as needing to
    # be regenerated; see services/pattern_store.py:list_patterns.)
    # Skipped on a database that does not have the pattern tables yet.
    cursor.execute("SELECT to_regclass('patterns')")
    if cursor.fetchone()[0] is not None:
        cursor.execute(
            """
            DELETE FROM patterns p
            WHERE p.original_member_count > 0
              AND NOT EXISTS (SELECT 1 FROM pattern_findings pf WHERE pf.pattern_id = p.id)
            """
        )
    return deleted_runs
