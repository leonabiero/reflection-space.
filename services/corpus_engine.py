"""
Corpus engine (pure logic)
============================

For the "Corpus analysis" area (see CORPUS.md): a manager loads a set of
existing texts (EDE's own ~70 documents) and the app looks for wording and
ideas that recur ACROSS those texts.

This module has no database and no AI. It does the three pieces of plain
logic the rest depends on:

  split_passages    cut one text into short passages that are EXACT pieces
                    of it (so a passage can always be found word for word
                    in its document)
  summarise_passages  honest counts for a group of passages: how many
                    passages, in how many DIFFERENT documents, out of how
                    many documents in the collection
  select_corpus_candidates  keep only groups seen in enough different
                    documents to be worth discussing

Grouping itself (similarity of meaning) reuses services/pattern_engine.py.
"""

import re

from services.pattern_engine import DEFAULT_MIN_OBSERVATIONS, MAX_PATTERNS_PER_RUN

# Starting points, NOT calibrated values. Raw sentences from different
# documents resemble each other less than AI-written observations do, so
# the levels sit a little higher than the observation-based ones. The
# page tells reviewers to change them and compare.
CORPUS_SIMILARITY_LEVELS = {"broad": 0.72, "balanced": 0.78, "strict": 0.84}
DEFAULT_CORPUS_SIMILARITY_LEVEL = "balanced"

DEFAULT_MIN_PASSAGES = 3
DEFAULT_MIN_DOCUMENTS = 3

TARGET_PASSAGE_CHARS = 380     # sentences are joined up to about this length
MAX_PASSAGE_CHARS = 800        # a single very long sentence is cut at this
MIN_PASSAGE_CHARS = 30         # shorter pieces (headings, "Ok.") are dropped
MAX_PASSAGES_PER_DOCUMENT = 150

# Cap on passages compared in one search (clustering stays fast to ~3,000).
MAX_PASSAGES_PER_RUN = 3000

# Sentence ends (. ! ? … : ;) followed by spaces, or any line break.
_BOUNDARY = re.compile(r"(?<=[.!?…:;])\s+|\n+")


def document_label(doc_no):
    """The neutral name shown for a document: T-001, T-002 ..."""
    return f"T-{int(doc_no):03d}"


def _sentence_spans(text):
    spans, start = [], 0
    for match in _BOUNDARY.finditer(text):
        if match.start() > start:
            spans.append((start, match.start()))
        start = match.end()
    if start < len(text):
        spans.append((start, len(text)))
    return [(s, e) for s, e in spans if text[s:e].strip()]


def _cut_long(text, start, end):
    """Cut an over-long stretch at spaces so no piece exceeds MAX_PASSAGE_CHARS."""
    pieces = []
    while end - start > MAX_PASSAGE_CHARS:
        cut = text.rfind(" ", start + MAX_PASSAGE_CHARS // 2, start + MAX_PASSAGE_CHARS)
        cut = cut if cut > start else start + MAX_PASSAGE_CHARS
        pieces.append((start, cut))
        start = cut
        while start < end and text[start] == " ":
            start += 1
    pieces.append((start, end))
    return pieces


def split_passages(text):
    """
    Cut `text` into passages.

    Every passage is `text[start:end]` for some span of the original, so it
    is always an EXACT piece of the document (never reworded, never joined
    across a gap). Consecutive sentences are grouped until a passage is
    about TARGET_PASSAGE_CHARS long. Pieces shorter than MIN_PASSAGE_CHARS
    are dropped, and at most MAX_PASSAGES_PER_DOCUMENT are returned.
    """
    text = text or ""
    spans = []
    for s, e in _sentence_spans(text):
        spans.extend(_cut_long(text, s, e))

    groups, current = [], None
    for s, e in spans:
        if current is None:
            current = [s, e]
        elif e - current[0] <= TARGET_PASSAGE_CHARS:
            current[1] = e
        else:
            groups.append(tuple(current))
            current = [s, e]
    if current is not None:
        groups.append(tuple(current))

    passages = []
    for s, e in groups:
        piece = text[s:e].strip()
        if len(piece) >= MIN_PASSAGE_CHARS:
            passages.append(piece)
        if len(passages) >= MAX_PASSAGES_PER_DOCUMENT:
            break
    return passages


def summarise_passages(members, total_documents):
    """
    Honest counts for a group of passages.

    Each member is a dict with at least `document_id` and `doc_no`.
    Returns:
      passages          how many passages
      documents         how many DIFFERENT documents they come from
      total_documents   how many documents the collection has
      doc_numbers       sorted document numbers (for display as T-003 ...)
      share             documents / total_documents (0 if the collection is empty)
    """
    docs = {}
    for member in members:
        docs[member["document_id"]] = member.get("doc_no")
    numbers = sorted(n for n in docs.values() if n is not None)
    total = max(int(total_documents or 0), len(docs))
    return {
        "passages": len(members),
        "documents": len(docs),
        "total_documents": total,
        "doc_numbers": numbers,
        "share": (len(docs) / total) if total else 0.0,
    }


def select_corpus_candidates(passages, clusters, total_documents,
                             min_passages=DEFAULT_MIN_PASSAGES,
                             min_documents=DEFAULT_MIN_DOCUMENTS,
                             max_patterns=MAX_PATTERNS_PER_RUN):
    """
    Keep only groups of passages seen in at least `min_documents` DIFFERENT
    documents and made of at least `min_passages` passages (so one long
    document that repeats itself can never create a pattern on its own).

    Returns [{"indices": [...], "counts": summarise_passages(...)}], ordered
    by strength of evidence (more documents, then more passages, then the
    earliest member), capped at `max_patterns`.
    """
    candidates = []
    for indices in clusters:
        members = [passages[i] for i in indices]
        counts = summarise_passages(members, total_documents)
        if counts["passages"] < min_passages or counts["documents"] < min_documents:
            continue
        candidates.append({"indices": list(indices), "counts": counts})
    candidates.sort(key=lambda c: (-c["counts"]["documents"], -c["counts"]["passages"],
                                   c["indices"][0]))
    return candidates[:max_patterns]
