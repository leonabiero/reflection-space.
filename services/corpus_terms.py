"""
Corpus word and phrase list (pure logic)
==========================================

For "Corpus analysis" Step 3 (see CORPUS.md). A manager keeps a list of
words and short phrases; for each one the app counts in how many of the
collection's texts it appears and how many times.

This is plain counting of written words. It has no database and no AI. It
does not understand meaning: a word can be used to deny something ("no es
agresivo"), and an idea can be present without any listed word. The page
and the report say so.

HOW A TERM IS MATCHED
  - Capitals and accents are ignored (atención = ATENCION), except the
    letter ñ, which is kept apart from n (año is not ano).
  - Whole words only: "mal" does not match "normal".
  - A phrase matches its words in order, separated by spaces or line
    breaks ("no quiere" matches "No   quiere").
  - A star at the end of a word stands for any ending: "agresiv*" matches
    agresivo, agresiva, agresivos... This matters for Basque, where words
    change at the end ("etxe*" finds etxea, etxeak, etxean...).

Everything a manager types is turned into a pattern that is built only from
escaped letters, spaces and one fixed "any ending" piece, so a typed term
can never be used as a regular expression of its own.
"""

import csv
import io
import re
import unicodedata

MAX_TERM_CHARS = 60
MAX_TERM_WORDS = 6
MIN_WORD_CHARS = 2
MIN_STAR_STEM_CHARS = 3
MAX_TERMS_PER_CORPUS = 200

_WORD_OK = re.compile(r"^\w+\*?$")
_EDGE_PUNCTUATION = " \t\"'“”‘’«»(),.;:!?¿¡"


def _fold_char(ch):
    """One character -> one character: lower case, accents removed, ñ kept."""
    if ch in "ñÑ":
        return "ñ"
    base = unicodedata.normalize("NFD", ch)[:1] or ch
    low = base.lower()
    return low if len(low) == 1 else base


def prepare_text(text):
    """The text in a standard form (so accents are single characters) and the
    folded copy used for matching. Both have the SAME length, so a match in
    the folded copy points at the same place in the standard text."""
    standard = unicodedata.normalize("NFC", text or "")
    return standard, "".join(_fold_char(c) for c in standard)


def parse_term(raw):
    """
    Check and tidy one typed term.

    Returns {"term": what to show, "norm": the matching form} or None if the
    term cannot be used (empty, too long, too many words, strange
    characters, a star in the middle of a word, a star with too few
    letters before it, or only one letter).
    """
    cleaned = re.sub(r"\s+", " ", (raw or "").strip()).strip(_EDGE_PUNCTUATION)
    if not cleaned or len(cleaned) > MAX_TERM_CHARS:
        return None
    words = cleaned.split(" ")
    if len(words) > MAX_TERM_WORDS:
        return None
    folded_words = []
    for word in words:
        if not _WORD_OK.match(word):
            return None
        stem = word.rstrip("*")
        if word.endswith("*") and len(stem) < MIN_STAR_STEM_CHARS:
            return None
        folded_words.append("".join(_fold_char(c) for c in word))
    if sum(len(w.rstrip("*")) for w in folded_words) < MIN_WORD_CHARS:
        return None
    return {"term": cleaned, "norm": " ".join(folded_words)}


def compile_term(norm):
    """The matcher for a tidied term (see parse_term). Built from escaped
    pieces only."""
    pieces = []
    for word in norm.split(" "):
        if word.endswith("*"):
            pieces.append(re.escape(word[:-1]) + r"\w*")
        else:
            pieces.append(re.escape(word))
    return re.compile(r"(?<!\w)" + r"\s+".join(pieces) + r"(?!\w)")


def count_terms(terms, documents):
    """
    Count every term in every text.

    terms       [{"id", "term", "norm"}]
    documents   [{"doc_no", "content"}]

    Returns {"total_documents": N, "doc_numbers": [...], "terms": [...]}
    where each term entry has: id, term, documents (in how many DIFFERENT
    texts it appears), occurrences (all appearances), per_doc
    ({doc_no: times}, only texts where it appears), doc_numbers (sorted).
    """
    prepared = [(d["doc_no"],) + prepare_text(d["content"])[1:] for d in documents]
    results = []
    for term in terms:
        matcher = compile_term(term["norm"])
        per_doc = {}
        for doc_no, folded in prepared:
            hits = sum(1 for _ in matcher.finditer(folded))
            if hits:
                per_doc[doc_no] = hits
        results.append({
            "id": term.get("id"), "term": term["term"],
            "documents": len(per_doc), "occurrences": sum(per_doc.values()),
            "per_doc": per_doc, "doc_numbers": sorted(per_doc),
        })
    return {
        "total_documents": len(documents),
        "doc_numbers": sorted(d["doc_no"] for d in documents),
        "terms": results,
    }


def term_snippets(norm, content, limit=2, width=80):
    """Short exact excerpts of `content` around the first `limit` appearances
    of a term (so a reader sees the word in its sentence). Excerpts are
    pieces of the text itself, with "…" where it was cut."""
    standard, folded = prepare_text(content)
    snippets = []
    for match in compile_term(norm).finditer(folded):
        start = max(0, match.start() - width)
        end = min(len(standard), match.end() + width)
        if start > 0:
            cut = standard.find(" ", start, match.start())
            start = cut + 1 if cut != -1 else start
        if end < len(standard):
            cut = standard.rfind(" ", match.end(), end)
            end = cut if cut != -1 else end
        piece = " ".join(standard[start:end].split())
        snippets.append(("…" if start > 0 else "") + piece + ("…" if end < len(standard) else ""))
        if len(snippets) >= limit:
            break
    return snippets


def counts_for_text(result, doc_no):
    """For one text: [(term, times)] for every listed term that appears in it,
    most frequent first."""
    rows = [(t["term"], t["per_doc"][doc_no]) for t in result["terms"] if doc_no in t["per_doc"]]
    return sorted(rows, key=lambda r: (-r[1], r[0].casefold()))


def _safe_cell(value):
    """Stop a spreadsheet from running a typed cell as a formula."""
    text = str(value)
    return "'" + text if text[:1] in ("=", "+", "-", "@", "\t", "\r") else text


def matrix_csv(result, label_for, headers):
    """
    A table (as text for a .csv file) with one row per term and one column
    per text. `headers` = (term column title, texts column title, times
    column title); `label_for` turns a text number into its label (T-001).
    Semicolon-separated, because Spanish spreadsheets expect it. Contains
    only the typed terms and counts, never any text from the documents.
    """
    out = io.StringIO()
    writer = csv.writer(out, delimiter=";", lineterminator="\r\n")
    writer.writerow([headers[0], headers[1], headers[2]]
                    + [label_for(n) for n in result["doc_numbers"]])
    for t in result["terms"]:
        writer.writerow([_safe_cell(t["term"]), t["documents"], t["occurrences"]]
                        + [t["per_doc"].get(n, 0) for n in result["doc_numbers"]])
    return out.getvalue()


# ---------------------------------------------------------------------
# Starter list
# ---------------------------------------------------------------------
# A first list of words and phrases that, in case notes, sometimes describe a
# person in a closed or negative way ("is manipulative", "refuses", "does not
# want"). It is a starting point to be edited, NOT a verdict on any word:
# whether a use is a problem depends on the sentence. The Spanish part is
# written to be sensible; the Basque part MUST be read by a native Basque
# speaker before it is relied on (the page says so).

STARTER_TERMS_ES = [
    "problemátic*", "conflictiv*", "agresiv*", "manipul*", "mentiros*", "miente*",
    "vago", "vaga", "desmotivad*", "falta de motivación", "falta de interés",
    "sin interés", "no quiere", "se niega", "no colabora", "poco colaborador*",
    "no cumple", "irresponsable*", "caso difícil", "no tiene conciencia",
    "no es de fiar", "no se implica", "pasivo", "pasiva",
]

STARTER_TERMS_EU = [
    "arazotsu*", "gatazkatsu*", "oldarkor*", "manipulatzaile*", "gezurti*",
    "alfer*", "motibaziorik ez", "interesik ez", "ez du nahi", "uko egiten",
    "ez du lankidetzan", "lankidetzarik ez", "erantzukizunik gabe",
    "ez da inplikatzen", "kasu zaila",
]

STARTER_TERMS = ([("starter_es", t) for t in STARTER_TERMS_ES]
                 + [("starter_eu", t) for t in STARTER_TERMS_EU])
