# Prompt review – internal map

Internal notes for the developers (not for EDE). The Word document `Reflection_Space_Instrucciones_IA_2026-11-23.docx` in this folder was produced for EDE's Prompt team on 23 November 2026. This file maps each numbered instruction in it to where it lives in the code, so the team's edits can be applied accurately.

- **Produced from commit:** `ce4a00b` (branch `main`). Note: the working folder also had uncommitted changes at the time (diagnostic-prompt work in `services/error_log.py`, `pages/admin_sections/ai_diagnostic_centre.py`, the locales, etc.); none of them touch the prompts below.

- **Model for every call:** `claude-sonnet-5-5` (`services/reflection_service.py`: `COMPANION_MODEL`, and the literal in `continue_companion_conversation()`).

- The original English text of every prompt is in Appendix A of the Word document; the Spanish in the main body is a translation for review only. Apply edits to the English source.


## Map: instruction number → code

| # | Name in the Word document | File | Function / constant |
|---|---|---|---|
| 1 | Marco común: papel y tono de la IA | `rdi/companions/prompt_builder.py` | SHARED_FRAME (line 75) |
| 2 | Mirada «Voz de la persona» | `rdi/companions/__init__.py` | COMPANIONS[0] (key "client_voice": "label" and "focus") |
|  |  | `rdi/companions/prompt_builder.py` | build_companion_prompt() -> focus_block (line 128), shared wording around label/focus |
| 3 | Mirada «Hechos vs. Interpretación» | `rdi/companions/__init__.py` | COMPANIONS[1] (key "observation_vs_interpretation": "label" and "focus") |
|  |  | `rdi/companions/prompt_builder.py` | build_companion_prompt() -> focus_block (line 128), shared wording around label/focus |
| 4 | Mirada «Etiquetas y lenguaje» | `rdi/companions/__init__.py` | COMPANIONS[2] (key "labels_and_language": "label" and "focus") |
|  |  | `rdi/companions/prompt_builder.py` | build_companion_prompt() -> focus_block (line 128), shared wording around label/focus |
| 5 | Mirada «Posibles sesgos» | `rdi/companions/__init__.py` | COMPANIONS[3] (key "possible_bias": "label" and "focus") |
|  |  | `rdi/companions/prompt_builder.py` | build_companion_prompt() -> focus_block (line 128), shared wording around label/focus |
| 6 | Mirada «Evidencia de las decisiones» | `rdi/companions/__init__.py` | COMPANIONS[4] (key "evidence_for_decisions": "label" and "focus") |
|  |  | `rdi/companions/prompt_builder.py` | build_companion_prompt() -> focus_block (line 128), shared wording around label/focus |
| 7 | Mirada «Información ausente» | `rdi/companions/__init__.py` | COMPANIONS[5] (key "missing_information": "label" and "focus") |
|  |  | `rdi/companions/prompt_builder.py` | build_companion_prompt() -> focus_block (line 128), shared wording around label/focus |
| 8 | Mirada «Fortalezas vs. Déficits» | `rdi/companions/__init__.py` | COMPANIONS[6] (key "strengths_and_deficits": "label" and "focus") |
|  |  | `rdi/companions/prompt_builder.py` | build_companion_prompt() -> focus_block (line 128), shared wording around label/focus |
| 9 | Mirada «Continuidad» | `rdi/companions/__init__.py` | COMPANIONS[7] (key "continuity": "label" and "focus") |
|  |  | `rdi/companions/prompt_builder.py` | build_companion_prompt() -> focus_block (line 128), shared wording around label/focus |
| 10 | Autocomprobación antes de responder | `rdi/companions/prompt_builder.py` | SELF_CHECK (line 109) |
| 11 | Formato de la respuesta de cada mirada | `rdi/companions/prompt_builder.py` | build_companion_prompt() -> output_block (line 136) |
| 12 | Nota sobre las etiquetas de anonimización | `services/anonymizer.py` | SENSITIVE_LABELS_NOTE (line 927) |
| 13 | Idioma de la respuesta | `services/reflection_service.py` | LANG_INSTRUCTIONS (line 62) |
| 14 | Mensaje con el texto del profesional | `services/reflection_service.py` | _call_companion_model() -> user message f-string (line 262) |
| 15 | Conversación «Explorar con el acompañante»: papel y reglas | `rdi/companions/prompt_builder.py` | build_companion_conversation_prompt() -> focus_block (line 171) |
|  |  | `rdi/companions/prompt_builder.py` | build_companion_conversation_prompt() -> conversation_rules (line 179) |
| 16 | Conversación «Explorar con el acompañante»: contexto que recibe la IA | `services/reflection_service.py` | continue_companion_conversation() -> context_block (line 393) |
|  |  | `services/reflection_service.py` | continue_companion_conversation() -> fixed assistant message (line 429) |
| 17 | Revisión de patrones – paso 1: lectura de los textos por grupos | `services/pattern_text_analysis.py` | BATCH_SYSTEM_PROMPT (line 105), assembled in read_batch(); {minimum}=config.PATTERN_MIN_TEXTS_PER_PATTERN, {max_patterns}=MAX_PATTERNS_PER_BATCH |
|  |  | `services/pattern_text_analysis.py` | build_batch_message() (user message) |
| 18 | Revisión de patrones – paso 2: informe final | `services/pattern_text_analysis.py` | REPORT_SYSTEM_PROMPT (line 121), assembled in analyse_texts(); {max_questions}=MAX_QUESTIONS, {max_patterns}=MAX_PATTERNS_IN_REPORT |
|  |  | `services/pattern_text_analysis.py` | build_report_message() (user message) |

## How the pieces are assembled (live call paths)

| Call | Path | System prompt (in order) | Messages |
|---|---|---|---|
| Reflection, 8 parallel companion calls | `pages/reflection_space.py` → `rdi/orchestrator.py:run_reflection()` → `_generate_companion_with_retry()` → `services/reflection_service.py:generate_companion_reflection()` → `_call_companion_model()` | `build_companion_prompt()` = 1 + (2–9) + 10 + 11, then `"\n\n"` + 12 + `"\n\n"` + 13 | 14 |
| "Explorar con el acompañante" conversation | `pages/reflection_space.py` → `services/reflection_service.py:continue_companion_conversation()` | `build_companion_conversation_prompt()` = 1 + 15 (focus) + 10 + 15 (rules), then 12 + 13 | 16, then history and new message (professional turns anonymised) |
| Pattern Review step 1 (per batch) | `pages/pattern_explorer.py` → `services/pattern_text_analysis.py:run_report()` → `analyse_texts()` → `read_batch()` → `_call()` | 17 (formatted) + 12 + 13 | `build_batch_message()` |
| Pattern Review step 2 (final) | `analyse_texts()` → `_call()` | 18 (formatted) + 13 | `build_report_message()` |

Language (13): reflection and conversation use the language chosen on the reflection screen; Pattern Review uses the UI language (`st.session_state["lang"]`). Unknown values fall back to Spanish.

## Things to update when applying edits

- Bump `PROMPT_VERSION` in `rdi/companions/prompt_builder.py` (currently `"2026-10-evidence-1"`) when changing 1–11 or 15, and in `services/pattern_text_analysis.py` (currently `"2026-11-text-patterns-2"`) when changing 17–18.
- Companion labels/focus (2–9) are also the dimension keys used across the app; change only the `label`/`focus` strings, never `key`.
- Instruction 11's evidence rules are checked by `services/evidence.py` (exact-match verification); instruction 17/18 JSON shapes are validated by `validate_batch_reply()` / `validate_report_reply()`.
- Tests that read prompt pieces: `tests/test_findings_orchestrator.py`, `tests/test_security_anonymizer_special_categories.py` (check them after edits; run the whole suite).

## Not included in the Word document

| Prompt | Where | Reason |
|---|---|---|
| Error diagnosis prompt (copy-paste prompt for Claude Code in alert emails and the System Administration problem list) | `services/diagnostics.py:_build_ai_prompt()`, `services/error_log.py:build_ai_prompt()` / `get_saved_ai_prompt()` | not included – technical (and it is never sent to Claude by the app; it is plain text for the administrator to copy) |
| Legacy single-call reflection prompt | `reflection_prompt.txt`, used only by `services/reflection_service.py:generate_reflection()` | not included – unused (no callers on `main`; kept as a rollback) |

Requested in the brief but **not present** on this branch (no AI prompt exists):

- **Context Engine** (`rdi/context_engine.py`): only `classify_context_strength()` remains; no Claude call.
- **Orchestrator** (`rdi/orchestrator.py`): runs the 8 companion calls; has no prompt of its own.
- **Conversation Builder** (`rdi/conversation_builder.py`): only reorders the results; no Claude call.
- **Tone pass**: does not exist (tone is handled inside 1 and 10).
- **Summary generation**: does not exist (the per-reflection AI summary was removed on 15 November 2026; prompts forbid summaries).
- **Corpus analysis / lens reading**: does not exist on `main`; the only corpus-level reading is Pattern Review (17–18).
