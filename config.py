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