"""
Knowledge Assistant (Organisational Learning)
================================================

Sprint 12. A natural-language question interface for Supervisors and
Programme Managers, surfaced inside the existing Learning page (never
a separate top-level page -- see pages/learning.py).

Reuses existing infrastructure -- no parallel systems
----------------------------------------------------------
This module does NOT create a second vector database, a second
retrieval pipeline, or a second Anthropic client pattern. It is a thin
orchestration layer over pieces that already exist:

    - rdi.retrieval_service.retrieve_global_context() -- the SAME
      Hybrid RAG / Qdrant semantic search already used by
      rdi/context_engine.py, just called without a case_ref so it can
      search across the WHOLE organisation's indexed knowledge, exactly
      the way the System Administration page's Retrieval Test "global
      mode" already does (see rdi/retrieval_service.py's module
      docstring, "Admin-only exception -- retrieve_global_context()").
      Practitioner Reflection's per-case retrieval
      (retrieve_historical_context()) is completely untouched by this.

    - services.research_metrics_SERVICE.build_research_summary() -- the
      SAME organisation-wide, anonymous aggregate counts (theme flags,
      theme explorations, completed documents, feedback) already used
      by the Research Metrics page. Reused here (not recomputed) so
      "how often is possible_bias raised" type questions are answered
      from real, already-audited numbers rather than the model's own
      arithmetic over raw text.

    - services.anonymizer.anonymize() -- the SAME anonymization
      boundary used everywhere else before any document content
      reaches Claude (reflection_service.py, qdrant_service.py). Every
      retrieved excerpt is anonymized again here (defense in depth: the
      Qdrant-indexed content was anonymized at index time already, but
      this module never assumes that and anonymizes independently
      before it ever gets included in a prompt).

Grounding, not general knowledge
------------------------------------
The assistant must answer ONLY from retrieved evidence and the
aggregate counts above -- never from the model's general/background
knowledge about social work, bias, or anything else. The system prompt
below is explicit about this, and about the three failure modes the
product requirements are most concerned with:
    1. Inventing a precise number the evidence can't actually support.
    2. Stating "practitioners are biased" as a fact rather than
       surfacing a pattern that may be worth reflecting on.
    3. Answering a question the evidence genuinely cannot answer (e.g.
       "which intervention had the best outcomes" when no outcome data
       is indexed) as if it could.

Cost note (flagged per project standing rules)
--------------------------------------------------
Each question asked here is exactly ONE Claude API call (no fan-out,
unlike the 8-companion Reflection orchestrator). Using
claude-sonnet-5 at standard current per-token pricing (~$3 / MTok
input, ~$15 / MTok output as of this writing -- Anthropic's published
pricing should always be checked for the current rate), a typical
question with up to 8 retrieved evidence excerpts plus the aggregate
summary runs roughly 4,000-6,000 input tokens and up to ~700 output
tokens, i.e. roughly $0.02-0.03 per question. This is NEW spend, is
used entirely at manager/supervisor discretion, and is NOT part of the
70-100 reflections/month practitioner volume the rest of the app's
cost projections are based on -- see the accompanying handoff notes
for how this scales with actual Knowledge Assistant usage.
"""

import json
import anthropic

from config import ANTHROPIC_API_KEY
from services.anonymizer import anonymize
from rdi.retrieval_service import retrieve_global_context
from services.research_metrics_SERVICE import build_research_summary

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

DEFAULT_EVIDENCE_LIMIT = 8
DEFAULT_WINDOW_DAYS = 365
MAX_EXCERPT_CHARS = 500

LANG_INSTRUCTIONS = {
    "Español": "Responde completamente en español.",
    "Euskera": "Erantzun osorik euskaraz.",
    "English": "Respond entirely in English.",
}

SYSTEM_PROMPT = """You are an organisational learning assistant for a social work \
documentation and reflection platform (RDI-SW). You help Supervisors and \
Programme Managers understand patterns across the organisation's \
reflective practice data.

You will be given two kinds of grounding material:
1. RETRIEVED EVIDENCE -- short, anonymized excerpts from real documentation \
and reflections, each with metadata (document type, approximate date, \
case/service reference, semantic relevance).
2. AGGREGATE STATISTICS -- organisation-wide counts already computed \
elsewhere in the system (how often each of the 8 reflective dimensions \
was flagged by the AI or explored by a professional, total reflection \
sessions, total completed documents, feedback ratings).

Hard rules, no exceptions:
- Answer ONLY from the RETRIEVED EVIDENCE and AGGREGATE STATISTICS you are \
given. Never use outside/general knowledge about social work, statistics, \
or this organisation. If the evidence doesn't cover something, say so \
plainly instead of guessing or filling the gap with plausible-sounding \
general knowledge.
- NEVER invent or estimate a number (a count, a percentage, a date range) \
that isn't directly supported by the evidence or statistics you were \
given. If a precise count isn't possible from what's available, say so \
explicitly and, where you can, give the most honest approximate framing \
instead (e.g. "at least N records", "based on the M documents retrieved").
- NEVER state that bias, poor practice, or any individual/team failing is \
a proven fact. You may describe a RECURRING PATTERN in the evidence (e.g. \
deficit-focused language, a particular kind of assumption appearing more \
than once) and note that it MAY be worth professional reflection -- but \
you must not conclude that bias or a mistake definitely occurred. You are \
surfacing patterns for a human's judgement, not issuing a verdict.
- Distinguish clearly between: (a) descriptive questions asking for a \
count or fact, (b) analytical questions asking about patterns or trends, \
(c) reflective/bias-related questions, and (d) questions the available \
evidence genuinely cannot answer (e.g. asking about client outcomes when \
no outcome data was retrieved) -- for (d), say plainly that the available \
data is insufficient to answer, rather than answering anyway.
- Never reveal a client/case's identifying details beyond the case or \
service reference already present in the evidence given to you -- you are \
already working from anonymized excerpts; do not attempt to reconstruct \
or guess identity.
- Keep your answer focused and readable: a few short paragraphs, not a \
long report. Do not restate the entire evidence you were given -- the \
evidence is already shown to the reader separately.

At the very end of your answer, on their own lines, add:
CONFIDENCE: one of strong | limited | insufficient
LIMITATIONS: one short sentence in the same language as your answer, \
explaining what would make the evidence stronger (e.g. "based on only 4 \
retrieved documents", "no outcome data is indexed in this system"). If \
there are no meaningful limitations, write "None noted."
"""


def _build_evidence_block(docs):
    """Turn retrieve_global_context()'s results into a compact,
    anonymized, numbered evidence list for the prompt -- and a parallel
    structured list for the UI's "Evidence used" panel."""
    evidence_lines = []
    evidence_for_ui = []
    for i, d in enumerate(docs, start=1):
        safe_excerpt = anonymize((d.get("content") or ""))[:MAX_EXCERPT_CHARS]
        date = d.get("completed_at") or d.get("created_at") or ""
        case_ref = d.get("case_ref") or ""
        score = d.get("score")

        evidence_lines.append(
            f"[{i}] doc_type={d.get('doc_type', '')!r} date={date[:10]!r} "
            f"case_ref={case_ref!r} relevance={score if score is not None else 'n/a'}\n"
            f"excerpt: {safe_excerpt}"
        )
        evidence_for_ui.append({
            "index": i,
            "doc_type": d.get("doc_type", ""),
            "date": date[:10],
            "case_ref": case_ref,
            "relevance": score,
        })
    return "\n\n".join(evidence_lines), evidence_for_ui


def _build_stats_block(summary):
    theme_flag = summary["theme_flag_counts"]
    theme_explore = summary["theme_explore_counts"]
    lines = [
        f"Period: last {summary['window_days']} days (since {summary['since']})",
        f"Total reflection sessions generated: {summary['total_reflection_sessions']}",
        f"Total documents completed: {summary['total_documents_completed']}",
        "Theme flagged-by-AI counts: " + ", ".join(f"{k}={theme_flag.get(k, 0)}" for k in theme_flag),
        "Theme explored-by-professional counts: " + ", ".join(f"{k}={theme_explore.get(k, 0)}" for k in theme_explore),
    ]
    fb = summary["feedback"]
    if fb["count"]:
        avg = f"{fb['average']:.1f}/5" if fb["average"] is not None else "n/a"
        lines.append(f"Usefulness feedback: {fb['count']} ratings, average {avg}")
    return "\n".join(lines)


def _parse_confidence_and_limitations(raw_text):
    """
    Pulls the trailing CONFIDENCE: / LIMITATIONS: lines back out of the
    model's plain-text reply and returns (answer_text, confidence,
    limitations). Falls back gracefully (confidence="limited") if the
    model didn't follow the format exactly -- this must never crash the
    page.
    """
    confidence = "limited"
    limitations = ""
    answer_lines = []

    for line in raw_text.splitlines():
        stripped = line.strip()
        if stripped.upper().startswith("CONFIDENCE:"):
            value = stripped.split(":", 1)[1].strip().lower()
            if value in {"strong", "limited", "insufficient"}:
                confidence = value
            continue
        if stripped.upper().startswith("LIMITATIONS:"):
            limitations = stripped.split(":", 1)[1].strip()
            continue
        answer_lines.append(line)

    answer = "\n".join(answer_lines).strip()
    return answer, confidence, limitations


def ask(question, lang="Español", evidence_limit=DEFAULT_EVIDENCE_LIMIT,
        window_days=DEFAULT_WINDOW_DAYS):
    """
    Answer one organisational question, grounded in retrieved evidence
    plus organisation-wide aggregate statistics.

    Returns:
        {
            "answer": str,
            "confidence": "strong" | "limited" | "insufficient",
            "limitations": str,
            "evidence": [ {index, doc_type, date, case_ref, relevance}, ... ],
            "evidence_count": int,
        }
      or, on any failure:
        {"error": "...", "raw": "..."}
    """
    question = (question or "").strip()
    if not question:
        return {"error": "Empty question", "raw": ""}

    docs = retrieve_global_context(query_text=question, limit=evidence_limit)
    evidence_block, evidence_for_ui = _build_evidence_block(docs)

    summary = build_research_summary(window_days=window_days)
    stats_block = _build_stats_block(summary)

    lang_instruction = LANG_INSTRUCTIONS.get(lang, LANG_INSTRUCTIONS["Español"])
    full_system_prompt = SYSTEM_PROMPT + "\n\n" + lang_instruction

    user_content = f"""QUESTION:
{question}

RETRIEVED EVIDENCE ({len(docs)} item(s)):
{evidence_block if evidence_block else "(no relevant documents were retrieved for this question)"}

AGGREGATE STATISTICS:
{stats_block}
"""

    try:
        message = client.messages.create(
            model="claude-sonnet-5",
            max_tokens=900,
            system=full_system_prompt,
            messages=[{"role": "user", "content": user_content}],
        )
    except Exception as e:
        return {"error": "API call failed", "raw": str(e)}

    raw = next((block.text for block in message.content if getattr(block, "type", None) == "text"), "")
    if not raw.strip():
        return {"error": "Empty response", "raw": ""}

    answer, confidence, limitations = _parse_confidence_and_limitations(raw)

    # If nothing was retrieved at all, never let the model's own framing
    # override the honest classification -- there is structurally no
    # evidence to be confident about.
    if not docs:
        confidence = "insufficient"
        if not limitations:
            limitations = {
                "Español": "No se recuperó ningún documento relevante para esta pregunta.",
                "Euskera": "Ez da galdera honentzako dokumentu garrantzitsurik berreskuratu.",
                "English": "No relevant documents were retrieved for this question.",
            }.get(lang, "No relevant documents were retrieved for this question.")

    return {
        "answer": answer,
        "confidence": confidence,
        "limitations": limitations,
        "evidence": evidence_for_ui,
        "evidence_count": len(docs),
    }