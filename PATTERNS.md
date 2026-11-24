# Pattern Review

Redesigned on **15 November 2026** (product owner's decision). For EDE's
management team: **Supervisors and Programme Managers only**
(`services/pattern_access.py`; the System Administrator is deliberately not
included).

## The idea in plain words

We want to find patterns in **what social workers write** about their cases,
not in what the AI says back to them. So:

1. A social worker writes, pastes or uploads a text and presses **Reflect**.
2. The text is anonymised and the reflection carries on as before: the
   social worker sees the AI's observations and questions.
3. The **original text** is saved with the reflection, as agreed with EDE
   (EU database, 15 months, readable only by its author). **No separate copy
   is saved** — Pattern Review uses these original texts.
4. The AI's **observations and questions are not saved**. They are shown to
   the social worker and then forgotten.
5. A manager opens **Pattern Review**, types a period (**any whole number
   of months from 1 to 15**; until 17 November 2026 it was a choice of 3,
   6, 9 or 12) and presses **Identify patterns**. The app takes that
   period's original texts, **anonymises each one again**, and only then
   lets the AI read them. The AI writes **one report** on recurring patterns
   in how cases are written.
6. The manager sees **the report only — never the texts**, never quotations,
   never who wrote anything. Reports are saved with their date and period and
   can be downloaded to print. Since 18 November 2026 a manager who has the
   downloaded file can delete the report (see "Deleting reports" below).

Social workers are told in **Help** (Privacy and "Your case" sections), in
all three languages, that their original text is used this way. The notices
that were on the writing screen were removed on 15 November 2026 at the
product owner's request.

Since Reflection History was removed (15 November 2026, evening), Pattern
Review is the only page in Manager mode and Manager mode opens on it. It also
shows the average usefulness rating of reflections in one small line at the
top (the average only — never individual ratings, comments or who gave them).

## Decisions (product owner, 15 November 2026)

| Question | Decision |
|---|---|
| Which texts are analysed? | The saved original texts (no separate copy is kept) |
| What does the AI receive? | Each text after anonymisation — never a name, role, code or date |
| What do managers see? | The AI's report only, never the texts |
| How long are texts kept? | 15 months (as agreed with EDE), then cleared automatically |
| Minimum number of texts before patterns can be identified | 5 |
| Which periods can a manager choose? (17 November 2026, at EDE's request) | Any whole number of months from 1 to 15 — never longer than the texts are kept |
| Are reports saved? | Yes, with their date and period, until a manager deletes them (18 November 2026) or "Erase all data" |
| Who may delete a report? (18 November 2026) | Any Supervisor or Programme Manager, any report — reports are shared by the whole management team, so a deleted report is gone for everyone. One at a time, or all at once |
| Are social workers told? | Yes, in Help (the writing-screen notices were removed at the product owner's request) |
| Does every text count, or only ones the author chooses? | Every text |

(For a few hours on 15 November 2026 a separate anonymised copy of each text
was saved for 13 months. The product owner decided against keeping two
copies; that table, `pattern_texts`, is removed by "Erase all data".)

## Privacy rules (enforced in code, not only on screen)

- `services/pattern_text_store.py` reads the texts for the AI only. No
  function there returns a text for display; `texts_for_period()` returns the
  text and language only (no name, role, code or date) and refuses anyone
  without a management role.
- `services/pattern_text_analysis.py` anonymises every text again with the
  same anonymiser as a reflection before the AI reads it. A text that cannot
  be anonymised is left out — never sent as written.
- Texts past their 15 months, and reflections waiting in their 48-hour bin or
  erased, are never used.
- Before a report is saved, any part of it that repeats 8 or more consecutive
  words from a text (original or anonymised) is removed, so a manager can
  never read a text through the report.
- A pattern is only reported if it appears in at least 3 texts
  (`PATTERN_MIN_TEXTS_PER_PATTERN`), and nothing runs with fewer than 5 texts
  (`PATTERN_MIN_TEXTS`), so a "pattern" can never point at one person.
- Texts are shuffled before the AI reads them.
- Texts are never written to logs — only counts.
- "Erase all data" erases the reports (and the texts, with the reflections).
- Deleting a report is checked twice: on the screen and again in
  `services/pattern_text_store.py` (`delete_report`, `delete_all_reports`
  refuse anyone without a management role).

## Deleting reports (18 November 2026, product owner's decision)

Safety first:

- **Downloading never deletes anything.** The downloaded file is the full
  report, exactly as before.
- Below the download button: **"Ya tengo el archivo: eliminar informe"**
  ("I have the file: delete report"). It first asks "Are you sure?" with
  **Yes, delete** / **Cancel**, and says the report goes for the whole
  management team.
- After "Yes" the report is **permanently deleted from the database** and
  disappears from the page, with the message "Report deleted. You can now
  run a new review." If older reports are saved, the next one is shown;
  when none are left the page shows "No report has been made yet".
- With two or more saved reports, **"Delete all saved reports"** deletes
  every saved report at once, with its own "Are you sure?".
- Deleting also lifts the 15-minute "a report was made a few minutes ago"
  lock for that report, so the same review can be run again straight away.
- Nothing else changes: the rating line, the months box, the minimum of 5
  texts, the saved original texts and "Erase all data".

What can go wrong:

- Two managers have the page open and one deletes a report: the other sees
  it disappear on their next click; pressing delete on it shows "This report
  had already been deleted" (not an error).
- The database cannot be reached: nothing is deleted and the manager is
  told to try again.
- Deleted by mistake: a deleted report cannot be recovered, but the review
  can be run again (small AI cost) while the texts are within their 15 months.
- Older reports (made before this change) need nothing special: each can be
  deleted the same way.

## How a report is made (`services/pattern_text_analysis.py`)

1. The period's original texts are read (for the AI only), anonymised one
   by one, and shuffled.
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
tokens). Nothing is spent until someone presses the button. The cost grows
roughly in line with the number of texts: about **$0.002 per text**, plus
$0.03–$0.10 for the final step. With texts of about 2,000 characters
(about 20 per group) and about 90 texts a month across the organisation:

| Period | Texts (approx.) | Cost per report |
|---|---|---|
| 1 month | 90 | ~$0.20 |
| 3 months | 270 | ~$0.60 |
| 6 months | 540 | ~$1.15 |
| 12 months | 1,080 | ~$2.25 |
| 15 months | 1,350 | ~$2.80 (range $2–$4) |

Long periods are also slow: with a full year of real texts a report may
take 10–15 minutes (about 60 groups, read 4 at a time). The "already
running" protection lasts 15 minutes (`BUSY_TTL_MINUTES`), so this should
be watched once real volumes build up.

The AI also "thinks" before it answers, and that thinking is billed as
output. Since 17 November 2026 each AI call has room for 12,000 tokens
(`BATCH_MAX_TOKENS`, `REPORT_MAX_TOKENS`; before: 2,500 per group and 4,000
for the final step, which was too little and made reports fail with
"reply was not valid JSON") and up to 300 seconds (`CALL_TIMEOUT_SECONDS`).
This room is a ceiling, not a price, but the thinking can add up to about
$0.03 per group: roughly $0.05–$0.15 for a small report (for example the
demo's 70 texts) and possibly $1–$2 more for a full year of real texts.
Thinking also makes each call slower, so long periods may take longer
than the 15 minutes above. If a reply cannot be read, the log line shows
only its shape (stop reason, tokens used, length, how it starts, library
version) -- never its text.
Recorded in the Service Cost & Usage Monitor as `pattern_text_batch` and
`pattern_text_report`. Google Gemini, which an earlier version used, was
removed from the app on 18 November 2026.

Since 18 November 2026 each group's instructions include one extra sentence
explaining the anonymiser's labels (such as `[HEALTH]`): about 60 tokens per
group, which adds roughly $0.0001 per group, about $0.008 for a full 15-month
report.

## Settings (`config.py`)

| Setting | Default | Meaning |
|---|---|---|
| `SAVE_ORIGINAL_TEXT` | on | Keep the original text (needed for Pattern Review) |
| `ORIGINAL_TEXT_RETENTION_MONTHS` | 15 | How long a text is kept |
| `PATTERN_MIN_MONTHS` / `PATTERN_MAX_MONTHS` | 1 / 15 | Shortest and longest period a manager can type. The longest is always `ORIGINAL_TEXT_RETENTION_MONTHS`. Checked on screen and again in `services/pattern_text_store.py` |
| `PATTERN_DEFAULT_MONTHS` | 3 | The number already in the box when the page opens |
| `PATTERN_MIN_TEXTS` | 5 | Fewest texts for a report |
| `PATTERN_MIN_TEXTS_PER_PATTERN` | 3 | Fewest texts for a pattern to be reported |
| `SAVE_OBSERVATIONS` | off | Switching it on brings back saved observations, notes and the "Saved observations" section of My Reflection |

## Limits (be honest about these)

- The report is written by AI and can be wrong; the team should check it
  against its own knowledge. Patterns are candidates for reflection, not
  conclusions, and are not evidence of bias or poor practice.
- The texts are only those written in the app during the period; they are
  not necessarily representative of the organisation.
- Anonymisation is automatic and good, but not perfect. Since 18 November
  2026 it also replaces words stating sensitive details (sexual orientation,
  gender identity, specific diagnoses / treatments / medicines, religion,
  ethnic origin, political opinions, trade union membership) with labels
  such as `[HEALTH]`, and the AI is told never to guess what was hidden.
  Indirect hints are not caught; see `REFLECTIONS.md`. Because every text is
  anonymised again each time a report runs, this also protects texts saved
  before that date.
- Reports already made are not changed when a reflection is deleted later
  (they never contain texts).
- The Basque wording should be checked by a native speaker.
- EDE should confirm in writing that the original texts may be used this way
  (read by the AI after anonymisation, for pattern reports).

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
  the printable report, the 1–15 month limits (also enforced in the service
  layer), "1 month" written correctly in every language, and deleting
  reports (confirmation first, download unchanged, roles checked in the
  service layer, the "just made" lock lifted, database failures).

## Demonstrations

Pattern Review is demonstrated with fictional texts in a separate demo app
and database, never in the real one. See `DEMO.md`.
- `tests/test_pattern_text_store_postgres.py` — real database (set
  `TEST_DATABASE_URL`): which texts are read, time limits, deletion, roles,
  reports, deleting one report or all of them.

## November 2026 update — frank analysis (EDE)

The AI's instructions (`services/pattern_text_analysis.py`, prompt version
`2026-11-text-patterns-3`) now say: "When the same bias is repeated, it
creates a pattern." Both steps use the EDE framework as checklist and name
repeated biases, stereotypes, prejudices and loaded labels frankly, with
grounded reasons, instead of "cautious wording". Unchanged: never about the
writers, never quotes or case details, at least
`PATTERN_MIN_TEXTS_PER_PATTERN` texts per pattern, the copy check, and the
**limitations** section, which is always present and now written frankly.
Texts are anonymised with placeholders in the language the manager chose
for the report; each text numbers its own people. The screen and printout
texts were updated to match (`pr_intro`, `pr_candidate_note`,
`pr_print_footer`, Help).

24 November 2026 (prompt version `2026-11-text-patterns-4`): the shared EDE
framework now has the Berriz guiding question for each of its five planes,
as questions the AI asks itself while analysing; it is told never to copy
them as the questions it gives the team. It also names the sources (reports,
case files, PIAs, emails, calls), says that language is never neutral, and
that the AI is a tool for contrast that does not give closed answers. The
sentence "When the same bias is repeated, it creates a pattern." was already
in both steps and is unchanged.