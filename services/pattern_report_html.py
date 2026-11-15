"""
Printable Pattern Review report (15 November 2026)
====================================================

Builds ONE self-contained web page from a saved Pattern Review report
(services/pattern_text_store.py), laid out for paper: A4, black on white,
a confidentiality footer on every printed page. The manager downloads it,
opens it in a browser and chooses Print (or "Save as PDF"). No extra
software and no outside service are involved. This replaces the printable
report of the earlier observation-based Pattern Review.

Rules it must never break (the same as the screen):
  - It speaks of candidate patterns for reflection, never conclusions.
  - It contains only what the report holds: no text, no quotation, no
    reflection code and no name of anyone who wrote a text.
  - Everything inserted is HTML-escaped; the page loads nothing from
    outside and runs no scripts.

Pure function (text in, text out): no database or AI work.
"""

from html import escape

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
.muted { color: #444; font-size: 9.5pt; }
.note { border: 1px solid #888; border-left: 4px solid #555; padding: 3mm 4mm; margin: 4mm 0; background: #f6f6f6; }
.pattern { page-break-inside: avoid; border-top: 1px solid #bbb; padding-top: 2mm; margin-top: 4mm; }
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


def build_report_html(T, lang, saved, prepared_on, created_on):
    """
    `saved`: one item from pattern_text_store.list_reports().
    `prepared_on` / `created_on`: dates already formatted for display.
    Returns the page as a string.
    """
    report = saved.get("report") or {}
    patterns = report.get("patterns") or []
    texts_read = report.get("texts_read", saved.get("texts_count", 0))

    parts = [
        "<!DOCTYPE html>",
        f'<html lang="{HTML_LANG.get(lang, "es")}"><head><meta charset="utf-8">',
        f'<meta http-equiv="Content-Security-Policy" content="{_CSP}">',
        f"<title>{escape(T['pr_print_title'])}</title><style>{_STYLE}</style></head><body>",
        f"<h1>{escape(T['pr_print_title'])}</h1>",
        _p(T["pr_print_confidential"], "muted"),
        _p(T["pr_print_prepared"].format(date=prepared_on), "muted"),
        _p(T["pr_report_meta"].format(
            date=created_on, months=saved.get("period_months", ""),
            texts=saved.get("texts_count", 0), read=texts_read,
        ), "muted"),
        f'<div class="note">{escape(T["pr_candidate_note"])}</div>',
    ]
    if report.get("overview"):
        parts.append(f"<h2>{escape(T['pr_overview_header'])}</h2>")
        parts.append(_p(report["overview"]))

    parts.append(f"<h2>{escape(T['pr_patterns_header'])}</h2>")
    if not patterns:
        parts.append(_p(T["pr_no_patterns"]))
    for n, pattern in enumerate(patterns, start=1):
        parts.append('<div class="pattern">')
        parts.append(f"<h3>{n}. {escape(pattern.get('title', ''))}</h3>")
        parts.append(_p(T["pr_seen_in"].format(count=pattern.get("texts_count", 0), total=texts_read), "muted"))
        parts.append(_p(pattern.get("description", "")))
        if pattern.get("why_it_may_matter"):
            parts.append(f"<p><strong>{escape(T['pr_why_header'])}</strong></p>")
            parts.append(_p(pattern["why_it_may_matter"]))
        if pattern.get("questions"):
            parts.append(f"<p><strong>{escape(T['pr_questions_header'])}</strong></p>")
            parts.append(_ul(pattern["questions"]))
        parts.append("</div>")

    parts.append(f"<h2>{escape(T['pr_limits_header'])}</h2>")
    parts.append(_ul(list(report.get("limitations") or []) + list(T["pr_standing_limits"])))
    parts.append(f'<div class="footer">{escape(T["pr_print_footer"].format(date=prepared_on))}</div>')
    parts.append("</body></html>")
    return "\n".join(p for p in parts if p)
