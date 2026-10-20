# Saved findings (Stage 1)

This document describes what Reflection Space now keeps after a reflection,
who can see it, how it is deleted, what it costs, and what is **not** done yet.

## What changed, in one paragraph

Before, a reflection was shown on screen and then forgotten (only a yes/no
flag per dimension was logged). Now each reflection is saved as a **run** with
one **finding** per dimension that produced something. Each finding holds the
AI's observation, its questions, and the **exact passage(s)** of the
documentation it was based on. Professionals can add their own notes to each
finding, and can come back to them later on the "My Reflection" page.

## What is stored

| Table | One row per | Holds |
|---|---|---|
| `reflection_runs` | generated reflection | case reference, language, prompt version, model, per-dimension status (`finding` / `no_finding` / `failed`), who ran it, when |
| `reflection_run_sources` | document used by a run | which documents (current + any history included) fed the run |
| `reflection_findings` | dimension with a result | observation, questions, verified quotes, how many proposed quotes were rejected |
| `finding_feedback` | professional + finding | label, note, alternative explanation, "AI misunderstood" flag |

The AI's finding is never edited after it is saved. A professional's words live
in their own table, so the two can never blend.

## Evidence: how quotations are verified

The AI is asked for up to two short passages per observation. Before anything
is saved or shown, `services/evidence.py` checks each one against the text the
AI was given:

- It must appear **word for word** in that text. Differences in line breaks,
  repeated spaces, or accent encoding (composed vs decomposed letters such as
  ñ, á, ü) are tolerated; what is saved is always the **source's** own wording.
- Paraphrases, translations, quotes stitched together with "...", and
  fragments shorter than 10 characters are rejected.
- Rejected passages are **not shown as quotations**. The screen says how many
  were not shown.
- The text checked is the **anonymized** text (names already replaced), so
  stored quotes contain placeholders, never real names from the raw document.

An observation about something that is *missing* from the text legitimately has
no quotation. That is expected, not an error.

## Who can see what

- **Findings and notes are only shown to the professional who ran the
  reflection.** The database filters by the person's name, and saving notes on
  someone else's finding is refused at the data layer.
- Notes and ratings are private. The "To discuss later" label is also private
  in Stage 1; it does not notify or share with anyone.
- Nothing in Stage 1 shows findings to supervisors or managers. (That is
  Stage 2, the pattern explorer, and will need its own sharing rules.)
- No finding text, quotation or note is written to application logs.

## Deletion

- **Pending draft deleted** (`delete_pending_draft`): every run that used the
  document, with its findings and notes, is deleted in the *same database
  transaction*.
- **Completed document soft-deleted** (48-hour window): its runs are *hidden*
  from their author immediately and reappear if the document is restored.
- **Permanent purge** (`purge_expired_deletions`): runs are deleted in the same
  transaction as the document.
- A run is deleted **whole** if *any* document that fed it is purged, because
  its quotes may come from any of them (including earlier documents added as
  history). This can remove findings about a surviving document; that is a
  deliberate, erasure-safe choice.

Not covered by this deletion path: backups held by the hosting provider, and
the existing yes/no theme log (`reflections` table), which holds no text.

## Cost

Asking the AI for evidence adds a little input (≈165 tokens of instructions per
companion) and output (the quotes). Estimated at the pricing in
`services/cost_pricing.py` (Claude Sonnet 5: $2 / $10 per million input /
output tokens):

- about **$0.007 per reflection** typically, **$0.011** at most
- ≈ $0.70–$1.15 per 100 reflections

These are estimates from token counts; the Service Usage & Costs panel shows
real figures. The reply-length ceiling was raised from 1024 to 1280 tokens so
the extra text can never truncate a reply (a ceiling, not a charge). Saving and
reading findings makes no AI calls.

## Prompt versioning

`PROMPT_VERSION` in `rdi/companions/prompt_builder.py` is saved with every run.
Change it whenever the instructions change in a way that could change the
output, so results from different pilot iterations can be told apart.

## Tests

- `tests/test_findings_evidence.py` – quote verification (Spanish, Basque,
  English, accents, paraphrase/translation rejection). Pure, no database.
- `tests/test_findings_orchestrator.py` – verification inside the
  orchestrator, with a **mocked** AI provider (no real model call).
- `tests/test_findings_static.py` – deletion wiring, translation completeness
  in all three languages, no sensitive text in logs, safe display of quotes.
- `tests/test_findings_store_postgres.py` – the real SQL against a real
  PostgreSQL database (saving, atomicity, privacy, notes, deletion paths,
  hiding during the deletion window, pagination). **Skipped unless**
  `TEST_DATABASE_URL` points at a throwaway database:

```
TEST_DATABASE_URL=postgresql://user:pass@localhost/test_db python -m pytest tests/test_findings_store_postgres.py -v
```

## Known limits (Stage 1)

- A **real** Claude call was not tested in development (no API key was
  available there). Whether the live model returns well-formed `evidence`, and
  how often it proposes passages that fail verification, must be checked on
  the first real reflections. The app handles missing or bad evidence safely
  (no quotation shown, count reported).
- Evidence is verified against the **anonymized** text. If the anonymizer
  alters wording, the saved quote shows the anonymized wording.
- Basque interface texts were written for this change and should be reviewed
  by a Basque speaker before the pilot.
- Findings keep the existing shape (observation + questions + evidence).
  Separate "alternative perspective" and "limitations" fields are not added
  (each would add AI cost).
- Free-text notes are stored as typed and could contain identifying details a
  professional chose to write. They are never sent to the AI.
- There is no cross-document pattern view, management view or report yet
  (Stages 2 and 3).
- Before real service-user data is used, EDE must approve keeping this extra
  text, and the existing data-protection arrangements should be confirmed to
  cover it.
