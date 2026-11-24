"""
Reading the AI's texts safely (November 2026)
==============================================

The AI is asked for plain sentences (an analysis, 1 or 2 questions...),
but it sometimes sends a small "object" instead -- for example a question
together with the kind of bias it is about:

    "questions": [{"question": "¿...?", "type": "bias"}]

instead of

    "questions": ["¿...?"]

On 24 November 2026 one such object crashed the analysis report page.
These helpers turn whatever arrives (plain text, an object, a number,
nothing) into clean text, so every screen and the downloadable report
work with both shapes and never crash on one unexpected item.

  - as_text(value): one clean piece of text ("" if nothing readable).
  - as_text_list(values): a list of clean, non-empty texts.
  - as_text_items(values): the same, as [{"text", "type"}], keeping the
    type only when it is one of the four known evidence types (so it can
    be shown with the app's own colour). Colours suggested by the AI are
    ignored on purpose: colours only ever come from services/highlight.py.

Pure functions: no database, no AI, no Streamlit.
"""

from services.evidence import clean_type

# Where the actual sentence is usually found inside an object, in order.
_TEXT_KEYS = (
    "text", "question", "pregunta", "galdera", "observation", "analysis",
    "content", "quote", "why", "summary", "description", "value", "message",
)
# Where the kind of bias/stereotype/... is usually found inside an object.
_TYPE_KEYS = ("type", "bias_type", "category", "kind", "bias", "evidence_type")

_MAX_DEPTH = 4


def as_text(value, _depth=0):
    """Clean text from a string, an object, a list, a number or nothing.
    Spacing is tidied; anything unreadable gives ""."""
    if _depth > _MAX_DEPTH or value is None or isinstance(value, bool):
        return ""
    if isinstance(value, str):
        return " ".join(value.split())
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, dict):
        for key in _TEXT_KEYS:
            if key in value:
                text = as_text(value[key], _depth + 1)
                if text:
                    return text
        # No known key: use the longest piece of text inside it (never
        # the raw "{...}" dump, and never a short tag such as "bias").
        texts = [as_text(v, _depth + 1) for v in value.values()]
        texts = [t for t in texts if t and clean_type(t) is None]
        return max(texts, key=len) if texts else ""
    if isinstance(value, (list, tuple)):
        return " ".join(t for t in (as_text(v, _depth + 1) for v in value) if t)
    return ""


def _as_type(value):
    if not isinstance(value, dict):
        return None
    for key in _TYPE_KEYS:
        kind = clean_type(value.get(key))
        if kind:
            return kind
    return None


def _as_items(values):
    if values is None:
        return []
    if isinstance(values, (str, dict)):
        return [values]          # a single item sent on its own
    if isinstance(values, (list, tuple)):
        return list(values)
    return []                    # e.g. the Retry button object -- not a list


def as_text_items(values):
    """[{"text": str, "type": str|None}] for every readable item."""
    items = []
    for value in _as_items(values):
        text = as_text(value)
        if text:
            items.append({"text": text, "type": _as_type(value)})
    return items


def as_text_list(values):
    """A list of clean, non-empty texts (for questions and similar)."""
    return [item["text"] for item in as_text_items(values)]
