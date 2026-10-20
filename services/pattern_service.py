"""
Pattern Service
=================

Stage 2 of the pattern explorer (see PATTERNS.md): runs one generation
from start to finish.

    shared observations  ->  meaning vectors  ->  groups  ->  evidence
    check  ->  one written explanation per group  ->  saved snapshot

Every step that costs money or could be abused is bounded:
  - Only observations their authors chose to share are read
    (services/pattern_store.py), and only for Supervisors / Programme
    Managers.
  - Only ONE generation can run at a time (pattern_store.start_run), so
    repeated clicks or two managers cannot launch duplicate paid work.
  - At most MAX_OBSERVATIONS_PER_RUN observations are compared and at most
    MAX_PATTERNS_PER_RUN groups are explained (services/pattern_engine.py),
    so the Claude spend of one generation has a hard ceiling.
  - Each observation is embedded once and the vector is cached, so
    regenerating costs only the new observations plus the explanations.

A generation is a SNAPSHOT: it never edits an earlier generation. If it
finds a group that substantially overlaps one a reviewer already judged in
the previous generation, that judgement is carried over (and recorded as
such), so regenerating does not throw away human review.

Failure handling: a failure while generating marks the run 'failed' (never
left 'running') and is re-raised so the page shows the standard numbered
error screen. A failure to EXPLAIN one group does not fail the run -- that
group is saved with the plain fallback explanation and can be retried.
"""

from concurrent.futures import ThreadPoolExecutor

from config import EMBEDDING_MODEL, EMBEDDING_DIMENSIONS
from services import embedding_service
from services.db_time import get_logger
from services.pattern_engine import (
    SIMILARITY_LEVELS, DEFAULT_SIMILARITY_LEVEL, DEFAULT_MIN_OBSERVATIONS,
    DEFAULT_MIN_REFLECTIONS, MAX_OBSERVATIONS_PER_RUN, MAX_PATTERNS_PER_RUN,
    cluster_by_similarity, select_candidates, representative_indices,
    match_previous, embedding_text,
)
from services.pattern_explainer import (
    explain_pattern, PATTERN_PROMPT_VERSION, MAX_OBSERVATIONS_SENT,
)
from services import pattern_store
from services.pattern_access import require_pattern_role
from services.reflection_service import COMPANION_MODEL

logger = get_logger(__name__)

# How many embedding / explanation requests run side by side.
EMBED_WORKERS = 6
EXPLAIN_WORKERS = 4


def embedding_model_key():
    """Identifies the embedding setup a cached vector belongs to, so a
    change of model or size never mixes incompatible vectors."""
    return f"{EMBEDDING_MODEL}:{EMBEDDING_DIMENSIONS}"


def _embed_missing(role, findings, vectors):
    """Embed every observation that has no cached vector yet and cache the
    results. Returns the number that could not be embedded."""
    missing = [f for f in findings if f["id"] not in vectors]
    if not missing:
        return 0

    def embed_one(finding):
        text = embedding_text(finding)
        return finding["id"], (embedding_service.embed_document(text) if text else None)

    new_vectors = {}
    with ThreadPoolExecutor(max_workers=EMBED_WORKERS) as pool:
        for finding_id, vector in pool.map(embed_one, missing):
            if vector:
                new_vectors[finding_id] = list(vector)

    if new_vectors:
        pattern_store.save_embeddings(role, new_vectors, embedding_model_key())
        vectors.update(new_vectors)
    return len(missing) - len(new_vectors)


def generate_patterns(role, actor, lang, lens_labels_by_key,
                      similarity_level=DEFAULT_SIMILARITY_LEVEL,
                      min_observations=DEFAULT_MIN_OBSERVATIONS,
                      min_reflections=DEFAULT_MIN_REFLECTIONS,
                      modules=None, date_from=None, date_to=None):
    """
    Run one pattern generation.

    Returns a dict with:
      status                'completed' | 'busy' | 'unavailable'
      run_id                the new snapshot (None when busy/unavailable)
      observations_considered
      truncated             True if more shared observations matched than
                            MAX_OBSERVATIONS_PER_RUN (the newest were used)
      not_embedded          observations that could not be given a meaning
                            vector this time (left out of grouping)
      patterns_created
      fallback_count        patterns whose written explanation failed and
                            was replaced by the plain fallback

    'busy': another generation is already running.
    'unavailable': the meaning-matching service is not configured.
    Raises PermissionError for any role other than Supervisor / Programme
    Manager, and re-raises unexpected failures after marking the run failed.
    """
    require_pattern_role(role)

    if similarity_level not in SIMILARITY_LEVELS:
        similarity_level = DEFAULT_SIMILARITY_LEVEL
    threshold = SIMILARITY_LEVELS[similarity_level]
    min_observations = max(2, int(min_observations))
    min_reflections = max(1, int(min_reflections))

    if not embedding_service.is_available():
        return {"status": "unavailable", "run_id": None, "observations_considered": 0,
                "truncated": False, "not_embedded": 0, "patterns_created": 0,
                "fallback_count": 0}

    parameters = {
        "similarity_level": similarity_level,
        "threshold": threshold,
        "min_observations": min_observations,
        "min_reflections": min_reflections,
        "modules": sorted(modules) if modules else [],
        "date_from": str(date_from) if date_from else None,
        "date_to": str(date_to) if date_to else None,
        "max_observations": MAX_OBSERVATIONS_PER_RUN,
        "max_patterns": MAX_PATTERNS_PER_RUN,
    }

    run_id = pattern_store.start_run(
        role, actor, parameters, lang, embedding_model_key(),
        COMPANION_MODEL, PATTERN_PROMPT_VERSION,
    )
    if run_id is None:
        return {"status": "busy", "run_id": None, "observations_considered": 0,
                "truncated": False, "not_embedded": 0, "patterns_created": 0,
                "fallback_count": 0}

    try:
        findings = pattern_store.get_shared_findings(
            role, modules=modules, date_from=date_from, date_to=date_to,
            limit=MAX_OBSERVATIONS_PER_RUN + 1,
        )
        truncated = len(findings) > MAX_OBSERVATIONS_PER_RUN
        findings = findings[:MAX_OBSERVATIONS_PER_RUN]

        vectors = pattern_store.get_cached_embeddings(
            role, [f["id"] for f in findings], embedding_model_key(),
        )
        not_embedded = _embed_missing(role, findings, vectors)

        usable = [f for f in findings if f["id"] in vectors]
        usable_vectors = [vectors[f["id"]] for f in usable]

        clusters = cluster_by_similarity(usable_vectors, threshold)
        candidates = select_candidates(
            usable, clusters, min_observations=min_observations,
            min_reflections=min_reflections,
        )

        previous = pattern_store.get_previous_patterns(role, run_id)

        def explain_group(candidate):
            chosen = representative_indices(
                usable_vectors, candidate["indices"], MAX_OBSERVATIONS_SENT,
            )
            return explain_pattern([usable[i] for i in chosen], lens_labels_by_key, lang)

        with ThreadPoolExecutor(max_workers=EXPLAIN_WORKERS) as pool:
            explanations = list(pool.map(explain_group, candidates))

        pattern_rows = []
        fallback_count = 0
        for candidate, explained in zip(candidates, explanations):
            members = [usable[i] for i in candidate["indices"]]
            member_ids = [m["id"] for m in members]
            counts = candidate["counts"]
            lens_order = sorted(counts["modules"], key=lambda k: (-counts["modules"][k], k))

            carried = match_previous(
                set(member_ids),
                [{"id": p["id"], "member_ids": p["member_ids"]} for p in previous],
            )
            carried_from = None
            if carried is not None:
                earlier = next(p for p in previous if p["id"] == carried["id"])
                carried_from = {
                    "pattern_id": earlier["id"],
                    "status": earlier["status"],
                    "excluded_ids": [i for i in earlier["excluded_ids"] if i in set(member_ids)],
                }

            if explained["status"] == "fallback":
                fallback_count += 1
            explanation = explained["explanation"]
            pattern_rows.append({
                **explanation,
                "modules": lens_order,
                "grouping_basis": {
                    "similarity_level": similarity_level,
                    "threshold": threshold,
                    "min_observations": min_observations,
                    "min_reflections": min_reflections,
                },
                "explanation_status": explained["status"],
                "member_ids": member_ids,
                "carried_from": carried_from,
            })

        if pattern_rows:
            pattern_store.save_patterns(role, run_id, pattern_rows)

        pattern_store.finish_run(
            run_id, "completed", observations_considered=len(usable),
            patterns_created=len(pattern_rows),
        )
        return {
            "status": "completed", "run_id": run_id,
            "observations_considered": len(usable), "truncated": truncated,
            "not_embedded": not_embedded, "patterns_created": len(pattern_rows),
            "fallback_count": fallback_count,
        }
    except Exception as exc:
        try:
            pattern_store.finish_run(
                run_id, "failed", error_summary=type(exc).__name__,
            )
        except Exception:
            logger.exception("Could not mark pattern run %r as failed", run_id)
        raise


def retry_explanation(role, actor, pattern_id, members, lens_labels_by_key, lang):
    """
    Try again to write the explanation of a pattern whose first attempt
    failed (explanation_status 'fallback'). `members` are the pattern's
    current observations. Returns True if a real explanation was saved.
    One Claude call (two if the first reply is invalid).
    """
    require_pattern_role(role)
    chosen = members[:MAX_OBSERVATIONS_SENT]
    explained = explain_pattern(chosen, lens_labels_by_key, lang)
    if explained["status"] != "ai":
        return False
    return pattern_store.update_pattern_explanation(
        role, actor, pattern_id, explained["explanation"],
    )
