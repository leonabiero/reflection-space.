"""
Corpus Store
==============

The database side of "Corpus analysis" (see CORPUS.md).

WHO: every function starts with require_pattern_role() -- only Supervisors
and Programme Managers (services/pattern_access.py). Social Workers and the
System Administrator are refused here, not just hidden in the menu.

WHAT IS STORED: the texts a manager loads (after the app's name-removal
safety net), cut into passages, with their meaning-vectors and the patterns
found. File names are NEVER stored: each text is known by a neutral number
(T-001 ...) that is never reused, even after a text is deleted, so a number
printed in an old report cannot later point at a different text.

THE COLLECTION IS APART: nothing here reads practitioners' drafts,
reflections or notes, and nothing practitioners can do touches it.

HISTORY: pattern wording is never overwritten by a review; status changes,
challenged passages and carried-over judgements are appended to
corpus_pattern_events.

The word and phrase list (corpus_terms) belongs to one collection and is
erased with it. Word counts are NOT stored: they are computed from the
stored texts each time, so they can never be out of date.

Deleting a text or a whole collection erases its passages, vectors and
their place in every pattern (database cascade). A pattern left with no
passages is no longer shown; one that lost some is flagged on screen
(lost_members), because its written explanation may still reflect them.
"""

import hashlib
import json
import re
from datetime import timedelta

from services.corpus_engine import (
    split_passages, summarise_passages,
)
from services.corpus_terms import MAX_TERMS_PER_CORPUS, parse_term
from services.db_pool import get_conn as _acquire_pooled_conn
from services.db_time import now_utc, iso, get_logger
from services.pattern_access import require_pattern_role
from services.pattern_store import PATTERN_STATUSES, MAX_COMMENT_CHARS, RUN_STALE_AFTER

logger = get_logger(__name__)

MAX_NAME_CHARS = 80
MAX_CORPORA = 50
MAX_DOCUMENTS_PER_CORPUS = 500

# Postgres advisory-lock key: only one search may run at a time.
_RUN_LOCK_KEY = 7731002


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


def content_fingerprint(text):
    """Identity used to spot the same text added twice: ignores capitals
    and differences in spacing."""
    normal = re.sub(r"\s+", " ", (text or "")).strip().casefold()
    return hashlib.sha256(normal.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------
# Collections
# ---------------------------------------------------------------------

def create_corpus(role, actor, name):
    """Create a collection. Returns its id, or None if the name is empty,
    the actor is missing, or the limit of collections is reached."""
    require_pattern_role(role)
    name = re.sub(r"\s+", " ", (name or "")).strip()[:MAX_NAME_CHARS]
    if not name or not actor:
        return None
    conn = _get_conn()
    try:
        with conn.cursor() as c:
            c.execute("SELECT COUNT(*) FROM corpora")
            if c.fetchone()[0] >= MAX_CORPORA:
                conn.rollback()
                return None
            c.execute(
                "INSERT INTO corpora (name, created_by, created_by_role, created_at) "
                "VALUES (%s, %s, %s, %s) RETURNING id",
                (name, actor, role, now_utc()),
            )
            corpus_id = c.fetchone()[0]
        conn.commit()
        return corpus_id
    except Exception:
        conn.rollback()
        logger.exception("create_corpus FAILED")
        raise
    finally:
        conn.close()


def list_corpora(role):
    """All collections, newest first, each with its document count."""
    require_pattern_role(role)
    conn = _get_conn()
    try:
        with conn.cursor() as c:
            c.execute(
                """
                SELECT k.id, k.name, k.created_at,
                       (SELECT COUNT(*) FROM corpus_documents d WHERE d.corpus_id = k.id)
                FROM corpora k ORDER BY k.id DESC
                """
            )
            rows = c.fetchall()
    finally:
        conn.close()
    return [{"id": r[0], "name": r[1], "created_at": iso(r[2]), "documents": r[3]} for r in rows]


def delete_corpus(role, actor, corpus_id):
    """Erase a collection with every text, passage, vector and pattern in
    it. Returns True if it existed."""
    require_pattern_role(role)
    conn = _get_conn()
    try:
        with conn.cursor() as c:
            c.execute("DELETE FROM corpora WHERE id = %s", (corpus_id,))
            deleted = c.rowcount > 0
        conn.commit()
        return deleted
    except Exception:
        conn.rollback()
        logger.exception("delete_corpus FAILED: corpus_id=%r", corpus_id)
        raise
    finally:
        conn.close()


# ---------------------------------------------------------------------
# Texts
# ---------------------------------------------------------------------

def add_document(role, actor, corpus_id, text):
    """
    Add one text (already cleaned and name-removed by the caller).

    Returns a dict:
      {"status": "added", "id", "doc_no", "passages"}
      {"status": "duplicate", "doc_no"}      same text already in the collection
      {"status": "empty"}                    no usable passage could be cut from it
      {"status": "missing"}                  the collection does not exist
      {"status": "full"}                     the collection is at its size limit
    """
    require_pattern_role(role)
    text = (text or "").strip()
    passages = split_passages(text)
    if not passages:
        return {"status": "empty"}
    fingerprint = content_fingerprint(text)

    conn = _get_conn()
    try:
        with conn.cursor() as c:
            # Locking the collection's row makes numbering and duplicate
            # checks safe when two managers add texts at the same moment.
            c.execute("SELECT id FROM corpora WHERE id = %s FOR UPDATE", (corpus_id,))
            if not c.fetchone():
                conn.rollback()
                return {"status": "missing"}
            c.execute(
                "SELECT doc_no FROM corpus_documents WHERE corpus_id = %s AND content_hash = %s",
                (corpus_id, fingerprint),
            )
            existing = c.fetchone()
            if existing:
                conn.rollback()
                return {"status": "duplicate", "doc_no": existing[0]}
            c.execute("SELECT COUNT(*) FROM corpus_documents WHERE corpus_id = %s", (corpus_id,))
            if c.fetchone()[0] >= MAX_DOCUMENTS_PER_CORPUS:
                conn.rollback()
                return {"status": "full"}
            c.execute(
                "UPDATE corpora SET last_doc_no = last_doc_no + 1 WHERE id = %s RETURNING last_doc_no",
                (corpus_id,),
            )
            doc_no = c.fetchone()[0]
            c.execute(
                """
                INSERT INTO corpus_documents
                    (corpus_id, doc_no, content, content_hash, char_count, added_by, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id
                """,
                (corpus_id, doc_no, text, fingerprint, len(text), actor, now_utc()),
            )
            document_id = c.fetchone()[0]
            for position, passage in enumerate(passages):
                c.execute(
                    "INSERT INTO corpus_passages (document_id, position, text) VALUES (%s, %s, %s)",
                    (document_id, position, passage),
                )
        conn.commit()
        return {"status": "added", "id": document_id, "doc_no": doc_no, "passages": len(passages)}
    except Exception:
        conn.rollback()
        logger.exception("add_document FAILED: corpus_id=%r", corpus_id)
        raise
    finally:
        conn.close()


def list_documents(role, corpus_id):
    """The texts of a collection in number order. Never includes the text
    itself, only: id, doc_no, char_count, passages, created_at."""
    require_pattern_role(role)
    conn = _get_conn()
    try:
        with conn.cursor() as c:
            c.execute(
                """
                SELECT d.id, d.doc_no, d.char_count, d.created_at,
                       (SELECT COUNT(*) FROM corpus_passages p WHERE p.document_id = d.id)
                FROM corpus_documents d WHERE d.corpus_id = %s ORDER BY d.doc_no
                """,
                (corpus_id,),
            )
            rows = c.fetchall()
    finally:
        conn.close()
    return [{"id": r[0], "doc_no": r[1], "char_count": r[2], "created_at": iso(r[3]),
             "passages": r[4]} for r in rows]


def delete_document(role, actor, corpus_id, doc_no):
    """Erase one text with its passages, vectors and place in patterns.
    Returns True if it existed. Its number is never reused."""
    require_pattern_role(role)
    conn = _get_conn()
    try:
        with conn.cursor() as c:
            c.execute(
                "DELETE FROM corpus_documents WHERE corpus_id = %s AND doc_no = %s",
                (corpus_id, doc_no),
            )
            deleted = c.rowcount > 0
        conn.commit()
        return deleted
    except Exception:
        conn.rollback()
        logger.exception("delete_document FAILED: corpus_id=%r", corpus_id)
        raise
    finally:
        conn.close()


def get_counts(role, corpus_id):
    """{"documents": n, "passages": m} for a collection."""
    require_pattern_role(role)
    conn = _get_conn()
    try:
        with conn.cursor() as c:
            c.execute(
                """
                SELECT COUNT(DISTINCT d.id), COUNT(p.id)
                FROM corpus_documents d
                LEFT JOIN corpus_passages p ON p.document_id = d.id
                WHERE d.corpus_id = %s
                """,
                (corpus_id,),
            )
            row = c.fetchone()
    finally:
        conn.close()
    return {"documents": row[0], "passages": row[1]}


def get_passages(role, corpus_id, limit=3000):
    """Passages of a collection in text-number then reading order:
    id, document_id, doc_no, position, text."""
    require_pattern_role(role)
    limit = max(1, min(int(limit), 10000))
    conn = _get_conn()
    try:
        with conn.cursor() as c:
            c.execute(
                """
                SELECT p.id, p.document_id, d.doc_no, p.position, p.text
                FROM corpus_passages p JOIN corpus_documents d ON d.id = p.document_id
                WHERE d.corpus_id = %s ORDER BY d.doc_no, p.position LIMIT %s
                """,
                (corpus_id, limit),
            )
            rows = c.fetchall()
    finally:
        conn.close()
    return [{"id": r[0], "document_id": r[1], "doc_no": r[2], "position": r[3], "text": r[4]}
            for r in rows]


# ---------------------------------------------------------------------
# Cached meaning-vectors
# ---------------------------------------------------------------------

def get_cached_embeddings(role, passage_ids, model):
    """{passage_id: vector} for passages already embedded with `model`."""
    require_pattern_role(role)
    if not passage_ids:
        return {}
    conn = _get_conn()
    try:
        with conn.cursor() as c:
            c.execute(
                "SELECT passage_id, vector FROM corpus_passage_embeddings "
                "WHERE model = %s AND passage_id = ANY(%s)",
                (model, list(passage_ids)),
            )
            return {r[0]: list(r[1]) for r in c.fetchall()}
    finally:
        conn.close()


def save_embeddings(role, vectors_by_passage_id, model):
    """Cache {passage_id: vector}. Safe to repeat; a passage erased in the
    meantime is skipped."""
    require_pattern_role(role)
    if not vectors_by_passage_id:
        return 0
    conn = _get_conn()
    try:
        with conn.cursor() as c:
            for passage_id, vector in vectors_by_passage_id.items():
                c.execute(
                    """
                    INSERT INTO corpus_passage_embeddings (passage_id, model, dims, vector, created_at)
                    SELECT %s, %s, %s, %s, %s
                    WHERE EXISTS (SELECT 1 FROM corpus_passages WHERE id = %s)
                    ON CONFLICT (passage_id) DO UPDATE SET
                        model = EXCLUDED.model, dims = EXCLUDED.dims,
                        vector = EXCLUDED.vector, created_at = EXCLUDED.created_at
                    """,
                    (passage_id, model, len(vector), [float(x) for x in vector],
                     now_utc(), passage_id),
                )
        conn.commit()
        return len(vectors_by_passage_id)
    except Exception:
        conn.rollback()
        logger.exception("save_embeddings FAILED (batch rolled back)")
        raise
    finally:
        conn.close()


# ---------------------------------------------------------------------
# Search runs
# ---------------------------------------------------------------------

def start_run(role, actor, corpus_id, parameters, language, embedding_model,
              explanation_model, prompt_version):
    """Begin a search. Returns the run id, or None if another search is
    already running (so repeated clicks cannot start duplicate paid work)
    or the collection does not exist."""
    require_pattern_role(role)
    conn = _get_conn()
    try:
        with conn.cursor() as c:
            c.execute("SELECT pg_advisory_xact_lock(%s)", (_RUN_LOCK_KEY,))
            c.execute("SELECT 1 FROM corpora WHERE id = %s", (corpus_id,))
            if not c.fetchone():
                conn.rollback()
                return None
            c.execute(
                "SELECT id FROM corpus_pattern_runs WHERE status = 'running' AND created_at > %s LIMIT 1",
                (now_utc() - RUN_STALE_AFTER,),
            )
            if c.fetchone():
                conn.rollback()
                return None
            c.execute(
                """
                INSERT INTO corpus_pattern_runs
                    (corpus_id, status, parameters, language, embedding_model,
                     explanation_model, prompt_version, created_by, created_by_role, created_at)
                VALUES (%s, 'running', %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id
                """,
                (corpus_id, _dumps(parameters), language, embedding_model,
                 explanation_model, prompt_version, actor, role, now_utc()),
            )
            run_id = c.fetchone()[0]
        conn.commit()
        return run_id
    except Exception:
        conn.rollback()
        logger.exception("corpus start_run FAILED")
        raise
    finally:
        conn.close()


def finish_run(run_id, status, documents_considered=0, passages_considered=0,
               patterns_created=0, error_summary=""):
    """Close a search as 'completed' or 'failed'. `error_summary` must be a
    short technical reason, never text from the documents."""
    if status not in ("completed", "failed"):
        raise ValueError("status must be 'completed' or 'failed'")
    conn = _get_conn()
    try:
        with conn.cursor() as c:
            c.execute(
                """
                UPDATE corpus_pattern_runs
                SET status = %s, documents_considered = %s, passages_considered = %s,
                    patterns_created = %s, error_summary = %s, finished_at = %s
                WHERE id = %s
                """,
                (status, documents_considered, passages_considered, patterns_created,
                 (error_summary or "")[:500], now_utc(), run_id),
            )
        conn.commit()
    except Exception:
        conn.rollback()
        logger.exception("corpus finish_run FAILED: run_id=%r", run_id)
        raise
    finally:
        conn.close()


_RUN_COLUMNS = (
    "id, corpus_id, status, parameters, language, embedding_model, explanation_model, "
    "prompt_version, documents_considered, passages_considered, patterns_created, "
    "error_summary, created_at, finished_at"
)


def _run_row(r):
    return {
        "id": r[0], "corpus_id": r[1], "status": r[2], "parameters": _loads(r[3], {}),
        "language": r[4], "embedding_model": r[5], "explanation_model": r[6],
        "prompt_version": r[7], "documents_considered": r[8], "passages_considered": r[9],
        "patterns_created": r[10], "error_summary": r[11] or "",
        "created_at": iso(r[12]), "finished_at": iso(r[13]),
    }


def get_run(role, run_id):
    require_pattern_role(role)
    conn = _get_conn()
    try:
        with conn.cursor() as c:
            c.execute(f"SELECT {_RUN_COLUMNS} FROM corpus_pattern_runs WHERE id = %s", (run_id,))
            r = c.fetchone()
    finally:
        conn.close()
    return _run_row(r) if r else None


def list_runs(role, corpus_id, limit=10):
    """Recent COMPLETED searches of a collection, newest first."""
    require_pattern_role(role)
    limit = max(1, min(int(limit), 50))
    conn = _get_conn()
    try:
        with conn.cursor() as c:
            c.execute(
                f"SELECT {_RUN_COLUMNS} FROM corpus_pattern_runs "
                "WHERE corpus_id = %s AND status = 'completed' ORDER BY id DESC LIMIT %s",
                (corpus_id, limit),
            )
            rows = c.fetchall()
    finally:
        conn.close()
    return [_run_row(r) for r in rows]


# ---------------------------------------------------------------------
# Patterns
# ---------------------------------------------------------------------

def get_previous_patterns(role, corpus_id, before_run_id):
    """Patterns of the latest completed search of this collection before
    `before_run_id`, with member ids and challenged ids, so a reviewer's
    judgement can be carried forward."""
    require_pattern_role(role)
    conn = _get_conn()
    try:
        with conn.cursor() as c:
            c.execute(
                """
                SELECT id FROM corpus_pattern_runs
                WHERE corpus_id = %s AND status = 'completed' AND id < %s AND patterns_created > 0
                ORDER BY id DESC LIMIT 1
                """,
                (corpus_id, before_run_id),
            )
            row = c.fetchone()
            if not row:
                return []
            c.execute("SELECT id, status FROM corpus_patterns WHERE run_id = %s ORDER BY id", (row[0],))
            patterns = {r[0]: {"id": r[0], "status": r[1], "member_ids": [], "excluded_ids": []}
                        for r in c.fetchall()}
            if patterns:
                c.execute(
                    "SELECT pattern_id, passage_id, excluded FROM corpus_pattern_passages "
                    "WHERE pattern_id = ANY(%s)",
                    (list(patterns),),
                )
                for pattern_id, passage_id, excluded in c.fetchall():
                    patterns[pattern_id]["member_ids"].append(passage_id)
                    if excluded:
                        patterns[pattern_id]["excluded_ids"].append(passage_id)
            return list(patterns.values())
    finally:
        conn.close()


def save_patterns(role, run_id, patterns):
    """Save a search's patterns, their passages and a 'generated' event in
    one transaction. Same dict shape as services/pattern_store.save_patterns
    (member_ids are passage ids). Returns the new pattern ids."""
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
                    INSERT INTO corpus_patterns
                        (run_id, title, description, why_it_matters,
                         alternative_explanations, limitations, questions,
                         grouping_basis, explanation_status, status,
                         original_member_count, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id
                    """,
                    (run_id, p["title"], p.get("description", ""), p.get("why_it_matters", ""),
                     _dumps(p.get("alternative_explanations", [])), _dumps(p.get("limitations", [])),
                     _dumps(p.get("questions", [])), _dumps(p.get("grouping_basis", {})),
                     p.get("explanation_status", "ai"), status, len(p["member_ids"]), now_utc()),
                )
                pattern_id = c.fetchone()[0]
                new_ids.append(pattern_id)
                excluded_ids = set((carried or {}).get("excluded_ids") or [])
                for passage_id in p["member_ids"]:
                    c.execute(
                        "INSERT INTO corpus_pattern_passages (pattern_id, passage_id, excluded) "
                        "VALUES (%s, %s, %s) ON CONFLICT DO NOTHING",
                        (pattern_id, passage_id, passage_id in excluded_ids),
                    )
                c.execute(
                    "INSERT INTO corpus_pattern_events (pattern_id, kind, actor, actor_role, "
                    "new_value, created_at) VALUES (%s, 'generated', 'system', 'system', 'candidate', %s)",
                    (pattern_id, now_utc()),
                )
                if carried and status != "candidate":
                    c.execute(
                        "INSERT INTO corpus_pattern_events (pattern_id, kind, actor, actor_role, "
                        "old_value, new_value, comment, created_at) "
                        "VALUES (%s, 'carried_over', 'system', 'system', %s, %s, %s, %s)",
                        (pattern_id, str(carried.get("pattern_id")), status,
                         "carried over from the same pattern in an earlier search", now_utc()),
                    )
        conn.commit()
        return new_ids
    except Exception:
        conn.rollback()
        logger.exception("corpus save_patterns FAILED (run %r rolled back)", run_id)
        raise
    finally:
        conn.close()


def list_patterns(role, run_id, statuses=None):
    """
    The patterns of one search, each with its CURRENT passages and honest
    counts (passages, different documents, out of how many documents the
    collection has NOW).

    A pattern left with no passages (texts deleted) is not returned. Keys:
    id, title, description, why_it_matters, alternative_explanations,
    limitations, questions, grouping_basis (dict), explanation_status,
    status, created_at, lost_members (passages no longer available -- the
    written explanation may still reflect them), members (current, not
    challenged), excluded_members, counts (see corpus_engine.summarise_passages),
    below_minimum (True if deletions or challenges dropped it under the
    search's own minimums).
    """
    require_pattern_role(role)
    run = get_run(role, run_id)
    if run is None:
        return []
    parameters = run["parameters"] or {}
    min_passages = int(parameters.get("min_passages", 0) or 0)
    min_documents = int(parameters.get("min_documents", 0) or 0)

    conn = _get_conn()
    try:
        with conn.cursor() as c:
            conditions, params = ["p.run_id = %s"], [run_id]
            if statuses:
                conditions.append("p.status = ANY(%s)")
                params.append(list(statuses))
            c.execute(
                f"""
                SELECT p.id, p.title, p.description, p.why_it_matters,
                       p.alternative_explanations, p.limitations, p.questions,
                       p.grouping_basis, p.explanation_status, p.status,
                       p.created_at, p.original_member_count
                FROM corpus_patterns p WHERE {' AND '.join(conditions)} ORDER BY p.id
                """,
                params,
            )
            pattern_rows = c.fetchall()
            if not pattern_rows:
                return []
            ids = [r[0] for r in pattern_rows]
            c.execute(
                """
                SELECT pp.pattern_id, pp.excluded, ps.id, ps.document_id, d.doc_no,
                       ps.position, ps.text
                FROM corpus_pattern_passages pp
                JOIN corpus_passages ps ON ps.id = pp.passage_id
                JOIN corpus_documents d ON d.id = ps.document_id
                WHERE pp.pattern_id = ANY(%s)
                ORDER BY d.doc_no, ps.position
                """,
                (ids,),
            )
            member_rows = c.fetchall()
            c.execute("SELECT COUNT(*) FROM corpus_documents WHERE corpus_id = %s", (run["corpus_id"],))
            total_documents = c.fetchone()[0]
    finally:
        conn.close()

    members_by, excluded_by = {i: [] for i in ids}, {i: [] for i in ids}
    for m in member_rows:
        passage = {"id": m[2], "document_id": m[3], "doc_no": m[4], "position": m[5], "text": m[6]}
        (excluded_by if m[1] else members_by)[m[0]].append(passage)

    results = []
    for r in pattern_rows:
        members, excluded = members_by[r[0]], excluded_by[r[0]]
        if not members:
            continue
        counts = summarise_passages(members, total_documents)
        results.append({
            "id": r[0], "title": r[1], "description": r[2] or "", "why_it_matters": r[3] or "",
            "alternative_explanations": _loads(r[4], []), "limitations": _loads(r[5], []),
            "questions": _loads(r[6], []), "grouping_basis": _loads(r[7], {}),
            "explanation_status": r[8], "status": r[9], "created_at": iso(r[10]),
            "lost_members": max(0, (r[11] or 0) - len(members) - len(excluded)),
            "members": members, "excluded_members": excluded, "counts": counts,
            "below_minimum": bool(
                (min_passages and counts["passages"] < min_passages)
                or (min_documents and counts["documents"] < min_documents)
            ),
        })
    return results


# ---------------------------------------------------------------------
# Review actions (append to history; nothing is overwritten)
# ---------------------------------------------------------------------

def set_pattern_status(role, actor, pattern_id, new_status, comment=""):
    """Record the team's judgement. Returns True if something changed."""
    require_pattern_role(role)
    if not actor or new_status not in PATTERN_STATUSES:
        return False
    comment = (comment or "").strip()[:MAX_COMMENT_CHARS]
    conn = _get_conn()
    try:
        with conn.cursor() as c:
            c.execute("SELECT status FROM corpus_patterns WHERE id = %s FOR UPDATE", (pattern_id,))
            row = c.fetchone()
            if not row:
                conn.rollback()
                return False
            old_status = row[0]
            if old_status == new_status and not comment:
                conn.rollback()
                return False
            if old_status != new_status:
                c.execute("UPDATE corpus_patterns SET status = %s WHERE id = %s", (new_status, pattern_id))
            c.execute(
                "INSERT INTO corpus_pattern_events (pattern_id, kind, actor, actor_role, "
                "old_value, new_value, comment, created_at) "
                "VALUES (%s, 'status_changed', %s, %s, %s, %s, %s, %s)",
                (pattern_id, actor, role, old_status, new_status, comment, now_utc()),
            )
        conn.commit()
        return True
    except Exception:
        conn.rollback()
        logger.exception("corpus set_pattern_status FAILED: pattern_id=%r", pattern_id)
        raise
    finally:
        conn.close()


def set_member_excluded(role, actor, pattern_id, passage_id, excluded, comment=""):
    """Challenge the grouping: mark one passage as not belonging to a
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
                "SELECT excluded FROM corpus_pattern_passages WHERE pattern_id = %s "
                "AND passage_id = %s FOR UPDATE",
                (pattern_id, passage_id),
            )
            row = c.fetchone()
            if not row or bool(row[0]) == excluded:
                conn.rollback()
                return False
            c.execute(
                "UPDATE corpus_pattern_passages SET excluded = %s WHERE pattern_id = %s AND passage_id = %s",
                (excluded, pattern_id, passage_id),
            )
            c.execute(
                "INSERT INTO corpus_pattern_events (pattern_id, kind, actor, actor_role, "
                "new_value, comment, created_at) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                (pattern_id, "member_excluded" if excluded else "member_restored",
                 actor, role, str(passage_id), comment, now_utc()),
            )
        conn.commit()
        return True
    except Exception:
        conn.rollback()
        logger.exception("corpus set_member_excluded FAILED: pattern_id=%r", pattern_id)
        raise
    finally:
        conn.close()


def update_pattern_explanation(role, actor, pattern_id, explanation):
    """Replace the written explanation of a pattern whose explanation is
    still the plain fallback. Recorded in history. Returns True if replaced."""
    require_pattern_role(role)
    conn = _get_conn()
    try:
        with conn.cursor() as c:
            c.execute("SELECT explanation_status FROM corpus_patterns WHERE id = %s FOR UPDATE",
                      (pattern_id,))
            row = c.fetchone()
            if not row or row[0] != "fallback":
                conn.rollback()
                return False
            c.execute(
                """
                UPDATE corpus_patterns SET title = %s, description = %s, why_it_matters = %s,
                    alternative_explanations = %s, limitations = %s, questions = %s,
                    explanation_status = 'ai'
                WHERE id = %s
                """,
                (explanation["title"], explanation["description"], explanation["why_it_matters"],
                 _dumps(explanation["alternative_explanations"]), _dumps(explanation["limitations"]),
                 _dumps(explanation["questions"]), pattern_id),
            )
            c.execute(
                "INSERT INTO corpus_pattern_events (pattern_id, kind, actor, actor_role, created_at) "
                "VALUES (%s, 'explanation_regenerated', %s, %s, %s)",
                (pattern_id, actor, role, now_utc()),
            )
        conn.commit()
        return True
    except Exception:
        conn.rollback()
        logger.exception("corpus update_pattern_explanation FAILED: pattern_id=%r", pattern_id)
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
                "SELECT kind, actor, actor_role, old_value, new_value, comment, created_at "
                "FROM corpus_pattern_events WHERE pattern_id = %s ORDER BY id",
                (pattern_id,),
            )
            rows = c.fetchall()
    finally:
        conn.close()
    return [{"kind": r[0], "actor": r[1] or "", "actor_role": r[2] or "", "old_value": r[3] or "",
             "new_value": r[4] or "", "comment": r[5] or "", "created_at": iso(r[6])} for r in rows]


# ---------------------------------------------------------------------
# Step 2: readings of each text through the reflection lenses
# ---------------------------------------------------------------------
#
# One row per text per lens: the AI's observation (written in the
# interface language), optional questions, and the exact passages that
# were VERIFIED to appear in the stored text (services/evidence.py). The
# reading of a text is replaced if it is read again; it is erased with
# the text. A lens the AI did not raise anything for is stored as
# "no_finding" -- that means "nothing raised", never "nothing there".

from services.findings_store import FINDING_MODULES as READING_LENSES

READING_STATUSES = ("finding", "no_finding", "failed")
_READING_LOCK_KEY = 7731003


def get_documents_to_read(role, corpus_id, limit):
    """The next texts that still need reading (fewer than all lenses
    successfully read), in number order: id, doc_no, content."""
    require_pattern_role(role)
    limit = max(1, min(int(limit), 100))
    conn = _get_conn()
    try:
        with conn.cursor() as c:
            c.execute(
                """
                SELECT d.id, d.doc_no, d.content
                FROM corpus_documents d
                WHERE d.corpus_id = %s
                  AND (SELECT COUNT(*) FROM corpus_readings r
                       WHERE r.document_id = d.id AND r.status <> 'failed') < %s
                ORDER BY d.doc_no LIMIT %s
                """,
                (corpus_id, len(READING_LENSES), limit),
            )
            rows = c.fetchall()
    finally:
        conn.close()
    return [{"id": r[0], "doc_no": r[1], "content": r[2]} for r in rows]


def start_reading_job(role, actor, corpus_id, documents_total):
    """Begin a reading job. Returns its id, or None if another reading is
    already running (so repeated clicks cannot start duplicate paid work)
    or the collection does not exist."""
    require_pattern_role(role)
    conn = _get_conn()
    try:
        with conn.cursor() as c:
            c.execute("SELECT pg_advisory_xact_lock(%s)", (_READING_LOCK_KEY,))
            c.execute("SELECT 1 FROM corpora WHERE id = %s", (corpus_id,))
            if not c.fetchone():
                conn.rollback()
                return None
            c.execute(
                "SELECT id FROM corpus_reading_jobs WHERE status = 'running' AND created_at > %s LIMIT 1",
                (now_utc() - RUN_STALE_AFTER,),
            )
            if c.fetchone():
                conn.rollback()
                return None
            c.execute(
                """
                INSERT INTO corpus_reading_jobs
                    (corpus_id, status, documents_total, created_by, created_by_role, created_at)
                VALUES (%s, 'running', %s, %s, %s, %s) RETURNING id
                """,
                (corpus_id, int(documents_total), actor, role, now_utc()),
            )
            job_id = c.fetchone()[0]
        conn.commit()
        return job_id
    except Exception:
        conn.rollback()
        logger.exception("start_reading_job FAILED")
        raise
    finally:
        conn.close()


def finish_reading_job(job_id, status, documents_done=0, failed_lenses=0, error_summary=""):
    """Close a reading job as 'completed' or 'failed'. `error_summary`
    must be a short technical reason, never text from the documents."""
    if status not in ("completed", "failed"):
        raise ValueError("status must be 'completed' or 'failed'")
    conn = _get_conn()
    try:
        with conn.cursor() as c:
            c.execute(
                """
                UPDATE corpus_reading_jobs
                SET status = %s, documents_done = %s, failed_lenses = %s,
                    error_summary = %s, finished_at = %s
                WHERE id = %s
                """,
                (status, documents_done, failed_lenses, (error_summary or "")[:500],
                 now_utc(), job_id),
            )
        conn.commit()
    except Exception:
        conn.rollback()
        logger.exception("finish_reading_job FAILED: job_id=%r", job_id)
        raise
    finally:
        conn.close()


def save_readings(role, document_id, readings):
    """
    Replace the stored reading of one text with `readings`, a list of dicts:
    lens, status, observation, questions (list), evidence (list of
    {"quote"}), unverified_count, model, prompt_version, include_questions,
    language. One transaction. Returns how many rows were saved (0 if the
    text was erased in the meantime).
    """
    require_pattern_role(role)
    clean = []
    for r in readings:
        if r.get("lens") not in READING_LENSES or r.get("status") not in READING_STATUSES:
            raise ValueError("invalid reading")
        clean.append(r)
    conn = _get_conn()
    try:
        with conn.cursor() as c:
            c.execute("SELECT id FROM corpus_documents WHERE id = %s FOR SHARE", (document_id,))
            if not c.fetchone():
                conn.rollback()
                return 0
            c.execute("DELETE FROM corpus_readings WHERE document_id = %s", (document_id,))
            for r in clean:
                c.execute(
                    """
                    INSERT INTO corpus_readings
                        (document_id, lens, status, observation, questions, evidence,
                         unverified_count, model, prompt_version, include_questions,
                         language, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (document_id, r["lens"], r["status"], r.get("observation", ""),
                     _dumps(r.get("questions", [])), _dumps(r.get("evidence", [])),
                     int(r.get("unverified_count", 0)), r.get("model", ""),
                     r.get("prompt_version", ""), bool(r.get("include_questions", True)),
                     r.get("language", ""), now_utc()),
                )
        conn.commit()
        return len(clean)
    except Exception:
        conn.rollback()
        logger.exception("save_readings FAILED: document_id=%r", document_id)
        raise
    finally:
        conn.close()


def get_reading_overview(role, corpus_id):
    """
    Honest counts for the reading of a collection:
      documents      texts in the collection
      read           texts with every lens successfully read
      unread         texts still to read (including ones with a failed lens)
      lenses         {lens: {"finding": n, "no_finding": n, "failed": n}} over ALL texts
    """
    require_pattern_role(role)
    conn = _get_conn()
    try:
        with conn.cursor() as c:
            c.execute("SELECT COUNT(*) FROM corpus_documents WHERE corpus_id = %s", (corpus_id,))
            documents = c.fetchone()[0]
            c.execute(
                """
                SELECT COUNT(*) FROM corpus_documents d
                WHERE d.corpus_id = %s
                  AND (SELECT COUNT(*) FROM corpus_readings r
                       WHERE r.document_id = d.id AND r.status <> 'failed') >= %s
                """,
                (corpus_id, len(READING_LENSES)),
            )
            read = c.fetchone()[0]
            c.execute(
                """
                SELECT r.lens, r.status, COUNT(*)
                FROM corpus_readings r JOIN corpus_documents d ON d.id = r.document_id
                WHERE d.corpus_id = %s GROUP BY r.lens, r.status
                """,
                (corpus_id,),
            )
            rows = c.fetchall()
    finally:
        conn.close()
    lenses = {lens: {"finding": 0, "no_finding": 0, "failed": 0} for lens in READING_LENSES}
    for lens, status, count in rows:
        if lens in lenses and status in lenses[lens]:
            lenses[lens][status] = count
    return {"documents": documents, "read": read, "unread": documents - read, "lenses": lenses}


def list_lens_readings(role, corpus_id, lens):
    """Every text where the AI raised an observation for `lens`, in text
    order: doc_no, observation, questions, evidence, unverified_count."""
    require_pattern_role(role)
    if lens not in READING_LENSES:
        return []
    conn = _get_conn()
    try:
        with conn.cursor() as c:
            c.execute(
                """
                SELECT d.doc_no, r.observation, r.questions, r.evidence, r.unverified_count
                FROM corpus_readings r JOIN corpus_documents d ON d.id = r.document_id
                WHERE d.corpus_id = %s AND r.lens = %s AND r.status = 'finding'
                ORDER BY d.doc_no
                """,
                (corpus_id, lens),
            )
            rows = c.fetchall()
    finally:
        conn.close()
    return [{"doc_no": r[0], "observation": r[1] or "", "questions": _loads(r[2], []),
             "evidence": _loads(r[3], []), "unverified_count": r[4]} for r in rows]


def get_text_readings(role, corpus_id, doc_no):
    """One text's reading across all lenses: {lens: {status, observation,
    questions, evidence, unverified_count}} (lenses not read are absent)."""
    require_pattern_role(role)
    conn = _get_conn()
    try:
        with conn.cursor() as c:
            c.execute(
                """
                SELECT r.lens, r.status, r.observation, r.questions, r.evidence, r.unverified_count
                FROM corpus_readings r JOIN corpus_documents d ON d.id = r.document_id
                WHERE d.corpus_id = %s AND d.doc_no = %s
                """,
                (corpus_id, doc_no),
            )
            rows = c.fetchall()
    finally:
        conn.close()
    return {r[0]: {"status": r[1], "observation": r[2] or "", "questions": _loads(r[3], []),
                   "evidence": _loads(r[4], []), "unverified_count": r[5]} for r in rows}


def clear_readings(role, actor, corpus_id):
    """Forget every reading of a collection (so all its texts can be read
    again). Returns how many rows were erased."""
    require_pattern_role(role)
    conn = _get_conn()
    try:
        with conn.cursor() as c:
            c.execute(
                "DELETE FROM corpus_readings WHERE document_id IN "
                "(SELECT id FROM corpus_documents WHERE corpus_id = %s)",
                (corpus_id,),
            )
            erased = c.rowcount
        conn.commit()
        return erased
    except Exception:
        conn.rollback()
        logger.exception("clear_readings FAILED: corpus_id=%r", corpus_id)
        raise
    finally:
        conn.close()


# ---------------------------------------------------------------------
# Step 3: the word and phrase list
# ---------------------------------------------------------------------

def get_document_contents(role, corpus_id):
    """The full (already name-removed) text of every document of a
    collection, in number order, for counting words: doc_no, content.
    Used only to count; the page never prints a whole text."""
    require_pattern_role(role)
    conn = _get_conn()
    try:
        with conn.cursor() as c:
            c.execute(
                "SELECT doc_no, content FROM corpus_documents WHERE corpus_id = %s ORDER BY doc_no",
                (corpus_id,),
            )
            rows = c.fetchall()
    finally:
        conn.close()
    return [{"doc_no": r[0], "content": r[1] or ""} for r in rows]


def list_terms(role, corpus_id):
    """The collection's word list in the order it was built: id, term,
    norm, origin ('manager', 'starter_es' or 'starter_eu')."""
    require_pattern_role(role)
    conn = _get_conn()
    try:
        with conn.cursor() as c:
            c.execute(
                "SELECT id, term, term_norm, origin FROM corpus_terms "
                "WHERE corpus_id = %s ORDER BY id",
                (corpus_id,),
            )
            rows = c.fetchall()
    finally:
        conn.close()
    return [{"id": r[0], "term": r[1], "norm": r[2], "origin": r[3]} for r in rows]


def add_terms(role, actor, corpus_id, raw_terms, origin="manager"):
    """
    Add words or phrases to a collection's list. `raw_terms` is a list of
    typed strings. Returns:
      {"status": "ok", "added": n, "duplicates": n, "invalid": [typed strings
       that could not be used], "full": True if the list limit stopped some}
      {"status": "missing"}   the collection does not exist
    Nothing is added twice (capitals, accents and spacing are ignored).
    """
    require_pattern_role(role)
    if not actor:
        return {"status": "missing"}
    added, duplicates, invalid, full = 0, 0, [], False
    conn = _get_conn()
    try:
        with conn.cursor() as c:
            c.execute("SELECT id FROM corpora WHERE id = %s FOR UPDATE", (corpus_id,))
            if not c.fetchone():
                conn.rollback()
                return {"status": "missing"}
            c.execute("SELECT COUNT(*) FROM corpus_terms WHERE corpus_id = %s", (corpus_id,))
            total = c.fetchone()[0]
            for raw in raw_terms:
                # A term may arrive as a plain string or as (origin, string).
                item_origin, text = (raw if isinstance(raw, tuple) else (origin, raw))
                parsed = parse_term(text)
                if parsed is None:
                    if (text or "").strip():
                        invalid.append((text or "").strip()[:80])
                    continue
                if total >= MAX_TERMS_PER_CORPUS:
                    full = True
                    continue
                c.execute(
                    """
                    INSERT INTO corpus_terms (corpus_id, term, term_norm, origin, created_by, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (corpus_id, term_norm) DO NOTHING
                    """,
                    (corpus_id, parsed["term"], parsed["norm"], item_origin, actor, now_utc()),
                )
                if c.rowcount:
                    added += 1
                    total += 1
                else:
                    duplicates += 1
        conn.commit()
        return {"status": "ok", "added": added, "duplicates": duplicates,
                "invalid": invalid, "full": full}
    except Exception:
        conn.rollback()
        logger.exception("add_terms FAILED: corpus_id=%r", corpus_id)
        raise
    finally:
        conn.close()


def delete_terms(role, actor, corpus_id, term_ids):
    """Remove words from a collection's list. Returns how many were removed."""
    require_pattern_role(role)
    ids = [int(i) for i in term_ids or []]
    if not ids:
        return 0
    conn = _get_conn()
    try:
        with conn.cursor() as c:
            c.execute(
                "DELETE FROM corpus_terms WHERE corpus_id = %s AND id = ANY(%s)",
                (corpus_id, ids),
            )
            removed = c.rowcount
        conn.commit()
        return removed
    except Exception:
        conn.rollback()
        logger.exception("delete_terms FAILED: corpus_id=%r", corpus_id)
        raise
    finally:
        conn.close()
