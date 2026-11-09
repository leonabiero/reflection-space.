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
- **Simpler results screen (November 2026, after the first session with the
  EDE team, who asked for a very simple tool).** After Reflect, only what is
  needed to start reflecting is open:
  - One folded band, **"Reflection info · <code> · <language>"**, holds the
    reflection code, the language, "View anonymised text" and "Case text (not
    saved)". Streamlit cannot put a fold inside a fold, so those two texts open
    with a switch (off by default). Warnings (a lens that failed, findings not
    saved) stay visible above it.
  - Opening a card shows **only the questions**. What the AI noticed — the
    whole observation, the quoted passage(s) and the "this is your professional
    decision" reminder — is in one fold just above them, **"Why these
    questions? See what the AI noticed"**, which the practitioner opens when
    they want. "My notes and sharing with the team" stays folded. (A first
    version showed the observation's first sentence open; the product owner
    asked for it to be folded too.)
  - The button is now **"Explore this with the companion"** ("Explorar con el
    acompañante", "Aztertu laguntzailearekin").
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
- **Exact ages are protected (November 2026).** "her actual age is 30 not 29",
  "tiene 30 años, no 29", "17 urte ditu", "a 24-year-old woman", ages written
  in words ("treinta y cinco", "hogeita hamar") and years of birth ("born in
  1996", "nació en 1996", "1996an jaio zen") used to reach the AI unchanged.
  Each age is now replaced by a life-stage tag — `[AGE_INFANT]`,
  `[AGE_CHILD]`, `[AGE_ADOLESCENT]`, `[AGE_YOUNG_ADULT]`, `[AGE_ADULT]`,
  `[AGE_OLDER_ADULT]` — and a year of birth by `[DATE]`. The groups are set in
  `config.AGE_BAND_LIMITS` (default 0-2, 3-12, 13-17, 18-25, 26-64, 65+); the
  adolescent group always ends at 17, so minor versus adult — which matters for
  safeguarding — is always exact. A number only counts as an age when the words
  around it say so; durations and quantities ("hace 3 años", "lleva 2 años en
  el piso", "duela 3 urte", "2 hijos", "30 euros") are kept. Known limits: a
  bare number with no age wording ("she was 30 then") may be kept, and the
  sentence is not rewritten ("age is [AGE_ADULT] not [AGE_ADULT]").
- **What the practitioner types in a follow-up conversation is protected too
  (November 2026).** Previously only the document was anonymised; the
  messages typed into a companion conversation went to Claude as written. Each
  message now goes through the same `anonymize()` first
  (`services/reflection_service.continue_companion_conversation`). If that
  fails, nothing is sent and the practitioner sees a plain message. They still
  see their own words on screen; only the AI receives the protected version.
  The same protection now covers the question typed into the **Knowledge
  Assistant** (`services/knowledge_assistant.ask`), and stored document-analysis
  texts are re-checked just before they are read
  (`services/corpus_reading_service.read_texts`), so texts saved before age
  protection existed do not send exact ages.
- **My Reflection is grouped by reflection (November 2026).** "Saved
  observations and your notes" used to list every observation on its own line
  (up to eight per reflection). It now shows one line per reflection — code,
  date, number of observations and how many have notes — and inside it the
  person picks one observation at a time, in the same order as the cards
  (`services/findings_store.get_my_findings_by_reflection`, five reflections
  per page). Every observation is still kept, so nothing is lost.
- **A professional's own notes are protected too (November 2026).** The two
  free-text boxes under "My notes and sharing with the team" (another possible
  explanation, my reflection or note) never go to the AI, but they are stored.
  They now go through the same `anonymize()` before saving
  (`services/findings_store.protect_note_text`, used by `upsert_feedback`), and
  after saving the boxes show the protected version that was stored. If
  anonymising fails, nothing is saved and the usual "couldn't be saved" message
  appears. Notes saved before this change are not rewritten.

**What stopped as a consequence (agreed with the product owner):**

- The **Earlier reflections** step is no longer shown. It matched on case
  themes and earlier codes, which practitioners no longer give. The code that
  powers it (`rdi/reflection_context.py`,
  `services/reflection_records.find_similar_reflections`) is kept unchanged so
  it can be brought back.
- New reflections are saved **without case themes or type of text**, so the
  theme filter in managers' Reflection History only finds older reflections.
  Nothing breaks.

### Reflection opportunities as cards (November 2026)

The eight dimensions are shown as **cards in one view** (4 per row on a
laptop, 2 on a phone) instead of tabs, in the fixed order of
`rdi/conversation_builder.py`. Nothing is open at first; choosing a card
opens its content (observation, passages, questions, Explore, notes) below
the grid. A **dot** in each card's top-right corner shows what that companion
produced — green: something to reflect on; grey: nothing notable; amber:
temporarily unavailable (Retry inside). The same meaning is given in words
(tooltip and a key under the cards), so it never relies on colour alone.
Status comes from `ReflectionSession.status_of()`.

### Practitioners can delete their own reflections (November 2026)

On **My Reflection → Your saved reflections**, each reflection has a
**Delete** button (with an "are you sure?" step). Deleting hides it
**everywhere at once** — the author's journal and timeline, managers'
Reflection History, pattern analysis, the Knowledge Assistant and the counts
— through the shared rule `findings_store.NOT_IN_DELETION_WINDOW`
(`reflection_runs.deleted_at`). For `DELETION_WINDOW_HOURS` (48) it is listed
under **Recently deleted** with **Restore**; after that
`reflection_records.purge_expired_reflection_deletions()` erases it for good:
the run, its observations, the author's notes, its anonymised text and its
journey entries (run when My Reflection or Reflection History is opened).
Only the author can delete or restore their own reflection; every step is
written to the audit log. Usefulness ratings (1–5 stars) are kept.

The privacy wording on My Reflection and in Help was corrected: notes and
explorations are private, but saved observations (and their anonymised text)
are also visible to managers in Reflection History.

### Saved anonymised text (November 2026, product owner decision)

To make it possible to study patterns across reflections later, each new
reflection also keeps the **anonymised** text the AI received — exactly what
"View anonymised text" shows. **The original text is still never saved.**

- Column `reflection_runs.anonymised_text` (`services/db_schema.py`), written
  by `services/findings_store.save_reflection_run(anonymised_text=...)` from
  `session.safe_text` only.
- **Who can read it:** the author (My Reflection → "Show the saved anonymised
  text") and management roles (Reflection History, same switch). Enforced in
  `services/reflection_records.get_anonymised_text` — the database query
  itself only returns the text to the author or a management role.
- **How long:** `config.ANONYMISED_TEXT_RETENTION_MONTHS` (default **12**).
  Expired text is never shown, and `purge_expired_anonymised_text()` clears it
  (after each new reflection and when Reflection History is opened). The
  reflection itself is kept. Deleting a reflection deletes its text.
- **On/off:** `SAVE_ANONYMISED_TEXT` (default on). Turning it off stops saving;
  text already saved ages out.
- Practitioners are told on the screen and in Help.
- Never logged.

**To confirm with EDE (data protection):** that keeping the anonymised text is
acceptable, the 12-month period, and who may read it. Anonymisation reduces
risk but is not a guarantee: a unique combination of details can still point
to a person, so the saved text must be treated as sensitive.

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
| **Since November 2026:** the **anonymised** text the AI received, for up to 12 months (see below) | The **original** text as written |

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
