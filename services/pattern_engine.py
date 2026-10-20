"""
Pattern Engine (pure logic)
=============================

Stage 2 of the pattern explorer (see PATTERNS.md).

This module decides which saved observations belong together and how
many independent pieces of evidence stand behind a group. It contains NO
database access, NO network calls and NO AI -- only arithmetic on data
passed in -- so every rule below can be tested exactly.

Three ideas it enforces
-------------------------
1. GROUPING BY MEANING, NOT BY LABEL. Observations are grouped by how
   similar their meaning is (their embedding vectors), across all eight
   reflection lenses, so one theme can span several lenses. It does not
   merely count how often a lens was used.

2. HONEST COUNTS. Several observations from the same reflection are not
   independent evidence, and several reflections about the same case are
   not several cases. So every group reports, separately:
     - observations     (how many saved observations are in the group)
     - reflections      (distinct reflection sessions behind them)
     - cases            (distinct case references -- only when recorded)
   Case identity is taken ONLY from the explicit case reference, never
   inferred from names, details, or similarity between narratives. Case
   references are typed by hand, so a typo can split one case into two;
   the interface says so.

3. A THRESHOLD IS NOT PROOF. The minimum group size and the similarity
   setting are configurable starting points that decide whether a group
   is worth showing for discussion. A group that clears them is a
   "candidate pattern for reflection" -- never evidence of bias, and
   never a statement about how common anything is across the
   organisation.

Clustering method: average-linkage agglomerative clustering on cosine
similarity. Two groups merge only while the AVERAGE similarity between all
their members stays at or above the threshold, which stops one loosely
related observation from chaining unrelated groups together.

numpy is already installed with Streamlit/pandas (see requirements.txt);
no new package is needed.
"""

import re
from collections import Counter

import numpy as np

# Starting-point similarity settings (cosine similarity, 0-1). These are
# NOT proven values: they must be calibrated against real shared
# observations during the pilot, which is why the page lets the reviewer
# change them and explains what they do.
SIMILARITY_LEVELS = {
    "broad": 0.70,
    "balanced": 0.76,
    "strict": 0.82,
}
DEFAULT_SIMILARITY_LEVEL = "balanced"

# Defaults for "enough evidence to be worth showing".
DEFAULT_MIN_OBSERVATIONS = 3
DEFAULT_MIN_REFLECTIONS = 2

# Never explain (and pay for) more than this many candidate patterns in
# one generation.
MAX_PATTERNS_PER_RUN = 20

# Bound on how many observations one generation will compare, so the
# grouping step stays fast. If there are more, the most recent are used
# and the page says so.
MAX_OBSERVATIONS_PER_RUN = 800

# Two patterns are treated as "the same pattern" across generations when
# their observations overlap at least this much (see match_previous).
CARRY_OVER_OVERLAP = 0.5


def normalise_case_ref(case_ref):
    """The identity used to count distinct cases: the case reference with
    surrounding spaces removed, inner spacing collapsed and capitals
    ignored. Returns None when no reference was recorded -- a missing
    reference is never counted as a case (and never as the same case)."""
    if not isinstance(case_ref, str):
        return None
    cleaned = re.sub(r"\s+", " ", case_ref).strip().casefold()
    return cleaned or None


def embedding_text(finding):
    """The text whose MEANING represents an observation. Only the
    observation itself: the lens it came from is deliberately left out so
    a theme can group across lenses, and the quotation is left out so
    grouping follows the idea, not incidental wording."""
    return (finding.get("observation") or "").strip()


def _normalised_matrix(vectors):
    matrix = np.asarray(vectors, dtype=float)
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return matrix / norms


def cluster_by_similarity(vectors, threshold):
    """
    Average-linkage agglomerative clustering.

    `vectors`: list of equal-length number lists (one per observation).
    Returns a list of clusters, each a sorted list of indices into
    `vectors`, ordered by their first index. Every index appears in
    exactly one cluster (singletons included). Deterministic: ties are
    broken by lowest index.
    """
    n = len(vectors)
    if n == 0:
        return []
    if n == 1:
        return [[0]]

    unit = _normalised_matrix(vectors)
    sim = unit @ unit.T
    np.fill_diagonal(sim, -np.inf)

    clusters = {i: [i] for i in range(n)}
    sizes = np.ones(n)

    while len(clusters) > 1:
        flat_index = int(np.argmax(sim))
        a, b = divmod(flat_index, n)
        best = sim[a, b]
        if not np.isfinite(best) or best < threshold:
            break
        if a > b:
            a, b = b, a
        # Merge b into a. Average linkage: the new group's similarity to
        # any other group is the size-weighted mean of the two it replaces.
        merged = (sizes[a] * sim[a] + sizes[b] * sim[b]) / (sizes[a] + sizes[b])
        sim[a, :] = merged
        sim[:, a] = merged
        sim[a, a] = -np.inf
        sim[b, :] = -np.inf
        sim[:, b] = -np.inf
        sizes[a] += sizes[b]
        clusters[a] = clusters[a] + clusters[b]
        del clusters[b]

    return sorted(sorted(members) for members in clusters.values())


def summarise_members(members):
    """
    Honest counts for a group of observations.

    Each member is a dict with at least: run_id, module, and optionally
    case_ref and created_at (ISO text). Returns:
      observations           how many observations
      reflections            distinct reflection sessions (run_id)
      cases                  distinct recorded case references
      reflections_without_case  reflections with no case reference
      case_recurrence_known  True only when EVERY reflection has a case
                             reference (otherwise cross-case recurrence
                             cannot be established)
      date_first / date_last  earliest / latest reflection date (or None)
      modules                {module: count}
    """
    run_ids = set()
    cases = set()
    runs_without_case = set()
    dates = []
    modules = Counter()

    for member in members:
        run_id = member.get("run_id")
        run_ids.add(run_id)
        case = normalise_case_ref(member.get("case_ref"))
        if case is None:
            runs_without_case.add(run_id)
        else:
            cases.add(case)
        created = member.get("created_at")
        if created:
            dates.append(str(created))
        if member.get("module"):
            modules[member["module"]] += 1

    return {
        "observations": len(members),
        "reflections": len(run_ids),
        "cases": len(cases),
        "reflections_without_case": len(runs_without_case),
        "case_recurrence_known": bool(cases) and not runs_without_case,
        "date_first": min(dates)[:10] if dates else None,
        "date_last": max(dates)[:10] if dates else None,
        "modules": dict(modules),
    }


def select_candidates(findings, clusters, min_observations=DEFAULT_MIN_OBSERVATIONS,
                      min_reflections=DEFAULT_MIN_REFLECTIONS,
                      max_patterns=MAX_PATTERNS_PER_RUN):
    """
    Keep only groups with enough evidence to be worth discussing: at least
    `min_observations` observations from at least `min_reflections`
    DISTINCT reflections (so one long reflection that repeats itself can
    never create a pattern on its own).

    Returns a list of {"indices": [...], "counts": summarise_members(...)}
    ordered by strength of evidence (more reflections, then more
    observations, then earliest member), capped at `max_patterns`.
    """
    candidates = []
    for indices in clusters:
        members = [findings[i] for i in indices]
        counts = summarise_members(members)
        if counts["observations"] < min_observations:
            continue
        if counts["reflections"] < min_reflections:
            continue
        candidates.append({"indices": list(indices), "counts": counts})

    candidates.sort(key=lambda c: (-c["counts"]["reflections"],
                                   -c["counts"]["observations"],
                                   c["indices"][0]))
    return candidates[:max_patterns]


def representative_indices(vectors, indices, limit):
    """The `limit` members closest to the group's centre -- the ones that
    best express what the group has in common. Used to keep what is sent
    to the explanation step small and focused. Returned in their original
    order."""
    if len(indices) <= limit:
        return list(indices)
    unit = _normalised_matrix([vectors[i] for i in indices])
    centre = unit.mean(axis=0)
    norm = np.linalg.norm(centre)
    if norm:
        centre = centre / norm
    scores = unit @ centre
    order = np.argsort(-scores, kind="stable")[:limit]
    return [indices[int(i)] for i in sorted(order)]


def jaccard(a, b):
    """Overlap between two sets of ids: shared / combined (0 to 1)."""
    a, b = set(a), set(b)
    if not a and not b:
        return 0.0
    return len(a & b) / len(a | b)


def match_previous(new_member_ids, previous_patterns, min_overlap=CARRY_OVER_OVERLAP):
    """
    Decide whether a newly found group is "the same pattern" as one from
    the previous generation, so a reviewer's judgement is not lost when
    patterns are regenerated.

    `new_member_ids`: set of finding ids in the new group.
    `previous_patterns`: [{"id": int, "member_ids": [...]}, ...]
    Returns the best-matching previous pattern dict whose overlap is at
    least `min_overlap`, or None. Ties go to the lowest pattern id.
    """
    best, best_score = None, 0.0
    for previous in sorted(previous_patterns, key=lambda p: p["id"]):
        score = jaccard(new_member_ids, previous["member_ids"])
        if score > best_score:
            best, best_score = previous, score
    if best is not None and best_score >= min_overlap:
        return best
    return None
