"""
Pattern Review analysis (15 November 2026)
============================================

Product owner's decision (see PATTERNS.md): when a Supervisor or
Programme Manager presses "Identify patterns" and picks a period (3, 6,
9 or 12 months), the AI reads the texts social workers wrote in that
period -- the ORIGINAL texts the app already keeps
(services/pattern_text_store.py), each ANONYMISED again here before the AI
sees it -- and writes ONE report on
the patterns it finds in how cases are written. Managers see the report
only -- never the texts.

How it works
------------
1. The texts are read for the AI (never for the screen), ANONYMISED one
   by one with the same anonymiser as a reflection (services/anonymizer.py)
   -- a text that cannot be anonymised is left out, never sent -- and
   shuffled, so their order says nothing about when or by whom they were
   written.
2. They are split into groups that the AI can read in one go
   (MAX_BATCH_TEXTS texts / MAX_BATCH_CHARS characters). Each group is
   read by one Claude call, which lists the recurring patterns and the
   NUMBERS of the texts in that group where each appears. Up to
   PARALLEL_CALLS groups are read at the same time.
3. One last Claude call combines the groups' findings into the final
   report. The number of texts behind each pattern is then COUNTED by
   this code from those text numbers (never estimated by the AI).
4. A pattern seen in fewer than config.PATTERN_MIN_TEXTS_PER_PATTERN
   texts is left out, so a "pattern" can never be one person's single
   text. Nothing runs with fewer than config.PATTERN_MIN_TEXTS texts.
5. Privacy check: any part of the report that repeats a run of
   COPY_CHECK_WORDS or more consecutive words from a text is removed, so
   a manager can never read a text through the report.

What the AI is and is not given
---------------------------------
Only the texts after anonymisation (and, for the last step, the groups'
own findings). The original texts never leave the database unprotected. Never a date, a reflection code, a language label tied to a
text, or anything about the author.

Cost (Claude Sonnet 5.5: $2 per million input tokens, $10 per million
output tokens): one call per group of up to 40 texts plus one final call.
With texts of about 2,000 characters, a 12-month report on 1,200 texts
is about 31 calls and roughly $1.50-$3.50; a 3-month report on 250 texts
roughly $0.40-$0.80. Recorded in the Service Cost & Usage Monitor as
"pattern_text_batch" and "pattern_text_report". Nothing is spent until a
manager presses the button.
"""

import json
import random
import re
import time
from concurrent.futures import ThreadPoolExecutor

from services.db_time import get_logger
from services import reflection_service
from services.reflection_service import LANG_INSTRUCTIONS
from services import pattern_text_store
from services.anonymizer import anonymize
from services import request_dedup

logger = get_logger(__name__)

PROMPT_VERSION = "2026-11-text-patterns-1"
BATCH_OPERATION = "pattern_text_batch"
REPORT_OPERATION = "pattern_text_report"

MAX_BATCH_TEXTS = 40
MAX_BATCH_CHARS = 40_000
MAX_TEXT_CHARS_FOR_AI = 8_000
PARALLEL_CALLS = 4
MAX_ATTEMPTS = 2
CALL_TIMEOUT_SECONDS = 180
BUSY_TTL_MINUTES = 15

MAX_PATTERNS_PER_BATCH = 8
MAX_PATTERNS_IN_REPORT = 10
MAX_QUESTIONS = 4
MAX_LIMITATIONS = 5
COPY_CHECK_WORDS = 8

_TITLE_MAX = 150
_FIELD_MAX = 1500
_ITEM_MAX = 400

BATCH_SYSTEM_PROMPT = """You help the management team of a social-intervention organisation in the Basque Country reflect on how professional case documentation is written.

You will receive a numbered set of texts written by social workers about their cases. Names and personal details have already been replaced by tags such as [PERSON] or [LOCATION]. The texts may be in Spanish, Basque or English.

Find patterns in HOW the cases are written that recur across several texts. For example: whether the person's own voice, wishes and goals appear or are missing; interpretations or opinions presented as facts; charged labels; a focus on problems and deficits rather than strengths and resources; decisions or plans without stated reasons; context that is regularly missing; kinds of situations or needs that keep coming up.

Rules you must follow exactly:
- A pattern must appear in at least {minimum} different texts. Give the numbers of the texts where you see it. Leave out anything that appears in fewer texts.
- Describe the writing, never the writers. Do not judge, score or label the professionals or anyone in the cases, and never try to work out who anyone is.
- Never quote or copy sentences from the texts, and never mention details that could point to one particular case or person (tags, places, ages, dates or events specific to one case).
- A pattern is not proof of bias or poor practice. Use cautious wording such as "appears", "may", "in several texts".
- At most {max_patterns} patterns, the most frequent first.

Return ONLY valid JSON, with no text before or after:
{{"patterns": [{{"title": "short title", "description": "two or three sentences", "texts": [1, 4, 7]}}]}}"""

REPORT_SYSTEM_PROMPT = """You help the management team of a social-intervention organisation in the Basque Country reflect on how professional case documentation is written.

Texts written by social workers were read in separate groups. For each group you will receive the candidate patterns found in it, each with an id and the number of texts in which it was seen. Write ONE report for the team.

Rules you must follow exactly:
- Combine candidate patterns that describe the same thing. For every pattern in your report, list in "sources" the ids of ALL the candidate patterns it combines. Use only ids that you were given.
- Use only what the candidate patterns say. Never invent quotations, cases, people, numbers or events.
- Describe the writing, never the writers. Do not judge, score or label professionals or anyone in the cases.
- A pattern is not proof of bias or poor practice. Use cautious wording ("may", "appears", "possible").
- "questions" are open questions the team could discuss (at most {max_questions} per pattern). "limitations" says what cannot be known from this kind of analysis.
- At most {max_patterns} patterns.

Return ONLY valid JSON, with no text before or after:
{{"overview": "a short paragraph (at most 80 words)", "patterns": [{{"title": "short title", "description": "two or three sentences", "why_it_may_matter": "one or two sentences", "questions": ["..."], "sources": ["g1-p1", "g3-p2"]}}], "limitations": ["..."]}}"""


# ---------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------
def _client():
    """The app's Claude client, with a longer time limit: reading a group
    of texts takes longer than one reflection card."""
    client = reflection_service.client
    try:
        return client.with_options(timeout=CALL_TIMEOUT_SECONDS)
    except Exception:
        return client


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


def _clean_str(value, limit):
    if not isinstance(value, str):
        return ""
    return " ".join(value.split())[:limit]


def _clean_list(value, limit_items, limit_chars):
    if not isinstance(value, list):
        return []
    items = [_clean_str(v, limit_chars) for v in value]
    return [v for v in items if v][:limit_items]


def _lang_instruction(lang):
    return LANG_INSTRUCTIONS.get(lang, LANG_INSTRUCTIONS["Español"])


def make_batches(texts, max_texts=MAX_BATCH_TEXTS, max_chars=MAX_BATCH_CHARS):
    """Split the texts (a list of strings) into groups of at most
    `max_texts` texts and about `max_chars` characters. Each text goes in
    exactly one group; a very long text gets a group of its own."""
    batches, current, size = [], [], 0
    for text in texts:
        if current and (len(current) >= max_texts or size + len(text) > max_chars):
            batches.append(current)
            current, size = [], 0
        current.append(text)
        size += len(text)
    if current:
        batches.append(current)
    return batches


def build_batch_message(batch):
    parts = [f"[{i}]\n{text}" for i, text in enumerate(batch, start=1)]
    return "TEXTS:\n\n" + "\n\n".join(parts) + "\n\nReturn the JSON now."


def validate_batch_reply(obj, batch_size):
    """The group's patterns as [{"title", "description", "texts": set of
    1-based numbers}], or None if the reply is not usable. Text numbers
    outside the group are ignored."""
    if not isinstance(obj, dict) or not isinstance(obj.get("patterns"), list):
        return None
    patterns = []
    for item in obj["patterns"][:MAX_PATTERNS_PER_BATCH]:
        if not isinstance(item, dict):
            continue
        title = _clean_str(item.get("title"), _TITLE_MAX)
        description = _clean_str(item.get("description"), _FIELD_MAX)
        numbers = set()
        for n in item.get("texts") or []:
            try:
                n = int(n)
            except (TypeError, ValueError):
                continue
            if 1 <= n <= batch_size:
                numbers.add(n)
        if title and description and numbers:
            patterns.append({"title": title, "description": description, "texts": numbers})
    return patterns


def _call(system, user, max_tokens, operation):
    """One Claude call with up to MAX_ATTEMPTS tries. Returns the parsed
    JSON object, or None. Never raises. Records cost for every attempt."""
    for attempt in range(1, MAX_ATTEMPTS + 1):
        started = time.monotonic()
        try:
            message = _client().messages.create(
                model=reflection_service.COMPANION_MODEL,
                max_tokens=max_tokens,
                system=system,
                messages=[{"role": "user", "content": user}],
            )
        except Exception as exc:
            reflection_service._record_claude_usage(
                operation, started, success=False, error_type=type(exc).__name__,
            )
            logger.warning("%s call failed (attempt %d): %s", operation, attempt, type(exc).__name__)
            continue
        reflection_service._record_claude_usage(operation, started, message=message)
        raw = next((b.text for b in message.content if getattr(b, "type", None) == "text"), "")
        parsed = _parse_json(raw)
        if parsed is not None:
            return parsed
        logger.warning("%s reply was not valid JSON (attempt %d)", operation, attempt)
    return None


def read_batch(batch, lang, min_per_pattern):
    """Read one group. Returns its validated patterns (possibly empty), or
    None if the group could not be read."""
    system = BATCH_SYSTEM_PROMPT.format(
        minimum=min_per_pattern, max_patterns=MAX_PATTERNS_PER_BATCH,
    ) + "\n\n" + _lang_instruction(lang)
    parsed = _call(system, build_batch_message(batch), 2500, BATCH_OPERATION)
    if parsed is None:
        return None
    return validate_batch_reply(parsed, len(batch))


def build_report_message(candidates):
    """candidates: [{"id", "title", "description", "count"}]."""
    lines = [
        f'- id {c["id"]} (seen in {c["count"]} texts): {c["title"]} -- {c["description"]}'
        for c in candidates
    ]
    return "CANDIDATE PATTERNS:\n" + "\n".join(lines) + "\n\nReturn the JSON now."


def validate_report_reply(obj, known_ids):
    """The cleaned report {"overview", "patterns": [{..., "sources": [..]}],
    "limitations"}, or None if unusable. Sources that were not given are
    dropped; a pattern with no valid source is dropped."""
    if not isinstance(obj, dict) or not isinstance(obj.get("patterns"), list):
        return None
    patterns = []
    for item in obj["patterns"][:MAX_PATTERNS_IN_REPORT]:
        if not isinstance(item, dict):
            continue
        sources = [s for s in (item.get("sources") or []) if isinstance(s, str) and s in known_ids]
        pattern = {
            "title": _clean_str(item.get("title"), _TITLE_MAX),
            "description": _clean_str(item.get("description"), _FIELD_MAX),
            "why_it_may_matter": _clean_str(item.get("why_it_may_matter"), _FIELD_MAX),
            "questions": _clean_list(item.get("questions"), MAX_QUESTIONS, _ITEM_MAX),
            "sources": list(dict.fromkeys(sources)),
        }
        if pattern["title"] and pattern["description"] and pattern["sources"]:
            patterns.append(pattern)
    return {
        "overview": _clean_str(obj.get("overview"), _FIELD_MAX),
        "patterns": patterns,
        "limitations": _clean_list(obj.get("limitations"), MAX_LIMITATIONS, _ITEM_MAX),
    }


# ---------------------------------------------------------------------
# Privacy check: no copied passages in the report
# ---------------------------------------------------------------------
_WORD_RE = re.compile(r"\w+", re.UNICODE)


def _words(text):
    return _WORD_RE.findall((text or "").lower())


def _shingles(words, size=COPY_CHECK_WORDS):
    return {tuple(words[i:i + size]) for i in range(len(words) - size + 1)}


def build_copy_index(texts, size=COPY_CHECK_WORDS):
    index = set()
    for text in texts:
        index |= _shingles(_words(text), size)
    return index


def repeats_a_text(value, copy_index, size=COPY_CHECK_WORDS):
    """True if `value` contains `size` or more consecutive words taken
    from any of the texts."""
    if not value or not copy_index:
        return False
    return not _shingles(_words(value), size).isdisjoint(copy_index)


def remove_copied_passages(report, copy_index):
    """Drop every part of the report that repeats a passage from a text:
    a pattern whose title, description or reason does is removed whole;
    a copied question, limitation or overview is removed on its own.
    Returns how many parts were removed."""
    removed = 0
    if repeats_a_text(report.get("overview"), copy_index):
        report["overview"] = ""
        removed += 1
    kept = []
    for pattern in report.get("patterns", []):
        if any(repeats_a_text(pattern.get(k), copy_index)
               for k in ("title", "description", "why_it_may_matter")):
            removed += 1
            continue
        questions = [q for q in pattern.get("questions", []) if not repeats_a_text(q, copy_index)]
        removed += len(pattern.get("questions", [])) - len(questions)
        pattern["questions"] = questions
        kept.append(pattern)
    report["patterns"] = kept
    limitations = [x for x in report.get("limitations", []) if not repeats_a_text(x, copy_index)]
    removed += len(report.get("limitations", [])) - len(limitations)
    report["limitations"] = limitations
    return removed


# ---------------------------------------------------------------------
# The whole analysis
# ---------------------------------------------------------------------
def protect_texts(texts):
    """Anonymise each text before the AI may see it. Returns
    (protected_texts, skipped): a text whose anonymisation fails or leaves
    nothing is skipped -- it is never sent as it was."""
    protected, skipped = [], 0
    for text in texts:
        if not (text or "").strip():
            continue
        try:
            safe = anonymize(text)
        except Exception:
            safe = None
        if (safe or "").strip():
            protected.append(safe.strip())
        else:
            skipped += 1
    return protected, skipped


def analyse_texts(texts, lang="Español", min_per_pattern=None, rng=None, originals=()):
    """
    Run the analysis on a list of text strings that are ALREADY anonymised
    (see protect_texts). `originals`: the texts as written, used only by
    the privacy check that removes copied passages from the report.

    Returns {"report": dict | None, "texts_read": int, "groups": int,
    "groups_failed": int, "removed_for_privacy": int}. The report is None
    if too few groups could be read or the final step failed. Never
    raises. Each pattern in the report gets "texts_count", counted here
    from the text numbers the AI gave, and patterns below
    `min_per_pattern` texts are removed.
    """
    from config import PATTERN_MIN_TEXTS_PER_PATTERN
    if min_per_pattern is None:
        min_per_pattern = PATTERN_MIN_TEXTS_PER_PATTERN
    outcome = {"report": None, "texts_read": 0, "groups": 0,
               "groups_failed": 0, "removed_for_privacy": 0}

    prepared = [t.strip()[:MAX_TEXT_CHARS_FOR_AI] for t in texts if (t or "").strip()]
    if not prepared:
        return outcome
    (rng or random.Random()).shuffle(prepared)
    batches = make_batches(prepared, MAX_BATCH_TEXTS, MAX_BATCH_CHARS)
    outcome["groups"] = len(batches)

    with ThreadPoolExecutor(max_workers=min(PARALLEL_CALLS, len(batches))) as pool:
        results = list(pool.map(lambda b: read_batch(b, lang, min_per_pattern), batches))

    candidates, text_ids = [], {}
    offset = 0
    for g, (batch, patterns) in enumerate(zip(batches, results), start=1):
        if patterns is None:
            outcome["groups_failed"] += 1
        else:
            outcome["texts_read"] += len(batch)
            for p, pattern in enumerate(patterns, start=1):
                pid = f"g{g}-p{p}"
                # Global text numbers, so two candidates from the same group
                # that are merged are not counted twice.
                text_ids[pid] = {offset + n for n in pattern["texts"]}
                candidates.append({"id": pid, "title": pattern["title"],
                                   "description": pattern["description"],
                                   "count": len(pattern["texts"])})
        offset += len(batch)

    # More than half of the texts unread: not a fair picture.
    if outcome["texts_read"] * 2 < len(prepared):
        return outcome

    if candidates:
        system = REPORT_SYSTEM_PROMPT.format(
            max_questions=MAX_QUESTIONS, max_patterns=MAX_PATTERNS_IN_REPORT,
        ) + "\n\n" + _lang_instruction(lang)
        parsed = _call(system, build_report_message(candidates), 4000, REPORT_OPERATION)
        report = validate_report_reply(parsed, set(text_ids)) if parsed is not None else None
        if report is None:
            return outcome
    else:
        # Nothing recurred: an honest, empty report (no extra AI call).
        report = {"overview": "", "patterns": [], "limitations": []}

    for pattern in report["patterns"]:
        covered = set()
        for source in pattern["sources"]:
            covered |= text_ids.get(source, set())
        pattern["texts_count"] = len(covered)
        del pattern["sources"]
    report["patterns"] = sorted(
        (p for p in report["patterns"] if p["texts_count"] >= min_per_pattern),
        key=lambda p: -p["texts_count"],
    )
    outcome["removed_for_privacy"] = remove_copied_passages(
        report, build_copy_index(list(prepared) + [t for t in originals if t]),
    )
    outcome["report"] = report
    return outcome


def run_report(actor_role, actor_name, period_months, lang="Español"):
    """
    What the "Identify patterns" button does. Returns a dict with
    "status": "ok" | "not_enough" | "busy" | "recent" | "failed", plus
    "report_id", "texts_count" (texts in the period), "texts_read",
    "patterns" (how many were reported) and "minimum".

    Raises PermissionError for anyone who may not use Pattern Review.
    """
    from config import PATTERN_MIN_TEXTS
    texts = pattern_text_store.texts_for_period(actor_role, period_months)
    result = {"status": "failed", "report_id": None, "texts_count": len(texts),
              "texts_read": 0, "patterns": 0, "minimum": PATTERN_MIN_TEXTS,
              "texts_skipped": 0}
    if len(texts) < PATTERN_MIN_TEXTS:
        result["status"] = "not_enough"
        return result

    # The same report (same period, same number of texts, same language)
    # is never run twice at once -- e.g. two managers, or two tabs.
    request_id = request_dedup.fingerprint(
        "pattern_text_report", int(period_months), len(texts), lang,
    )
    claim = request_dedup.claim(request_id, "pattern_text_report", ttl_minutes=BUSY_TTL_MINUTES)
    if claim == "in_progress":
        result["status"] = "busy"
        return result
    if claim == "completed":
        result["status"] = "recent"
        return result

    succeeded = False
    try:
        originals = [t["text"] for t in texts]
        protected, skipped = protect_texts(originals)
        result["texts_skipped"] = skipped
        outcome = analyse_texts(protected, lang=lang, originals=originals)
        result["texts_read"] = outcome["texts_read"]
        report = outcome["report"]
        if report is not None:
            report["texts_read"] = outcome["texts_read"]
            report["texts_not_anonymised"] = skipped
            report["groups_failed"] = outcome["groups_failed"]
            report["removed_for_privacy"] = outcome["removed_for_privacy"]
            result["report_id"] = pattern_text_store.save_report(
                actor_role, actor_name, period_months, len(texts), lang, report,
                model=reflection_service.COMPANION_MODEL, prompt_version=PROMPT_VERSION,
            )
            result["patterns"] = len(report["patterns"])
            result["status"] = "ok"
            succeeded = True
    except PermissionError:
        raise
    except Exception:
        logger.exception("Pattern Review report FAILED (no text logged)")
    finally:
        if succeeded:
            request_dedup.complete(request_id)
        else:
            request_dedup.release(request_id)
    logger.info(
        "Pattern Review report: status=%s period=%s texts=%d read=%d patterns=%d",
        result["status"], period_months, result["texts_count"], result["texts_read"], result["patterns"],
    )
    return result
