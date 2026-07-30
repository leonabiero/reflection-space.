import os

# Claude API Key (set this in your environment OR paste directly for testing)
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

# --- Hybrid RAG: semantic retrieval layer -------------------------------
#
# Embeddings are generated with Voyage AI (Anthropic's recommended
# embedding partner -- Anthropic does not offer its own embedding
# endpoint). This is a SEPARATE account/API key from ANTHROPIC_API_KEY.
#
# Sign up at https://dash.voyageai.com, create an API key, and set it as
# a secret named VOYAGE_API_KEY (same place ANTHROPIC_API_KEY lives).
#
# If VOYAGE_API_KEY is not set, semantic retrieval is automatically
# disabled and the app falls back to the same recency-based historical
# context it used before this change -- nothing breaks, you just don't
# get semantic matches until the key is added.
VOYAGE_API_KEY = os.getenv("VOYAGE_API_KEY", "")

# voyage-4-lite: $0.02 / 1M tokens, 200M tokens free per account,
# 32K context window, Matryoshka-truncatable embeddings. Cheapest
# current-generation Voyage model and more than sufficient quality for
# same-case document matching (see chat writeup for pricing detail).
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "voyage-4-lite")

# Truncated (Matryoshka) embedding dimension. 512 keeps Qdrant's free
# tier (1GB RAM) comfortable for years at this pilot's volume, with
# negligible quality loss vs the full 1024 for this use case.
EMBEDDING_DIMENSIONS = int(os.getenv("EMBEDDING_DIMENSIONS", "512"))

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
# value in this app (ANTHROPIC_API_KEY, VOYAGE_API_KEY, QDRANT_URL,
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