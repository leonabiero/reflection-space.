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
location, school and rare event) cannot be reliably solved by pattern matching;
callers must therefore treat anonymization as risk reduction, not a formal
guarantee of anonymity.
"""

import re

_NAME_TOKEN = r"[A-ZÀ-ÖØ-Þ][A-Za-zÀ-ÖØ-öø-ÿ]*(?:['’\-][A-ZÀ-ÖØ-Þ][A-Za-zÀ-ÖØ-öø-ÿ]*)*"
_NAME_SEQUENCE_RE = re.compile(rf"\b{_NAME_TOKEN}(?:\s+{_NAME_TOKEN}){{1,3}}\b")
_SINGLE_COMPLEX_NAME_RE = re.compile(rf"\b{_NAME_TOKEN}\b")

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

_CONTEXTUAL_IDENTIFIER_PATTERNS = [
    # Person labels / introductions.
    (re.compile(r"\b(?:client|patient|child|mother|father|guardian|caregiver|named|name(?:d)?\s+as)\s*[:\-]?\s+(%s(?:\s+%s){0,3})\b" % (_NAME_TOKEN, _NAME_TOKEN)), "[PERSON]"),
    # Institution names where the type comes first ("Hospital City Eye").
    (re.compile(r"\b(?:school|hospital|clinic|organisation|organization|company|employer|university)\s*[:\-]?\s+(%s(?:\s+%s){0,4})\b" % (_NAME_TOKEN, _NAME_TOKEN)), "[ORGANISATION]"),
    # Institution names where the type is a suffix ("City Eye Hospital").
    (re.compile(r"\b(%s(?:\s+%s){0,4})\s+(?:school|hospital|clinic|organisation|organization|company|university|foundation)\b" % (_NAME_TOKEN, _NAME_TOKEN), re.IGNORECASE), "[ORGANISATION]"),
    # Places after common location cues.
    (re.compile(r"\b(?:from|near|in|at|lives?\s+in|resides?\s+in|based\s+in)\s+(%s(?:\s+%s){0,3})(?=\s*[,.;:!?)]|\s+(?:and|but|who|where|which|was|is|has|had)\b|$)" % (_NAME_TOKEN, _NAME_TOKEN)), "[LOCATION]"),
    # Explicit address labels and natural-language residence/address phrases.
    (re.compile(r"\b(?:home\s+address|postal\s+address|physical\s+address|address)\s*[:\-]?\s+[^\n,.;!?]+", re.IGNORECASE), "[ADDRESS]"),
    (re.compile(r"\b(?:lives?|resides?)\s+at\s+[^\n,.;!?]+", re.IGNORECASE), "[ADDRESS]"),
]

# The complete identifier label must end at a word boundary. In particular,
# plain `ref` must NOT match the beginning of words such as "referral".
_IDENTIFIER_RE = re.compile(
    r"\b(?:case\s*(?:reference|ref|number|no|id)|client\s*(?:id|number|no)|national\s*(?:id|number|no)|identifier|reference|ref)\b\s*[:#\-]?\s*[A-Za-z0-9][A-Za-z0-9/_\-.]{2,}\b",
    re.IGNORECASE,
)
_EMAIL_RE = re.compile(r"\b[\w.+-]+@[\w-]+(?:\.[\w-]+)+\b", re.UNICODE)
_DATE_RE = re.compile(
    r"\b(?:\d{1,2}[/.-]\d{1,2}[/.-]\d{2,4}|\d{1,2}\s+(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:t(?:ember)?)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+\d{2,4}|\d{1,2}\s+de\s+(?:enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre)\s+de\s+\d{2,4})\b",
    re.IGNORECASE,
)
_PHONE_RE = re.compile(
    r"(?<!\w)(?:\+\d{1,3}[\s.-]?)?(?:\(?\d{2,4}\)?[\s.-])?\d{3,4}[\s.-]\d{3,4}(?:[\s.-]\d{2,4})?(?!\w)"
)
_LONG_NUMERIC_ID_RE = re.compile(r"(?<!\w)\d{5,}(?!\w)")


def _replace_proper_names(text: str) -> str:
    """Redact conservative multi-token names plus complex single names."""
    def repl(match):
        phrase = match.group(0)
        if phrase in _PROTECTED_PROPER_PHRASES:
            return phrase
        if phrase.split()[0].lower().rstrip(".") in {"mr", "mrs", "ms", "miss", "dr", "sr", "sra", "srta"}:
            return phrase
        return "[PERSON]"

    text = _NAME_SEQUENCE_RE.sub(repl, text)

    def complex_repl(match):
        token = match.group(0)
        if "-" in token or "'" in token or "’" in token:
            return "[PERSON]"
        return token

    return _SINGLE_COMPLEX_NAME_RE.sub(complex_repl, text)


def anonymize(text: str) -> str:
    """Return a privacy-hardened representation suitable for external AI."""
    if not text:
        return text

    safe = str(text)
    safe = _EMAIL_RE.sub("[EMAIL]", safe)
    safe = _DATE_RE.sub("[DATE]", safe)
    safe = _PHONE_RE.sub("[PHONE]", safe)
    safe = _IDENTIFIER_RE.sub("[ID]", safe)
    safe = _LONG_NUMERIC_ID_RE.sub("[ID]", safe)

    for pattern, replacement in _CONTEXTUAL_IDENTIFIER_PATTERNS:
        safe = pattern.sub(lambda m, r=replacement: r, safe)

    safe = re.sub(
        rf"\b(?:Mr|Mrs|Ms|Miss|Dr|Sr|Sra|Srta)\.?\s+{_NAME_TOKEN}(?:\s+{_NAME_TOKEN}){{0,3}}\b",
        "[PERSON]",
        safe,
    )

    return _replace_proper_names(safe)
