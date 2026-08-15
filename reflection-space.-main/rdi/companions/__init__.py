"""
Reflection Companions
=======================

Each companion focuses on exactly one of the 8 reflection dimensions your
prompt has always used. The focus questions below are taken directly from
reflection_prompt.txt's numbered list -- nothing new was invented here,
this just breaks the existing 8 dimensions into 8 independently-callable
units.

Order matters: it's preserved through the orchestrator and used to build
the raw dict handed to services.reflection_log.log_reflection(), which
expects these exact keys.
"""

COMPANIONS = [
    {
        "key": "client_voice",
        "label": "Client's Voice",
        "focus": (
            "Is the person's own voice, goals, and preferences reflected in "
            "the text, or does the narrative come mostly from the "
            "professional's perspective?"
        ),
    },
    {
        "key": "observation_vs_interpretation",
        "label": "Observation vs Interpretation",
        "focus": (
            "Are statements presented as directly observed facts, or are "
            "some actually professional interpretations, assumptions, or "
            "opinions written as if they were facts?"
        ),
    },
    {
        "key": "labels_and_language",
        "label": "Labels & Language",
        "focus": (
            "Are there labels or charged terms (for example 'conflictive,' "
            "'disengaged,' 'dysfunctional family') that could quietly steer "
            "how this person or family is perceived?"
        ),
    },
    {
        "key": "possible_bias",
        "label": "Possible Bias",
        "focus": (
            "Are there possible stereotypes or unexamined assumptions "
            "connected to origin, gender, age, migration status, mental "
            "health, substance use, or other personal circumstances?"
        ),
    },
    {
        "key": "evidence_for_decisions",
        "label": "Evidence for Decisions",
        "focus": (
            "Are the intervention decisions described in the text clearly "
            "supported by evidence, or do they appear to rely on implicit "
            "assumptions?"
        ),
    },
    {
        "key": "missing_information",
        "label": "Missing Information",
        "focus": (
            "Is there information that seems relevant but is absent from "
            "the documentation, and whose absence could affect how the "
            "situation is understood?"
        ),
    },
    {
        "key": "strengths_and_deficits",
        "label": "Strengths vs Deficits",
        "focus": (
            "Does the language focus mainly on problems, limitations, or "
            "deficits, while overlooking the person's strengths, "
            "abilities, and resources?"
        ),
    },
    {
        "key": "continuity",
        "label": "Continuity",
        "focus": (
            "Are there contradictions, shifts, or notable changes across "
            "the document(s) compared to what came before?"
        ),
    },
]

COMPANION_KEYS = [c["key"] for c in COMPANIONS]