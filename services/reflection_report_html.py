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

from html import escape

from services.highlight import highlight_html, legend_html

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
"""


def _p(text, css=""):
    cls = f' class="{css}"' if css else ""
    return f"<p{cls}>{escape(text or '')}</p>"


def _ul(items):
    items = [i for i in (items or []) if i]
    if not items:
        return ""
    return "<ul>" + "".join(f"<li>{escape(i)}</li>" for i in items) + "</ul>"


def _quote(T, item):
    kind = item.get("type")
    label = T["evidence_type_labels"].get(kind, "") if kind else ""
    prefix = f"[{label}] " if label else ""
    return f"<blockquote>{escape(prefix)}«{escape(item.get('quote', ''))}»</blockquote>"


def build_reflection_report_html(T, lang, code, prepared_on, report, lenses, safe_text, quotes):
    """
    `report`: the analysis report dict (or None).
    `lenses`: [{"label", "analysis", "evidence": [{"quote", "type"}], "questions"}]
              -- only lenses with something to show.
    `safe_text`: the ANONYMISED text. `quotes`: typed quotes to highlight.
    Returns the page as a string.
    """
    types = T["evidence_type_labels"]
    areas = T["ar_area_names"]
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
    if report:
        if report.get("summary"):
            parts.append(f"<h3>{escape(T['ar_summary_header'])}</h3>")
            parts.append(_p(report["summary"]))
        if report.get("items"):
            parts.append(f"<h3>{escape(T['ar_items_header'])}</h3>")
            for item in report["items"]:
                parts.append('<div class="block">')
                parts.append(f"<p><strong>{escape(types.get(item['type'], item['type']))}</strong>"
                             f" · {escape(areas.get(str(item['area']), str(item['area'])))}</p>")
                if item.get("quote"):
                    parts.append(_quote(T, {"quote": item["quote"]}))
                else:
                    parts.append(_p(T["ar_missing_quote"], "muted"))
                parts.append(_p(item.get("why", "")))
                parts.append("</div>")
        if report.get("questions"):
            parts.append(f"<h3>{escape(T['ar_questions_header'])}</h3>")
            parts.append(_ul(report["questions"]))
    else:
        parts.append(_p(T["ar_failed_notice"]))

    parts.append(f"<h2>{escape(T['rr_lenses_header'])}</h2>")
    for lens in lenses or []:
        parts.append('<div class="block">')
        parts.append(f"<h3>{escape(lens.get('label', ''))}</h3>")
        if lens.get("analysis"):
            parts.append(_p(lens["analysis"]))
        for item in lens.get("evidence") or []:
            parts.append(_quote(T, item))
        if lens.get("questions"):
            parts.append(_ul(lens["questions"]))
        parts.append("</div>")

    parts.append(f"<h2>{escape(T['hl_header'])}</h2>")
    parts.append(_p(T["hl_intro"], "muted"))
    parts.append(legend_html(types, T["hl_legend_title"]))
    parts.append(f'<div class="text">{highlight_html(safe_text, quotes, types)}</div>')
    parts.append(f'<div class="footer">{escape(T["rr_print_footer"].format(date=prepared_on))}</div>')
    parts.append("</body></html>")
    return "\n".join(p for p in parts if p)
