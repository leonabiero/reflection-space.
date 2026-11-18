# Reflection-only design (October 2026, simplified November 2026)

## 15 November 2026 update — what is kept, and Pattern Review

Product owner's decision (see `PATTERNS.md` for the full detail):

- **Pattern Review reads the saved original texts**, each anonymised again
  before the AI sees it (`services/pattern_text_store.py`,
  `services/pattern_text_analysis.py`). No separate copy is saved.
- **The AI's observations and questions are no longer saved**
  (`config.SAVE_OBSERVATIONS`, off). They are shown to the social worker and
  then forgotten. As a consequence:
  - Reflection History shows one line per reflection (code, date in Bilbao
    time, who did it); the AI summary (`services/reflection_summary.py`) and
    the folded observations were removed;
  - the notes boxes under each card and My Reflection's "Saved observations
    and your notes" no longer appear (they need saved observations);
    "Show the saved text" moved to "Your saved reflections".
- **Reflection History (`pages/case_history.py`) was removed** later the same
  day: with observations no longer saved it had no job left. The average
  usefulness rating moved to Pattern Review, and the System Administrator no
  longer has Manager mode. Everything below about Reflection History is
  history.
- **The original text** (agreed with EDE) is still saved for 15 months, and
  is readable **only by its author**. Managers no longer read any texts; the
  "Saved original texts" section of Pattern Review was removed, and managers
  see only the AI's report.
- The rest of this document is kept as a record. Where it says observations
  are saved, shown in Reflection History or read by managers, the update
  above replaces it.

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
- **Places and addresses (November 2026, from a synthetic Spanish case).**
  Bizkaia municipalities, the other Basque capitals and nearby / large cities
  (Spanish and Basque spellings, with Basque endings such as "Bilboko",
  "Barakaldon") are tagged `[LOCATION]` instead of `[PERSON]`; "una tienda de
  Barakaldo" is a place. Floor and door after an address ("2º izquierda",
  "3ºB", "bajo", "2. ezkerra") are removed with it. In text written in
  capitals, "VIVE EN BILBAO CON SU MADRE" no longer loses "CON SU MADRE".
- **Sensitive personal details — GDPR "special categories" (18 November
  2026).** EDE's test showed that words such as "gay" reached the AI. Words
  that state a sensitive detail are now replaced by a neutral label, in
  Spanish, Basque and English, so the AI knows such a detail was mentioned
  but never what it was: `[SEXUAL_ORIENTATION]`, `[GENDER_IDENTITY]`,
  `[HEALTH]`, `[RELIGION_BELIEF]`, `[ETHNIC_ORIGIN]`, `[POLITICAL_OPINION]`,
  `[TRADE_UNION]`. Every AI instruction that receives anonymised text also
  says what the labels mean and that the AI must never guess what was hidden
  (`anonymizer.SENSITIVE_LABELS_NOTE`).
  - *Product owner's decisions:* health — only **specific** diagnoses,
    treatments and medicine names are hidden ("esquizofrenia", "VIH",
    "sertralina"); general words ("enfermedad", "problema de salud", "salud
    mental") are kept. Nationality is **not** hidden for now. Both can be
    switched on, and any category off, with `ANONYMISER_SPECIAL_CATEGORIES`
    in `config.py` (an invalid value falls back to the defaults).
  - *Named mental health centres:* "Centro de Salud Mental de Uribarri" keeps
    "Centro de Salud Mental" and the place becomes `[LOCATION]` (it used to be
    "[PERSON] de Salud Mental de [PERSON]").
  - *What it will not catch (be honest about this):* indirect hints ("vive con
    su novia", "va a la mezquita los viernes", "fue a la manifestación",
    "lleva velo"), misspellings and slang, medicines and conditions that are
    not on the lists, "Podemos" and "Sumar" (left out because they are also
    everyday verbs), and the Spanish feminine "atea" (left out because in
    Basque it means "the door"). "ELA" is always labelled as a trade union,
    even when it means the disease — still hidden, but with the wrong label.
    Some words may be hidden when they did not mean a sensitive detail (for
    example "adicto al trabajo"); the anonymiser leans towards hiding.
  - *Pattern Review* re-anonymises every saved text each time it runs, so the
    new protection applies to texts written before this change too.
- **What the practitioner types in a follow-up conversation is protected too
  (November 2026).** Previously only the document was anonymised; the
  messages typed into a companion conversation went to Claude as written. Each
  message now goes through the same `anonymize()` first
  (`services/reflection_service.continue_companion_conversation`). If that
  fails, nothing is sent and the practitioner sees a plain message. They still
  see their own words on screen; only the AI receives the protected version.
  (The Knowledge Assistant and Text analysis, which had the same protection,
  were removed later in November 2026.)
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
Reflection History, pattern analysis and the counts
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

### Saved ORIGINAL text (10 November 2026, agreed with EDE) — replaces the section below

EDE agreed that the **original** text can be stored, because the database
(Neon, Frankfurt) is in the EU. It is needed later to study patterns in how
cases are written (patterns in the text *before* reflection). From this date
each new reflection keeps the **original** text instead of the anonymised copy.

- **What the AI receives is unchanged:** Claude still only ever receives the
  anonymised text (`run_reflection(safe_text, …)`). The original is stored,
  never sent.
- Column `reflection_runs.original_text` (`services/db_schema.py`), written by
  `services/findings_store.save_reflection_run(original_text=...)` from the
  text the professional wrote, pasted or uploaded. The anonymised copy is no
  longer saved for new reflections.
- **Who can read it** (enforced in SQL in `services/reflection_records.py`):
  - the **author** only: My Reflection → "Show the saved text"
    (`get_original_text`, author only);
  - since 15 November 2026 managers no longer read it (Pattern Review shows
    an AI report; the AI reads the texts anonymised again; see `PATTERNS.md`).
- **How long:** `config.ORIGINAL_TEXT_RETENTION_MONTHS` (default **15**).
  Expired text is never shown, and `purge_expired_original_text()` clears it
  (after each new reflection and when the Pattern Review texts are opened).
  The reflection itself is kept. A reflection its author deletes is hidden at
  once and erased for good, text included, after the deletion window.
- **On/off:** `SAVE_ORIGINAL_TEXT` (default on). Turning it off stops saving;
  text already saved ages out.
- Practitioners are told in Help (the notice on the reflection screen was
  removed on 15 November 2026 at the product owner's request) that the text is
  saved and may be read by supervisors and programme managers without their
  name.
- Never logged.
- Reflections made between 4 and 10 November 2026 keep their anonymised copy
  until it expires (12 months); it stays readable as before.

**Points for EDE:** written confirmation (ideally from whoever handles data
protection); the text passes through the app's hosting (Streamlit Community
Cloud, outside the EU) while it is being written — that was already the case
and storing does not change it; the database is currently under a personal
account and should move to an EDE-owned account.

**Gemini:** removed on 18 November 2026. No text had been sent to Google Gemini
since 15 November 2026, so the earlier concern about its free tier no longer
applies. Claude is the only AI service the app uses.

### Saved anonymised text (4–10 November 2026, product owner decision) — superseded

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
   optional short conversations, private notes. "Finish reflection" ends it
   in one click. *(Since 15 November 2026 there is no feedback step: rating
   the reflection is optional, through the small "Rate" button in the
   top-right corner of the results, and nothing depends on it.)*

When the professional finishes (or starts again, or logs out) the case text
is cleared from the screen. *(Since 10 November 2026 the original text is also
saved with the reflection — see "Saved ORIGINAL text" above.)*

## What is stored

| Stored | Not stored |
|---|---|
| Reflection code, case themes, type of text, optional link to an earlier code | Uploaded files |
| | **Since 15 November 2026:** the AI's observations and questions |
| *(Until 15 November 2026 only)* short verified passages the AI quoted, and the professional's private notes on observations | Conversation text with the companion |
| | Names or real file numbers (codes are random) |
| **Since 10 November 2026:** the **original** text, for up to 15 months (see "Saved ORIGINAL text" above) | The anonymised copy (4–10 November 2026 only) |

Tables: `reflection_runs` (new columns `reflection_code`, `case_tags`,
`note_type`, `previous_code`), `reflection_findings`, `finding_feedback`
— see `services/db_schema.py`.

## Where the code lives

- `pages/reflection_space.py` — the single screen (three stages).
- `services/reflection_records.py` — codes, case themes, similar-reflection
  matching, the management listing, counts.
- `rdi/reflection_context.py` — holds the case text (session only) and the
  chosen earlier reflections before generating.
- `services/findings_store.py` — saves the reflection with its identifiers.
- `pages/case_history.py` — managers' **Reflection History** (codes, themes,
  observations; never case text or private notes; System Administrator can
  delete a reflection). Since 15 November 2026 each reflection shows a short
  AI summary first, readable in one go, with the full observations,
  passages and questions folded underneath.
- `services/reflection_summary.py` — writes that summary with one Claude
  call, from the saved **observations only** (never the case text, quoted
  passages, code, dates or author). Written straight after a reflection is
  saved; older reflections get a "Create summary" button. Stored in
  `reflection_runs.summary_text`, so it is erased with the reflection.
- `services/data_reset.py` and `pages/admin_sections/data_reset.py` — System
  Administration → **Erase all data** (November 2026).

## Privacy rules

- Similar-reflection matching only looks at the professional's **own**
  reflections (filtered by name in the database query).
- A previous code can only be linked if it is the professional's own.
- Management views require a management role (checked in the page **and** in
  `services/reflection_records.py`) and never show private notes.
- Nothing logs case text, observations, quotes, notes or themes — only codes,
  ids and counts.

## Old stored documents

Documents saved before this change stay in the database until a System
Administrator uses **System Administration → Erase all data** (type the
confirmation word, then press the button). Since November 2026 this single
action replaces the earlier "Erase old stored documents" panel: because
everything saved up to then was synthetic test data, it erases *all* saved
data — old documents, reflections, observations, notes, feedback, patterns,
recorded problems and cost records — so the pilot starts from zero. User
accounts, sign-in sessions and settings are kept. Nothing is ever erased
automatically on start-up.

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
