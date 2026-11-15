# Pattern Review

Redesigned on **15 November 2026** (product owner's decision). For EDE's
management team: **Supervisors and Programme Managers only**
(`services/pattern_access.py`; the System Administrator is deliberately not
included).

## The idea in plain words

We want to find patterns in **what social workers write** about their cases,
not in what the AI says back to them. So:

1. A social worker writes, pastes or uploads a text and presses **Reflect**.
2. The text is anonymised (names, ages, places and other personal details
   removed). If that fails, nothing happens and nothing is saved.
3. Straight away, two things happen:
   - an **anonymised copy** of the text is saved for Pattern Review, with
     only the date and the language — **no name and no role**;
   - the reflection carries on exactly as before: the social worker sees the
     AI's observations and questions.
4. The AI's **observations and questions are not saved**. They are shown to
   the social worker and then forgotten.
5. A manager opens **Pattern Review**, chooses a period (**the last 3, 6, 9
   or 12 months**) and presses **Identify patterns**. The AI reads the
   anonymised texts from that period and writes **one report** on recurring
   patterns in how cases are written.
6. The manager sees **the report only — never the texts**, never quotations,
   never who wrote anything. Reports are saved with their date and period and
   can be downloaded to print.

The social worker is told, in one line on the writing screen, that an
anonymised copy is kept without their name.

## Decisions (product owner, 15 November 2026)

| Question | Decision |
|---|---|
| What do managers see? | The AI's report only, never the texts |
| Is the author's name or role kept with a copy? | No. Only the date and the language |
| How long are copies kept? | 13 months, then deleted automatically |
| Minimum number of texts before patterns can be identified | 5 |
| Are reports saved? | Yes, with their date and period |
| Are social workers told? | Yes, one line on the writing screen (and in Help) |
| Does every text count, or only ones the author chooses? | Every text (the earlier per-observation "share" choice no longer exists) |
| The original text, as agreed with EDE | Still saved for 15 months, readable only by its author |

## Privacy rules (enforced in code, not only on screen)

- `services/pattern_text_store.py` is the only place that stores or reads the
  copies. No function there returns a text for display; `texts_for_period()`
  returns texts only for the AI and refuses anyone without a management role.
- The table `pattern_texts` has no author or role column. It keeps the
  reflection code for one purpose only: so that deleting a reflection also
  deletes its copy. The code is never sent to the AI or shown.
- A reflection waiting in its 48-hour bin is left out of any analysis at once;
  when it is erased for good, its copy is erased too. A System Administrator
  deleting a reflection also deletes its copy.
- If a reflection fails completely, its copy is removed, so "Try again" does
  not count the same text twice.
- Before a report is saved, any part of it that repeats 8 or more consecutive
  words from a text is removed (`remove_copied_passages`), so a manager can
  never read a text through the report.
- A pattern is only reported if it appears in at least 3 texts
  (`PATTERN_MIN_TEXTS_PER_PATTERN`), and nothing runs with fewer than 5 texts
  (`PATTERN_MIN_TEXTS`), so a "pattern" can never point at one person.
- Texts are shuffled before the AI reads them, and the AI never receives a
  date, code or name with a text.
- Copies are never written to logs — only counts.
- "Erase all data" erases the copies and the reports.

## How a report is made (`services/pattern_text_analysis.py`)

1. The period's texts are read (for the AI only) and shuffled.
2. They are split into groups of up to 40 texts / about 40,000 characters.
   Up to 4 groups are read at the same time, one Claude call each. For each
   group the AI lists recurring patterns and the **numbers** of the texts in
   which each appears.
3. One last Claude call combines the groups' findings into the report.
4. The number of texts behind each pattern is **counted by the app** from the
   text numbers — it is never the AI's guess.
5. If more than half of the texts could not be read, no report is saved and
   the manager is told to try again later.
6. The same report (same period, same number of texts, same language) cannot
   be started twice at once.

## Cost

Claude Sonnet 5.5 ($2 per million input tokens, $10 per million output
tokens). Nothing is spent until someone presses the button. With texts of
about 2,000 characters: a 3-month report on about 250 texts costs roughly
$0.40–$0.80; a 12-month report on about 1,200 texts roughly $1.50–$3.50.
Recorded in the Service Cost & Usage Monitor as `pattern_text_batch` and
`pattern_text_report`. No text is sent to Google Gemini any more.

## Settings (`config.py`)

| Setting | Default | Meaning |
|---|---|---|
| `SAVE_PATTERN_TEXT` | on | Save the anonymised copy |
| `PATTERN_TEXT_RETENTION_MONTHS` | 13 | How long a copy is kept |
| `PATTERN_PERIOD_CHOICES` | 3, 6, 9, 12 | Periods a manager can choose |
| `PATTERN_MIN_TEXTS` | 5 | Fewest texts for a report |
| `PATTERN_MIN_TEXTS_PER_PATTERN` | 3 | Fewest texts for a pattern to be reported |
| `SAVE_OBSERVATIONS` | off | Switching it on brings back saved observations, notes and the "Saved observations" section of My Reflection |

## Limits (be honest about these)

- The report is written by AI and can be wrong; the team should check it
  against its own knowledge. Patterns are candidates for reflection, not
  conclusions, and are not evidence of bias or poor practice.
- The texts are only those written in the app during the period; they are
  not necessarily representative of the organisation.
- Anonymisation is automatic and good, but not perfect.
- Reports already made are not changed when a reflection is deleted later
  (they never contain texts).
- The Basque wording should be checked by a native speaker.
- EDE should confirm in writing that keeping the anonymised copies for 13
  months is acceptable.

## What was replaced

The earlier Pattern Review (October–November 2026) grouped the AI's saved
**observations** using Google Gemini "meaning fingerprints", with a team
status for each pattern and a printable report. It was removed because
observations are no longer saved. Its database tables (`pattern_runs`,
`patterns`, `pattern_findings`, `pattern_events`, `finding_embeddings`) are
left untouched so existing databases keep working, and are emptied by
"Erase all data". The full earlier version is in the git history.

## Tests

- `tests/test_pattern_text_analysis.py` — grouping, counting, the minimums,
  removal of copied passages, failures, duplicate protection, roles.
- `tests/test_pattern_review_static.py` — the screens, settings, the
  database table has no author column, translations in all three languages,
  the printable report.
- `tests/test_pattern_text_store_postgres.py` — real database (set
  `TEST_DATABASE_URL`): saving, the 13-month limit, deletion, roles, reports.
