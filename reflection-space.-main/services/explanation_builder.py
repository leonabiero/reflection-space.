"""
Explanation Builder
======================

Sprint 11 (Explainability). Turns the retrieval metadata that
rdi/retrieval_service.py already attaches to every historical document
(match_reasons, score, doc_type) into short, practitioner-facing
sentences explaining WHY a document was suggested for this reflection.

This module is purely presentational. It does NOT touch retrieval,
ranking, or which documents are returned -- it only reads fields that
already exist on every historical document dict (see
rdi/retrieval_service.py's _doc_to_dict() / HybridRetriever.retrieve())
and turns them into text for the Reflection Context screen.

No Anthropic API calls -- by design
--------------------------------------
Every explanation here is generated LOCALLY with plain Python string
matching. There is no Claude API call anywhere in this module, and
nothing here changes how many companion calls run per reflection.

This was a deliberate choice: a truly AI-generated "this document also
discusses X and Y" sentence would need an extra Claude call for every
historical document shown (up to 4 per reflection, per
rdi/context_engine.py's DEFAULT_HISTORY_LIMIT), on every one of the
70-100 reflections/month this pilot runs -- see the accompanying
handoff notes for exact projected cost. A lightweight local
keyword-overlap heuristic gets most of the practitioner-trust benefit
("oh yes, we did discuss that") at zero additional cost. If a fully
AI-generated version is ever wanted instead, this is the one module
that would need to change.

How the semantic explanation is derived
-------------------------------------------
For a document proposed by the SemanticRetriever, this module compares
today's selected document text against the historical document's
content: common short "stopwords" (Spanish/Euskera/English) are
filtered out of both, and whatever meaningful words (5+ letters) remain
in BOTH are treated as shared themes and named directly in the
sentence. This is a plain shared-vocabulary check, not topic modeling
or classification -- but it is enough to turn a bare "match found" flag
into something a practitioner can actually evaluate for themselves.

If no shared keywords are found, the explanation falls back to a
generic sentence rather than inventing specifics that aren't there.

Similarity categories
------------------------
SIMILARITY_BANDS converts a raw Qdrant cosine similarity score
(0.0-1.0) into one of four practitioner-facing labels (Very High / High
/ Moderate / Low). The raw score is NEVER shown in the UI -- only the
category -- so nothing about embeddings, vectors, or cosine similarity
is exposed to the practitioner.

Why the doc-type constants are duplicated here
---------------------------------------------------
PLAN_DOC_TYPES / ASSESSMENT_DOC_TYPES already exist in
rdi/retrieval_service.py. They are intentionally re-listed below
(word-for-word identical) rather than imported from there, so that this
purely-cosmetic module stays a lightweight, standalone import with no
path back into services.draft_storage / services.qdrant_service (and
therefore no dependency on psycopg2 / qdrant_client just to render an
explanation). If those two sets are ever changed in
rdi/retrieval_service.py, update the copies below to match.
"""

import re

# Keep in sync with rdi/retrieval_service.py's PLAN_DOC_TYPES / ASSESSMENT_DOC_TYPES.
PLAN_DOC_TYPES = {"Intervention plan", "Esku-hartze plana", "Plan de intervención"}
ASSESSMENT_DOC_TYPES = {"Social work report", "Gizarte-txostena", "Informe social"}


# --- Similarity categories ----------------------------------------------

# (minimum score, category key) pairs, checked highest-first.
SIMILARITY_BANDS = [
    (0.80, "very_high"),
    (0.65, "high"),
    (0.50, "moderate"),
    (0.0, "low"),
]


def similarity_category(score):
    """
    score (float 0-1, or None) -> "very_high" | "high" | "moderate" |
    "low" | None.

    Returns None if no score is available (e.g. the document was
    included only as a must_include or recency match, never proposed
    by the SemanticRetriever) -- callers should treat None as "don't
    show a Technical Details section at all".
    """
    if score is None:
        return None
    for threshold, label in SIMILARITY_BANDS:
        if score >= threshold:
            return label
    return "low"


# --- Shared-keyword extraction (for semantic explanations) --------------

# Small, common-function-word lists -- just enough to keep "the", "y",
# "eta", "de", etc. out of the comparison. Not a full NLP stopword list;
# the goal is only to stop the most frequent connector words from being
# reported as a "shared theme".
_STOPWORDS = {
    # Spanish
    "que", "de", "la", "el", "en", "y", "a", "los", "las", "un", "una",
    "por", "con", "para", "se", "su", "sus", "es", "del", "al", "lo",
    "como", "más", "pero", "sí", "no", "ha", "han", "fue", "ser", "esta",
    "este", "estos", "estas", "muy", "también", "sobre", "entre",
    # Euskera
    "eta", "da", "ez", "du", "duen", "dira", "bat", "batzuk", "hau",
    "hori", "honek", "horrek", "izan", "dela", "zen", "diren",
    # English
    "the", "and", "of", "to", "in", "on", "for", "with", "is", "are",
    "was", "were", "this", "that", "these", "those", "as", "at", "by",
    "or", "an", "it", "be", "has", "have", "had", "not", "also", "more",
}

# Words of 5+ letters only -- short words are almost never a meaningful
# "shared theme" and are more likely to be noise.
_WORD_RE = re.compile(r"[A-Za-zÀ-ÿ]{5,}", re.UNICODE)

MAX_SHARED_KEYWORDS = 3


def _keywords(text):
    if not text:
        return set()
    words = _WORD_RE.findall(text.lower())
    return {w for w in words if w not in _STOPWORDS}


def _shared_keywords(current_text, historical_text):
    """
    Words (5+ letters, minus stopwords) present in BOTH texts. Sorted
    longest-first as a cheap, dependency-free proxy for "more specific /
    more topical", and capped at MAX_SHARED_KEYWORDS so the resulting
    sentence stays short and readable.
    """
    current_kw = _keywords(current_text)
    hist_kw = _keywords(historical_text)
    shared = current_kw & hist_kw
    return sorted(shared, key=len, reverse=True)[:MAX_SHARED_KEYWORDS]


# --- Explanation sentences -----------------------------------------------

def _must_include_sentence(h, T):
    doc_type = h.get("doc_type", "")
    if doc_type in PLAN_DOC_TYPES:
        return T["why_reason_must_include_plan"]
    if doc_type in ASSESSMENT_DOC_TYPES:
        return T["why_reason_must_include_assessment"]
    return T["why_reason_must_include_generic"]


def _semantic_sentence(h, current_text, T):
    shared = _shared_keywords(current_text, h.get("content", ""))
    if shared:
        return T["why_reason_semantic_specific"].format(themes=", ".join(shared))
    return T["why_reason_semantic_generic"]


def _recency_sentence(T):
    return T["why_reason_recency"]


def build_explanations(h, current_text, T):
    """
    Build the list of human-readable explanation sentences for one
    historical document, covering every reason it was included.

    Parameters
    ----------
    h : dict
        One merged document dict from
        rdi.context_engine.get_historical_context() -- must carry
        "match_reasons" (or the older singular "match_reason"),
        "doc_type", and "content". "score" is read separately by
        similarity_category(), not by this function.
    current_text : str
        The practitioner's currently-selected document text (used only
        for the local keyword-overlap check -- never sent anywhere,
        never logged).
    T : dict
        The active language dict from services.language.get_lang().

    Returns
    -------
    list[str]
        One sentence per applicable reason, always in the fixed order
        (must_include, semantic, recency) regardless of what order
        match_reasons lists them in, so the panel reads consistently
        for every document.
    """
    reasons = h.get("match_reasons")
    if not reasons:
        single = h.get("match_reason")
        reasons = [single] if single else []

    sentences = []
    if "must_include" in reasons:
        sentences.append(_must_include_sentence(h, T))
    if "semantic" in reasons:
        sentences.append(_semantic_sentence(h, current_text, T))
    if "recency" in reasons:
        sentences.append(_recency_sentence(T))

    return sentences