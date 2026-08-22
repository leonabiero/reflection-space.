"""Privacy boundary for text that may leave Reflection Space.

This module intentionally uses a layered, deterministic approach rather than
claiming that a handful of regular expressions can make arbitrary social-work
narratives anonymous. It removes common direct identifiers, contextual
identifiers, and conservative proper-name phrases before text reaches Claude,
Gemini embeddings, or Qdrant.

The final layer is deliberately conservative in the privacy direction: a
proper-looking multi-token name may be redacted even when it turns out to be a
place or organisation. That is preferable to preserving a likely client's
name. Indirect identification (for example, a unique combination of age,
location, school and rare event) cannot be reliably solved with pattern
matching; callers must therefore treat anonymization as risk reduction, not a
formal guarantee of anonymity.
"""

import re


# Unicode-aware-ish name token: initial capital followed by letters and optional
# apostrophe/hyphen segments. This covers common African, Spanish and Basque
# forms such as "Amina Wanjiku", "María José García", "Jean-Luc Martin",
# "O'Connor" and "N'Guessan" without requiring an external NER model.
_NAME_TOKEN = r"[A-ZÀ-ÖØ-Þ][A-Za-zÀ-ÖØ-öø-ÿ]*(?:['’\-][A-ZÀ-ÖØ-Þ][A-Za-zÀ-ÖØ-öø-ÿ]*)*"
_NAME_SEQUENCE_RE = re.compile(
    rf"\b{_NAME_TOKEN}(?:\s+{_NAME_TOKEN}){{1,3}}\b"
)

# Common capitalized phrases in professional documentation that are not
# normally client names. Keeping these intact reduces needless degradation of
# the clinical/social-work vocabulary while the name rule remains conservative.
_PROTECTED_PROPER_PHRASES = {
    "Social Worker",
    "Programme Manager",
    "System Administrator",
    "System Administration",
    "Social Work Report",
    "Intervention Plan",
    "Reflection Space",
    "Knowledge Assistant",
}

# Context words which make a following proper phrase much more likely to be a
# person/place/organisation identifier. These patterns are intentionally
# label/context driven; they are not an attempt to maintain a world-wide list
# of schools, hospitals, villages or organisations.
_CONTEXTUAL_IDENTIFIER_PATTERNS = [
    # Person labels / introductions.
    (re.compile(r"\b(?:client|patient|child|mother|father|guardian|caregiver|named|name(?:d)?\s+as)\s*[:\-]?\s+(%s(?:\s+%s){0,3})\b" % (_NAME_TOKEN, _NAME_TOKEN)), "[PERSON]"),
    # School / hospital / clinic / organisation names.
    (re.compile(r"\b(?:school|hospital|clinic|organisation|organization|company|employer|university)\s*[:\-]?\s+(%s(?:\s+%s){0,4})\b" % (_NAME_TOKEN, _NAME_TOKEN)), "[ORGANISATION]"),
    # Places after common location cues. The phrase is bounded by punctuation
    # so an entire sentence is never swallowed.
    (re.compile(r"\b(?:from|near|in|at|lives?\s+in|resides?\s+in|based\s+in)\s+(%s(?:\s+%s){0,3})(?=\s*[,.;:!?)]|\s+(?:and|but|who|where|which|was|is|has|had)\b|$)" % (_NAME_TOKEN, _NAME_TOKEN)), "[LOCATION]"),
    # Explicit address labels and natural-language residence/address phrases.
    (re.compile(r"\b(?:home\s+address|postal\s+address|physical\s+address|address)\s*[:\-]?\s+[^\n,.;!?]+"), "[ADDRESS]"),
    (re.compile(r"\b(?:lives?|resides?)\s+at\s+[^\n,.;!?]+"), "[ADDRESS]"),
]

# Explicit identifier labels catch both numeric and alphanumeric case refs.
_IDENTIFIER_RE = re.compile(
    r"\b(?:case\s*(?:reference|ref|number|no|id)|client\s*(?:id|number|no)|national\s*(?:id|number|no)|identifier|reference|ref)\s*[:#\-]?\s*[A-Za-z0-9][A-Za-z0-9/_\-.]{2,}\b",
    re.IGNORECASE,
)

_EMAIL_RE = re.compile(r"\b[\w.+-]+@[\w-]+(?:\.[\w-]+)+\b", re.UNICODE)

# Dates: numeric forms plus common English/Spanish month names. The latter is
# important because social-work narratives frequently spell dates out.
_DATE_RE = re.compile(
    r"\b(?:\d{1,2}[/.-]\d{1,2}[/.-]\d{2,4}|\d{1,2}\s+(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:t(?:ember)?)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+\d{2,4}|\d{1,2}\s+de\s+(?:enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre)\s+de\s+\d{2,4})\b",
    re.IGNORECASE,
)

# Phone formats common in Kenya/Spain/international text. Require enough
# digits and allow spaces, parentheses, hyphens and an optional country code.
_PHONE_RE = re.compile(
    r"(?<!\w)(?:\+\d{1,3}[\s.-]?)?(?:\(?\d{2,4}\)?[\s.-])?\d{3,4}[\s.-]\d{3,4}(?:[\s.-]\d{2,4})?(?!\w)"
)

_LONG_NUMERIC_ID_RE = re.compile(r"(?<!\w)\d{5,}(?!\w)")


def _replace_proper_names(text: str) -> str:
    """Redact conservative 2-4 token proper-name sequences.

    The rule is intentionally applied after contextual identifiers and explicit
    IDs, so a person name embedded in a labelled field is not fragmented by a
    later rule. Protected phrases prevent common professional vocabulary from
    being turned into [PERSON].
    """
    def repl(match):
        phrase = match.group(0)
        if phrase in _PROTECTED_PROPER_PHRASES:
            return phrase
        # Avoid treating a title followed by a name as a second independent
        # replacement; title handling below is more explicit.
        if phrase.split()[0].lower().rstrip(".") in {"mr", "mrs", "ms", "miss", "dr", "sr", "sra", "srta"}:
            return phrase
        return "[PERSON]"

    return _NAME_SEQUENCE_RE.sub(repl, text)


def anonymize(text: str) -> str:
    """Return a privacy-hardened representation suitable for external AI.

    Ordering matters: high-confidence identifiers are removed first; explicit
    identifier labels are removed before generic capitalized-name matching;
    the final proper-name pass catches multi-part names, including hyphenated
    and apostrophe names. The function never raises and preserves empty input.
    """
    if not text:
        return text

    safe = str(text)

    # 1. Highest-confidence direct identifiers.
    safe = _EMAIL_RE.sub("[EMAIL]", safe)
    safe = _DATE_RE.sub("[DATE]", safe)
    safe = _PHONE_RE.sub("[PHONE]", safe)
    safe = _IDENTIFIER_RE.sub("[ID]", safe)
    safe = _LONG_NUMERIC_ID_RE.sub("[ID]", safe)

    # 2. Contextual identifiers: people, institutions, places and addresses.
    for pattern, replacement in _CONTEXTUAL_IDENTIFIER_PATTERNS:
        safe = pattern.sub(lambda m, r=replacement: r, safe)

    # 3. Explicit titles + names. Supports accented, hyphenated and
    # apostrophe-containing names.
    safe = re.sub(
        rf"\b(?:Mr|Mrs|Ms|Miss|Dr|Sr|Sra|Srta)\.?\s+{_NAME_TOKEN}(?:\s+{_NAME_TOKEN}){{0,3}}\b",
        "[PERSON]",
        safe,
    )

    # 4. Conservative catch-all for natural sentences containing a likely
    # multi-token proper name. This is the privacy-first layer for names that
    # are not introduced by "client:" / "mother:" etc.
    safe = _replace_proper_names(safe)

    return safe
