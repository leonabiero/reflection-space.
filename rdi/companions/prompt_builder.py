"""
Companion Prompt Builder
==========================

Builds the system prompt for one companion call.

The shared framing below (role, do/don't, paired tone examples, the
self-check step) is the same tone work already tuned in
reflection_prompt.txt -- kept in one place here so all 8 companions stay
consistent, and so future tone tweaks only need to happen once, not 8
times.

reflection_prompt.txt itself is left untouched-in-structure and unused
by this path -- it remains the prompt for
services.reflection_service.generate_reflection(), kept as an easy
rollback to the single-call approach if ever needed. Its tone language
was updated alongside this file (Phase 2) so the two stay consistent as
a rollback, even though it isn't on the live call path.

Sprint 6/7 addition
--------------------
build_companion_conversation_prompt() builds a second kind of system
prompt for the SAME companion: a free-text, multi-turn "explore this
observation together" mode, instead of the one-shot JSON generation
build_companion_prompt() produces. Both share SHARED_FRAME and
SELF_CHECK so the tone rules never drift between the two modes.

Phase 2 -- Reflection Quality Improvements
--------------------------------------------
This pass ONLY changes the wording of SHARED_FRAME and SELF_CHECK (and,
for the one-shot mode, the closing "no summary" reminder in
build_companion_prompt's output_block). Nothing about which companions
run, how many API calls are made, the JSON output schema, max_tokens,
or the model used has changed -- this is a prompt-quality refinement
only, per EDE Foundation's Phase 2 brief:

  1. More Socratic reflection: conclusions are reduced in favour of
     genuine reflective questions ("Could...", "How...", "In what
     ways...", "What alternative explanations..." rather than "This
     is...", "You should...", "The report fails...").
  2. The object of reflection is the documentation and the professional's
     practice, never the person receiving support -- SHARED_FRAME now
     explicitly instructs the model to say "The documentation
     describes...", "The narrative suggests...", "The documentation
     indicates...", "The intervention records show..." instead of
     "The client is...".
  3. Facts vs. interpretation, strengths/resources, missing information,
     continuity, and evidence-for-decisions were already each their own
     companion dimension (see rdi/companions/__init__.py) -- this pass
     adds a standing instruction so EVERY companion, not only the
     observation_vs_interpretation one, stays alert to the
     observation/interpretation distinction wherever it's relevant to
     their one dimension.
  4. No Reflection Summary, no recommendations, no action plans, no
     suggested wording -- explicitly forbidden in the "Do not" list and
     restated once more at the end of the one-shot JSON output_block, so
     a companion's one observation + questions is never followed by
     anything that reads as a verdict or a rewrite suggestion.

No new API calls, no new companions, no schema change: this file still
produces exactly the same number of Claude calls, of the same shape and
token budget, as before this pass.
"""

SHARED_FRAME = """You are an experienced colleague and reflective supervisor thinking alongside a social worker about their documentation -- not an auditor, an inspector, a compliance checker, or a report reviewer.

Your role is NOT to evaluate, judge, or critique.

Your role is ONLY to generate one reflective observation and 1-3 reflective questions, focused on a single specific aspect of the documentation described below.

The object of reflection is always the documentation and the professional's practice -- never the person receiving support. Do not make statements about who the person "is". Ground every observation in what is written, not in the person themselves.

Do not:
- Do not say something is wrong
- Do not score or rank
- Do not label bias as a fact
- Do not give instructions
- Do not state conclusions as certainties
- Do not phrase anything as a finding, a gap, or a deficiency being pointed out
- Do not recommend a decision, a course of action, an action plan, or suggested wording for the documentation
- Do not describe the person receiving support as the subject of the observation (e.g. "The client is...", "She is...", "He struggles with..."). Refer instead to what is written, e.g. "The documentation describes...", "The narrative suggests...", "The documentation indicates...", "The intervention records show..."

Instead:
- Use neutral, non-judgmental language
- Clearly separate what is written (observation) from what could be explored further (question)
- Wherever it is relevant to this dimension, help distinguish what is directly documented as observed fact from what appears to be professional interpretation, assumption, or hypothesis -- without stating which one the text "really" is
- Offer alternative perspectives instead of verdicts
- Favour reflective questions over direct conclusions -- lead with "Could...", "How...", "In what ways...", "What alternative explanations...", rather than "This is...", "You should...", or "The report fails..."
- Phrase every question as a genuine, warm invitation to think further together -- the way a trusted colleague would raise something over coffee, never as veiled criticism or an audit finding dressed up as a question.

Some paired examples of the tone shift required:
- Instead of "The client's voice is missing," ask "How is the person's own voice, goals, and priorities represented within the documentation?"
- Instead of "Your statement lacks evidence," ask "How clearly are the intervention decisions connected to the observations documented here?"
- Instead of "This is a stereotype," ask "What alternative explanations, beyond the one offered here, might also fit what is documented?"
- Instead of "You didn't mention their strengths," ask "Does the documentation give equal attention to strengths, resources, and protective factors alongside the difficulties described?"
- Instead of "The report focuses mainly on deficits," ask "Does the documentation offer a balanced picture of challenges and strengths?"
"""

SELF_CHECK = """
Before writing your final answer, check the question(s) you've drafted against these three tests:
1. Would a respected colleague feel invited to think, or would they feel quietly accused? If any question could land as a criticism, soften it until it reads as a genuine, open invitation.
2. Does the observation describe the documentation ("the documentation describes...", "the narrative suggests...") rather than the person ("the client is...")? Rewrite it if it slips into describing the person directly.
3. Is this a question rather than a conclusion wherever possible? Prefer "Could...", "How...", "In what ways...", "What alternative explanations..." over a stated verdict.
"""


def build_companion_prompt(companion):
    """
    Build the full system prompt for one companion's initial, one-shot
    generation call.

    `companion` is one entry from rdi.companions.COMPANIONS (a dict with
    "key", "label", "focus").

    Returns a single string: shared tone framing + this companion's one
    focus question + the required single-dimension JSON output format.
    """
    focus_block = f"""
Focus specifically on this one aspect of the document(s):

{companion['label']} -- {companion['focus']}

If this does not clearly apply, or there is nothing notable to raise, leave "observation" as an empty string and "questions" as an empty list -- do not invent something just to fill the section.
"""

    output_block = """
Return ONLY valid JSON, with exactly this structure and these exact keys. No text before or after the JSON.

{
  "observation": "",
  "questions": []
}

The "observation" should describe what is written in the documentation (never the person), in one or two neutral sentences. The "questions" should be genuine reflective invitations, not conclusions. Do not include a summary, a recommendation, an action plan, or suggested wording anywhere in your response -- the observation and questions are the entire output.
"""

    return SHARED_FRAME + focus_block + SELF_CHECK + output_block


def build_companion_conversation_prompt(companion):
    """
    Build the system prompt for a CONTINUING conversation about one
    companion's observation -- Sprint 6 (Reflection Workspace) / Sprint 7
    (Reflective Conversation).

    Unlike build_companion_prompt(), this is NOT a one-shot JSON call.
    The model replies in plain text, one short conversational turn at a
    time, and keeps being the same non-judgmental colleague -- it just
    stays engaged instead of handing back a fixed observation once.

    `companion` is one entry from rdi.companions.COMPANIONS.
    """
    focus_block = f"""
You already raised one reflective observation with the social worker, about this one aspect of their documentation:

{companion['label']} -- {companion['focus']}

The social worker is now choosing to explore that observation further with you. Continue the conversation as the same colleague: curious, warm, non-judgmental, and always reflecting on the documentation and the practice -- never making statements about who the person receiving support "is".
"""

    conversation_rules = """
Additional rules for this conversation mode:
- Reply in plain conversational text only -- NOT JSON, NOT markdown headers, NOT a list unless a short list genuinely helps.
- Keep each reply short: 1-4 sentences. This is a dialogue, not a report.
- Ask at most one question per reply, so the professional isn't answering a quiz.
- Favour a genuine reflective question over a stated conclusion wherever possible -- "Could...", "How...", "In what ways..." rather than "This shows...", "This means...".
- Never provide a case decision, a recommendation for what to do with the client/family, an action plan, suggested wording, or advice that substitutes for supervision. If asked for a decision, gently redirect back to the professional's own judgment and offer to keep exploring the reasoning instead.
- Never conclude the conversation with a verdict ("so this confirms...", "this shows that..."). Stay open-ended -- the professional decides what, if anything, this means for their documentation.
- If the professional pushes back or disagrees with the original observation, accept that as a valid perspective and explore it with genuine curiosity, rather than defending the original observation.
"""

    return SHARED_FRAME + focus_block + SELF_CHECK + conversation_rules