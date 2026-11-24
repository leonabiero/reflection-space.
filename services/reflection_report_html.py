"""
Printable reflection report (November 2026, EDE)
==================================================

ONE self-contained web page for a single reflection, made only when the
professional presses "Download report" under the analysis report. They
open it in a browser and choose Print (or "Save as PDF"). Same method as
the Pattern Review printout (services/pattern_report_html.py): no extra
software and no outside service.

It contains: the analysis report, the eight lens results, and the
ANONYMISED text with the quotes highlighted. Never the original text,
never a name. Nothing is saved by the app.

Everything inserted is HTML-escaped (services/highlight.py escapes the
text it highlights); the page loads nothing from outside and runs no
scripts.

Pure function (text in, text out): no database or AI work.
"""

import logging
from html import escape

from services.ai_text import as_text, as_text_items
from services.evidence import clean_type
from services.highlight import (
    PRINT_EXACT_COLOURS_CSS, highlight_html, legend_html, type_badge_html,
)

logger = logging.getLogger(__name__)

_CSP = "default-src 'none'; style-src 'unsafe-inline'"
HTML_LANG = {"Español": "es", "Euskera": "eu", "English": "en"}

_STYLE = """
@page { size: A4; margin: 18mm 16mm 22mm 16mm; }
* { box-sizing: border-box; }
body { font-family: Georgia, 'Times New Roman', serif; color: #111; background: #fff;
       line-height: 1.45; font-size: 11pt; max-width: 180mm; margin: 0 auto; padding: 12mm 4mm; }
h1 { font-size: 20pt; margin: 0 0 2mm; }
h2 { font-size: 14pt; margin: 8mm 0 2mm; border-bottom: 1px solid #999; padding-bottom: 1mm; }
h3 { font-size: 12pt; margin: 5mm 0 1mm; }
p, li { margin: 0 0 2mm; }
ul { margin: 0 0 2mm 5mm; padding: 0; }
blockquote { margin: 1mm 0 2mm 4mm; padding-left: 3mm; border-left: 3px solid #999; }
.muted { color: #444; font-size: 9.5pt; }
.block { page-break-inside: avoid; border-top: 1px solid #bbb; padding-top: 2mm; margin-top: 4mm; }
.text { border: 1px solid #bbb; padding: 3mm 4mm; }
.footer { display: none; }
@media print {
  body { padding: 0; max-width: none; }
  .footer { display: block; position: fixed; bottom: 0; left: 0; right: 0; text-align: center;
            font-size: 8.5pt; color: #444; }
}
""" + PRINT_EXACT_COLOURS_CSS + "\n"   # keep the type colours when printed


def _p(text, css=""):
    cls = f' class="{css}"' if css else ""
    return f"<p{cls}>{escape(as_text(text))}</p>"


def _ul(items, types=None):
    """A list of plain-text or object-style items (services/ai_text.py).
    An item that carries one of the four known types gets the app's own
    coloured type badge in front of it."""
    items = as_text_items(items)
    if not items:
        return ""
    lis = []
    for item in items:
        label = (types or {}).get(item["type"], "") if item["type"] else ""
        badge = (type_badge_html(item["type"], label) + " ") if label else ""
        lis.append(f"<li>{badge}{escape(item['text'])}</li>")
    return "<ul>" + "".join(lis) + "</ul>"


def _quote(T, item):
    if not isinstance(item, dict):
        item = {"quote": item}
    kind = clean_type(item.get("type"))
    label = T["evidence_type_labels"].get(kind, "") if kind else ""
    # The type in words and in its colour (services/highlight.py).
    prefix = (type_badge_html(kind, label) + " ") if label else ""
    quote = as_text(item.get("quote"))
    if not quote:
        return ""
    return f"<blockquote>{prefix}«{escape(quote)}»</blockquote>"


def _item_block(T, item):
    """One item of the analysis report (type · area, quote, why)."""
    types = T["evidence_type_labels"]
    areas = T["ar_area_names"]
    kind = clean_type(item.get("type"))
    area = as_text(item.get("area"))
    head = []
    if kind:
        head.append(type_badge_html(kind, types.get(kind, kind)))
    if area:
        head.append(escape(areas.get(area, area)))
    out = ['<div class="block">']
    if head:
        out.append(f"<p>{' · '.join(head)}</p>")
    quote = _quote(T, {"quote": item.get("quote")})
    out.append(quote or _p(T["ar_missing_quote"], "muted"))
    out.append(_p(item.get("why")))
    out.append("</div>")
    return "".join(out)


def _lens_block(T, lens):
    """One lens: name, analysis, quotes, questions."""
    out = ['<div class="block">', f"<h3>{escape(as_text(lens.get('label')))}</h3>"]
    if as_text(lens.get("analysis")):
        out.append(_p(lens["analysis"]))
    evidence = lens.get("evidence") or []
    for item in evidence if isinstance(evidence, (list, tuple)) else []:
        out.append(_quote(T, item))
    out.append(_ul(lens.get("questions"), T["evidence_type_labels"]))
    out.append("</div>")
    return "".join(out)


def build_reflection_report_html(T, lang, code, prepared_on, report, lenses, safe_text, quotes,
                                 on_problem=None):
    """
    `report`: the analysis report dict (or None).
    `lenses`: [{"label", "analysis", "evidence": [{"quote", "type"}], "questions"}]
              -- only lenses with something to show.
    `safe_text`: the ANONYMISED text. `quotes`: typed quotes to highlight.
    `on_problem`: optional function called once, with a short description
              (never any case text), if some part could not be shown.
    Returns the page as a string.

    Texts and list items may be plain text or small objects (the AI
    sometimes sends {"question": ..., "type": ...}); both are read
    (services/ai_text.py). Each part of the page is built on its own: a
    part that still cannot be read is left out, a short note says so, and
    the rest of the report is shown -- it never crashes the page.
    """
    types = T["evidence_type_labels"]
    problems = []

    def safe(section, build, *args):
        try:
            return build(*args) or ""
        except Exception as exc:     # never let one part break the page
            problems.append(f"{section}: {type(exc).__name__}")
            return _p(T.get("rr_part_unreadable", ""), "muted")

    parts = [
        "<!DOCTYPE html>",
        f'<html lang="{HTML_LANG.get(lang, "es")}"><head><meta charset="utf-8">',
        f'<meta http-equiv="Content-Security-Policy" content="{_CSP}">',
        f"<title>{escape(T['rr_print_title'])}</title><style>{_STYLE}</style></head><body>",
        f"<h1>{escape(T['rr_print_title'])}</h1>",
        _p(T["rr_print_confidential"], "muted"),
        _p(T["rr_print_meta"].format(code=code, date=prepared_on), "muted"),
        f"<h2>{escape(T['ar_header'])}</h2>",
    ]
    if isinstance(report, dict) and report:
        if as_text(report.get("summary")):
            parts.append(f"<h3>{escape(T['ar_summary_header'])}</h3>")
            parts.append(safe("summary", _p, report.get("summary")))
        items = report.get("items")
        if isinstance(items, (list, tuple)) and items:
            parts.append(f"<h3>{escape(T['ar_items_header'])}</h3>")
            for item in items:
                if isinstance(item, dict):
                    parts.append(safe("report item", _item_block, T, item))
        questions = safe("report questions", _ul, report.get("questions"), types)
        if questions:
            parts.append(f"<h3>{escape(T['ar_questions_header'])}</h3>")
            parts.append(questions)
    else:
        parts.append(_p(T["ar_failed_notice"]))

    parts.append(f"<h2>{escape(T['rr_lenses_header'])}</h2>")
    for lens in lenses if isinstance(lenses, (list, tuple)) else []:
        if isinstance(lens, dict):
            parts.append(safe("lens", _lens_block, T, lens))

    parts.append(f"<h2>{escape(T['hl_header'])}</h2>")
    parts.append(_p(T["hl_intro"], "muted"))
    parts.append(legend_html(types, T["hl_legend_title"]))
    parts.append(safe("highlighted text", lambda: f'<div class="text">{highlight_html(safe_text, quotes, types)}</div>'))
    parts.append(f'<div class="footer">{escape(T["rr_print_footer"].format(date=prepared_on))}</div>')
    parts.append("</body></html>")

    if problems:
        # Quietly: the page is still given; only section names, no case text.
        logger.warning("Reflection report: some parts could not be shown: %s", "; ".join(problems))
        if on_problem is not None:
            try:
                on_problem("; ".join(problems))
            except Exception:
                logger.exception("Reflection report: reporting a problem failed")
    return "\n".join(p for p in parts if p)
