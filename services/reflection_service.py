import anthropic
import json
import traceback
from config import ANTHROPIC_API_KEY, SIMULATE_RATE_LIMIT_ERROR, CLAUDE_REQUEST_TIMEOUT_SECONDS
from services.anonymizer import anonymize
from services.error_log import log_error
from rdi.companions.prompt_builder import build_companion_prompt, build_companion_conversation_prompt

# Scalability pass (September pilot hardening): explicit per-call
# timeout instead of the SDK default (several minutes) -- see
# config.py:CLAUDE_REQUEST_TIMEOUT_SECONDS for why. Applies to every
# call made through this client (generate_reflection(),
# generate_companion_reflection(), continue_companion_conversation()).
client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY, timeout=CLAUDE_REQUEST_TIMEOUT_SECONDS)

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

    QA testing hook (Test B -- Rate Limit): if config.SIMULATE_RATE_LIMIT_ERROR
    is on, this raises a fake rate-limit error immediately, before any
    real API call is made -- see config.py for how to enable/disable it.
    """
    if SIMULATE_RATE_LIMIT_ERROR:
        raise Exception(
            "Simulated for testing (Test B): 429 rate_limit_error - "
            "Number of request tokens has exceeded your per-minute rate limit"
        )

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
    used elsewhere so callers can handle both paths identically. When
    the failure is an unexpected exception (the Anthropic API call
    itself failing), the dict also carries "issue_id"/"error_id" --
    the failure is logged via services/error_log.py:log_error() first,
    the same way rdi/orchestrator.py logs a Complete Failure, so the
    page can show the SAME standard "Something went wrong" screen with
    a real reference number instead of a generic, unlogged message.

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

    Sprint 7 -- prompt caching
    --------------------------
    Every turn of a given opportunity's conversation resends the exact
    same system prompt and the exact same "DOCUMENT + original
    observation" context block -- only the conversation history and the
    newest message actually change turn to turn. Those two repeating
    pieces are marked with `cache_control: {"type": "ephemeral"}`, so
    from the 2nd turn onward Anthropic reuses the cached prefix instead
    of reprocessing it, at a fraction of normal input-token cost.

    This changes nothing the professional sees or how the model
    responds -- caching only affects what Anthropic charges to reprocess
    already-seen content, never the content or quality of the reply.

    Two things worth knowing:
    - Cached blocks need to be at least ~1,024 tokens to actually cache
      (Anthropic's minimum for Sonnet-class models). Below that, the
      marker is simply ignored and billing is unaffected -- a short
      case note plus system prompt may not always clear this bar, and
      that's fine, it just means this particular conversation doesn't
      benefit.
    - The cache entry expires after a short idle window (currently ~5
      minutes). A conversation the practitioner returns to after a long
      pause will simply re-cache on its next turn rather than error.
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

    # Cache breakpoint 1: the system prompt. Identical for every turn of
    # every conversation about this companion+language combination.
    system_param = [
        {
            "type": "text",
            "text": full_system_prompt,
            "cache_control": {"type": "ephemeral"},
        }
    ]

    # Cache breakpoint 2: the document + original observation. Identical
    # for every turn of THIS opportunity's conversation. Anthropic caches
    # everything up to and including this block (system + this message),
    # so this is the point where the big, reusable prefix ends.
    messages = [
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": context_block,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
        },
        {"role": "assistant", "content": "Understood -- I'll keep exploring this with them."},
    ]

    # Everything after the cache breakpoint is genuinely new each turn,
    # so it's sent as plain (uncached) messages -- caching it wouldn't
    # help, since it never repeats identically.
    for turn in conversation_history:
        role = "assistant" if turn.get("role") == "ai" else "user"
        messages.append({"role": role, "content": turn.get("content", "")})

    messages.append({"role": "user", "content": professional_message})

    try:
        message = client.messages.create(
            model="claude-sonnet-5",
            max_tokens=400,
            system=system_param,
            messages=messages,
        )
    except Exception as e:
        error_id, issue_id = log_error(
            page="reflection_space (workspace conversation)",
            error_type=type(e).__name__,
            message=str(e),
            traceback_text=traceback.format_exc(),
            context={"companion": companion.get("key")},
            severity="error",
        )
        return {"error": "API call failed", "raw": str(e), "issue_id": issue_id, "error_id": error_id}

    raw = next((block.text for block in message.content if getattr(block, "type", None) == "text"), "")

    if not raw.strip():
        return {"error": "Empty response", "raw": ""}

    # Surface cache stats for visibility (Sprint 10 research metrics can
    # persist these later; for now this is just an observability hook
    # and never affects behavior or the returned reply).
    usage = getattr(message, "usage", None)
    cache_read = getattr(usage, "cache_read_input_tokens", 0) if usage else 0
    cache_created = getattr(usage, "cache_creation_input_tokens", 0) if usage else 0
    if cache_read or cache_created:
        print(f"[prompt cache] companion={companion.get('key')} "
              f"cache_read_input_tokens={cache_read} cache_creation_input_tokens={cache_created}")

    return {"reply": raw.strip()}