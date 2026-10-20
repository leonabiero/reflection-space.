"""
Printable report for Corpus analysis
======================================

Builds ONE self-contained web page (HTML) laid out for paper, in the same
way as services/report_builder.py does for Pattern Review: A4, black on
white, a confidentiality line on every printed page. The manager downloads
it, opens it in a browser and chooses Print (or "Save as PDF").

Rules this report must never break (the same as the on-screen page):
  - It says "candidate pattern for reflection", never that bias or poor
    practice was found.
  - Strength is always "appears in X of N texts", never a percentage on its
    own. It says plainly that the texts carry no labels, so the report
    cannot say anything about whether groups are treated alike or not.
  - "Raised" in the lens reading means the AI raised an observation; it is
    not a frequency.
  - Texts are named only by their neutral numbers (T-001 ...). No file name,
    no author, no name of any person is ever included.
  - The questions switch is honoured: when it is off, no AI question is
    printed.
  - Passages and exact quotes are optional (a paper copy travels further
    than a screen).
  - Everything inserted is HTML-escaped; the page loads nothing from outside
    and runs no scripts (see _CSP).

The function is pure (data in, text out): no database, no AI.
"""

from html import escape

from services.corpus_engine import document_label
from services.report_builder import HTML_LANG, _CSP, _STYLE

MAX_PASSAGES_PER_PATTERN = 15
MAX_LABELS_SHOWN = 60


def _e(value):
    return escape("" if value is None else str(value), quote=True)


def _paragraph(text):
    return f"<p>{_e(text)}</p>" if text else ""


def _bullets(items):
    items = [i for i in (items or []) if i]
    return "<ul>" + "".join(f"<li>{_e(i)}</li>" for i in items) + "</ul>" if items else ""


def _labels(doc_numbers, T):
    shown = [document_label(n) for n in doc_numbers[:MAX_LABELS_SHOWN]]
    text = ", ".join(shown)
    hidden = len(doc_numbers) - len(shown)
    if hidden > 0:
        text += " " + T["corpus_report_more_texts"].format(count=hidden)
    return text


def build_corpus_report(T, lang, lens_labels, corpus, counts, prepared_on,
                        run=None, patterns=None, events_by_pattern=None,
                        readings=None, terms=None,
                        include_passages=True, include_questions=True,
                        include_comments=True):
    """
    Return the report as an HTML string.

    corpus        {"name": ...}
    counts        {"documents": n, "passages": m}
    run           the search the patterns come from (corpus_store run dict) or None
    patterns      corpus_store.list_patterns(...) results to include, or None
                  to leave the patterns out
    readings      {"overview": corpus_store.get_reading_overview(...),
                   "items": {lens: corpus_store.list_lens_readings(...)}} or None
    terms         corpus_terms.count_terms(...) result (with at least one
                  term) or None
    include_passages   exact passages of patterns and exact quotes of readings
    include_questions  AI-written questions (the page's switch)
    """
    events_by_pattern = events_by_pattern or {}
    parts = []
    add = parts.append

    add(f"<h1>{_e(T['corpus_report_doc_title'])}</h1>")
    add(f"<p class='muted'>{_e(T['report_confidential'])} · "
        f"{_e(T['report_prepared'].format(date=prepared_on))}</p>")
    add("<div class='note'>"
        f"<strong>{_e(T['report_how_to_read_title'])}</strong>"
        f"{_paragraph(T['corpus_report_how_to_read'])}"
        f"{_paragraph(T['corpus_no_groups_note'])}</div>")

    add(f"<h2>{_e(T['corpus_report_collection_title'])}</h2>")
    add(_paragraph(T["corpus_report_collection_line"].format(
        name=(corpus or {}).get("name", ""), documents=counts["documents"],
        passages=counts["passages"])))

    # ----------------------------------------------------------- patterns
    if patterns is not None:
        add(f"<h2>{_e(T['corpus_report_search_title'])}</h2>")
        if run:
            params = run.get("parameters") or {}
            add(_paragraph(T["corpus_report_search_line"].format(
                date=(run.get("created_at") or "")[:10],
                documents=run.get("documents_considered", 0),
                passages=run.get("passages_considered", 0),
                patterns=run.get("patterns_created", 0))))
            add(_paragraph(T["corpus_run_caption"].format(
                level=T["patterns_similarity_levels"].get(params.get("similarity_level"), "—"),
                min_passages=params.get("min_passages", "—"),
                min_documents=params.get("min_documents", "—"),
                questions=T["corpus_yes"] if params.get("include_questions", True) else T["corpus_no"])))
        run_has_questions = bool((run or {}).get("parameters", {}).get("include_questions", True))
        show_questions = include_questions and run_has_questions

        statuses = sorted({p["status"] for p in patterns})
        if statuses:
            add(_paragraph(T["report_statuses_line"].format(
                statuses=", ".join(T["patterns_statuses"].get(s, s) for s in statuses))))

        if not patterns:
            add(_paragraph(T["report_no_patterns"]))
        else:
            add(f"<h2>{_e(T['report_summary_title'])}</h2>")
            rows = "".join(
                f"<tr><td>{n}</td><td>{_e(p['title'])}</td>"
                f"<td>{_e(T['patterns_statuses'].get(p['status'], p['status']))}</td>"
                f"<td>{_e(T['corpus_terms_texts_cell'].format(documents=p['counts']['documents'], total=p['counts']['total_documents']))}</td>"
                f"<td>{p['counts']['passages']}</td></tr>"
                for n, p in enumerate(patterns, 1))
            add("<table><tr>"
                f"<th>#</th><th>{_e(T['report_col_pattern'])}</th><th>{_e(T['report_col_status'])}</th>"
                f"<th>{_e(T['corpus_report_col_texts'])}</th><th>{_e(T['corpus_report_col_passages'])}</th>"
                f"</tr>{rows}</table>")

            for n, p in enumerate(patterns, 1):
                counts_p = p["counts"]
                add("<section class='pattern'>")
                add(f"<h2>{_e(T['report_pattern_heading'].format(n=n, title=p['title']))}</h2>")
                add(f"<p class='tag'>{_e(T['patterns_candidate_label'])} · "
                    f"{_e(T['patterns_statuses'].get(p['status'], p['status']))}</p>")
                add(_paragraph(T["corpus_counts_line"].format(
                    documents=counts_p["documents"], total=counts_p["total_documents"],
                    percent=round(counts_p["share"] * 100), passages=counts_p["passages"])))
                add(f"<p class='muted'>{_e(T['corpus_documents_line'].format(labels=_labels(counts_p['doc_numbers'], T)))}</p>")
                if p.get("lost_members"):
                    add(f"<div class='warn'>{_e(T['corpus_lost_members'].format(count=p['lost_members']))}</div>")
                if p.get("below_minimum"):
                    add(f"<div class='warn'>{_e(T['corpus_below_minimum'])}</div>")
                if p.get("explanation_status") == "fallback":
                    add(f"<div class='warn'>{_e(T['patterns_explanation_failed'])}</div>")

                add(f"<h3>{_e(T['patterns_what_in_common'])}</h3>{_paragraph(p['description'])}")
                add(f"<h3>{_e(T['patterns_why_it_matters'])}</h3>{_paragraph(p['why_it_matters'])}")
                add(f"<h3>{_e(T['patterns_alternatives'])}</h3>{_bullets(p['alternative_explanations'])}")
                add(f"<h3>{_e(T['patterns_limitations'])}</h3>{_bullets(p['limitations'])}")
                if show_questions and p["questions"]:
                    add(f"<h3>{_e(T['patterns_questions'])}</h3>{_bullets(p['questions'])}")

                if include_comments:
                    notes = [e for e in events_by_pattern.get(p["id"], []) if e.get("comment")]
                    if notes:
                        add(f"<h3>{_e(T['report_team_comments'])}</h3>")
                        add("<ul>" + "".join(
                            f"<li>{_e((e.get('created_at') or '')[:10])} — “{_e(e['comment'])}”</li>"
                            for e in notes[-10:]) + "</ul>")

                add(f"<h3>{_e(T['corpus_passages_header'])}</h3>")
                if not include_passages:
                    add(f"<p class='muted'>{_e(T['corpus_report_passages_omitted'])}</p>")
                else:
                    for m in p["members"][:MAX_PASSAGES_PER_PATTERN]:
                        add(f"<div class='obs'><p class='tag'>{_e(document_label(m['doc_no']))}</p>"
                            f"<p class='quote'>“{_e(m['text'])}”</p></div>")
                    hidden = len(p["members"]) - MAX_PASSAGES_PER_PATTERN
                    if hidden > 0:
                        add(f"<p class='muted'>{_e(T['corpus_more_passages'].format(count=hidden))}</p>")
                add("</section>")

    # ----------------------------------------------------------- readings
    if readings is not None:
        overview = readings["overview"]
        add(f"<h2>{_e(T['corpus_report_readings_title'])}</h2>")
        add(_paragraph(T["corpus_read_status"].format(
            read=overview["read"], documents=overview["documents"], unread=overview["unread"])))
        add(f"<div class='note'>{_e(T['corpus_read_caveat'])}</div>")
        for lens, lens_counts in overview["lenses"].items():
            considered = lens_counts["finding"] + lens_counts["no_finding"]
            if not considered:
                continue
            add(f"<h3>{_e(T['corpus_lens_item'].format(lens=lens_labels.get(lens, lens), raised=lens_counts['finding'], considered=considered))}</h3>")
            items = readings["items"].get(lens, [])
            if not include_passages:
                add(f"<p class='muted'>{_e(T['corpus_report_readings_omitted'])}</p>"
                    if items else "")
                if items:
                    add(f"<p class='muted'>{_e(T['corpus_documents_line'].format(labels=_labels([i['doc_no'] for i in items], T)))}</p>")
                continue
            if not items:
                add(_paragraph(T["corpus_lens_none"]))
            for item in items:
                add(f"<div class='obs'><p class='tag'>{_e(document_label(item['doc_no']))}</p>"
                    f"{_paragraph(item['observation'])}")
                quotes = [ev.get("quote") for ev in (item.get("evidence") or [])[:3]
                          if isinstance(ev, dict) and ev.get("quote")]
                for quote in quotes:
                    add(f"<p class='quote'>{_e(T['report_quote_label'])}: “{_e(quote)}”</p>")
                if not quotes:
                    add(f"<p class='muted'>{_e(T['corpus_lens_no_quote'])}</p>")
                if include_questions and item.get("questions"):
                    add(_bullets(item["questions"]))
                add("</div>")

    # ---------------------------------------------------------- word list
    if terms is not None and terms["terms"]:
        total = terms["total_documents"]
        add(f"<h2>{_e(T['corpus_report_terms_title'])}</h2>")
        add(f"<div class='note'>{_e(T['corpus_terms_caveat'])}</div>")
        ordered = sorted(terms["terms"], key=lambda t: (-t["documents"], t["term"].casefold()))
        rows = "".join(
            f"<tr><td>{_e(t['term'])}</td>"
            f"<td>{_e(T['corpus_terms_texts_cell'].format(documents=t['documents'], total=total))}</td>"
            f"<td>{t['occurrences']}</td>"
            f"<td>{_e(_labels(t['doc_numbers'], T))}</td></tr>"
            for t in ordered)
        add("<table><tr>"
            f"<th>{_e(T['corpus_terms_col_term'])}</th><th>{_e(T['corpus_terms_col_texts'])}</th>"
            f"<th>{_e(T['corpus_terms_col_times'])}</th><th>{_e(T['corpus_report_col_where'])}</th>"
            f"</tr>{rows}</table>")

    add(f"<h2>{_e(T['report_limits_title'])}</h2>{_bullets(T['corpus_report_limits_list'])}")
    add(f"<div class='footer'>{_e(T['corpus_report_footer'].format(date=prepared_on))}</div>")

    return (
        f"<!doctype html><html lang='{HTML_LANG.get(lang, 'es')}'><head><meta charset='utf-8'>"
        f"<meta http-equiv='Content-Security-Policy' content=\"{_CSP}\">"
        "<meta name='viewport' content='width=device-width, initial-scale=1'>"
        f"<title>{_e(T['corpus_report_doc_title'])}</title><style>{_STYLE}</style></head>"
        f"<body>{''.join(parts)}</body></html>"
    )
