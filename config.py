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