# Demonstrations with fictional data

Added on **17 November 2026** (product owner's decision) for the
18 November demonstration of Reflection Space and Pattern Review.

## The idea in plain words

Pattern Review needs many texts written over many months to show anything.
Real texts must never be used for a demo, and fictional texts must never
reach the real pilot's database. If they did, they would appear in real
Pattern Review reports and stay there for 15 months.

So there are **two separate apps**, built from the same code:

| | Real app | Demo app |
|---|---|---|
| Web address | the existing one | a second Streamlit app |
| Database | the real Neon project | a separate Neon project, used only for demos (EU region) |
| User accounts | real staff | demo-only accounts (one per role, demo passwords) |
| `DEMO_MODE` secret | not set | `"true"` |
| What you see | normal | a red **DEMO** banner on every page, and a "Demo data" section in System Administration |

You never switch one app between demo and real data: you open the demo
app's address for a demo and the real app's address for real work. One
push to GitHub updates both apps.

## What the demo data is

`services/demo_texts.py` holds **70 fictional practitioner notes** (52 in
Spanish, 18 in Basque) by eight fictional authors, spread over the last
13 months, plus **20 fictional usefulness ratings**. Every person and
situation is invented.

The notes repeat a few patterns over time on purpose, so Pattern Review
finds something meaningful: opinions written as facts, directive language
and warnings, decisions without reasons, missing context, charged labels
("familia desestructurada") and the person's own voice missing. About one
in six notes is written the other way (the person's own words, strengths,
plans agreed together), for contrast. A few notes mention sexual
orientation, gender identity, a specific illness or medicine, religion or
ethnic origin, so the anonymiser can be demonstrated on them.

The Basque notes should be checked by a native speaker before being shown
to Basque-speaking staff.

The notes are short (about 230 characters on average; some are one-line
entries, as real notes often are), so all 70 fit in two AI groups.

Loading the notes does **not** use the AI and costs nothing. Each Pattern
Review report on all 70 demo texts costs roughly $0.05–$0.10 and takes
about one to two minutes.

## Loading and removing (System Administrator, demo app only)

System Administration → **Demo data**:

- **Load demo data** — loads the 70 notes and 20 ratings. Only works once;
  press "Remove demo data" first to load them again.
- **Remove demo data** — removes the fictional notes and ratings, and every
  Pattern Review report in the demo database.

"Erase all data" in the demo app also clears everything. To get rid of the
demo completely, delete the demo app in Streamlit and the demo project in
Neon.

Reflections typed live in the demo app (by the demo practitioner account)
stay in the demo database until "Erase all data" is pressed there; they are
never in the real database.

## The locks (`services/demo_data.py`)

1. **Demo mode** must be on (`DEMO_MODE = "true"`, only in the demo app's
   secrets).
2. **Each database is labelled** "live" or "demo" the first time an app
   connects to it (`app.py`, stored in `app_settings`):
   - the real app labels its database "live";
   - the demo app labels a database "demo" only if it holds no reflections
     and no ratings at all.
   A label is never changed afterwards, and "Erase all data" keeps it.
3. **Demo texts are only loaded into a database labelled "demo".** If the
   demo app were ever connected to the real database, it would refuse to
   load anything and show a warning on every page. If the real app were
   ever connected to the demo database, it would show a warning on every
   page.
4. **System Administrator only**, checked in the service layer and on screen.
5. **Every demo row is marked** (its author starts with `demo:`), so
   removing demo data removes exactly those rows.

## Demo accounts

Demo-only accounts live **only in the demo app's secrets**, never in this
repository and never in the real app: one per role (Social Worker,
Supervisor, Programme Manager, System Administrator), with demo names and
demo passwords. Passwords are stored as bcrypt hashes, like real accounts.

## Setting it up (product owner)

1. Neon: create a new project for demos in the Frankfurt (EU) region and
   copy its connection address.
2. Streamlit Community Cloud: create a second app from this repository
   (`main` branch, `app.py`).
3. In the demo app's secrets: the demo database address, the Anthropic key,
   `DEMO_MODE = "true"` and the demo-only accounts.
4. Sign in to the demo app as the demo System Administrator and press
   **Load demo data**.
5. Sign in as the demo Supervisor and run a Pattern Review report before the
   meeting (the same report cannot be run again within about 10–15
   minutes).

## Tests

`tests/test_demo_data.py` — the fictional texts (how many, languages,
spread over 13 months, inside the 15-month limit), every lock, how a
database is labelled, loading and removing, the banner and translations in
all three languages, and that no password or password hash is in the code.
