import os

# Claude API Key (set this in your environment OR paste directly for testing)
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

# Qdrant (optional)
QDRANT_URL = os.getenv("QDRANT_URL", None)
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY", None)

APP_NAME = "Reflection Space"