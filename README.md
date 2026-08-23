# Reflection Space

Reflection Space is a web application built for **EDE Fundazioa** (a social
services organisation in the Basque Country, Spain). It helps social workers
pause and reflect on their casework — surfacing possible blind spots, asking
whether the client's own voice has been heard, and pointing out information
that might be missing — before decisions are finalised.

It is not a case-management system and it does not evaluate or score
practitioners. It is a private reflective space that sits alongside their
existing work.

## Who uses it

Four roles, each with different screens available to them:

- **Social Worker** — writes reflections, uses the AI reflection companion
- **Supervisor** — same as Social Worker, plus visibility into their team
- **Programme Manager** — organisation-wide activity views, no individual
  case content
- **System Administrator** — user management, system health, diagnostics

Access to each screen and each action is checked in two places: once in the
screens themselves, and again inside the service layer underneath, so a
mistake in one place doesn't expose data it shouldn't.

## How it's built

| Piece | What it does | Where |
|---|---|---|
| Streamlit | The web app itself (all the screens) | `app.py`, `pages/` |
| PostgreSQL (hosted on Neon) | Stores accounts, reflections, logs | `services/db_*.py` |
| Qdrant | Vector search — finds similar past reflections/cases | `services/qdrant_service.py` |
| Google Gemini | Turns text into the numbers Qdrant searches on | `services/embedding_service.py` |
| Claude (Anthropic) | Powers the reflection companion and the Knowledge Assistant | `rdi/`, `services/knowledge_assistant.py` |

**Data flow, in short:** a social worker writes a reflection → it's saved to
Postgres → a copy is turned into a search-friendly format by Gemini and
stored in Qdrant → the RDI ("Reflective Decision Intelligence") layer in
`rdi/` uses that context plus Claude to generate reflective prompts, never
directive advice.

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

## Translations

All user-visible text goes through `services/language.py`. Spanish is the
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

All tests must stay green. If a change breaks one of these, the change is
wrong, not the test.

## Continuous Integration

Two GitHub Actions workflows run automatically on every push, in
`.github/workflows/`: `security-tests.yml` and `reliability-tests.yml`. Both
must pass before a change is considered safe to keep.

## Contributing safely

- Never hardcode user-facing text — add it to `services/language.py` in all
  three languages.
- Never bypass the database connection pool (`services/db_pool.py`) for
  application queries — it exists to keep the app stable under load.
- Keep business logic out of `pages/` files where possible — pages should
  mostly call into `services/` and `rdi/`.
- Run the full test suite before considering any change finished.
