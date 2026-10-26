# Reflection-only design (October 2026)

Agreed with the EDE Fundazioa team in October 2026. This replaces the earlier
"save a document first, reflect later" design.

## The decision in plain words

- Reflection Space is **not a place to store documents**. It is a place to
  reflect.
- A professional writes, pastes or uploads a case and **reflects on it on the
  spot**. There is no separate Documentation screen any more.
- **What is kept is the reflection**, not the case text.
- Each reflection carries **identifiers that are not personal identity**, so
  that later reflections on similar situations can be connected to it.

## What a professional sees (one screen: Reflection Space)

1. **Your case** — the app shows a neutral reflection code (e.g. `RS-7F3K2Q`).
   The professional chooses the type of text, ticks up to six case themes
   (e.g. *Housing / homelessness*, *Mental health*), can optionally type the
   code of an earlier reflection on the same situation, and writes, pastes or
   uploads the case (Word, PDF or text — only the text is read; the file is
   never kept).
2. **Earlier reflections** — the professional's **own** earlier reflections
   that are linked (by code) or share themes are offered as context. Each can
   be left out. Only the AI's observations are used — never quotes or notes.
3. **Professional reflection** — unchanged: the eight reflective dimensions,
   optional short conversations, private notes. "Finish reflection" ends it;
   optional usefulness feedback follows.

When the professional finishes (or starts again, or logs out) the case text
is discarded. It only ever lived in the browser session.

## What is stored

| Stored | Not stored |
|---|---|
| Reflection code, case themes, type of text, optional link to an earlier code | The case text |
| The AI's observations and questions for each dimension | Uploaded files |
| Short verified passages the AI quoted (taken from the **anonymised** text) | Conversation text with the companion |
| The professional's own private notes on observations | Names or real file numbers (codes are random) |

Tables: `reflection_runs` (new columns `reflection_code`, `case_tags`,
`note_type`, `previous_code`), `reflection_findings`, `finding_feedback`
— see `services/db_schema.py`.

## Where the code lives

- `pages/reflection_space.py` — the single screen (three stages).
- `pages/documentation.py` — retired; only redirects old links to Reflection Space.
- `services/reflection_records.py` — codes, case themes, similar-reflection
  matching, the management listing, Knowledge Assistant evidence, counts.
- `rdi/reflection_context.py` — holds the case text (session only) and the
  chosen earlier reflections before generating.
- `services/findings_store.py` — saves the reflection with its identifiers.
- `pages/case_history.py` — managers' **Reflection History** (codes, themes,
  observations; never case text or private notes; System Administrator can
  delete a reflection).
- `services/knowledge_assistant.py` — now answers from saved reflections.
- `services/research_metrics_service.py` — "documents completed" became
  "observations saved".
- `pages/admin_sections/legacy_documents.py` — System Administration →
  **Erase old stored documents**.

## Privacy rules

- Similar-reflection matching only looks at the professional's **own**
  reflections (filtered by name in the database query).
- A previous code can only be linked if it is the professional's own.
- Management views require a management role (checked in the page **and** in
  `services/reflection_records.py`) and never show private notes.
- Nothing logs case text, observations, quotes, notes or themes — only codes,
  ids and counts.

## Old stored documents

Documents saved before this change are still in the database until a System
Administrator erases them from **System Administration → Erase old stored
documents** (type the confirmation word, then press the button). This
permanently removes every old document, its edit history, the reflections that
were generated from those documents, and their search copies. Reflections made
with the new screen are not touched. Nothing is ever erased automatically on
start-up.

A full copy of the project as it was before this change is kept on GitHub in
the branch **`master-version`**.

## Tests

- `tests/test_reflection_records_static.py` — codes, themes, translations,
  "case text is never stored", navigation.
- `tests/test_reflection_records_postgres.py` — real-database checks (skipped
  unless `TEST_DATABASE_URL` is set).
