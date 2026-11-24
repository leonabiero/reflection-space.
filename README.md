# Reflection Space

Reflection Space is a web application built for **EDE Fundazioa** (a social
services organisation in the Basque Country, Spain). It helps social workers
pause and reflect on their casework — surfacing possible blind spots, asking
whether the client's own voice has been heard, and pointing out information
that might be missing — before decisions are finalised.

It is not a case-management system and it never scores or judges
practitioners. Since November 2026 (EDE project team, approved by the
project leads) the AI gives a **direct, grounded analysis** of the
documentation: it clearly names stereotypes, biases, prejudices and loaded
labels, with reasons and exact quotes, and asks 1–2 questions per lens —
but never gives case decisions, action plans or suggested rewording. It is
a private reflective space that sits alongside their existing work.

Since October 2026 it is also **not a document store**: a professional
writes, pastes or uploads a case and reflects on it on the spot, and only the
reflection is kept — identified by a neutral code, never by the case text.
Since November 2026 the screen asks for nothing else: write or upload, choose
the language of the reflection, press **Reflect**. See `REFLECTIONS.md`.

## Who uses it

Four roles, each with different screens available to them:

- **Social Worker** — reflects on cases on the spot, uses the AI reflection companion
- **Supervisor** and **Programme Manager** — same as Social Worker, plus the
  Manager area: Pattern Review (AI reports on patterns in how cases are
  written, and the average usefulness rating). Since 18 November 2026 a
  manager who has downloaded a report can delete it, or all saved reports,
  after an "Are you sure?" step; reports are shared, so a deleted report is
  gone for the whole management team (see `PATTERNS.md`)
- **System Administrator** — same as Social Worker, plus user list, system
  health, the list of recorded problems, service costs, and the "Erase all
  data" action. No Manager area (since 15 November 2026)

Access to each screen and each action is checked in two places: once in the
screens themselves, and again inside the service layer underneath, so a
mistake in one place doesn't expose data it shouldn't.

## How it's built

| Piece | What it does | Where |
|---|---|---|
| Streamlit | The web app itself (all the screens) | `app.py` (start file), `pages/`; `demo_app.py` is the demo app's start file and only hands over to `app.py` (see `DEMO.md`) |
| PostgreSQL (hosted on Neon) | Stores accounts, reflections, logs | `services/db_*.py` |
| Claude (Anthropic) | Powers the reflection companion and writes the Pattern Review reports | `rdi/`, `services/reflection_service.py`, `services/pattern_text_analysis.py` |

**Data flow, in short:** a social worker writes, pastes or uploads a case on
the Reflection Space screen and presses **Reflect** → the text is anonymised
first (if that fails, nothing is sent anywhere) → only the anonymised text
goes to the RDI ("Reflective Decision Intelligence") layer in `rdi/`, which
uses Claude to analyse the text through eight lenses (never directive
advice) in the language the worker chose, and then writes one **analysis
report** that brings them together (one extra AI call; see "November 2026:
direct, grounded analysis" below). What is saved to Postgres: the reflection record
with a neutral, automatically created code and the **original** text (since
10 November 2026, agreed with EDE — stored in the EU database, readable only
by its author). Since 15 November 2026 Pattern Review has the AI read these
original texts, each anonymised again first, and shows managers only the
report (see `PATTERNS.md`). The AI's observations and questions are **not** saved. Messages typed into follow-up conversations
go through the same anonymisation before they
reach Claude, with the same "if it fails, nothing is sent" rule. Since
November 2026 (approved by EDE) the anonymiser hides direct identifiers
only — names (numbered: `[PERSONA 1]`, `[PERSONA 2]`…), addresses, IDs,
phones, emails, dates, towns and organisations, plus political opinion and
trade union membership — and deliberately leaves visible the context where
bias tends to appear (sex, origin, nationality, migration status, religion,
exact age, health, substance use, disability, sexual orientation). The
placeholders are written in the language of the reflection (Spanish
`[DIRECCIÓN]`, Basque `[HELBIDEA]`, English `[ADDRESS]`); the words live in
`services/locales/*.py` (`anon_placeholders`). See `REFLECTIONS.md`. What
each placeholder means is explained in plain words, in all three languages,
on the System Administration anonymiser test, under "View anonymised text"
and in Help. The Qdrant search service,
which served the old document-based design, was removed in November 2026,
and Google Gemini (which no longer received any text) on 18 November 2026:
Claude is now the only AI service.

## November 2026 clean-up

At the product owner's request the app was trimmed to what the pilot needs:

- **Removed screens:** Learning (Team Presence, Knowledge Assistant, Learning
  Insights, Team Learning), Text analysis, Research Metrics, and the retired
  Documentation redirect page.
- **Reflection History** shows only the *average* usefulness rating — never
  individual ratings, comments or who gave them.
- **15 November 2026:** Rating a reflection is optional, through a small
  "Rate" button in the corner of the results; "Finish reflection" no longer
  leads to a feedback step.
- **15 November 2026 (later the same day): Pattern Review redesigned.**
  Patterns are looked for in what social workers write, not in the AI's
  output: the saved original texts, anonymised again before the AI reads
  them. Managers pick a period and get an AI report (never the
  texts) — since 17 November 2026 they type any number of months from 1
  to 15 (it was 3, 6, 9 or 12). The AI's
  observations and questions are no longer saved, so Reflection History is
  one line per reflection and the per-reflection AI summary was removed.
  See `PATTERNS.md`.
- **15 November 2026 (evening): Reflection History removed.** With nothing
  saved to show, the page had no job left. The average usefulness rating
  moved to the top of Pattern Review; Manager mode opens on Pattern Review;
  the System Administrator no longer has Manager mode (deleting a single
  reflection is now done by its author; "Erase all data" still clears
  everything).
- **System Administration** lost "Erase old stored documents", "Configuration"
  and "Case Knowledge Search". The Diagnostic Centre is now a plain list of
  recorded problems (what happened, when, status); the AI diagnosis still
  arrives in the alert email. Problems are recorded exactly as before.
  Since 18 November 2026 each problem also shows the ready-to-paste Claude
  Code prompt from its alert email (most recent occurrence), with a copy
  button. It is the exact text saved with the record when the email was
  made, read through one shared helper (`services/error_log.py`), so the
  email and the screen can never differ; no extra AI call is made. Older
  records without a saved prompt show a short "no prompt" message.
- **Erase all data** (System Administration, typed confirmation, System
  Administrator only) empties every data table so the real pilot starts from
  zero. User accounts, sign-in sessions and settings are kept. See
  `services/data_reset.py`. Nothing is ever erased automatically.

## November 2026: direct, grounded analysis

Requested by the EDE project team and approved by the project leads:

- **AI instructions** (`rdi/companions/prompt_builder.py`): "Your role is NOT
  to judge or criticise, but it IS to assess and analyse." Direct and frank,
  no softening, no suggested question openings; the EDE framework for
  reflective practice analysis (5 areas) is the AI's checklist. Each lens
  gives a 2–4 sentence analysis, 1–2 questions and exact quotes tagged as
  bias, stereotype, prejudice or loaded label. The chat ("Explore with the
  companion") follows the same tone.
- **Cards** show the analysis open, then the typed quotes, then the questions.
- **Analysis report** (`services/analysis_report.py`): one extra call after
  the lenses; shown under the cards, with an optional **Download report**
  button underneath it (`services/reflection_report_html.py`, printable page
  with anonymised text only). If it fails, the cards still show and there is
  one Retry button. Nothing is saved.
- **Highlighted text** (`services/highlight.py`): the anonymised text with
  every exact quote highlighted, one colour and underline style per type,
  the type also in words, with a legend. Since 24 November 2026 the colours
  are solid with dark text (Sesgo yellow, Prejuicio red, Estereotipo blue,
  Etiqueta cargada purple), so they look the same on the dark screen, a
  light screen and paper, and both downloadable reports keep their colours
  when printed. The "View anonymised text" preview shows the text as
  written (paragraphs and accents kept), like the highlighted text.
- **Chat replies** ("Explore with the companion") can be up to 1,000 tokens
  (was 400, which cut replies mid-word); see `SERVICE_USAGE_MONITORING.md`.
- **Pattern Review** names repeated biases frankly ("When the same bias is
  repeated, it creates a pattern."), never the writers, and always keeps
  its limitations section.
- **Cost:** about $0.07 per reflection instead of about $0.038 (see
  `SERVICE_USAGE_MONITORING.md`).

## Demonstrations (17 November 2026)

Demonstrations use a **separate demo app with its own empty database**,
filled with about 70 fictional texts, so demo data can never mix with the
real pilot's data. The demo app shows a red "DEMO" banner on every page.
See `DEMO.md` for how it is set up, how demo data is loaded and removed,
and the locks that stop demo texts reaching the real database.

## Where things live

- `pages/` — one file per screen the user sees
- `services/` — the actual logic: database access, authentication,
  translations, rate limiting, error logging, etc. Pages call into services
  for this. A handful of services (session tracking, pagination controls,
  language selection) are screen-glue by nature and do use Streamlit
  directly — that's a deliberate, reviewed choice, not business logic
  leaking into the wrong layer.
- `rdi/` — the reflection companion's "thinking": builds context, calls
  Claude, assembles the conversation
- `navigation/` — decides which menu items and pages a given role can see
- `load_test/` — a toolkit for simulating many users at once, used to test
  the database connection pool under load
- `tests/` — automated tests, grouped by what they protect: security,
  reliability, scalability
- Service Cost & Usage Monitor — tracks what Claude, the
  database, and SMTP are actually costing/being used, shown on System
  Administration → "Service Usage & Costs". See `SERVICE_USAGE_MONITORING.md`.

## Translations

All user-visible text goes through `services/language.py` (the texts
themselves live in `services/locales/es.py`, `eu.py` and `en.py`). Spanish is the
default and master language; Basque and English are also supported. If a
translation is missing for a given key, the app falls back to Spanish so it
never shows a broken or empty label. New screens or messages must add their
text to this file in all three languages — nothing should be hardcoded in a
page file.

## Configuration

`config.py` centralises settings that vary by environment (database
connection details, AI provider settings, timeouts). Actual secrets
(passwords, API keys, user accounts) live in Streamlit's secrets system, not
in this repository.

## Running the tests

```
pip install -r requirements.txt
pip install pytest
python -m pytest tests/ -v
```

Tests are organised by what they guard:

- `test_security_*.py` — access control, authentication, data anonymisation
  (including sensitive personal details and where their labels are
  explained, `test_security_anonymizer_special_categories.py`),
  deletion behaviour (Phase 1)
- `test_reliability_*.py` — retries, rate limiting, error recovery
  (Phase 2)
- `test_scalability_*.py` — pagination, caching, load behaviour under many
  concurrent users (Phase 3)
- `test_reflection_records_*.py` — the reflection-only design: neutral codes,
  case themes, who may read the saved original text, similar-reflection matching
- `test_demo_data.py` — the demo app: the fictional texts, the locks that
  keep demo texts out of the real database, loading and removing, the
  banner and translations, and no password in the code
- `test_frank_analysis_prompts.py`, `test_analysis_report.py`,
  `test_highlight.py`, `test_anonymizer_context_and_numbering.py` — the
  November 2026 changes: the AI's wording, the analysis report and typed
  quotes, the highlighted text, and the anonymiser's numbered,
  language-specific placeholders and visible context
- `test_anonymizer_home_visit_fixes.py`, `test_accents_preserved.py` — the
  24 November 2026 fixes: service names, Bilbao neighbourhoods and floor/door
  in addresses (with checks that real names stay hidden), and accents and
  paragraph breaks surviving from a Word document to the preview
- `test_simple_reflection_screen.py` — the simplified screen: typed text vs
  uploaded document, the AI only ever receiving anonymised text, no fallback
  when anonymisation fails, the chosen language reaching every AI call

Tests named `*_postgres.py` need a throwaway PostgreSQL database and are
skipped unless `TEST_DATABASE_URL` is set.

All tests must stay green. If a change breaks one of these, the change is
wrong, not the test.

## Continuous Integration

Two GitHub Actions workflows run automatically on every push, in
`.github/workflows/`: `security-tests.yml` and `reliability-tests.yml`. Both
must pass before a change is considered safe to keep.

## Contributing safely

- Never hardcode user-facing text — add it to the translation files in
  `services/locales/` in all three languages.
- Never send the original case text to an AI provider: only the anonymised
  text goes to Claude. Since 10 November 2026 (agreed with EDE) the original
  text is stored, time-limited, in the EU database and read only under the
  rules in `REFLECTIONS.md` ("Saved ORIGINAL text").
- Never bypass the database connection pool (`services/db_pool.py`) for
  application queries — it exists to keep the app stable under load.
- Keep business logic out of `pages/` files where possible — pages should
  mostly call into `services/` and `rdi/`.
- Run the full test suite before considering any change finished.
