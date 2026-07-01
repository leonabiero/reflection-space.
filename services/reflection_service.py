import anthropic
import json
from config import ANTHROPIC_API_KEY

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

LANG_INSTRUCTIONS = {
    "Español": "Responde completamente en español.",
    "Euskera": "Erantzun osorik euskaraz.",
    "English": "Respond entirely in English.",
}


def generate_reflection(text: str, lang: str = "Español"):
    system_prompt = open("reflection_prompt.txt", "r", encoding="utf-8").read()
    lang_instruction = LANG_INSTRUCTIONS.get(lang, LANG_INSTRUCTIONS["Español"])
    full_system_prompt = system_prompt + "\n\n" + lang_instruction

    message = client.messages.create(
        model="claude-sonnet-5",
        max_tokens=1200,
        system=full_system_prompt,
        messages=[
            {
                "role": "user",
                "content": f"""
DOCUMENT:
{text}
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