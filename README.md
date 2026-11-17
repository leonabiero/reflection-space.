# Reflection Space

Reflection Space is a web application built for **EDE Fundazioa** (a social
services organisation in the Basque Country, Spain). It helps social workers
pause and reflect on their casework — surfacing possible blind spots, asking
whether the client's own voice has been heard, and pointing out information
that might be missing — before decisions are finalised.

It is not a case-management system and it does not evaluate or score
practitioners. It is a private reflective space that sits alongside their
existing work.

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
  written, and the average usefulness rating)
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
| Google Gemini | Since 15 November 2026 no text is sent to Gemini; only its availability is still checked on the System Health and cost screens | `services/embedding_service.py` |
| Claude (Anthropic) | Powers the reflection companion and writes the Pattern Review reports | `rdi/`, `services/reflection_service.py`, `services/pattern_text_analysis.py` |

**Data flow, in short:** a social worker writes, pastes or uploads a case on
the Reflection Space screen and presses **Reflect** → the text is anonymised
first (if that fails, nothing is sent anywhere) → only the anonymised text
goes to the RDI ("Reflective Decision Intelligence") layer in `rdi/`, which
uses Claude to generate reflective prompts (never directive advice) in the
language the worker chose. What is saved to Postgres: the reflection record
with a neutral, automatically created code and the **original** text (since
10 November 2026, agreed with EDE — stored in the EU database, readable only
by its author). Since 15 November 2026 Pattern Review has the AI read these
original texts, each anonymised again first, and shows managers only the
report (see `PATTERNS.md`). The AI's observations and questions are **not** saved. Messages typed into follow-up conversations
go through the same anonymisation before they
reach Claude, with the same "if it fails, nothing is sent" rule; exact ages
are replaced by life stages (see `REFLECTIONS.md`). The Qdrant search service,
which served the old document-based design, was removed in November 2026.

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
- **Erase all data** (System Administration, typed confirmation, System
  Administrator only) empties every data table so the real pilot starts from
  zero. User accounts, sign-in sessions and settings are kept. See
  `services/data_reset.py`. Nothing is ever erased automatically.

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
- Service Cost & Usage Monitor — tracks what Claude, Gemini, the
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

- `test_security_*.py` — access control, authentication, data anonymisation,
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
