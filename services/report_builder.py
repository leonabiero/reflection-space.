"""
Printable pattern report (Stage 3)
====================================

Builds ONE self-contained web page (HTML) from a pattern search, laid out
for paper: A4, black on white, page-break rules, a confidentiality footer on
every printed page. The manager downloads it, opens it in any browser and
chooses Print (or "Save as PDF"). No extra software and no outside service
are involved.

Rules this report must never break (the same as the on-screen page):
  - It says "candidate pattern for reflection". It never says bias or poor
    practice has been found, and it repeats plainly what the data cannot show.
  - Counts of observations, reflections and cases are shown separately, and
    "across cases" is only claimed when every reflection has a case reference.
  - It contains NO author name and NO private note or rating. It is built
    only from what pattern_store already returns for managers.
  - Case references are left out unless the manager ticks the option
    (a printed page travels further than a screen).
  - Everything inserted into the page is HTML-escaped, and the page loads
    nothing from outside and runs no scripts (see _CSP).

The function is pure (text in, text out): it does no database or AI work.
"""

from html import escape

# The page may use inline styles only: nothing is fetched, no script runs.
_CSP = "default-src 'none'; style-src 'unsafe-inline'; img-src data:"

HTML_LANG = {"Español": "es", "Euskera": "eu", "English": "en"}

MAX_OBSERVATIONS_PER_PATTERN = 25

_STYLE = """
@page { size: A4; margin: 18mm 16mm 22mm 16mm; }
* { box-sizing: border-box; }
body { font-family: Georgia, 'Times New Roman', serif; color: #111; background: #fff;
       line-height: 1.45; font-size: 11pt; max-width: 180mm; margin: 0 auto; padding: 12mm 4mm; }
h1 { font-size: 20pt; margin: 0 0 2mm; }
h2 { font-size: 14pt; margin: 8mm 0 2mm; border-bottom: 1px solid #999; padding-bottom: 1mm; }
h3 { font-size: 12pt; margin: 5mm 0 1mm; }
p, li { margin: 0 0 2mm; white-space: pre-line; }
ul { margin: 0 0 2mm 5mm; padding: 0; }
.muted { color: #444; font-size: 9.5pt; }
.note { border: 1px solid #888; border-left: 4px solid #555; padding: 3mm 4mm; margin: 4mm 0; background: #f6f6f6; }
.warn { border: 1px solid #a60; border-left: 4px solid #a60; padding: 2mm 3mm; margin: 2mm 0; background: #fff8ee; }
table { border-collapse: collapse; width: 100%; font-size: 10pt; margin: 2mm 0; }
th, td { border: 1px solid #888; padding: 1.5mm 2mm; text-align: left; vertical-align: top; }
th { background: #eee; }
.pattern { page-break-before: always; }
.pattern:first-of-type { page-break-before: auto; }
.obs { border-top: 1px dotted #999; padding-top: 1.5mm; margin-top: 2mm; page-break-inside: avoid; }
.quote { font-style: italic; margin-left: 4mm; }
.tag { font-family: Arial, Helvetica, sans-serif; font-size: 9pt; text-transform: uppercase;
       letter-spacing: .04em; color: #333; }
.footer { display: none; }
@media print {
  body { padding: 0; max-width: none; }
  .footer { display: block; position: fixed; bottom: 0; left: 0; right: 0; text-align: center;
            font-size: 8.5pt; color: #333; border-top: 1px solid #999; padding-top: 1mm; background: #fff; }
}
"""


def _e(value):
    return escape("" if value is None else str(value), quote=True)


def _paragraphs(text):
    return f"<p>{_e(text)}</p>" if text else ""


def _bullets(items):
    items = [i for i in (items or []) if i]
    return "<ul>" + "".join(f"<li>{_e(i)}</li>" for i in items) + "</ul>" if items else ""


def case_message(T, counts):
    """The honest sentence about cases for a group (same rules as the page)."""
    if counts["cases"] == 0:
        return T["patterns_cases_none"]
    if not counts["case_recurrence_known"]:
        return T["patterns_cases_incomplete"].format(
            missing=counts["reflections_without_case"], total=counts["reflections"])
    if counts["cases"] == 1:
        return T["patterns_cases_single"]
    return T["patterns_cases_multiple"].format(cases=counts["cases"])


def _filters_text(T, params, lens_labels):
    parts = []
    modules = params.get("modules") or []
    if modules:
        parts.append(", ".join(lens_labels.get(m, m) for m in modules))
    if params.get("date_from") or params.get("date_to"):
        parts.append(f"{params.get('date_from') or '…'} → {params.get('date_to') or '…'}")
    return "; ".join(parts) if parts else T["report_no_filters"]


def build_pattern_report(T, lang, lens_labels, run, patterns, events_by_pattern,
                         prepared_on, include_observations=True,
                         include_case_refs=False, include_comments=True):
    """
    Return the report as an HTML string.

    T, lang           the translation dictionary and its language name
    lens_labels       {lens key: readable name}
    run               a pattern_store run dict (created_at, parameters, ...)
    patterns          pattern_store.list_patterns(...) results to include
    events_by_pattern {pattern id: [event dicts]} (only used for comments)
    prepared_on       text for the preparation date (e.g. '2026-10-20')
    """
    params = (run or {}).get("parameters") or {}
    parts = []
    add = parts.append

    add(f"<h1>{_e(T['report_doc_title'])}</h1>")
    add(f"<p class='muted'>{_e(T['report_confidential'])} · "
        f"{_e(T['report_prepared'].format(date=prepared_on))}</p>")

    add("<div class='note'>"
        f"<strong>{_e(T['report_how_to_read_title'])}</strong>"
        f"{_paragraphs(T['report_how_to_read'])}</div>")

    add(f"<h2>{_e(T['report_search_title'])}</h2>")
    add(_paragraphs(T["report_search_line"].format(
        date=((run or {}).get("created_at") or "")[:10],
        observations=(run or {}).get("observations_considered", 0),
        patterns=(run or {}).get("patterns_created", 0))))
    add(_paragraphs(T["patterns_run_caption"].format(
        level=T["patterns_similarity_levels"].get(params.get("similarity_level"), "—"),
        min_obs=params.get("min_observations", "—"),
        min_refl=params.get("min_reflections", "—"))))
    add(_paragraphs(T["report_filters_line"].format(filters=_filters_text(T, params, lens_labels))))
    statuses = sorted({p["status"] for p in patterns})
    add(_paragraphs(T["report_statuses_line"].format(
        statuses=", ".join(T["patterns_statuses"].get(s, s) for s in statuses) or "—")))

    if not patterns:
        add(f"<p>{_e(T['report_no_patterns'])}</p>")
    else:
        add(f"<h2>{_e(T['report_summary_title'])}</h2>")
        rows = "".join(
            f"<tr><td>{n}</td><td>{_e(p['title'])}</td>"
            f"<td>{_e(T['patterns_statuses'].get(p['status'], p['status']))}</td>"
            f"<td>{p['counts']['observations']}</td><td>{p['counts']['reflections']}</td>"
            f"<td>{p['counts']['cases']}</td></tr>"
            for n, p in enumerate(patterns, 1))
        add("<table><tr>"
            f"<th>#</th><th>{_e(T['report_col_pattern'])}</th><th>{_e(T['report_col_status'])}</th>"
            f"<th>{_e(T['report_col_obs'])}</th><th>{_e(T['report_col_refl'])}</th>"
            f"<th>{_e(T['report_col_cases'])}</th></tr>{rows}</table>")

        for n, p in enumerate(patterns, 1):
            counts = p["counts"]
            add("<section class='pattern'>")
            add(f"<h2>{_e(T['report_pattern_heading'].format(n=n, title=p['title']))}</h2>")
            add(f"<p class='tag'>{_e(T['patterns_candidate_label'])} · "
                f"{_e(T['patterns_statuses'].get(p['status'], p['status']))}</p>")
            add(_paragraphs(T["patterns_counts_line"].format(
                observations=counts["observations"], reflections=counts["reflections"],
                cases=counts["cases"])))
            add(f"<p class='muted'>{_e(case_message(T, counts))} {_e(T['patterns_case_ref_caveat'])}</p>")
            if counts.get("date_first"):
                add(f"<p class='muted'>{_e(T['patterns_dates_line'].format(first=counts['date_first'], last=counts['date_last']))}</p>")
            lens_text = ", ".join(
                f"{lens_labels.get(k, k)} ({counts['modules'][k]})"
                for k in sorted(counts["modules"], key=lambda k: (-counts["modules"][k], k)))
            if lens_text:
                add(f"<p class='muted'>{_e(T['patterns_lenses_line'].format(lenses=lens_text))}</p>")

            if p.get("lost_members"):
                add(f"<div class='warn'>{_e(T['patterns_lost_members'].format(count=p['lost_members']))}</div>")
            if p.get("below_minimum"):
                add(f"<div class='warn'>{_e(T['patterns_below_minimum'])}</div>")
            if p.get("explanation_status") == "fallback":
                add(f"<div class='warn'>{_e(T['patterns_explanation_failed'])}</div>")

            add(f"<h3>{_e(T['patterns_what_in_common'])}</h3>{_paragraphs(p['description'])}")
            add(f"<h3>{_e(T['patterns_why_it_matters'])}</h3>{_paragraphs(p['why_it_matters'])}")
            add(f"<h3>{_e(T['patterns_alternatives'])}</h3>{_bullets(p['alternative_explanations'])}")
            add(f"<h3>{_e(T['patterns_limitations'])}</h3>{_bullets(p['limitations'])}")
            add(f"<h3>{_e(T['patterns_questions'])}</h3>{_bullets(p['questions'])}")

            if include_comments:
                notes = [e for e in events_by_pattern.get(p["id"], []) if e.get("comment")]
                if notes:
                    add(f"<h3>{_e(T['report_team_comments'])}</h3>")
                    add("<ul>" + "".join(
                        f"<li>{_e((e.get('created_at') or '')[:10])} — “{_e(e['comment'])}”</li>"
                        for e in notes[-10:]) + "</ul>")

            add(f"<h3>{_e(T['patterns_observations_header'])}</h3>")
            if not include_observations:
                add(f"<p class='muted'>{_e(T['report_observations_omitted'])}</p>")
            else:
                for m in p["members"][:MAX_OBSERVATIONS_PER_PATTERN]:
                    head = lens_labels.get(m["module"], m["module"])
                    if include_case_refs:
                        head += f" — {m['case_ref'] or T['reflection_no_case_ref']}"
                    head += f" — {(m.get('created_at') or '')[:10]}"
                    add(f"<div class='obs'><p class='tag'>{_e(head)}</p>{_paragraphs(m['observation'])}")
                    for ev in (m.get("evidence") or [])[:3]:
                        quote = ev.get("quote") if isinstance(ev, dict) else None
                        if quote:
                            add(f"<p class='quote'>{_e(T['report_quote_label'])}: “{_e(quote)}”</p>")
                    add("</div>")
                hidden = len(p["members"]) - MAX_OBSERVATIONS_PER_PATTERN
                if hidden > 0:
                    add(f"<p class='muted'>{_e(T['patterns_more_observations'].format(count=hidden))}</p>")
            add("</section>")

    add(f"<h2>{_e(T['report_limits_title'])}</h2>{_bullets(T['report_limits_list'])}")
    add(f"<div class='footer'>{_e(T['report_footer'].format(date=prepared_on))}</div>")

    return (
        f"<!doctype html><html lang='{HTML_LANG.get(lang, 'es')}'><head><meta charset='utf-8'>"
        f"<meta http-equiv='Content-Security-Policy' content=\"{_CSP}\">"
        "<meta name='viewport' content='width=device-width, initial-scale=1'>"
        f"<title>{_e(T['report_doc_title'])}</title><style>{_STYLE}</style></head>"
        f"<body>{''.join(parts)}</body></html>"
    )
