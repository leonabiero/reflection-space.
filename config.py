import os

# Claude API Key (set this in your environment OR paste directly for testing)
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

# --- Hybrid RAG: semantic retrieval layer -------------------------------
#
# Embeddings are generated with the Google Gemini API. This is a separate
# API key from ANTHROPIC_API_KEY and is used only for semantic retrieval.
#
# If GEMINI_API_KEY is not set, semantic retrieval is automatically
# disabled and the app falls back to the same recency-based historical
# context it used before semantic retrieval was enabled.
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# Gemini embedding model used for RAG. gemini-embedding-001 supports
# retrieval-specific task types (document/query) and configurable output
# dimensionality, which maps cleanly to this app's existing architecture.
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "gemini-embedding-001")

# Gemini recommends 768, 1536, or 3072 dimensions for reduced/full output.
# 768 is a good testing balance between retrieval quality and Qdrant memory.
EMBEDDING_DIMENSIONS = int(os.getenv("EMBEDDING_DIMENSIONS", "768"))

# Qdrant (semantic retrieval layer -- system of record stays Postgres)
QDRANT_URL = os.getenv("QDRANT_URL", None)
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY", None)
QDRANT_COLLECTION_NAME = os.getenv("QDRANT_COLLECTION_NAME", "rdi_documents")

APP_NAME = "Reflection Space"
# Optional deployment/version label, shown only inside diagnostic
# packages built by services/diagnostics.py (Phase 1 Diagnostic
# Engine) -- has no effect on anything else. Leave unset unless you
# want a specific build/release label to show up in the AI-ready
# diagnostic prompt.
APP_VERSION = os.getenv("APP_VERSION", "unspecified")
# Password to view the private visit log page (set this as a secret on Streamlit Cloud)
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "")

# Neon PostgreSQL connection string (set as a secret on Streamlit Cloud)
DATABASE_URL = os.getenv("DATABASE_URL", "")

# ---------------------------------------------------------------------
# Centralized operational constants (Change 8 -- Constants/config
# cleanup)
# ---------------------------------------------------------------------
#
# These were previously hard-coded, duplicated module-level constants
# scattered across services/draft_storage.py (DELETION_WINDOW_HOURS)
# and services/presence.py (ACTIVE_WINDOW_MINUTES,
# RECENT_WINDOW_MINUTES). Moving them here means every deployment-
# tunable "how long/how many" knob for the storage layer lives in one
# place, consistent with how every other environment-configurable
# value in this app (ANTHROPIC_API_KEY, GEMINI_API_KEY, QDRANT_URL,
# etc.) is already defined here.
#
# Values are unchanged from their previous hard-coded defaults, so this
# is a pure relocation -- nothing about actual runtime behavior changes
# unless one of these environment variables is explicitly set.

# GDPR right-to-erasure: how long a soft-deleted case stays restorable
# in services/draft_storage.py before purge_expired_deletions() removes
# it permanently. Previously a hard-coded module constant in
# draft_storage.py.
DELETION_WINDOW_HOURS = int(os.getenv("DELETION_WINDOW_HOURS", "48"))

# Team Presence (services/presence.py) status-classification windows.
# Previously hard-coded module constants in presence.py.
PRESENCE_ACTIVE_WINDOW_MINUTES = int(os.getenv("PRESENCE_ACTIVE_WINDOW_MINUTES", "5"))
PRESENCE_RECENT_WINDOW_MINUTES = int(os.getenv("PRESENCE_RECENT_WINDOW_MINUTES", "15"))

# ---------------------------------------------------------------------
# PostgreSQL connection pool sizing (services/db_pool.py)
# ---------------------------------------------------------------------
# Previously every services/*.py module called psycopg2.connect()
# directly, opening and tearing down a brand-new TCP/TLS connection to
# Postgres for every single read or write -- expensive on its own, and
# a real problem under concurrent Streamlit users (each connection
# also re-ran full schema DDL, see services/db_schema.py). These two
# knobs size the shared pool that replaces that pattern.
#
# DB_POOL_MIN_CONN: connections opened eagerly when the pool is first
# created (kept warm even when idle).
# DB_POOL_MAX_CONN: hard ceiling on concurrent connections this
# process will ever hold open. Neon's free/pilot tiers commonly cap
# total concurrent connections in the low tens, and a single
# Streamlit process can have several user sessions running
# concurrently (each on its own script-run thread), so this is set
# conservatively by default -- raise it via the environment if a
# larger Postgres plan allows it.
DB_POOL_MIN_CONN = int(os.getenv("DB_POOL_MIN_CONN", "1"))
DB_POOL_MAX_CONN = int(os.getenv("DB_POOL_MAX_CONN", "10"))

# DB_POOL_HEALTH_RECHECK_SECONDS: a pooled connection is only re-verified
# with a liveness check (see services/db_pool.py) if it hasn't been
# successfully verified in at least this many seconds. Load testing
# (10 concurrent users) measured this liveness check costing a real,
# consistent ~350ms of network round-trip time on every single checkout
# -- worth paying occasionally to catch a connection Neon or the network
# silently dropped while idle, but not worth paying on every checkout of
# a connection that was just used and returned a moment ago. 30 seconds
# is comfortably shorter than the minutes-long idle windows where a
# connection actually risks going stale (e.g. Neon's autosuspend/
# compute-scale-to-zero behavior), so real staleness is still caught
# quickly -- this only skips redundant back-to-back re-checks during
# active use.
DB_POOL_HEALTH_RECHECK_SECONDS = int(os.getenv("DB_POOL_HEALTH_RECHECK_SECONDS", "30"))

# DB_POOL_MAX_REPLACE_ATTEMPTS: when a pooled connection turns out to be
# dead (see services/db_pool.py's liveness check above), the pool
# discards it and fetches a replacement. Previously that replacement
# was handed to the caller without ever being checked itself -- if it
# also happened to be dead (plausible if several connections went
# stale around the same time, e.g. after a period of inactivity or a
# brief network blip), the caller would get handed a connection
# guaranteed to fail on first real use, surfacing as a confusing
# downstream database error instead of being caught here. This caps
# how many times get_conn() will discard-and-fetch-again before giving
# up and raising a clear, immediate error instead of a silently broken
# connection. 3 is generous for a pool this size (DB_POOL_MAX_CONN
# above) without risking a long stall if the database itself is
# genuinely unreachable.
DB_POOL_MAX_REPLACE_ATTEMPTS = int(os.getenv("DB_POOL_MAX_REPLACE_ATTEMPTS", "3"))

# Default page size used ONLY when a caller of one of the newly
# paginated read functions (see Change 4 -- get_audit_log(),
# get_completed_drafts(), get_all_feedback(), get_pending_deletions())
# explicitly opts into pagination without specifying their own limit.
# It is NOT applied automatically -- every one of those functions still
# defaults its own `limit` parameter to None (meaning "return
# everything", exactly as before this pass), so existing call sites
# that don't pass `limit` see zero behavior change. This constant is
# just a convenient, centrally-tunable default for any NEW call site
# that wants pagination but doesn't want to pick its own page size.
DEFAULT_PAGE_LIMIT = int(os.getenv("DEFAULT_PAGE_LIMIT", "100"))

# ---------------------------------------------------------------------
# Production error email alerts (services/email_alert.py)
# ---------------------------------------------------------------------
# Lets Leon get notified by email the moment a real error is logged
# (an automatic crash, or someone using the "Report a problem" button)
# -- even when he isn't actively looking at the app.
#
# Disabled by default. To enable, add these as secrets on Streamlit
# Cloud (Settings -> Secrets, same place ANTHROPIC_API_KEY/DATABASE_URL
# already live):
#
#   SMTP_HOST      e.g. smtp.gmail.com
#   SMTP_PORT      e.g. 587 (STARTTLS) or 465 (SSL) -- 587 is the
#                  common default for most providers
#   SMTP_USER      the mailbox username/address that sends the alert
#   SMTP_PASSWORD  an APP PASSWORD, not your normal account password
#                  -- for Gmail: Google Account -> Security -> 2-Step
#                  Verification -> App passwords. Most providers have
#                  an equivalent; using your real login password here
#                  either won't work or is a bad idea.
#   ALERT_EMAIL_TO      the address that should receive alerts (yours)
#   ALERT_EMAIL_FROM     optional, defaults to SMTP_USER if not set
#
# If SMTP_HOST or ALERT_EMAIL_TO is missing, email alerting is simply
# skipped (logged to stdout only) -- nothing else in the app depends
# on it, so leaving it unconfigured never breaks anything.
SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
ALERT_EMAIL_TO = os.getenv("ALERT_EMAIL_TO", "")
ALERT_EMAIL_FROM = os.getenv("ALERT_EMAIL_FROM", "") or SMTP_USER

# ---------------------------------------------------------------------
# Login lockout / brute-force guard (services/login_rate_limiter.py)
# ---------------------------------------------------------------------
# After LOGIN_MAX_ATTEMPTS failed logins for the same username within
# LOGIN_LOCKOUT_WINDOW_MINUTES, that username is locked out for
# LOGIN_LOCKOUT_DURATION_MINUTES. See services/login_rate_limiter.py
# for the full design notes. Defaults below are sensible out of the
# box -- override via Streamlit Cloud secrets only if you want
# different thresholds.
LOGIN_MAX_ATTEMPTS = int(os.getenv("LOGIN_MAX_ATTEMPTS", "5"))
LOGIN_LOCKOUT_WINDOW_MINUTES = int(os.getenv("LOGIN_LOCKOUT_WINDOW_MINUTES", "15"))
LOGIN_LOCKOUT_DURATION_MINUTES = int(os.getenv("LOGIN_LOCKOUT_DURATION_MINUTES", "15"))

# ---------------------------------------------------------------------
# Persistent login sessions (services/session_store.py,
# services/session_cookie.py) -- survive a browser refresh (F5)
# ---------------------------------------------------------------------
# Previously, authentication lived ONLY in st.session_state, which
# Streamlit clears on every browser refresh/reconnect -- pressing F5
# silently logged everyone out and sent them back to the login form.
#
# A successful login now ALSO opens a persistent, server-side session
# (a row in the auth_sessions table -- see services/db_schema.py) and
# writes its opaque, unguessable session_id into a browser cookie (see
# services/session_cookie.py). Every authenticated page load re-reads
# that cookie and revalidates the session against the database --
# the cookie's contents are never trusted on their own -- and, as long
# as the person keeps using the app, extends the session's expiry (a
# "sliding" session: it only expires after this many hours of no
# activity at all, never on a fixed clock).
#
# SESSION_LIFETIME_HOURS: how long an inactive session stays valid
# before requiring login again. Also used as the browser cookie's
# Max-Age, so the browser discards the cookie at the same moment the
# server would have expired it anyway.
SESSION_LIFETIME_HOURS = int(os.getenv("SESSION_LIFETIME_HOURS", "12"))

# SESSION_COOKIE_NAME: the browser cookie holding the session_id
# (meaningless on its own without the matching database row -- see
# services/session_store.py). Change only if it collides with another
# cookie name in your deployment.
SESSION_COOKIE_NAME = os.getenv("SESSION_COOKIE_NAME", "rs_session")

# SESSION_COOKIE_SECURE: whether the cookie is marked `Secure` (the
# browser then refuses to store or send it over a plain http://
# connection). Streamlit Cloud -- and any real deployment -- always
# serves over https://, so leave this "true" in production. Set it to
# "false" ONLY for local development over http://localhost, where a
# `Secure` cookie would otherwise silently never get set at all.
SESSION_COOKIE_SECURE = os.getenv("SESSION_COOKIE_SECURE", "true").strip().lower() == "true"

# ---------------------------------------------------------------------
# QA testing hook: simulate a Reflection Generation "Rate Limit" failure
# (Test B) -- services/reflection_service.py
# ---------------------------------------------------------------------
# Off by default -- leaving this secret unset or set to "false" means
# ZERO change to normal behavior; no real API call is ever skipped.
#
# To run Test B: add a secret named SIMULATE_RATE_LIMIT_ERROR on
# Streamlit Cloud (Settings -> Secrets, same place ANTHROPIC_API_KEY
# lives), set it to "true", and reboot the app. Every reflection
# companion call will then immediately fail with a fake 429/rate-limit
# error -- no real Anthropic API call is made, so this costs nothing
# and is 100% reproducible on demand. Set it back to "false" (or
# delete the secret) and reboot to return to normal behavior.
SIMULATE_RATE_LIMIT_ERROR = os.getenv("SIMULATE_RATE_LIMIT_ERROR", "false").strip().lower() == "true"

# ---------------------------------------------------------------------
# Claude API concurrency control (September pilot hardening --
# "Change 11: Claude concurrency control")
# ---------------------------------------------------------------------
# Each reflection generation fans out to 8 parallel Claude calls (one
# per companion, see rdi/orchestrator.py) -- this keeps ONE reflection
# fast, but has no ceiling on how many reflections can be generating,
# org-wide, at the same moment. Before this change, N practitioners
# clicking "Generate" at the same moment meant N x 8 simultaneous
# Anthropic API requests with no upper bound -- e.g. 50 practitioners
# at once is 400 simultaneous calls, all competing for the same
# account-level rate limit.
#
# CLAUDE_MAX_CONCURRENT_REFLECTIONS caps how many *reflections*
# (each still fanning out to its own 8 parallel companion calls) may
# be actively generating at once, across the whole process -- not how
# many individual companion calls. This deliberately leaves the
# per-reflection 8-way parallelism (and therefore latency, and
# therefore reflection quality) completely unchanged; it only bounds
# how many of those 8-way fan-outs can be in flight simultaneously.
# See rdi/orchestrator.py:run_reflection() for the semaphore this
# gates.
#
# CLAUDE_REFLECTION_QUEUE_TIMEOUT_SECONDS: how long a reflection
# request will wait for a free "slot" before giving up -- this is the
# "queue" behavior (a practitioner who clicks Generate while the app
# is at capacity simply waits a little longer, spinner still showing,
# for the next slot) rather than an immediate hard rejection. Only if
# the queue doesn't clear within this window does the request give up
# and show the practitioner the same calm, numbered "Something went
# wrong" screen every other unexpected failure uses (see
# rdi/orchestrator.py) -- this should be rare at the 1000-worker pilot's
# real usage volume (~70-100 reflections/month ORG-WIDE, per
# services/rate_limiter.py's docstring); it exists as a backstop for a
# genuine traffic spike, not something expected to fire in normal use.
CLAUDE_MAX_CONCURRENT_REFLECTIONS = int(os.getenv("CLAUDE_MAX_CONCURRENT_REFLECTIONS", "20"))
CLAUDE_REFLECTION_QUEUE_TIMEOUT_SECONDS = int(os.getenv("CLAUDE_REFLECTION_QUEUE_TIMEOUT_SECONDS", "90"))

# CLAUDE_REQUEST_TIMEOUT_SECONDS: explicit per-call timeout passed to
# the Anthropic client (services/reflection_service.py), instead of
# relying on the SDK's own default (several minutes). Under load, a
# handful of calls hanging near the default timeout would each hold a
# concurrency "slot" (see CLAUDE_MAX_CONCURRENT_REFLECTIONS above) far
# longer than a normal call ever takes, making a slow patch worse
# instead of letting rdi/orchestrator.py's existing retry logic recover
# quickly. This does not change retry COUNT or backoff -- only how
# long one attempt is allowed to hang before being treated as failed
# (and retried, or counted as a companion failure) the same way a
# network error already is.
CLAUDE_REQUEST_TIMEOUT_SECONDS = int(os.getenv("CLAUDE_REQUEST_TIMEOUT_SECONDS", "60"))

# ---------------------------------------------------------------------
# Historical Context Prefetch -- REMOVED
# ---------------------------------------------------------------------
# This feature (services/context_prefetch.py, now deleted) used to
# precompute a draft's historical context on a background thread right
# after it was saved, so "Begin Reflection" could serve it instantly.
# It was removed after load testing showed its background workers had
# no limit on how many could run at once, which competed with normal
# user traffic for the shared database connection pool (services/
# db_pool.py) and contributed to connection-pool exhaustion under
# concurrent use. "Begin Reflection" now always uses the original live
# retrieval path (rdi/context_engine.py -> get_historical_context()),
# which measured at roughly 1 second -- an acceptable, and much safer,
# trade-off. If prefetching is ever revisited, it must run with a
# bounded number of concurrent workers, not an unlimited one.