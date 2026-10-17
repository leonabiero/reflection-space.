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
- Service Cost & Usage Monitor — tracks what Claude, Gemini, Qdrant, the
  database, and SMTP are actually costing/being used, shown on System
  Administration → "Service Usage & Costs". See `SERVICE_USAGE_MONITORING.md`.

## EDE reflection workflow (pilot)

A second, separate screen — **EDE Reflection** (`pages/ede_reflection.py`,
Practitioner workspace) — helps professionals reflect on how ONE selected
text documents an intervention. It exists alongside the original Reflection
Space; nothing of that flow was changed.

**Principle.** The object of learning is professional practice, not the
people receiving support. Every result is an AI *hypothesis* for
discussion. The workflow never scores or ranks people, cases or
professionals, never decides eligibility, diagnosis or risk, and never
labels a professional as biased.

**How a request flows** (`services/ede_analysis.py`):

1. the text is validated (not empty, not too short/long);
2. the actor's role is checked again inside the service (fails closed);
3. the existing anonymiser (`services/anonymizer.py`) is applied;
4. the document language (Spanish / Basque / English / mixed) is detected
   locally, without any new library;
5. programme and document type (from `config.py`) are added to the prompt;
6. the configured Claude client (`services/reflection_service.py`, same
   model, timeout, usage ledger and concurrency cap as the rest of the app)
   analyses all **eight dimensions** in one call;
7. the reply must be one JSON object matching a strict schema;
8. every quotation must appear verbatim in the text that was sent to the
   model (whitespace aside); its paragraph number is recorded;
9. malformed findings and unsupported quotations are discarded and counted
   (never repaired, never replaced);
10. only validated findings reach the screen or an export.

**The eight dimensions** (`services/ede_framework.py`): strengths vs
deficits · observation vs interpretation · labels · stereotypes and
assumptions · evidence for decisions · missing information · contradictions
and change · the person's voice. Findings that rest on wording carry an
exact quotation; findings about something *not written* use the
`absence_in_document` type, carry no quotation, and are always shown with the
reminder that "not in this text" does not mean "unknown". A single document
can only show contradictions *inside that text*, never change over time.

**Defaults and configuration.** Programme *Social Accommodation – Bizkaia*,
document type *Follow-up report*, language *automatic*. Change them in
`config.py` (`EDE_DEFAULT_PROGRAMME`, `EDE_DEFAULT_DOCUMENT_TYPE`) or with
environment variables of the same name. Limits: `EDE_MAX_DOCUMENT_CHARS`
(20 000), `EDE_MAX_UPLOAD_BYTES`, `EDE_ANALYSIS_MAX_TOKENS`,
`EDE_MAX_PROVIDER_ATTEMPTS`, `EDE_MAX_FINDINGS_PER_DIMENSION`. The only
secret needed is the existing `ANTHROPIC_API_KEY`.

**What is stored.** Nothing new. The text, the results and the
professional's feedback live only in the browser session and disappear on
"Clear" or logout. Nothing is written to PostgreSQL or Qdrant and the text is
never embedded. Existing operational records are used as before: the usage
ledger (token counts only) and, on failure, the error log (exception class
name only — never document text or provider messages). Exports are produced
in memory and contain validated findings plus the user's own notes, never the
full document.

**Not yet done / needs a human decision before real reports are used:**

- EDE approval and a data-processing agreement for sending social-work text to
  the AI provider, and confirmation of the provider's retention terms. Until
  then use synthetic or fully invented texts only.
- The model name in `services/reflection_service.py` (`CLAUDE_MODEL`) has been
  reused as-is; confirm it with the provider before the pilot.
- A native Basque speaker should review `services/locales/ede_eu.py`.
- The anonymiser is pattern-based: it reduces risk but cannot catch every
  indirect identifier (rare events, unusual combinations of details).
- Comparing several documents over time is **not** built. The natural place
  for it is a new service that takes several already-validated results with
  verified chronology; it must never merge documents from unrelated people or
  link them by guessing identity.
- Language detection is a simple word-frequency check; the professional can
  override the explanation language.

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
- `test_ede_*.py` and `test_security_ede_workflow.py` — the EDE reflection
  workflow: analysis, evidence checking, interface, privacy

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
