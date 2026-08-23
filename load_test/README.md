# Phase 3 Load / Performance Testing Toolkit

## What this answers

*"What happens when many social workers use Reflection Space at the
same time?"*

This toolkit runs Reflection Space's real backend code — the database
connection pool, the reflection-generation concurrency limit, the two
AI-cost rate limiters, request deduplication, and login bookkeeping —
under many simulated simultaneous practitioners, and reports honest
timing and success/failure numbers.

## What is real, and what is faked

**Real (unmodified):** every piece of application logic being tested —
`services/db_pool.py`, `services/rate_limiter.py`,
`services/ka_rate_limiter.py`, `services/request_dedup.py`,
`services/login_rate_limiter.py`, and `rdi/orchestrator.py`'s
concurrency semaphore, 8-way companion fan-out, and retry logic.

**Faked (see `load_test/fakes.py`):**

- **The database.** `psycopg2.connect()` is pointed at an in-memory
  `FakeDatabase` instead of a real PostgreSQL server. The real
  `psycopg2.pool.ThreadedConnectionPool` class is still used
  unmodified — only the actual network connection it opens is fake —
  so pool sizing, checkout queueing, and timeout behavior are all real.
- **The Claude API.** `services.reflection_service.client.messages` is
  swapped for `FakeAnthropicMessages`, which returns a realistically
  shaped response after a configurable simulated delay, and can
  simulate a configurable failure/timeout rate. No real API call is
  ever made and no real credits are ever spent.

This toolkit never imports the real `psycopg2.connect`, never calls a
real Anthropic/Gemini/Qdrant endpoint, and never touches a production
database. It cannot accidentally run against production.

## How to run it

```bash
# From the repository root, with dependencies installed:
python -m load_test.run_load_test --scenario all --users 30

# Simulate 50 practitioners hitting the database pool at once
# (pool sized to 20, the real production default):
python -m load_test.run_load_test --scenario db-read --users 50

# Simulate 30 practitioners generating reflections at once:
python -m load_test.run_load_test --scenario reflection-generation \
    --users 30 --max-concurrent-reflections 20 --ai-latency-ms 1500

# Explore a slow/degraded AI provider (10% of calls time out):
python -m load_test.run_load_test --scenario reflection-generation \
    --users 20 --ai-timeout-rate 0.1
```

Run `python -m load_test.run_load_test --help` for every available
option (pool size, simulated query latency, AI latency/failure rates,
concurrency limits).

## Scenarios available

| Scenario | What it exercises |
|---|---|
| `db-read` | Database connection pool checkout/queueing under concurrent reads |
| `reflection-rate` | The reflection-generation cost limiter under concurrent hits from the same user |
| `ka-rate` | The Knowledge Assistant cost limiter under concurrent hits from the same user |
| `dedup` | Request deduplication when many identical requests arrive at once |
| `login` | Login failure bookkeeping under concurrent attempts |
| `reflection-generation` | A full reflection: real semaphore, real 8-way companion fan-out, real retries (AI faked) |

## Automated regression coverage

A small, fast subset of these scenarios runs automatically as part of
the normal test suite — see `tests/test_scalability_load_harness.py`.
Those tests are deliberately small-scale (a handful of virtual users,
milliseconds of simulated latency) so they run in a couple of seconds
in CI, but they exercise the exact same real code paths as a full-scale
manual run.

## Honest limitations

This toolkit is deliberately honest about what it does **not** prove:

- **It does not measure real network latency** to a real Postgres
  instance, a real Anthropic endpoint, or real Qdrant Cloud — only the
  application's own logic around those calls (queueing, concurrency
  limits, retries). Real-world latency will be higher than the
  simulated values used here, and will vary with the actual hosting
  region and provider load.
- **It does not measure Streamlit's own request-handling capacity**
  (how many simultaneous browser sessions one Streamlit Community
  Cloud instance can serve) — that is infrastructure outside this
  application's own code, and would need a real deployed instance and
  an HTTP-level load-testing tool (e.g. Locust or k6 pointed at a
  staging deployment) to measure honestly.
- **It does not measure Qdrant query performance under load** — the
  Knowledge Assistant's retrieval path was not included in this pass
  (only the AI-generation and rate-limiting paths were in scope); a
  future load-testing pass could add a fake Qdrant client following
  the same pattern as `FakeAnthropicMessages`.
- Simulated latencies (a few milliseconds for a fake DB query, ~1.5s
  for a fake Claude call) are reasonable estimates, not measurements —
  they make the reported queueing/contention behavior meaningful, but
  the absolute latency numbers should not be read as "this is how fast
  production will be."

Where real infrastructure would be needed to go further (a real
staging Postgres/Qdrant instance, or metered test API keys), that is
called out explicitly here rather than guessed at.
