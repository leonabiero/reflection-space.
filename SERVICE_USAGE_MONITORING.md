# Service Cost & Usage Monitor

This document explains the "💰 Service Usage & Costs" panel on the
System Administration page: what it measures, how it calculates a
dollar figure, what it deliberately does NOT calculate, and how to
keep it accurate as providers change their prices. It complements
`OPERATIONS.md` (day-to-day running of the app) and `README.md`
(overall architecture).

## What it monitors

| Service | What's tracked | Cost shown? |
|---|---|---|
| Claude (Anthropic) | Every reflection companion call, every retry, every companion follow-up conversation, every Pattern Review call (`pattern_text_batch`, `pattern_text_report`) | Yes — from actual token usage |
| PostgreSQL (Neon) | This app's own connection-pool usage | No — this is an *application* metric, not Neon's bill (see below) |
| Streamlit | Active sessions, where reliably measurable | No — hosting cost isn't available from this deployment |
| SMTP | Alert emails sent/failed | No — depends on whatever email provider is configured |

Google Gemini was removed on 18 November 2026 (no text had been sent to it
since 15 November), so it is no longer listed. Old Gemini rows already in
the `service_usage` table are simply no longer shown.

## How a cost is calculated

Every dollar figure on the panel comes from the same two steps:

1. **Record actual usage.** Every Claude call is
   instrumented at its call site (`services/reflection_service.py`,
   `services/pattern_text_analysis.py`)
   to capture the token counts the *provider itself* reports back —
   `message.usage.input_tokens` / `output_tokens`. **The
   `max_tokens` a call is allowed to use is never treated as the
   number of tokens it actually used** — that would overstate cost
   every time a response finishes early.

2. **Price it centrally.** `services/cost_pricing.py` is the *only*
   place a provider's price per token is written down. Everything else
   — the ledger, the dashboard, the forecast — calls into that one
   file. If Anthropic changes its prices, updating the cost
   shown everywhere in the app is a one-line edit in that single file
   (see "Updating pricing" below).

Every usage event is written to a `service_usage` database table
(`services/usage_ledger.py`) in the background, off the request path,
so recording usage can never add latency to — or ever cause a failure
of — a practitioner's reflection, a Pattern Review report, or an email. If the
database write itself fails, it's logged and silently dropped; the
only consequence is a slightly incomplete dashboard, never a broken
feature.

## What counts as exact vs. an estimate

- **Exact:** Claude token counts (from the API response).
- **Estimate:** any cost computed from a token count when the model
  name wasn't recognized in `cost_pricing.py` (falls back to the
  default Claude model's price, and is flagged
  `cost_is_estimate`). The dashboard shows a warning caption whenever
  this happened during the period being viewed.
- **Unavailable, not guessed:** Neon's own compute/storage billing
  (this app has no API access to it — the panel says "Provider billing
  data unavailable" rather than inventing a figure), Streamlit hosting
  cost, and any service's "% of limit" when no budget or capacity has
  been configured (shows "Limit unavailable").

## Cost per reflection

One reflection currently triggers **8 parallel companion calls** (see
`rdi/orchestrator.py`), each logged as its own `service_usage` row —
including any retried attempts. The panel's "Average Claude cost per
reflection" is:

```
sum(estimated cost of every companion_reflection row in the window)
÷ (number of completed reflections in that window)
```

A median is intentionally NOT shown: individual companion rows aren't
currently tagged with which specific reflection they belong to, so
only the aggregate mean can be computed honestly. Retry rate is shown
alongside it (failed companion attempts ÷ total companion attempts).

**Pattern Review reports (15 November 2026).** The per-reflection AI
summary (`reflection_summary`) was removed, so a reflection no longer costs
anything beyond its companion calls. Pattern Review costs money only when a
manager presses "Identify patterns": one Claude call per group of up to 40
texts (`pattern_text_batch`) plus one final call (`pattern_text_report`).
See `PATTERNS.md` for the cost table by period (1–15 months) and
`services/pattern_text_analysis.py`.

**Sensitive-label sentence (18 November 2026).** Every reflection companion
call, follow-up conversation and Pattern Review group now includes one extra
sentence (about 60 input tokens) explaining the anonymiser's labels such as
`[HEALTH]`. That adds about $0.001 per reflection (8 calls), about $0.0001
per follow-up message, and about $0.0001 per Pattern Review group (around
$0.008 for a full 15-month report) — roughly $0.10 a month at the pilot's
expected volume.

## User-volume forecast

The "Common scenarios" table (Current / 100 / 250 / 500 / 1,000 users)
projects cost by multiplying the pilot's own currently-measured average
cost per reflection by a hypothetical reflection volume. **This is
always labeled an estimate.** It does not model prompt-caching hit
rate changes, retry-rate changes, or document-length changes at higher
volume — all of which can move the real number in either direction.

## Alerts

`services/usage_alerts.py` reuses the existing email alert system
(`services/email_alert.py`) — there is no second notification channel.
When a service crosses the 70% / 85% / 95% threshold, one email is sent. The last-alerted tier is remembered in
the existing `app_settings` key-value table so the same crossing never
re-sends on every page load; dropping back to green and crossing again
later re-arms the alert.

## Updating pricing

1. Open `services/cost_pricing.py`.
2. Update the relevant rate in `ANTHROPIC_PRICING`.
3. Update that entry's `effective_date` to today.
4. Nothing else needs to change — every dashboard figure recalculates
   from the same registry automatically.

## Configuring budgets

Monthly budgets (used only for the dashboard's status colour, never
sent to any provider) are environment variables, set the same way as
every other configuration value in `OPERATIONS.md`:

| Setting | Default | What it's for |
|---|---|---|
| `MONTHLY_BUDGET_ANTHROPIC_USD` | 50 | Claude monthly budget ceiling |

(`MONTHLY_BUDGET_GEMINI_USD` was removed with Gemini; if it is still in the
hosting secrets it is ignored.)

## What happens if monitoring itself fails

Nothing, from the practitioner's point of view. Every instrumentation
point wraps its usage-recording call so that a database outage, a
full recording queue, or any other monitoring-side failure is caught,
logged, and ignored — the reflection, report or email that
triggered it always completes exactly as if monitoring weren't there.
See `services/usage_ledger.py`'s module docstring for the full design
reasoning, and `tests/test_service_usage_monitoring.py` for tests that
enforce this.

## Privacy

The `service_usage` table never stores reflection text, AI responses,
case content, names, emails, or secrets — only counts, token numbers,
timing, and a small allowlisted label (a companion name, an operation
name, a model name). See `services/usage_ledger.py`'s
`_METADATA_ALLOWLIST` for the exact, enforced list of what's permitted
in that table's `metadata` column.

## November 2026 — cost of the direct analysis and the analysis report

Estimate (Claude Sonnet 5.5, $2 / $10 per million input / output tokens),
for a typical text of about 550 tokens:

| | Input tokens | Output tokens | Cost |
|---|---|---|---|
| Before: 8 lenses | ~14,000 | ~1,040 | ~$0.038 |
| Now: 8 lenses (longer instructions with the EDE framework; longer analysis and typed quotes) | ~16,800 | ~2,160 | ~$0.055 |
| Now: analysis report (1 call) | ~3,700 | ~900 | ~$0.016 |
| **Now: total** | ~20,500 | ~3,060 | **~$0.072** |

About **$0.033 more per reflection** (range $0.06–$0.09 in total). At about
90 reflections a month: roughly **$3 more a month**. Reply ceilings: lens
1,280 → 2,000 tokens; analysis report 6,000 (new); chat 400 (unchanged);
Pattern Review 12,000 (unchanged). Ceilings are not costs: only tokens
actually used are billed. The report call is recorded as `analysis_report`
and is included in "Average Claude cost per reflection".

## 24 November 2026 — Berriz framework completed in the instructions

The shared instructions grew by about 1,200 characters (≈ 300 input tokens
per call): the Berriz guiding question for each of the five framework areas,
the sources, "language is never neutral", the AI as a tool for contrast and
"do give a well-founded assessment". Each reflection makes
9 calls (8 lenses + analysis report), so ≈ 2,700 more input tokens ≈
**$0.005 more per reflection** (≈ $0.072 → ≈ $0.077). At 70–100
reflections a month: **≈ $0.40–0.55 more a month**. Chat: the instructions
are cached, so well under a tenth of a cent per conversation. Pattern
Review: under $0.01 more per report. Reply length is not expected to change.

## 24 November 2026 — chat reply ceiling 400 → 1,000 tokens

Replies in "Explore with the companion" sometimes stopped mid-word ("Ahí se
ve cóm") because they reached the 400-token ceiling. The ceiling is now
1,000 tokens (`CHAT_REPLY_MAX_TOKENS` in `services/reflection_service.py`);
the instructions still ask for 1–4 sentences and were not changed. If a
reply ever still reaches the ceiling, it is shown up to its last complete
sentence (no extra AI call).

Cost: a normal short reply costs exactly the same as before (about $0.01
per chat message, mostly re-reading the case). Only a reply that would
have been cut costs more: at most about $0.006 extra (600 more output
tokens at $10 per million), typically $0.001–$0.002. At pilot volumes this
is well under $1 a month.

## 27 November 2026 — Reflection timing (Batch 1, measurement only)

Practitioners said the wait after pressing **Reflect** feels long. The
investigation estimated 35–70 seconds, mostly two AI rounds one after the
other (the eight lenses, then the analysis report). Before anything is
changed, the app now **measures** the real times and the real cost, so the
speed improvements (Batch 2) are chosen on real numbers. Nothing changes
for practitioners.

- **What is measured** (`services/reflection_timing.py`): each step after
  pressing Reflect, on our server. That covers:
  - the page reload;
  - anonymisation;
  - the hourly limit check;
  - the double-click guard;
  - each of the eight lenses (with their retries), and the wait for all eight;
  - the analysis report;
  - each saving step (including the duplicate-text check and the
    expired-text clean-up);
  - drawing the results;
  - the total.

  The time the browser and the internet take is **not** included.
- **What is stored:** a new table, `reflection_timings`. Each row holds
  only the reflection code, a step name from a fixed list and whole
  milliseconds. It **never** holds case text, anonymised text, quotes, AI
  answers, names, roles or the language. Times are kept in memory while
  the reflection runs and saved in one background write after the results
  are shown, so the practitioner never waits for them. If saving fails, a
  warning goes to the server log and the reflection is not affected. The
  eight lenses record at the same time, so the stopwatch is protected by a
  lock and nothing is lost or mixed up.
- **When it is deleted:**
  - automatically after `REFLECTION_TIMING_RETENTION_DAYS` (30);
  - with its reflection (deleted by its author after the 48-hour bin, or
    by the System Administrator);
  - by **Erase all data**.
- **On and off:** the `REFLECTION_TIMING_LOG` setting (in Streamlit secrets
  or the environment). It is on by default. Set it to `false` and restart
  the app to stop recording; nothing is then timed or saved.
- **Where to see it:** System Administration → **Reflection timing**
  (System Administrator only; checked on the screen and again in the
  service layer). It shows, for the last 7 or 30 days:
  - the **measured average Claude cost per reflection**, next to the
    earlier $0.072 estimate;
  - the lens and report AI calls: average, slowest 10 % and slowest time,
    average input and output tokens (output includes the AI's hidden
    "thinking"), failures and time-outs;
  - one line per step.
- **Measured cost per reflection:** the cost of all lens and report calls
  in the period (retries, failed attempts and practitioner retries
  included, because they are real cost), divided by the reflections
  completed in the same period. The figures come from the existing usage
  records. `usage_ledger.get_call_stats()` is a new read-only summary;
  how usage is recorded is unchanged.
- **Fix:** the older `get_cost_per_reflection()` (used by the forecast
  calculation, not shown on screen) divided 30 days of cost by **all**
  reflections ever made, which made the average look lower over time. It
  now counts reflections from the same 30 days.
- **Cost of the measurement itself:** no AI calls; one small database
  write per reflection.
- **Tests:** `tests/test_reflection_timing.py`, and
  `tests/test_reflection_timing_postgres.py` (real database, skipped unless
  `TEST_DATABASE_URL` is set).