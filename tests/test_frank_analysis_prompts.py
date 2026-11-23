"""
Direct, grounded analysis (November 2026, EDE project team, approved by
the project leads).

The AI's instructions changed from "gentle questions only" to a frank,
grounded analysis that clearly names biases -- while still never judging
the professional, never describing who the supported person "is", and
never giving case decisions, action plans or suggested rewording. These
tests protect that wording in every live prompt: the eight lenses, the
"Explore with the companion" chat, the analysis report, Pattern Review,
and the old single-call prompt kept as a rollback.
"""

import re
import unittest
from pathlib import Path

from rdi.companions import COMPANIONS
from rdi.companions import prompt_builder as pb
from services import pattern_text_analysis as pta

ROOT = Path(__file__).resolve().parents[1]

# Everything EDE asked to remove so the AI is not softened or conditioned.
REMOVED = (
    "NOT to evaluate",
    "Favour reflective questions over direct conclusions",
    "warm invitation",
    "over coffee",
    "soften it until",
    "Is this a question rather than a conclusion",
    '"Could..."',
    '"How..."',
    '"In what ways..."',
    '"What alternative explanations..."',
    "Instead of",
    "You didn't mention their strengths",
    "Do not say something is wrong",
    "Do not label bias as a fact",
    "Do not include a summary",
    "1-3",
    "Focus specifically on",
    "gently",
)

FRAMEWORK_LINES = (
    "EDE framework for reflective practice analysis (no intervention is neutral)",
    "(1) Axes of oppression and social context",
    "(2) Implicit value system",
    "(3) Institutional structures and dynamics",
    "(4) Key intervention concepts understood differently by each professional",
    "(5) Language, categories and construction of reality",
    '"fácil de controlar"',
    "Use it as your checklist when assessing the text",
)


def _all_live_prompts():
    prompts = {}
    for c in COMPANIONS:
        prompts[f"lens:{c['key']}"] = pb.build_companion_prompt(c)
        prompts[f"chat:{c['key']}"] = pb.build_companion_conversation_prompt(c)
    prompts["report"] = pb.build_analysis_report_prompt()
    return prompts


class RoleAndToneTests(unittest.TestCase):
    def test_role_is_to_assess_and_analyse(self):
        for name, prompt in _all_live_prompts().items():
            self.assertIn("Your role is NOT to judge or criticise, but it IS to assess and analyse.",
                          prompt, name)

    def test_frank_tone_and_limits_kept(self):
        for name, prompt in _all_live_prompts().items():
            self.assertIn("Be direct and frank", prompt, name)
            self.assertIn("do not soften your findings", prompt, name)
            self.assertIn("never the person receiving support", prompt, name)
            self.assertIn("action plan", prompt, name)
            self.assertIn("suggested wording", prompt, name)

    def test_softening_and_example_questions_are_gone(self):
        for name, prompt in _all_live_prompts().items():
            for phrase in REMOVED:
                self.assertNotIn(phrase, prompt, f"{phrase!r} still in {name}")

    def test_issue_examples_without_example_questions(self):
        self.assertIn("As well as identifying and pointing out the issue", pb.SHARED_FRAME)
        for issue in ("The client's voice is missing", "Your claim lacks evidence",
                      "This is a stereotype", "The report focuses mainly on deficits"):
            self.assertIn(issue, pb.SHARED_FRAME)
        self.assertIn("ask in a way that invites reflection.", pb.SHARED_FRAME)
        self.assertNotIn("?", pb.SHARED_FRAME.split("ask in a way that invites reflection.")[0]
                         .split("As well as identifying")[1])

    def test_self_check_has_two_rules(self):
        self.assertIn("1. Do NOT soften; speak frankly and directly.", pb.SELF_CHECK)
        self.assertIn("2. Does the analysis describe the documentation", pb.SELF_CHECK)
        self.assertNotIn("3.", pb.SELF_CHECK)

    def test_framework_is_the_checklist_everywhere(self):
        prompts = _all_live_prompts()
        prompts["pattern step 1"] = pta.BATCH_SYSTEM_PROMPT
        prompts["pattern step 2"] = pta.REPORT_SYSTEM_PROMPT
        for name, prompt in prompts.items():
            for line in FRAMEWORK_LINES:
                self.assertIn(line, prompt, f"{line!r} missing from {name}")


class LensOutputTests(unittest.TestCase):
    def test_each_lens_focuses_mainly_and_may_stay_empty(self):
        for c in COMPANIONS:
            prompt = pb.build_companion_prompt(c)
            self.assertIn("Focus mainly on this aspect", prompt)
            self.assertIn("do not invent something just to fill the section", prompt)

    def test_grounded_analysis_one_or_two_questions_typed_quotes(self):
        prompt = pb.build_companion_prompt(COMPANIONS[0])
        self.assertIn("grounded analysis", prompt)
        self.assertIn("2 to 4 sentences", prompt)
        self.assertIn("1 or 2 questions", prompt)
        self.assertIn('"type"', prompt)
        for kind in pb.EVIDENCE_TYPES:
            self.assertIn(f'"{kind}"', prompt)
        # Exact-quote rules unchanged.
        self.assertIn("EXACTLY", prompt)
        self.assertIn("never invent", prompt.lower())
        self.assertIn("about 30 words", prompt)
        self.assertIn("language of the document", prompt)
        # The JSON keys the rest of the app reads are unchanged.
        for key in ('"observation"', '"evidence"', '"questions"'):
            self.assertIn(key, prompt)

    def test_version_was_bumped(self):
        self.assertEqual(pb.PROMPT_VERSION, "2026-11-frank-analysis-1")
        self.assertEqual(pta.PROMPT_VERSION, "2026-11-text-patterns-3")


class ChatTests(unittest.TestCase):
    def test_chat_rules(self):
        prompt = pb.build_companion_conversation_prompt(COMPANIONS[3])
        self.assertIn("Keep each reply short: 1-4 sentences.", prompt)
        self.assertIn("Ask at most one question per reply.", prompt)
        self.assertIn("Never provide a case decision", prompt)
        self.assertIn("accept that as a valid perspective", prompt)
        self.assertIn("do not soften what you see", prompt)
        self.assertNotIn("Never conclude the conversation with a verdict", prompt)


class ReportPromptTests(unittest.TestCase):
    def test_report_asks_for_the_agreed_shape(self):
        prompt = pb.build_analysis_report_prompt()
        for key in ('"summary"', '"items"', '"type"', '"area"', '"quote"', '"why"', '"questions"'):
            self.assertIn(key, prompt)
        self.assertIn("1 or 2 overall questions", prompt)
        self.assertIn("Never invent quotations", prompt)


class PatternReviewTests(unittest.TestCase):
    def test_repeated_bias_sentence_and_frank_tone(self):
        for prompt in (pta.BATCH_SYSTEM_PROMPT, pta.REPORT_SYSTEM_PROMPT):
            self.assertIn("When the same bias is repeated, it creates a pattern.", prompt)
            self.assertIn("Be direct and frank", prompt)
            self.assertNotIn("Use cautious wording", prompt)
            self.assertNotIn("A pattern is not proof of bias", prompt)
            self.assertIn("never the writers", prompt)

    def test_privacy_rules_and_limitations_kept(self):
        self.assertIn("Never quote or copy sentences from the texts", pta.BATCH_SYSTEM_PROMPT)
        self.assertIn('"limitations" must always be present', pta.REPORT_SYSTEM_PROMPT)
        self.assertIn('"limitations"', pta.REPORT_SYSTEM_PROMPT)
        # .format() still works (no stray braces from the framework).
        pta.BATCH_SYSTEM_PROMPT.format(minimum=3, max_patterns=8)
        pta.REPORT_SYSTEM_PROMPT.format(max_questions=4, max_patterns=10)


class RollbackPromptTests(unittest.TestCase):
    def test_legacy_prompt_is_kept_in_step(self):
        legacy = (ROOT / "reflection_prompt.txt").read_text(encoding="utf-8")
        self.assertIn("Your role is NOT to judge or criticise, but it IS to assess and analyse.", legacy)
        self.assertIn("1. Do NOT soften; speak frankly and directly.", legacy)
        for phrase in ("NOT to evaluate", "warm invitation", '"Could..."', "Instead of", "1-3"):
            self.assertNotIn(phrase, legacy)
        for line in FRAMEWORK_LINES[:6]:
            self.assertIn(line, legacy)


class ReplyRoomTests(unittest.TestCase):
    def test_reply_ceilings(self):
        import inspect
        from services import reflection_service as rs
        self.assertIn("max_tokens=2000", inspect.getsource(rs._call_companion_model))
        self.assertEqual(rs.ANALYSIS_REPORT_MAX_TOKENS, 6000)
        self.assertIn("max_tokens=400", inspect.getsource(rs.continue_companion_conversation))
        self.assertTrue(re.search(r"max_tokens=ANALYSIS_REPORT_MAX_TOKENS",
                                  inspect.getsource(rs.generate_analysis_report)))


if __name__ == "__main__":
    unittest.main()
