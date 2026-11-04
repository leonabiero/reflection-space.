# Reflection-only design (October 2026, simplified November 2026)

## November 2026 update — "Let's reflect." (one simple screen)

After a further meeting with the EDE team, the practitioner screen was cut
down to one activity:

**Write, paste or upload → choose the language → press Reflect → read the
reflection.**

- The practitioner gives **no metadata**: no reflection code to note, no type
  of text, no case themes, no earlier-reflection code. The neutral reflection
  code is still created **automatically** and saved with the reflection; it is
  shown small at the top of the results.
- **Typed text and an uploaded document are kept separate.** If both are
  present, the practitioner is asked which to use: *my written text*, *the
  uploaded document* or *both together* (`services/document_import.py:
  pick_material`). Nothing is combined or overwritten silently.
- **Language of the reflection** (Español / Euskara / English) is chosen on
  the screen. It starts on the app's current language and only changes the
  language of the reflection — not the menus. Follow-up conversations and the
  manual "Retry" for a dimension use the same language.
- **Anonymisation happens first, on the page**, before anything else. If it
  fails, the practitioner sees a plain message, their text stays on screen and
  **nothing is sent to any AI** — there is no fallback to the original text.
  The error record contains no text and no traceback. Only the anonymised text
  is passed to the orchestrator (which anonymises again; that is harmless
  because `anonymize()` is idempotent).
- The practitioner sees *"Your text has been anonymised."* then *"Preparing
  your reflection..."*, and goes straight to the results.
- On the results, a collapsed **"View anonymised text"** section shows exactly
  what the AI received. It never shows the original text.
- If the whole reflection fails, **"Try again with the same text"** puts the
  text and the chosen language back into the form.
- After **Finish reflection** the screen is immediately empty and ready for
  the next reflection; the thank-you is a small pop-up that disappears.
- **Text written in CAPITAL LETTERS** is now anonymised too
  (`services/anonymizer.py`, second pass). The rules recognise names by their
  shape ("John"), so "HELLO, JOHN IS A HAPPY CLIENT" used to reach the AI
  unchanged. The extra pass can only add protection; normal text is handled
  exactly as before. Known limits: in capitals, a word straight after a name
  may be hidden as if it were a surname ("UNAI ESTABAN"), place names without
  a cue ("…, BILBAO.") are kept, and names written all in lower case
  ("john") are still not recognised.

**What stopped as a consequence (agreed with the product owner):**

- The **Earlier reflections** step is no longer shown. It matched on case
  themes and earlier codes, which practitioners no longer give. The code that
  powers it (`rdi/reflection_context.py`,
  `services/reflection_records.find_similar_reflections`) is kept unchanged so
  it can be brought back.
- New reflections are saved **without case themes or type of text**, so the
  theme filter in managers' Reflection History only finds older reflections.
  Nothing breaks.

The rest of this document describes the October 2026 design; where it
mentions case themes, the type of text or the earlier-reflections step, those
now only apply to reflections made before November 2026.

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
- `tests/test_simple_reflection_screen.py` — the November 2026 simplified
  screen: input rules, privacy (the AI only receives anonymised text, failure
  stops everything), reflection language, translations.
