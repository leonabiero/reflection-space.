"""
Pattern Explainer
===================

Stage 2 of the pattern explorer (see PATTERNS.md).

Once the pattern engine has grouped similar observations
(services/pattern_engine.py), ONE Claude call per group writes the
explanation a reviewer reads: a title, what the group has in common, why
it may matter for reflective practice, other plausible explanations, the
limits of what can be concluded, and questions for discussion.

What Claude is and is not given
---------------------------------
- It receives ONLY the group's saved observations (already written from
  anonymized text) and the name of the lens each came from. It never
  receives the original documents, the quotations, case references, dates,
  or any author information. That keeps cost small and exposure low.
- It is NOT told the counts, so it cannot be tempted to restate them; the
  counts shown on screen always come from the database, never from the
  model.

What the reply must be
-----------------------
Strict JSON with fixed fields (see validate_explanation). A reply that is
not valid is retried once; if it still fails, the pattern is saved with a
plain, honest fallback explanation (explanation_status = 'fallback') and
the reviewer can retry it from the page. A pattern is never lost, and
never shown with made-up text, because the explanation failed.

The prompt is versioned (PATTERN_PROMPT_VERSION) and saved with every
generation so results from different wordings can be compared later.
"""

import json
import time

from services.db_time import get_logger
from services import reflection_service
from services.reflection_service import LANG_INSTRUCTIONS

logger = get_logger(__name__)

PATTERN_PROMPT_VERSION = "2026-10-patterns-1"

# How many of a group's observations are shown to the model (the ones
# closest to the group's centre -- chosen by the caller).
MAX_OBSERVATIONS_SENT = 12

MAX_ATTEMPTS = 2

# (min items, max items, max characters per item) for list fields.
_LIMITS = {
    "title": 140,
    "description": 900,
    "why_it_matters": 600,
    "alternative_explanations": (1, 4, 350),
    "limitations": (1, 4, 350),
    "questions": (2, 4, 300),
}

SYSTEM_PROMPT = """You help a management team in a social-intervention organisation reflect on recurring themes in how professional documentation is written.

You will receive several short observations. Each was produced by a reflection tool that read a different professional's written documentation (names already removed) and is tagged with the reflection lens it came from. They have been grouped because their meaning is similar.

Write a cautious explanation of this group as a CANDIDATE PATTERN FOR REFLECTION. Follow these rules exactly:
- Use only what is in the observations. Never invent events, quotations, people, dates, numbers or history.
- Do not state how many observations, documents or cases there are, and do not claim anything about how common this is across the organisation.
- Do not diagnose, classify, score or rank any person or any professional. Do not infer anyone's intentions, motives or protected characteristics.
- A recurring theme is NOT proof of bias, and possible bias is NOT proof of discriminatory practice. Never say that bias, discrimination, or poor practice has been shown. Use wording such as "candidate pattern", "recurring theme", "possible interpretation", "may".
- Offer other plausible explanations that fit the same observations, without inventing facts. Say plainly what cannot be established from observations alone.
- Questions must be open, non-accusatory, specific to this group, and invite discussion rather than steer toward a conclusion.
- Use respectful, plain language. Do not give recommendations, action plans, or instructions.

Return ONLY valid JSON with exactly these keys and no text before or after:
{
  "title": "short descriptive title (under 100 characters)",
  "description": "2-4 sentences: what the observations have in common",
  "why_it_matters": "1-3 sentences: why this may matter for reflective practice",
  "alternative_explanations": ["1-3 other plausible explanations"],
  "limitations": ["1-3 things that cannot be established from this"],
  "questions": ["2-3 open questions for an individual or a team"]
}"""

_FALLBACK_TEXT = {
    "Español": {
        "title": "Observaciones similares ({lenses})",
        "description": "Estas observaciones se agruparon por la similitud de su significado. La explicación automática no pudo generarse en este momento; revisa las observaciones y sus citas exactas para valorar si comparten algo relevante.",
        "why_it_matters": "Una agrupación solo indica que unas observaciones se parecen. Corresponde al equipo decidir si merece atención.",
        "alternative_explanations": ["Las observaciones pueden parecerse por la forma en que se redactan las notas o por el tipo de caso, y no por una cuestión de práctica."],
        "limitations": ["Se trata de un agrupamiento automático de un conjunto pequeño y no representativo de observaciones compartidas voluntariamente; no permite concluir nada sobre la organización."],
        "questions": [
            "¿Qué tienen en común, realmente, estas observaciones cuando se leen con sus citas?",
            "¿Qué información adicional cambiaría la forma de entender este grupo?",
        ],
    },
    "English": {
        "title": "Similar observations ({lenses})",
        "description": "These observations were grouped because their meaning is similar. The automatic explanation could not be generated just now; please read the observations and their exact quotations to judge whether they share something relevant.",
        "why_it_matters": "A grouping only shows that some observations resemble each other. It is for the team to decide whether it deserves attention.",
        "alternative_explanations": ["The observations may resemble each other because of how notes are written or the kind of case, rather than because of a practice issue."],
        "limitations": ["This is an automatic grouping of a small, non-representative set of voluntarily shared observations; it cannot support conclusions about the organisation."],
        "questions": [
            "What do these observations really have in common when read alongside their quotations?",
            "What further information would change how this group is understood?",
        ],
    },
    "Euskera": {
        "title": "Antzeko behaketak ({lenses})",
        "description": "Behaketa hauek euren esanahiaren antzagatik multzokatu dira. Azalpen automatikoa ezin izan da sortu une honetan; irakurri behaketak eta haien aipu zehatzak, partekatzen duten zerbait garrantzitsua dagoen baloratzeko.",
        "why_it_matters": "Multzokatze batek behaketa batzuk elkarren antzekoak direla soilik adierazten du. Taldeari dagokio erabakitzea arreta merezi duen.",
        "alternative_explanations": ["Behaketak elkarren antzekoak izan daitezke oharrak idazteko moduagatik edo kasu motagatik, eta ez jardunaren inguruko arazo bategatik."],
        "limitations": ["Borondatez partekatutako behaketa-sorta txiki eta ez-adierazgarri baten multzokatze automatikoa da; ezin da erakundeari buruzko ondoriorik atera."],
        "questions": [
            "Zer dute benetan komunean behaketa hauek aipuekin batera irakurrita?",
            "Zer informazio gehigarrik aldatuko luke multzo hau ulertzeko modua?",
        ],
    },
}


def fallback_explanation(lang, lens_labels):
    """The honest plain explanation used when the AI one could not be
    produced. Contains no claims beyond 'these were grouped by similarity'."""
    text = _FALLBACK_TEXT.get(lang, _FALLBACK_TEXT["Español"])
    lenses = ", ".join(lens_labels[:3]) if lens_labels else "—"
    return {
        "title": text["title"].format(lenses=lenses)[:_LIMITS["title"]],
        "description": text["description"],
        "why_it_matters": text["why_it_matters"],
        "alternative_explanations": list(text["alternative_explanations"]),
        "limitations": list(text["limitations"]),
        "questions": list(text["questions"]),
    }


def _clean_string(value, max_chars):
    if not isinstance(value, str):
        return None
    value = value.strip()
    if not value or len(value) > max_chars:
        return None
    return value


def _clean_list(value, minimum, maximum, max_chars):
    if not isinstance(value, list):
        return None
    items = [_clean_string(v, max_chars) for v in value]
    if any(i is None for i in items):
        return None
    if not (minimum <= len(items) <= maximum):
        return None
    return items


def validate_explanation(obj):
    """Return a cleaned explanation dict, or None if `obj` does not match
    the required shape and limits exactly. Extra keys are ignored; missing
    keys, wrong types, empty or over-long text all make it invalid."""
    if not isinstance(obj, dict):
        return None
    title = _clean_string(obj.get("title"), _LIMITS["title"])
    description = _clean_string(obj.get("description"), _LIMITS["description"])
    why = _clean_string(obj.get("why_it_matters"), _LIMITS["why_it_matters"])
    alternatives = _clean_list(obj.get("alternative_explanations"), *_LIMITS["alternative_explanations"])
    limitations = _clean_list(obj.get("limitations"), *_LIMITS["limitations"])
    questions = _clean_list(obj.get("questions"), *_LIMITS["questions"])
    if None in (title, description, why, alternatives, limitations, questions):
        return None
    return {
        "title": title, "description": description, "why_it_matters": why,
        "alternative_explanations": alternatives, "limitations": limitations,
        "questions": questions,
    }


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


def build_user_message(observations, lens_labels_by_key):
    """The text sent as the user turn: lens name + observation, one per
    line. Nothing else about the observations is included."""
    lines = []
    for item in observations[:MAX_OBSERVATIONS_SENT]:
        lens = lens_labels_by_key.get(item["module"], item["module"])
        text = " ".join((item.get("observation") or "").split())
        lines.append(f"- [{lens}] {text}")
    return "OBSERVATIONS:\n" + "\n".join(lines) + "\n\nReturn the JSON now."


def explain_pattern(observations, lens_labels_by_key, lang="Español"):
    """
    Explain one group of observations.

    `observations`: list of {"module", "observation"} dicts (the caller
    has already chosen the most representative few).
    `lens_labels_by_key`: {lens key: readable name}.
    `lang`: "Español" | "Euskera" | "English" -- language of the answer.

    Returns {"explanation": {...}, "status": "ai"} on success, or
    {"explanation": <fallback>, "status": "fallback"} if the model
    could not be reached or kept returning invalid output. Never raises.
    """
    labels = [lens_labels_by_key.get(o["module"], o["module"]) for o in observations]
    unique_labels = list(dict.fromkeys(labels))

    system = SYSTEM_PROMPT + "\n\n" + LANG_INSTRUCTIONS.get(lang, LANG_INSTRUCTIONS["Español"])
    user = build_user_message(observations, lens_labels_by_key)

    for attempt in range(1, MAX_ATTEMPTS + 1):
        started = time.monotonic()
        try:
            message = reflection_service.client.messages.create(
                model=reflection_service.COMPANION_MODEL,
                max_tokens=1100,
                system=system,
                messages=[{"role": "user", "content": user}],
            )
        except Exception as exc:
            reflection_service._record_claude_usage(
                "pattern_explanation", started, success=False,
                error_type=type(exc).__name__,
            )
            logger.warning("pattern explanation call failed (attempt %d): %s",
                           attempt, type(exc).__name__)
            continue

        reflection_service._record_claude_usage("pattern_explanation", started, message=message)
        raw = next((b.text for b in message.content if getattr(b, "type", None) == "text"), "")
        explanation = validate_explanation(_parse_json(raw))
        if explanation is not None:
            return {"explanation": explanation, "status": "ai"}
        logger.warning("pattern explanation reply was not valid (attempt %d)", attempt)

    return {"explanation": fallback_explanation(lang, unique_labels), "status": "fallback"}
