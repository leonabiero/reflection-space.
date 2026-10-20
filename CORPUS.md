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

## Switch: AI-written questions
On by default. When off, the AI is told not to write questions, any it sends is dropped, none are stored or shown.

## Limits (honest)
- The texts have **no labels**, so the page cannot say anything about unequal treatment of any group.
- Similarity thresholds (broad 0.72 / balanced 0.78 / strict 0.84) are **uncalibrated starting points**.
- Grouping Spanish and Basque passages together relies on multilingual embeddings and is **untested**.
- At most 3000 passages per search, 20 groups explained, 500 texts per collection, 50 collections.
- Basque wording of the screens needs a native speaker's review.
- Not yet built: per-text reading with reflection lenses (Step 2), editable word/phrase list with per-text counts (Step 3), printable corpus report.

## Cost
Embeddings ≈ $0.015 per ~1000 passages (once per passage). Explanations: up to 20 per search, a few cents.

## Data
Tables: `corpora`, `corpus_documents`, `corpus_passages`, `corpus_passage_embeddings`, `corpus_pattern_runs`,
`corpus_patterns`, `corpus_pattern_passages`, `corpus_pattern_events` (all in `services/db_schema.py`).
Deleting a text or collection erases passages, vectors and their place in patterns (cascade).
The collection is separate from practitioner data; nothing joins to drafts, reflections or observations.

## Tests
`tests/test_corpus_engine.py`, `tests/test_corpus_static.py`, `tests/test_corpus_store_postgres.py`
(real database via `TEST_DATABASE_URL`), plus the clustering speed/equivalence tests in `tests/test_patterns_engine.py`.
