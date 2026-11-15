"""
Reflection Summary
====================

Reflection History redesign (November 2026, product owner's decision).

Management roles open Reflection History to see, at a glance, what each
reflection was mainly about. Showing all eight observations, their quoted
passages and every question -- the same full reflection the practitioner
already saw -- was too long for that purpose. So each reflection now gets
ONE short paragraph, written by Claude, that can be read in one go. The
full observations and questions stay available underneath, folded away.

What Claude is and is not given
---------------------------------
- ONLY the reflection's saved observations (already written from
  anonymised text) and the name of the lens each came from.
- Never the original text, the anonymised text, the quoted passages,
  the reflection code, dates, or anything about the author.

When it is written
--------------------
- Straight after a new reflection is saved (pages/reflection_space.py),
  best-effort: if it fails, the reflection is unaffected.
- For reflections without a summary (made before this change, or where
  writing it failed), Reflection History offers a "Create summary"
  button that writes it once and keeps it.

The summary is stored on the reflection itself (reflection_runs.summary_text),
so it is erased together with the reflection -- by the author's own
deletion, by a System Administrator, or by "Erase all data".

Cost: one Claude call per reflection, about 1,500 input and 250 output
tokens -- roughly $0.005 at Sonnet 5.5 prices. Recorded in the Service
Cost & Usage Monitor as the operation "reflection_summary".
"""

import json
import time

from services.db_time import get_logger
from services import reflection_service
from services.reflection_service import LANG_INSTRUCTIONS

logger = get_logger(__name__)

SUMMARY_PROMPT_VERSION = "2026-11-summary-1"
USAGE_OPERATION = "reflection_summary"

MAX_OBSERVATIONS_SENT = 8
MAX_SUMMARY_CHARS = 900
MIN_SUMMARY_CHARS = 40
MAX_ATTEMPTS = 2

SYSTEM_PROMPT = """You help supervisors in a social-intervention organisation get a quick overview of one professional's reflection.

You will receive the observations a reflection tool made about ONE piece of professional documentation (names already removed). Each observation is tagged with the reflection lens it came from.

Write ONE short paragraph (2 to 4 sentences, under 90 words) that a supervisor can read in one go, describing the main recurring theme or pattern across these observations. Follow these rules exactly:
- Use only what is in the observations. Never invent events, quotations, people, dates or numbers.
- Describe the documentation and the reflection, never the person: do not diagnose, judge, score or label the professional or anyone in the case, and do not infer intentions or protected characteristics.
- A theme is not proof of bias or poor practice. Use cautious wording such as "the reflection highlights", "may", "possible".
- Plain, respectful language. No recommendations, instructions, lists or headings.

Return ONLY valid JSON, with no text before or after:
{"summary": "the paragraph"}"""


def _parse_json(raw):
    cleaned = (raw or "").strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        if lines and lines[0].startswith("```"):
            lines.pop(0)
        if lines and lines[-1].startswith("```"):
            lines.pop()
        cleaned = "\n".join(lines).strip()
    try:
        return json.loads(cleaned)
    except Exception:
        return None


def validate_summary(obj):
    """The cleaned paragraph, or None if `obj` is not {"summary": text}
    with a sensible length."""
    if not isinstance(obj, dict):
        return None
    text = obj.get("summary")
    if not isinstance(text, str):
        return None
    text = " ".join(text.split())
    if not (MIN_SUMMARY_CHARS <= len(text) <= MAX_SUMMARY_CHARS):
        return None
    return text


def build_user_message(findings, lens_labels_by_key):
    """Lens name + observation, one per line. Nothing else about the
    reflection is included (no quotes, codes, dates or authors)."""
    lines = []
    for item in findings:
        text = " ".join((item.get("observation") or "").split())
        if not text:
            continue
        lens = lens_labels_by_key.get(item.get("module"), item.get("module") or "")
        lines.append(f"- [{lens}] {text}")
        if len(lines) >= MAX_OBSERVATIONS_SENT:
            break
    return "OBSERVATIONS:\n" + "\n".join(lines) + "\n\nReturn the JSON now."


def has_observations(findings):
    return any((f.get("observation") or "").strip() for f in (findings or []))


def write_summary(findings, lens_labels_by_key, lang="Español"):
    """
    Write the summary paragraph for one reflection.

    `findings`: list of dicts with at least "module" and "observation".
    `lens_labels_by_key`: {lens key: readable name}.
    `lang`: "Español" | "Euskera" | "English" -- language of the answer.

    Returns the paragraph, or None if there is nothing to summarise or the
    model could not produce a valid one. Never raises.
    """
    if not has_observations(findings):
        return None
    system = SYSTEM_PROMPT + "\n\n" + LANG_INSTRUCTIONS.get(lang, LANG_INSTRUCTIONS["Español"])
    user = build_user_message(findings, lens_labels_by_key)

    for attempt in range(1, MAX_ATTEMPTS + 1):
        started = time.monotonic()
        try:
            message = reflection_service.client.messages.create(
                model=reflection_service.COMPANION_MODEL,
                max_tokens=400,
                system=system,
                messages=[{"role": "user", "content": user}],
            )
        except Exception as exc:
            reflection_service._record_claude_usage(
                USAGE_OPERATION, started, success=False, error_type=type(exc).__name__,
            )
            logger.warning("reflection summary call failed (attempt %d): %s",
                           attempt, type(exc).__name__)
            continue

        reflection_service._record_claude_usage(USAGE_OPERATION, started, message=message)
        raw = next((b.text for b in message.content if getattr(b, "type", None) == "text"), "")
        summary = validate_summary(_parse_json(raw))
        if summary is not None:
            return summary
        logger.warning("reflection summary reply was not valid (attempt %d)", attempt)
    return None


def create_and_save(run_id, findings, lens_labels_by_key, lang="Español"):
    """Write the summary and store it on the reflection. Returns the
    paragraph, or None if it could not be written or saved. Never raises."""
    if not run_id:
        return None
    summary = write_summary(findings, lens_labels_by_key, lang)
    if not summary:
        return None
    try:
        from services import reflection_records
        if reflection_records.save_summary(run_id, summary):
            return summary
    except Exception:
        logger.exception("saving reflection summary FAILED: run_id=%r", run_id)
    return None
