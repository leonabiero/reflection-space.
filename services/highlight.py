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
  - Colours are solid, with dark text on them, so they look the same and
    stay readable in light mode, dark mode and on paper.
  - Every piece of text is HTML-escaped; nothing else is inserted.

Pure functions (text in, HTML out): no database, no AI, no Streamlit.
"""

from html import escape

from services.evidence import locate_quote, EVIDENCE_TYPES

# THE ONE PLACE where the colours of the four kinds of evidence are
# defined. Everything that shows a type in colour -- the highlighted text
# and its legend, the type badges on the cards, the on-screen analysis
# report and the downloadable report -- takes them from here.
#
# For each type: (semi-transparent background, underline style, solid
# colour for the underline and the badge border).
#
# 24 November 2026 (product owner): "Sesgo" and "Prejuicio" looked too
# alike (orange and dark orange). Now:
#   bias         -> clear yellow
#   prejudice    -> clear red
#   stereotype   -> blue (unchanged)
#   loaded_label -> purple (was pink, which sat too close to the new red)
#
# 24 November 2026 (later, product owner): on the app's dark indigo
# background the see-through yellow mixed into a dull mustard that looked
# orange next to the red. The backgrounds are now SOLID colours with dark
# text (TEXT_ON_COLOUR), so every type looks exactly the same on the dark
# screen, a light screen and paper. Contrast between the dark text and
# each background is at least 4.5:1 (checked in tests/test_highlight.py).
TEXT_ON_COLOUR = "#111111"
TYPE_STYLES = {
    "bias": ("#FFD60A", "solid", "#C9A200"),
    "stereotype": ("#7CC4F2", "dashed", "#1D72B8"),
    "prejudice": ("#EF4444", "double", "#B91C1C"),
    "loaded_label": ("#B794F6", "dotted", "#6D28D9"),
}

# Asks the browser to print the colours exactly as shown (browsers leave
# background colours out of printouts unless told otherwise). Used in the
# style of every downloadable printable page.
PRINT_EXACT_COLOURS_CSS = (
    "* { -webkit-print-color-adjust: exact; print-color-adjust: exact; }"
)


def type_badge_html(kind, label):
    """The type of a quote in words, as a small badge in the type's colour
    (used on the cards and in the reports). Unknown or missing type: the
    word only, with no colour. Escaped."""
    if kind not in TYPE_STYLES:
        return f"[{escape(label or '')}]" if label else ""
    background, _underline, colour = TYPE_STYLES[kind]
    return (
        f'<span style="background:{background};color:{TEXT_ON_COLOUR};border:1px solid {colour};'
        f'border-radius:3px;padding:0 4px;font-size:0.85em;font-weight:600;white-space:nowrap;">'
        f'{escape(label or kind)}</span>'
    )


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
        f'<mark style="background:{background};color:{TEXT_ON_COLOUR};padding:0 2px;'
        f'border-bottom:3px {underline} {colour};border-radius:2px;">'
        f'{escape(fragment)}</mark>'
        f'<span style="font-size:0.72em;font-weight:600;background:{background};'
        f'color:{TEXT_ON_COLOUR};border:1px solid {colour};'
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


def plain_text_html(text):
    """The text as HTML exactly as written: escaped (so symbols such as
    #, * or | in a document are never read as formatting), line breaks
    and accents kept. Used for the first "view anonymised text" preview,
    so it shows paragraphs the same way as the highlighted text."""
    body = escape(text or "").replace("\n", "<br>")
    return f'<div style="line-height:1.7;white-space:normal;">{body}</div>'


def legend_html(type_labels, title):
    """The legend: one sample per type, with its name in words."""
    items = []
    for kind in EVIDENCE_TYPES:
        label = type_labels.get(kind, kind)
        items.append(_mark(label, kind, f"[{label}]"))
    return (f'<div style="margin:0.4rem 0 0.8rem;"><strong>{escape(title)}</strong> '
            + " &nbsp; ".join(items) + "</div>")
