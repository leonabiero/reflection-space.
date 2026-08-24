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
| Claude (Anthropic) | Every reflection companion call, every retry, every companion follow-up conversation, every Knowledge Assistant question | Yes — from actual token usage |
| Gemini Embeddings (Google) | Every document embedding, every query embedding | Yes — from actual token usage |
| Qdrant | Vector upserts, deletes, searches (case-scoped and global), current vector count | No dollar cost — Qdrant's API doesn't expose billing, so only usage/health is shown |
| PostgreSQL (Neon) | This app's own connection-pool usage | No — this is an *application* metric, not Neon's bill (see below) |
| Streamlit | Active sessions, where reliably measurable | No — hosting cost isn't available from this deployment |
| SMTP | Alert emails sent/failed | No — depends on whatever email provider is configured |

## How a cost is calculated

Every dollar figure on the panel comes from the same two steps:

1. **Record actual usage.** Every Claude and Gemini call is
   instrumented at its call site (`services/reflection_service.py`,
   `services/knowledge_assistant.py`, `services/embedding_service.py`)
   to capture the token counts the *provider itself* reports back —
   `message.usage.input_tokens` / `output_tokens` for Claude, and the
   Google GenAI SDK's `statistics.token_count` for Gemini. **The
   `max_tokens` a call is allowed to use is never treated as the
   number of tokens it actually used** — that would overstate cost
   every time a response finishes early.

2. **Price it centrally.** `services/cost_pricing.py` is the *only*
   place a provider's price per token is written down. Everything else
   — the ledger, the dashboard, the forecast — calls into that one
   file. If Anthropic or Google change their prices, updating the cost
   shown everywhere in the app is a one-line edit in that single file
   (see "Updating pricing" below).

Every usage event is written to a `service_usage` database table
(`services/usage_ledger.py`) in the background, off the request path,
so recording usage can never add latency to — or ever cause a failure
of — a practitioner's reflection, an embedding, or an email. If the
database write itself fails, it's logged and silently dropped; the
only consequence is a slightly incomplete dashboard, never a broken
feature.

## What counts as exact vs. an estimate

- **Exact:** Claude token counts (from the API response), Gemini token
  counts (from the SDK response), Qdrant vector counts (from a live
  API call).
- **Estimate:** any cost computed from a token count when the model
  name wasn't recognized in `cost_pricing.py` (falls back to the
  default Claude/Gemini model's price, and is flagged
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
When a service crosses the 70% / 85% / 95% threshold (or Qdrant becomes
unreachable), one email is sent. The last-alerted tier is remembered in
the existing `app_settings` key-value table so the same crossing never
re-sends on every page load; dropping back to green and crossing again
later re-arms the alert.

## Updating pricing

1. Open `services/cost_pricing.py`.
2. Update the relevant rate in `ANTHROPIC_PRICING` or `GEMINI_PRICING`.
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
| `MONTHLY_BUDGET_GEMINI_USD` | 10 | Gemini monthly budget ceiling |
| `QDRANT_CAPACITY_VECTORS` | 0 (unset) | Qdrant plan's vector capacity, if known — leave unset to show "Limit unavailable" instead of a guess |

## What happens if monitoring itself fails

Nothing, from the practitioner's point of view. Every instrumentation
point wraps its usage-recording call so that a database outage, a
full recording queue, or any other monitoring-side failure is caught,
logged, and ignored — the reflection, embedding, search, or email that
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
