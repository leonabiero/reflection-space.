"""
Corpus Service
================

Runs one search for recurring wording and ideas across a collection of
texts (see CORPUS.md):

    passages  ->  meaning vectors  ->  groups  ->  evidence check
    (passages in at least N different documents)  ->  one written
    explanation per group  ->  saved snapshot

Bounded like the observation search: one search at a time, at most
MAX_PASSAGES_PER_RUN passages compared, at most MAX_PATTERNS_PER_RUN
groups explained, each passage embedded once and cached.

The page's "AI-written questions" switch arrives here as
`include_questions`; when it is off the model is told not to write any
and any it sends anyway is dropped.
"""

from concurrent.futures import ThreadPoolExecutor

from services import embedding_service, corpus_store
from services.corpus_engine import (
    CORPUS_SIMILARITY_LEVELS, DEFAULT_CORPUS_SIMILARITY_LEVEL,
    DEFAULT_MIN_PASSAGES, DEFAULT_MIN_DOCUMENTS, MAX_PASSAGES_PER_RUN,
    select_corpus_candidates,
)
from services.db_time import get_logger
from services.pattern_access import require_pattern_role
from services.pattern_engine import (
    cluster_by_similarity, representative_indices, match_previous,
    MAX_PATTERNS_PER_RUN,
)
from services.pattern_explainer import (
    explain_passage_group, CORPUS_PROMPT_VERSION, MAX_PASSAGES_SENT,
)
from services.pattern_service import embedding_model_key, EMBED_WORKERS, EXPLAIN_WORKERS
from services.reflection_service import COMPANION_MODEL

logger = get_logger(__name__)


def _embed_missing(role, passages, vectors):
    missing = [p for p in passages if p["id"] not in vectors]
    if not missing:
        return 0

    def embed_one(passage):
        text = (passage.get("text") or "").strip()
        return passage["id"], (embedding_service.embed_document(text) if text else None)

    new_vectors = {}
    with ThreadPoolExecutor(max_workers=EMBED_WORKERS) as pool:
        for passage_id, vector in pool.map(embed_one, missing):
            if vector:
                new_vectors[passage_id] = list(vector)
    if new_vectors:
        corpus_store.save_embeddings(role, new_vectors, embedding_model_key())
        vectors.update(new_vectors)
    return len(missing) - len(new_vectors)


def generate_corpus_patterns(role, actor, corpus_id, lang,
                             similarity_level=DEFAULT_CORPUS_SIMILARITY_LEVEL,
                             min_passages=DEFAULT_MIN_PASSAGES,
                             min_documents=DEFAULT_MIN_DOCUMENTS,
                             include_questions=True):
    """
    Run one search over a collection.

    Returns a dict: status ('completed' | 'busy' | 'unavailable' | 'empty'),
    run_id, documents_considered, passages_considered, truncated,
    not_embedded, patterns_created, fallback_count.

    'empty': the collection has fewer documents than the minimum asked for,
    so no pattern could possibly qualify (nothing is spent).
    Raises PermissionError for other roles; unexpected failures mark the run
    failed and are re-raised.
    """
    require_pattern_role(role)
    blank = {"run_id": None, "documents_considered": 0, "passages_considered": 0,
             "truncated": False, "not_embedded": 0, "patterns_created": 0,
             "fallback_count": 0}

    if similarity_level not in CORPUS_SIMILARITY_LEVELS:
        similarity_level = DEFAULT_CORPUS_SIMILARITY_LEVEL
    threshold = CORPUS_SIMILARITY_LEVELS[similarity_level]
    min_passages = max(2, int(min_passages))
    min_documents = max(2, int(min_documents))
    include_questions = bool(include_questions)

    if not embedding_service.is_available():
        return {"status": "unavailable", **blank}

    counts = corpus_store.get_counts(role, corpus_id)
    if counts["documents"] < min_documents:
        return {"status": "empty", **blank, "documents_considered": counts["documents"]}

    parameters = {
        "similarity_level": similarity_level, "threshold": threshold,
        "min_passages": min_passages, "min_documents": min_documents,
        "include_questions": include_questions,
        "max_passages": MAX_PASSAGES_PER_RUN, "max_patterns": MAX_PATTERNS_PER_RUN,
    }
    run_id = corpus_store.start_run(
        role, actor, corpus_id, parameters, lang, embedding_model_key(),
        COMPANION_MODEL, CORPUS_PROMPT_VERSION,
    )
    if run_id is None:
        return {"status": "busy", **blank}

    try:
        passages = corpus_store.get_passages(role, corpus_id, limit=MAX_PASSAGES_PER_RUN + 1)
        truncated = len(passages) > MAX_PASSAGES_PER_RUN
        passages = passages[:MAX_PASSAGES_PER_RUN]

        vectors = corpus_store.get_cached_embeddings(
            role, [p["id"] for p in passages], embedding_model_key())
        not_embedded = _embed_missing(role, passages, vectors)

        usable = [p for p in passages if p["id"] in vectors]
        usable_vectors = [vectors[p["id"]] for p in usable]
        documents_considered = len({p["document_id"] for p in usable})

        clusters = cluster_by_similarity(usable_vectors, threshold)
        candidates = select_corpus_candidates(
            usable, clusters, counts["documents"],
            min_passages=min_passages, min_documents=min_documents,
            max_patterns=MAX_PATTERNS_PER_RUN,
        )
        previous = corpus_store.get_previous_patterns(role, corpus_id, run_id)

        def explain_group(candidate):
            chosen = representative_indices(usable_vectors, candidate["indices"], MAX_PASSAGES_SENT)
            return explain_passage_group([usable[i] for i in chosen], lang, include_questions)

        with ThreadPoolExecutor(max_workers=EXPLAIN_WORKERS) as pool:
            explanations = list(pool.map(explain_group, candidates))

        rows, fallback_count = [], 0
        for candidate, explained in zip(candidates, explanations):
            member_ids = [usable[i]["id"] for i in candidate["indices"]]
            carried = match_previous(
                set(member_ids),
                [{"id": p["id"], "member_ids": p["member_ids"]} for p in previous])
            carried_from = None
            if carried is not None:
                earlier = next(p for p in previous if p["id"] == carried["id"])
                carried_from = {
                    "pattern_id": earlier["id"], "status": earlier["status"],
                    "excluded_ids": [i for i in earlier["excluded_ids"] if i in set(member_ids)],
                }
            if explained["status"] == "fallback":
                fallback_count += 1
            rows.append({
                **explained["explanation"],
                "grouping_basis": {
                    "similarity_level": similarity_level, "threshold": threshold,
                    "min_passages": min_passages, "min_documents": min_documents,
                },
                "explanation_status": explained["status"],
                "member_ids": member_ids,
                "carried_from": carried_from,
            })

        if rows:
            corpus_store.save_patterns(role, run_id, rows)
        corpus_store.finish_run(
            run_id, "completed", documents_considered=documents_considered,
            passages_considered=len(usable), patterns_created=len(rows))
        return {
            "status": "completed", "run_id": run_id,
            "documents_considered": documents_considered,
            "passages_considered": len(usable), "truncated": truncated,
            "not_embedded": not_embedded, "patterns_created": len(rows),
            "fallback_count": fallback_count,
        }
    except Exception as exc:
        try:
            corpus_store.finish_run(run_id, "failed", error_summary=type(exc).__name__)
        except Exception:
            logger.exception("Could not mark corpus run %r as failed", run_id)
        raise


def retry_explanation(role, actor, pattern_id, members, lang, include_questions=True):
    """Try again to write the explanation of a pattern whose first attempt
    failed. `members` are its current passages. True if a real one was saved."""
    require_pattern_role(role)
    explained = explain_passage_group(members[:MAX_PASSAGES_SENT], lang, include_questions)
    if explained["status"] != "ai":
        return False
    return corpus_store.update_pattern_explanation(role, actor, pattern_id, explained["explanation"])
