# Corpus analysis (Text analysis)

A manager-only area for finding wording and ideas that recur across a
collection of existing texts (for example EDE's ~70 raw, already-anonymised
Spanish/Basque texts), **before** practitioners' own observations are used.

Page: `pages/corpus_analysis.py` · menu entry "📚 Análisis de textos" (Manager mode).

## Who can use it
Supervisors and Programme Managers only (same rule as Pattern Review:
`services/pattern_access.py`). Social Workers and the System Administrator are
refused both in the menu **and** in the data layer (`services/corpus_store.py`).

## How it works
1. Create a collection and add texts: files (txt/Word/PDF) one by one, many at once, or paste.
   Each text is name-scrubbed with the app's automatic anonymiser (a safety net, not a guarantee),
   cut into short passages (exact pieces of the text) and given a neutral number (T-001…).
   Numbers are never reused. File names are never stored. The same text added twice is detected.
2. "Look for recurring passages": passages get a meaning-vector (cached, one per passage),
   similar passages are grouped, and a group is kept only if it appears in **at least N different
   texts** (default 3) and has at least 3 passages. One long text that repeats itself can never create a pattern.
3. One AI explanation per group, cautious wording, never claims bias; the strength is always
   "appears in X of N texts".
4. The team records its judgement (status + comment), can challenge a passage, and sees the history.
   Judgements are carried over when the same group is found again.

## Step 2: reading each text with the reflection lenses
Section "Leer cada texto con las lentes de reflexión" (`services/corpus_reading_service.py`).
- Each text is read ALONE with the same eight lenses practitioners use (`rdi/companions`): 8 AI calls per text, about $0.05 per text (≈ $3.50 for 70 texts; shown on screen before each batch).
- Batches of 10 texts per click, resumable (unread texts are picked up next time); one reading job at a time.
- Quotes are checked against the stored text (`services/evidence.py`); unverifiable ones are dropped and counted.
- "Raised in X of N texts" = the AI raised an observation; it is NOT a measure of how often something happens, and "nothing raised" does not mean "free of it". The page says so.
- Results are browsable per lens (all texts where it was raised, with exact quotes) and per text (all lenses). Reading again replaces the old reading; "Borrar las lecturas" clears a collection's readings.
- Tables: `corpus_readings`, `corpus_reading_jobs` (erased with their text/collection). Prompt version `2026-10-corpus-reading-1`.
- The questions switch applies here too: off = AI told not to write questions, none stored or shown.

## Step 3: the word and phrase list
- A manager keeps a list of words and short phrases per collection (`corpus_terms`, erased with the collection, at most 200 terms).
- For each term the page shows "in X of N texts" and how many times it appears; per text (choose a text), and where it appears (with short exact excerpts around it). A semicolon-separated CSV of the whole table (terms x texts) can be downloaded: it contains only the typed terms and counts, never text from the documents.
- Matching (`services/corpus_terms.py`, pure, no AI): capitals and accents ignored (but ñ is not n), whole words only, phrases match in order, a `*` at the end of a word means "any ending" (`etxe*` finds etxea, etxeak, etxean). Typed terms are checked and escaped; they can never act as a regular expression.
- Counts are computed live from the stored texts, so deleting a text or editing the list is always reflected.
- A starter list (`STARTER_TERMS_ES`, `STARTER_TERMS_EU`) can be added with one button; each term remembers its origin (`manager`, `starter_es`, `starter_eu`). **The Basque starter words need a native speaker's review**; the page says so while any are on the list.
- The page says what a count is not: a word can be used to deny something, and an idea can be present without any listed word.

## Printable report
`services/corpus_report_builder.py` (pure) builds one self-contained HTML page for paper (like the Pattern Review report). The manager chooses the parts: patterns of a chosen search (with the status filter), the lens reading, the word list; and whether to include exact passages/quotes and team comments. It always shows "in X of N texts", names texts only as T-001..., states that the texts carry no labels (so groups cannot be compared), honours the questions switch, escapes everything, includes no scripts and loads nothing from outside.

## Switch: AI-written questions
On by default. When off, the AI is told not to write questions, any it sends is dropped, none are stored or shown.

## Limits (honest)
- The texts have **no labels**, so the page cannot say anything about unequal treatment of any group.
- Similarity thresholds (broad 0.72 / balanced 0.78 / strict 0.84) are **uncalibrated starting points**.
- Grouping Spanish and Basque passages together relies on multilingual embeddings and is **untested**.
- At most 3000 passages per search, 20 groups explained, 500 texts per collection, 50 collections.
- Basque wording of the screens needs a native speaker's review.
- The word list counts written words only (no synonyms, no context).

## Cost
Embeddings ≈ $0.015 per ~1000 passages (once per passage). Explanations: up to 20 per search, a few cents.

## Data
Tables: `corpora`, `corpus_documents`, `corpus_passages`, `corpus_passage_embeddings`, `corpus_pattern_runs`,
`corpus_patterns`, `corpus_pattern_passages`, `corpus_pattern_events`, `corpus_readings`, `corpus_reading_jobs`, `corpus_terms` (all in `services/db_schema.py`).
Deleting a text or collection erases passages, vectors and their place in patterns (cascade).
The collection is separate from practitioner data; nothing joins to drafts, reflections or observations.

## Tests
`tests/test_corpus_engine.py`, `tests/test_corpus_terms.py`, `tests/test_corpus_report.py`, `tests/test_corpus_static.py`, `tests/test_corpus_store_postgres.py`
(real database via `TEST_DATABASE_URL`), plus the clustering speed/equivalence tests in `tests/test_patterns_engine.py`.
