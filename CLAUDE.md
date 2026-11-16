# Project instructions for Claude Code

Reflection Space is a Streamlit web app for EDE Fundazioa that helps social
workers reflect on their casework. `README.md` describes what it does, who
uses it and where things live; read it before starting any task.

## Working with the product owner

- The person giving instructions is the **product owner, not a developer**.
  Always explain things in simple, plain English.
- **Never show code, diffs or editing instructions**, and never ask the
  product owner to edit files themselves.
- **You make all changes directly** to the files in this folder.
- **Never push to GitHub** (and do not commit unless asked). The product
  owner pushes themselves with GitHub Desktop.
- If the product owner says **"let's just discuss"**, do not change any
  files until they say go ahead.
- When guiding the product owner through something they must do
  themselves, give **one step at a time** and wait for them to confirm
  before giving the next step.

## "Ready to push" summary

When a task is finished and checked, always end with a **"Ready to push"**
summary for GitHub Desktop:

1. **Summary** — a one-line commit title.
2. **Description** — a short plain-English description of what changed and
   why.
3. **Files** — the full list of changed, created and removed files.

## Languages and translations

- **Spanish is the default and master language**, then Basque, then
  English. Never change the default language.
- All user-visible text must go through the translation system
  (`services/language.py`, with the texts in `services/locales/es.py`,
  `eu.py` and `en.py`). Never hardcode user-facing text in a page file.
- Add new text in all three languages. If a translation is missing, use the
  Spanish text temporarily.

## Doing the whole job

- Complete the whole job: update every affected file, including
  translations, configuration, navigation (`navigation/`), documentation
  (`README.md` and the other `.md` files) and tests (`tests/`).
- **Run the tests before saying a task is finished**:
  `python -m pytest tests/ -v`. All tests must stay green; if a change
  breaks a test, the change is wrong, not the test. Tests named
  `*_postgres.py` are skipped unless `TEST_DATABASE_URL` is set.
- If something could not be checked, say so plainly.

## Safety rules

- **Never add new libraries, packages or outside services** without first
  explaining what they are, why they are needed and what they cost, and
  getting the product owner's approval.
- **Preserve existing features.** Do not remove anything without first
  checking it is truly unused, and avoid breaking changes.
- Never send the original case text to an AI provider: only anonymised text
  goes to Claude, and if anonymisation fails nothing is sent (see
  `REFLECTIONS.md`).
- Access checks happen both in the screens and in the service layer; keep
  both.
- Never bypass the database connection pool (`services/db_pool.py`) for
  application queries.
- Keep business logic out of `pages/` where possible; pages should call into
  `services/` and `rdi/`.
- Secrets (passwords, API keys, user accounts) live in Streamlit's secrets
  system, never in this repository.
