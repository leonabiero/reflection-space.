import anthropic
import json
from config import ANTHROPIC_API_KEY
from services.anonymizer import anonymize
from rdi.companions.prompt_builder import build_companion_prompt, build_companion_conversation_prompt

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

LANG_INSTRUCTIONS = {
    "Español": "Responde completamente en español.",
    "Euskera": "Erantzun osorik euskaraz.",
    "English": "Respond entirely in English.",
}


def generate_reflection(text: str, lang: str = "Español"):
    # NOTE: kept exactly as-is. This is the original single-call path
    # (all 8 dimensions in one prompt, reflection_prompt.txt). It is no
    # longer called by rdi/orchestrator.py, which now uses
    # generate_companion_reflection() below instead, but this function is
    # left in place as a simple rollback if the companion split ever
    # needs to be reverted.

    # Anonymize before any text leaves the system and reaches the API.
    # This is the single point where all callers are protected, per
    # NFR-019 / NFR-020 (controlled AI data sharing, anonymisation
    # support) in the Technical Operations Documentation.
    safe_text = anonymize(text)

    system_prompt = open("reflection_prompt.txt", "r", encoding="utf-8").read()
    lang_instruction = LANG_INSTRUCTIONS.get(lang, LANG_INSTRUCTIONS["Español"])
    full_system_prompt = system_prompt + "\n\n" + lang_instruction

    message = client.messages.create(
        model="claude-sonnet-5",
        max_tokens=3000,
        system=full_system_prompt,
        messages=[
            {
                "role": "user",
                "content": f"""
DOCUMENT:
{safe_text}
Return structured reflection JSON only.
""",
            }
        ],
    )

    # Safely extracts the text block, ignoring ThinkingBlocks
    raw = next((block.text for block in message.content if getattr(block, "type", None) == "text"), "")

    # Clean markdown backticks if the model wrapped the JSON output
    cleaned_raw = raw.strip()
    if cleaned_raw.startswith("```"):
        lines = cleaned_raw.splitlines()
        if lines[0].startswith("```"):
            lines.pop(0)
        if lines and lines[-1].startswith("```"):
            lines.pop()
        cleaned_raw = "\n".join(lines).strip()

    try:
        return json.loads(cleaned_raw)
    except Exception:
        return {
            "error": "Failed to parse JSON",
            "raw": raw
        }


def generate_companion_reflection(companion: dict, safe_text: str, lang: str = "Español"):
    """
    Generate a reflection for ONE companion (one dimension) only.

    Unlike generate_reflection(), this expects `safe_text` to already be
    anonymized -- the orchestrator anonymizes once and reuses the result
    across all 8 companion calls, rather than repeating that work 8
    times for the same document.

    `companion` is one entry from rdi.companions.COMPANIONS.

    Returns either:
      - {"observation": "...", "questions": [...]}
      - {"error": "...", "raw": "..."}  -- same error shape as
        generate_reflection(), so callers can handle both the same way.
    """
    system_prompt = build_companion_prompt(companion)
    lang_instruction = LANG_INSTRUCTIONS.get(lang, LANG_INSTRUCTIONS["Español"])
    full_system_prompt = system_prompt + "\n\n" + lang_instruction

    message = client.messages.create(
        model="claude-sonnet-5",
        # A single dimension needs far less headroom than all 8 combined.
        max_tokens=600,
        system=full_system_prompt,
        messages=[
            {
                "role": "user",
                "content": f"""
DOCUMENT:
{safe_text}
Return structured reflection JSON only.
""",
            }
        ],
    )

    raw = next((block.text for block in message.content if getattr(block, "type", None) == "text"), "")

    cleaned_raw = raw.strip()
    if cleaned_raw.startswith("```"):
        lines = cleaned_raw.splitlines()
        if lines[0].startswith("```"):
            lines.pop(0)
        if lines and lines[-1].startswith("```"):
            lines.pop()
        cleaned_raw = "\n".join(lines).strip()

    try:
        return json.loads(cleaned_raw)
    except Exception:
        return {
            "error": "Failed to parse JSON",
            "raw": raw
        }


def continue_companion_conversation(companion: dict, safe_text: str, initial_observation: str,
                                     initial_questions, conversation_history, professional_message: str,
                                     lang: str = "Español"):
    """
    Sprint 6/7: continue a free-text reflective conversation for ONE
    companion's opportunity, inside the Reflection Workspace.

    Unlike generate_companion_reflection(), this does NOT ask for JSON.
    It returns plain text -- one short conversational reply -- or an
    error dict on failure, in the same {"error": ..., "raw": ...} shape
    used elsewhere so callers can handle both paths identically.

    Parameters
    ----------
    companion : one entry from rdi.companions.COMPANIONS
    safe_text : the already-anonymized document text (reused from the
        original orchestrator run -- never re-anonymized here, and the
        raw/original document is never seen by this function or the API)
    initial_observation, initial_questions : what this companion raised
        originally, so the model has the full context of what's being
        explored
    conversation_history : list of {"role": "professional"|"ai",
        "content": str} for turns that already happened in this
        opportunity's conversation (NOT including professional_message)
    professional_message : the practitioner's newest message, to be
        answered now
    """
    system_prompt = build_companion_conversation_prompt(companion)
    lang_instruction = LANG_INSTRUCTIONS.get(lang, LANG_INSTRUCTIONS["Español"])
    full_system_prompt = system_prompt + "\n\n" + lang_instruction

    context_block = f"""
DOCUMENT:
{safe_text}

Your original observation was:
{initial_observation}

Your original reflective question(s) were:
{chr(10).join(f"- {q}" for q in (initial_questions or []))}
"""

    messages = [{"role": "user", "content": context_block}]
    messages.append({"role": "assistant", "content": "Understood -- I'll keep exploring this with them."})

    for turn in conversation_history:
        role = "assistant" if turn.get("role") == "ai" else "user"
        messages.append({"role": role, "content": turn.get("content", "")})

    messages.append({"role": "user", "content": professional_message})

    try:
        message = client.messages.create(
            model="claude-sonnet-5",
            max_tokens=400,
            system=full_system_prompt,
            messages=messages,
        )
    except Exception as e:
        return {"error": "API call failed", "raw": str(e)}

    raw = next((block.text for block in message.content if getattr(block, "type", None) == "text"), "")

    if not raw.strip():
        return {"error": "Empty response", "raw": ""}

    return {"reply": raw.strip()}