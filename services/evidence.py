"""
Evidence Verification
=======================

Stage 1 of the "saved findings" feature (see FINDINGS_STORAGE.md).

When a reflection companion points at a passage in the documentation,
the app must never show that passage as a quotation unless it really is
an exact excerpt of the text the AI was given. This module is the single
place that decides that. It is pure Python (no database, no Streamlit,
no network), so it is cheap to test and safe to call from anywhere.

What counts as "verified"
--------------------------
A proposed quote is verified only if it appears, character for
character, inside the source text. Two harmless differences are
tolerated, because models (and Word/PDF copy-paste) often introduce
them and neither changes the wording:

  1. Line breaks and runs of spaces: "She said\\n  no" matches
     "She said no".
  2. Unicode accent encoding: Spanish and Basque letters such as
     "n~" or "a'" can be stored either as one character or as a letter
     plus a combining mark. Both spellings look identical on screen.

In both cases what gets returned is the text copied FROM THE SOURCE,
never the model's version of it, so what is saved and shown is always
the real wording.

What is never accepted
------------------------
- Paraphrases, translations, or quotes with words changed.
- Quotes stitched together with "..." (each excerpt must be one
  continuous passage).
- Very short fragments (see MIN_QUOTE_CHARS) that would match almost
  any document and therefore prove nothing.

A quote that cannot be verified is DROPPED, counted, and reported back
as `unverified_count` so the interface can say honestly that some
proposed passages were not shown. It is never presented as a quotation.

The source text handed in here is the ANONYMIZED text the model saw (see
services/anonymizer.py), so stored quotes contain placeholders rather
than real names -- the raw document is never used for evidence.
"""

import re
import unicodedata

# Shorter than this and a "quote" would match almost anything, so it is
# not meaningful evidence.
MIN_QUOTE_CHARS = 10

# A single piece of evidence should be a short excerpt, not a whole
# paragraph. Longer proposals are treated as unverifiable.
MAX_QUOTE_CHARS = 400

# At most this many excerpts are kept per observation.
MAX_QUOTES_PER_FINDING = 3

_OUTER_QUOTE_PAIRS = [
    ('"', '"'),
    ("'", "'"),
    ("\u201c", "\u201d"),   # curly double quotes
    ("\u2018", "\u2019"),   # curly single quotes
    ("\u00ab", "\u00bb"),   # guillemets, common in Spanish typing
]

_WHITESPACE_RUN = re.compile(r"\s+")


def _strip_outer_quote_marks(text):
    """Models often wrap an excerpt in quotation marks. Those marks
    belong to the model's formatting, not to the source, so remove one
    matching outer pair before searching."""
    text = text.strip()
    for opening, closing in _OUTER_QUOTE_PAIRS:
        if len(text) >= 2 and text.startswith(opening) and text.endswith(closing):
            return text[1:-1].strip()
    return text


def _normalize_whitespace_with_map(source):
    """Collapse every run of whitespace in `source` to one space.

    Returns (normalized_text, index_map) where index_map[i] is the
    position in the ORIGINAL source of normalized character i, so a
    match found in the normalized text can be translated back into the
    exact original slice.
    """
    normalized_chars = []
    index_map = []
    in_whitespace = False
    for position, char in enumerate(source):
        if char.isspace():
            if not in_whitespace:
                normalized_chars.append(" ")
                index_map.append(position)
                in_whitespace = True
        else:
            normalized_chars.append(char)
            index_map.append(position)
            in_whitespace = False
    return "".join(normalized_chars), index_map


def _find_in_source(quote, source):
    """Return the exact slice of `source` that matches `quote`, or None."""
    # 1. Character-for-character.
    if quote in source:
        return quote

    # 2. Same words, different line breaks / spacing.
    normalized_source, index_map = _normalize_whitespace_with_map(source)
    normalized_quote = _WHITESPACE_RUN.sub(" ", quote).strip()
    if not normalized_quote:
        return None
    start = normalized_source.find(normalized_quote)
    if start == -1:
        return None
    end = start + len(normalized_quote) - 1
    original_start = index_map[start]
    original_end = index_map[end] + 1
    return source[original_start:original_end]


# (November 2026, EDE) Each quote can carry the kind of evidence it is.
# Kept in step with rdi/companions/prompt_builder.py:EVIDENCE_TYPES (not
# imported, so this module stays free of other app code).
EVIDENCE_TYPES = ("bias", "stereotype", "prejudice", "loaded_label")

# A loaded label is often a single short word ("dócil", "pobres",
# "víctima"). Such a quote is accepted from this length, but only when it
# is a whole word (or words) in the text -- never part of a longer word.
MIN_LABEL_QUOTE_CHARS = 3


def clean_type(value):
    """The evidence type if it is one of the four known ones, else None."""
    if isinstance(value, str):
        value = value.strip().lower().replace(" ", "_").replace("-", "_")
        if value == "loaded_labels":
            value = "loaded_label"
        if value in EVIDENCE_TYPES:
            return value
    return None


def _clean_candidate(raw):
    """Accept either a plain string or {"quote": "...", "type": "..."} from
    the model. Returns (text, type) or (None, None)."""
    kind = None
    if isinstance(raw, dict):
        kind = clean_type(raw.get("type"))
        raw = raw.get("quote")
    if not isinstance(raw, str):
        return None, None
    text = _strip_outer_quote_marks(raw)
    minimum = MIN_LABEL_QUOTE_CHARS if kind == "loaded_label" else MIN_QUOTE_CHARS
    if len(text) < minimum or len(text) > MAX_QUOTE_CHARS:
        return None, None
    return text, kind


def _is_whole_words(match, source):
    """True if the matched slice does not start or end inside a word."""
    start = source.find(match)
    while start != -1:
        end = start + len(match)
        before_ok = start == 0 or not source[start - 1].isalnum()
        after_ok = end >= len(source) or not source[end].isalnum()
        if before_ok and after_ok:
            return True
        start = source.find(match, start + 1)
    return False


def locate_quote(quote, source):
    """(start, end) of `quote` in `source` with the same tolerance as
    verify_quotes (spacing, accent encoding), or None. Used to highlight
    quotes in the text (services/highlight.py)."""
    if not isinstance(quote, str) or not isinstance(source, str) or not quote.strip():
        return None
    for form in dict.fromkeys([quote, unicodedata.normalize("NFC", quote)]):
        match = _find_in_source(form, source)
        if match is not None:
            start = source.find(match)
            if start != -1:
                return start, start + len(match)
    return None


def verify_quotes(candidates, source_text):
    """
    Check the model's proposed excerpts against the source text.

    Parameters
    ----------
    candidates : list (or anything else -- anything that is not a list
        is treated as "no evidence offered") of strings or
        {"quote": str} dicts, as returned by a reflection companion.
    source_text : the exact text the model was given.

    Returns
    -------
    (verified, unverified_count)
      verified: list of {"quote": <exact excerpt copied from the source>}
        with duplicates removed, at most MAX_QUOTES_PER_FINDING long.
      unverified_count: how many offered excerpts could not be matched
        to the source and were therefore dropped.
    """
    if not isinstance(candidates, list) or not isinstance(source_text, str):
        return [], 0

    # Two spellings of the same accented text are the same text -- try
    # the source as given first, then its canonical (NFC) form.
    sources_to_try = [source_text]
    nfc_source = unicodedata.normalize("NFC", source_text)
    if nfc_source != source_text:
        sources_to_try.append(nfc_source)

    verified = []
    seen = set()
    unverified_count = 0

    for raw in candidates:
        cleaned, kind = _clean_candidate(raw)
        if cleaned is None:
            unverified_count += 1
            continue

        match = None
        for source in sources_to_try:
            candidate_forms = [cleaned]
            nfc_candidate = unicodedata.normalize("NFC", cleaned)
            if nfc_candidate != cleaned:
                candidate_forms.append(nfc_candidate)
            for form in candidate_forms:
                match = _find_in_source(form, source)
                if match is not None:
                    break
            if match is not None:
                break

        # A short label quote must be a whole word in the text ("dócil",
        # never the "ocil" of "dócil").
        if match is not None and len(cleaned) < MIN_QUOTE_CHARS and not any(
                _is_whole_words(match, s) for s in sources_to_try):
            match = None

        if match is None:
            unverified_count += 1
            continue

        if match in seen:
            continue
        seen.add(match)
        if len(verified) < MAX_QUOTES_PER_FINDING:
            item = {"quote": match}
            if kind:
                item["type"] = kind
            verified.append(item)

    return verified, unverified_count
