# Pattern Review (Stage 2)

A page for EDE's management team (**Supervisors and Programme Managers only**) that looks for
themes repeating across the observations made in professionals' reflections.

## What it is and is not
- It shows **candidate patterns for reflection**. It never says bias or poor practice has been found.
- The team records its own judgement (Candidate / Under review / Worth discussing / Not supported / Archived).
  The AI's original wording is never overwritten; every change goes into a history.

## Privacy rules (enforced in the database layer, `services/pattern_store.py`)
- **Every saved observation is used** (product owner decision, 10 November 2026). Until then only observations whose
  author ticked "Share this observation with the team review" were used; that tick was removed from the screen and the
  stored flag (`finding_feedback.shared_with_team`) is no longer read. All data at the time was synthetic test data.
- Management sees the observation and its exact quotation only. Never the author, never private notes or ratings.
- Deleting the reflection (immediately when put in the 48-hour bin), or deleting its source documents, removes the
  observation from the pool. Patterns left with no members are deleted; partly affected patterns show a warning
  ("regenerate before relying on the written explanation").
- Roles: `services/pattern_access.py` (System Administrator is deliberately excluded).

## How a search works
1. Observations are turned into meaning vectors (Gemini embedding, cached per observation).
2. They are grouped by similarity (numpy only; no new package). Levels: Broad 0.70, Balanced 0.76, Strict 0.82.
3. A group is shown only with at least N observations from at least M distinct reflections (defaults 3 and 2).
4. One Claude call per group writes a cautious explanation from the observation text only (no quotes, cases, dates, authors).
5. The result is a saved snapshot. A new search never edits an old one; earlier reviews are carried over when the same group reappears (50% overlap).

## Counts
Observations, reflections and cases are always shown separately. "Across cases" is only said when every reflection has a case
reference. Case references are typed by hand, so a typo can split one case in two.

## Cost
About $0.00002 per observation embedded (once), about $0.007 per written explanation, at most 20 per search (~$0.14).
Nothing is paid again until someone presses the button.

## Limits (be honest about these)
- Thresholds are starting points, not calibrated values. Compare settings before trusting results.
- The observations come from the reflections made in the app; they are not necessarily representative of the organisation.
- The written explanation can still reflect an observation deleted after the search (flagged on screen).
- Basque texts need review by a native speaker. EDE should confirm that all observations may be used for the team review.

## Tests
`tests/test_patterns_engine.py`, `tests/test_patterns_static.py`, and `tests/test_patterns_store_postgres.py`
(real database; set `TEST_DATABASE_URL`).

## Stage 3: printable report
On the Pattern Review page, the "Printable report" section builds one downloadable web page (`services/report_builder.py`)
for the patterns currently shown (filtered by status). Open it in a browser and print or save as PDF (A4, confidentiality
footer on each page). No extra software or outside service is used.
- Same cautious wording as the screen: "candidate pattern", "not a conclusion", a standing list of limits.
- No author names (even of the managers who commented) and no private notes.
- Options: include observations and exact quotations (on by default), include team comments (on), include case
  references (off by default, because paper travels further than a screen).
- Everything is escaped, the page loads nothing from outside and runs no scripts.
- Tests: `tests/test_patterns_report.py`.
