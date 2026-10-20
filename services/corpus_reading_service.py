"""
Corpus Reading Service
========================

Corpus analysis, Step 2 (see CORPUS.md): reads each text of a collection
through the same eight reflection lenses practitioners use
(rdi/companions), one AI call per lens per text, and keeps only quotes
that really appear in the text (services/evidence.py).

What it is -- and is not
--------------------------
- Each text is read ALONE. The AI is told it sees one document among many
  and must not compare or say how common anything is. Counts across texts
  come from the database, never from the AI.
- "no_finding" means the AI raised nothing for that lens; it never means
  the text was checked and found free of the issue. Counts of "lens raised
  in X of N texts" therefore describe what the AI noticed, not how often
  something happens.
- The text sent is the stored (already name-scrubbed) text, so every
  verified quote is an exact piece of what is stored.

Bounds: one reading job at a time; at most BATCH_SIZE texts per click so a
click never runs for many minutes; each text is saved as soon as its eight
lenses finish, so an interrupted job loses at most the texts in flight and
the next click resumes with the unread ones.

The questions switch: when off, the AI is told not to write questions and
none are stored.
"""

import json
import random
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from config import ANTHROPIC_API_KEY
from rdi.companions import COMPANIONS
from rdi.companions.prompt_builder import SHARED_FRAME, SELF_CHECK
from services import corpus_store, reflection_service
from services.corpus_store import READING_LENSES
from services.db_time import get_logger
from services.evidence import verify_quotes
from services.pattern_access import require_pattern_role
from services.reflection_service import LANG_INSTRUCTIONS, COMPANION_MODEL

logger = get_logger(__name__)

READING_PROMPT_VERSION = "2026-10-corpus-reading-1"

BATCH_SIZE = 10            # texts per click
APPROX_COST_PER_TEXT_USD = 0.05   # shown to the manager before reading; an estimate, not a bill
READ_WORKERS = 8           # AI calls running side by side
MAX_ATTEMPTS = 3
RETRY_BACKOFF_SECONDS = 0.75
MAX_OBSERVATION_CHARS = 900
MAX_QUESTION_CHARS = 300
MAX_QUESTIONS = 3

_FRAME_WITH_QUESTIONS = "generate one reflective observation and 1-3 reflective questions"
_FRAME_WITHOUT_QUESTIONS = "generate one reflective observation"

_CORPUS_NOTE = """
You are reading ONE document that belongs to a large collection of professional documents, each read separately. You only see this one. Do not compare it with other documents, do not say how common anything is, and do not make claims about the organisation.
"""


def _companion_by_key():
    return {c["key"]: c for c in COMPANIONS}


def build_reading_prompt(companion, include_questions=True):
    """System prompt for one lens of one text. Same tone rules as the
    practitioner reflection, one-document framing, optional questions."""
    frame = SHARED_FRAME
    assert _FRAME_WITH_QUESTIONS in frame, "SHARED_FRAME wording changed; update corpus_reading_service"
    if not include_questions:
        frame = frame.replace(_FRAME_WITH_QUESTIONS, _FRAME_WITHOUT_QUESTIONS)
    focus = f"""
Focus specifically on this one aspect of the document:

{companion['label']} -- {companion['focus']}

If this does not clearly apply, or there is nothing notable to raise, leave "observation" as an empty string -- do not invent something just to fill the section.
"""
    if include_questions:
        keys = '{\n  "observation": "",\n  "evidence": [],\n  "questions": []\n}'
        describe = ('The "observation" should describe what is written in the documentation (never the person), '
                    'in one or two neutral sentences. The "questions" should be genuine reflective invitations, '
                    'not conclusions.')
    else:
        keys = '{\n  "observation": "",\n  "evidence": []\n}'
        describe = ('The "observation" should describe what is written in the documentation (never the person), '
                    'in one or two neutral sentences. Do NOT include any questions.')
    output = f"""
Return ONLY valid JSON, with exactly this structure and these exact keys. No text before or after the JSON.

{keys}

{describe}

The "evidence" list holds the passage(s) of the DOCUMENT that your observation is based on:
- Include 1 or 2 short passages (at most about 30 words each), each copied EXACTLY, word for word, from the DOCUMENT, as one continuous excerpt.
- Never paraphrase, correct, shorten with "...", combine separate sentences, or translate a passage. Keep it in the language of the document even if you write the rest of your answer in another language.
- If your observation is about something that is NOT in the text (for example, missing information), or you cannot point to an exact passage, leave "evidence" as an empty list -- never invent or approximate a quotation.

Do not include a summary, a recommendation, an action plan, or suggested wording anywhere in your response.
"""
    return frame + focus + SELF_CHECK + _CORPUS_NOTE + output


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


def interpret_reply(obj, source_text, include_questions):
    """Turn the model's parsed JSON into a reading dict, or None if it does
    not have the required shape. Quotes are verified against `source_text`;
    unverifiable ones are dropped and counted."""
    if not isinstance(obj, dict):
        return None
    observation = obj.get("observation")
    if not isinstance(observation, str) or len(observation.strip()) > MAX_OBSERVATION_CHARS:
        return None
    observation = observation.strip()
    questions = []
    if include_questions:
        raw_questions = obj.get("questions", [])
        if not isinstance(raw_questions, list):
            return None
        for q in raw_questions:
            if not isinstance(q, str) or len(q.strip()) > MAX_QUESTION_CHARS:
                return None
            if q.strip():
                questions.append(q.strip())
        questions = questions[:MAX_QUESTIONS]
    if not observation:
        return {"status": "no_finding", "observation": "", "questions": [],
                "evidence": [], "unverified_count": 0}
    evidence, unverified = verify_quotes(obj.get("evidence", []), source_text)
    return {"status": "finding", "observation": observation, "questions": questions,
            "evidence": evidence, "unverified_count": unverified}


def read_lens(companion, text, lang, include_questions):
    """One lens of one text. Retries up to MAX_ATTEMPTS. Returns a reading
    dict (with the lens key) or {"lens", "status": "failed"}. Never raises."""
    system = build_reading_prompt(companion, include_questions) + "\n\n" + LANG_INSTRUCTIONS.get(
        lang, LANG_INSTRUCTIONS["Español"])
    user = f"\nDOCUMENT:\n{text}\nReturn structured reflection JSON only.\n"
    for attempt in range(1, MAX_ATTEMPTS + 1):
        started = time.monotonic()
        try:
            message = reflection_service.client.messages.create(
                model=COMPANION_MODEL, max_tokens=1280, system=system,
                messages=[{"role": "user", "content": user}],
            )
        except Exception as exc:
            reflection_service._record_claude_usage(
                "corpus_reading", started, success=False,
                error_type=type(exc).__name__, companion_key=companion["key"])
            logger.warning("corpus reading call failed (attempt %d): %s", attempt, type(exc).__name__)
        else:
            reflection_service._record_claude_usage(
                "corpus_reading", started, message=message, companion_key=companion["key"])
            raw = next((b.text for b in message.content if getattr(b, "type", None) == "text"), "")
            reading = interpret_reply(_parse_json(raw), text, include_questions)
            if reading is not None:
                reading["lens"] = companion["key"]
                return reading
            logger.warning("corpus reading reply was not valid (attempt %d)", attempt)
        if attempt < MAX_ATTEMPTS:
            time.sleep(RETRY_BACKOFF_SECONDS * attempt + random.uniform(0, 0.4))
    return {"lens": companion["key"], "status": "failed", "observation": "",
            "questions": [], "evidence": [], "unverified_count": 0}


def is_available():
    """True if the AI service is configured."""
    return bool(ANTHROPIC_API_KEY)


def read_texts(role, actor, corpus_id, lang, include_questions=True,
               batch_size=BATCH_SIZE, progress=None):
    """
    Read the next `batch_size` unread texts of a collection.

    `progress(done, total)` is called from the calling thread after each
    text is saved.

    Returns a dict: status ('completed' | 'busy' | 'unavailable' |
    'nothing_to_read'), job_id, documents_read, failed_lenses, remaining
    (texts still unread afterwards). Raises PermissionError for other
    roles; unexpected failures mark the job failed and are re-raised.
    """
    require_pattern_role(role)
    blank = {"job_id": None, "documents_read": 0, "failed_lenses": 0, "remaining": 0}
    if not is_available():
        return {"status": "unavailable", **blank}
    include_questions = bool(include_questions)
    batch_size = max(1, min(int(batch_size), 25))

    documents = corpus_store.get_documents_to_read(role, corpus_id, batch_size)
    if not documents:
        return {"status": "nothing_to_read", **blank}
    job_id = corpus_store.start_reading_job(role, actor, corpus_id, len(documents))
    if job_id is None:
        return {"status": "busy", **blank}

    companions = [_companion_by_key()[k] for k in READING_LENSES]
    done_docs = failed_lenses = 0
    try:
        results = {d["id"]: [] for d in documents}
        by_id = {d["id"]: d for d in documents}
        with ThreadPoolExecutor(max_workers=READ_WORKERS) as pool:
            futures = {pool.submit(read_lens, comp, d["content"], lang, include_questions): d["id"]
                       for d in documents for comp in companions}
            for future in as_completed(futures):
                document_id = futures[future]
                results[document_id].append(future.result())
                if len(results[document_id]) == len(companions):
                    readings = results[document_id]
                    failed_lenses += sum(r["status"] == "failed" for r in readings)
                    for r in readings:
                        r.update(model=COMPANION_MODEL, prompt_version=READING_PROMPT_VERSION,
                                 include_questions=include_questions, language=lang)
                    corpus_store.save_readings(role, document_id, readings)
                    done_docs += 1
                    if progress:
                        progress(done_docs, len(documents))
        corpus_store.finish_reading_job(job_id, "completed", done_docs, failed_lenses)
    except Exception as exc:
        try:
            corpus_store.finish_reading_job(job_id, "failed", done_docs, failed_lenses,
                                            type(exc).__name__)
        except Exception:
            logger.exception("Could not mark reading job %r as failed", job_id)
        raise

    remaining = corpus_store.get_reading_overview(role, corpus_id)["unread"]
    return {"status": "completed", "job_id": job_id, "documents_read": done_docs,
            "failed_lenses": failed_lenses, "remaining": remaining}
