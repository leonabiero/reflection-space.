"""
Highlighted text (November 2026, EDE)
=======================================

Shows the ANONYMISED text with every exact evidence quote highlighted,
one colour per type of evidence (bias, stereotype, prejudice, loaded
label). Used on the results screen (pages/reflection_space.py) and in the
downloadable report (services/reflection_report_html.py).

Rules:
  - Only quotes found exactly in the text are highlighted (same tolerance
    as services/evidence.py: spacing and accent encoding only). Quotes
    without a known type are not coloured.
  - Overlapping quotes: the longer one wins; the other is not drawn
    inside it.
  - Never colour alone: each highlight also shows its type as text (a
    small label after it) and uses a different underline style per type.
  - Colours are semi-transparent, so the text keeps the theme's own text
    colour and stays readable in light and dark mode.
  - Every piece of text is HTML-escaped; nothing else is inserted.

Pure functions (text in, HTML out): no database, no AI, no Streamlit.
"""

from html import escape

from services.evidence import locate_quote, EVIDENCE_TYPES

# Background (semi-transparent) and underline style for each type.
TYPE_STYLES = {
    "bias": ("rgba(230, 159, 0, 0.30)", "solid", "#E69F00"),
    "stereotype": ("rgba(86, 180, 233, 0.30)", "dashed", "#3A9AD9"),
    "prejudice": ("rgba(213, 94, 0, 0.28)", "double", "#D55E00"),
    "loaded_label": ("rgba(204, 121, 167, 0.32)", "dotted", "#CC79A7"),
}


def find_spans(text, quotes):
    """[(start, end, type)] for every quote found exactly in `text`,
    without overlaps (longer quotes first), in text order."""
    candidates = []
    for q in quotes or []:
        if not isinstance(q, dict) or q.get("type") not in EVIDENCE_TYPES:
            continue
        found = locate_quote(q.get("quote"), text or "")
        if found:
            candidates.append((found[0], found[1], q["type"]))
    candidates.sort(key=lambda s: (-(s[1] - s[0]), s[0]))
    chosen = []
    for start, end, kind in candidates:
        if all(end <= s or start >= e for s, e, _ in chosen):
            chosen.append((start, end, kind))
    return sorted(chosen)


def _mark(fragment, kind, label):
    background, underline, colour = TYPE_STYLES[kind]
    return (
        f'<mark style="background:{background};color:inherit;padding:0 2px;'
        f'border-bottom:3px {underline} {colour};border-radius:2px;">'
        f'{escape(fragment)}</mark>'
        f'<span style="font-size:0.72em;font-weight:600;border:1px solid {colour};'
        f'border-radius:3px;padding:0 3px;margin-left:2px;white-space:nowrap;">'
        f'{escape(label)}</span>'
    )


def highlight_html(text, quotes, type_labels):
    """The text as HTML with the quotes highlighted. `type_labels`:
    {type: word shown to people} from the translation files. Line breaks
    are kept."""
    text = text or ""
    pieces = []
    last = 0
    for start, end, kind in find_spans(text, quotes):
        pieces.append(escape(text[last:start]))
        pieces.append(_mark(text[start:end], kind, f"[{type_labels.get(kind, kind)}]"))
        last = end
    pieces.append(escape(text[last:]))
    body = "".join(pieces).replace("\n", "<br>")
    return f'<div style="line-height:1.9;white-space:normal;">{body}</div>'


def legend_html(type_labels, title):
    """The legend: one sample per type, with its name in words."""
    items = []
    for kind in EVIDENCE_TYPES:
        label = type_labels.get(kind, kind)
        items.append(_mark(label, kind, f"[{label}]"))
    return (f'<div style="margin:0.4rem 0 0.8rem;"><strong>{escape(title)}</strong> '
            + " &nbsp; ".join(items) + "</div>")
