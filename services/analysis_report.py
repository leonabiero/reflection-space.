"""
Analysis report ("Informe de análisis") -- November 2026
=========================================================

EDE project team (approved by the project leads): after the eight lens
cards, a report brings their results together. It is made by ONE extra
Claude call (services/reflection_service.py:generate_analysis_report),
which receives only ANONYMISED material: the anonymised document and the
eight lenses' results (themselves written from that anonymised text).

This module builds what that call receives, checks what comes back, and
decides what happens if it fails:

  - Only the four evidence types are kept (bias, stereotype, prejudice,
    loaded_label); the framework area must be 1 to 5.
  - Every quote is checked word for word against the anonymised text
    (services/evidence.py). A quote that cannot be found is removed and
    counted; the item stays, without a quote.
  - At most MAX_ITEMS items and MAX_QUESTIONS questions; texts are capped.
  - Two attempts. If both fail, the reflection is still shown with all its
    lens cards; the page shows a short notice and a Retry button. The
    failure is logged once (no case text in the log).

Like the lenses' results, the report is shown and then forgotten: it is
never saved.
"""

import traceback

from services.evidence import verify_quotes, clean_type, EVIDENCE_TYPES
from services.ai_text import as_text, as_text_list

MAX_ITEMS = 10
MAX_QUESTIONS = 2
MAX_ATTEMPTS = 2
FRAMEWORK_AREAS = (1, 2, 3, 4, 5)

_SUMMARY_MAX = 1200
_WHY_MAX = 600
_QUESTION_MAX = 400


def _clean_str(value, limit):
    # Plain text or a small object such as {"question": ..., "type": ...}
    # (the AI sometimes sends those): its text is read, never dropped.
    return as_text(value)[:limit]


def build_lens_results_text(findings, labels=None):
    """The eight lenses' results as plain text for the report call.
    `findings`: the orchestrator's findings list ({"module", "observation",
    "questions", "evidence"}). `labels`: {module key: lens name}."""
    labels = labels or {}
    parts = []
    for f in findings or []:
        lines = [f"## {labels.get(f.get('module'), f.get('module'))}"]
        observation = as_text(f.get("observation"))
        if observation:
            lines.append(f"Analysis: {observation}")
        for e in f.get("evidence") or []:
            if not isinstance(e, dict):
                continue
            kind = e.get("type") or "unclassified"
            lines.append(f'Quote ({kind}): "{as_text(e.get("quote"))}"')
        for q in as_text_list(f.get("questions")):
            lines.append(f"Question: {q}")
        parts.append("\n".join(lines))
    return "\n\n".join(parts) if parts else "(No lens found anything notable.)"


def validate_report(obj, safe_text):
    """The cleaned report, or None if the answer is not usable.

    Returns {"summary": str, "items": [{"type", "area", "quote", "why"}],
    "questions": [str], "unverified_quote_count": int}.
    """
    if not isinstance(obj, dict) or "error" in obj:
        return None
    raw_items = obj.get("items")
    if not isinstance(raw_items, list):
        raw_items = []
    items = []
    unverified = 0
    for raw in raw_items:
        if not isinstance(raw, dict):
            continue
        kind = clean_type(raw.get("type"))
        try:
            area = int(raw.get("area"))
        except (TypeError, ValueError):
            area = None
        why = _clean_str(raw.get("why"), _WHY_MAX)
        if kind is None or area not in FRAMEWORK_AREAS or not why:
            continue
        quote = ""
        proposed = raw.get("quote")
        if isinstance(proposed, str) and proposed.strip():
            verified, bad = verify_quotes([{"quote": proposed, "type": kind}], safe_text or "")
            if verified:
                quote = verified[0]["quote"]
            else:
                unverified += max(1, bad)
        items.append({"type": kind, "area": area, "quote": quote, "why": why})
        if len(items) >= MAX_ITEMS:
            break

    questions = [q[:_QUESTION_MAX] for q in as_text_list(obj.get("questions"))][:MAX_QUESTIONS]

    summary = _clean_str(obj.get("summary"), _SUMMARY_MAX)
    if not summary and not items and not questions:
        return None
    return {"summary": summary, "items": items, "questions": questions,
            "unverified_quote_count": unverified}


def generate_report(safe_text, findings, lang="Español", labels=None, attempts=MAX_ATTEMPTS):
    """Make the report. Returns {"report": dict} or {"error": str,
    "root_cause_detail": dict}. Never raises; never logs (the caller logs
    once)."""
    from services.reflection_service import generate_analysis_report
    lens_text = build_lens_results_text(findings, labels)
    last = {"error": "Analysis report could not be generated", "raw": "", "traceback": None}
    for _ in range(max(1, attempts)):
        try:
            answer = generate_analysis_report(safe_text, lens_text, lang)
        except Exception as exc:
            last = {"error": "API call failed", "raw": str(exc), "traceback": traceback.format_exc()}
            continue
        report = validate_report(answer, safe_text)
        if report is not None:
            return {"report": report}
        last = {"error": (answer or {}).get("error", "Report reply was not usable"),
                "raw": "", "traceback": None}
    return last


def log_report_failure(failure, lang, manual=False):
    """One log entry for a failed report (never any case text)."""
    from services.error_log import log_error
    from services.issue_fingerprint import classify_reflection_failure_root_cause
    root = classify_reflection_failure_root_cause(
        failure.get("error", ""), failure.get("raw", ""), failure.get("traceback"),
    )
    try:
        return log_error(
            page="reflection_space (analysis report)",
            error_type="AnalysisReportFailed",
            message=(f"The analysis report could not be generated"
                     f"{' (practitioner retry)' if manual else ''}. Root cause: {root}. "
                     "The lens cards were still shown."),
            traceback_text=failure.get("traceback"),
            traceback_unavailable_reason=None if failure.get("traceback") else (
                "No Python exception: the reply could not be used. The reply itself "
                "is not stored because logs must not contain case content."
            ),
            context={"lang": lang, "manual_retry": manual},
            severity="warning",
            title_override=f"Analysis Report Failed – {root}",
            root_cause_hint=root,
        )
    except Exception:
        return None, None


def all_quotes(findings, report):
    """Every typed, verified quote from the lenses and the report, as
    [{"quote", "type"}] -- what the highlighted text shows."""
    quotes = []
    for f in findings or []:
        for e in f.get("evidence") or []:
            if isinstance(e, dict) and e.get("quote") and e.get("type") in EVIDENCE_TYPES:
                quotes.append({"quote": e["quote"], "type": e["type"]})
    for item in (report or {}).get("items") or []:
        if item.get("quote") and item.get("type") in EVIDENCE_TYPES:
            quotes.append({"quote": item["quote"], "type": item["type"]})
    return quotes
