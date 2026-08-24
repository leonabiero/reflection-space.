"""
Centralized Provider Pricing Registry
=========================================

Service Cost & Usage Monitor -- Phase 9 (Cost Engine).

This is the ONLY place in the application where a provider's dollar
price per token/unit is written down. Every cost shown anywhere in the
app (services/usage_ledger.py, services/cost_dashboard_service.py, the
System Administration "Service Usage & Costs" panel) is computed by
calling estimate_cost() below -- never by re-implementing a price
somewhere else.

Why this matters: provider prices change (Anthropic and Google both
revise theirs from time to time). Because every price lives in ONE
dict, updating a rate after an official price change is a one-line
edit here, with no other file to hunt down and no risk of two
different parts of the app quietly disagreeing about what a token
costs.

Each entry records an `effective_date` -- the date this app's pricing
was last verified against the provider's own published rate. This is
informational only (shown in the admin panel and documentation); it
does not change any calculation. When you update a price, update its
effective_date too, so anyone reading the dashboard can see how fresh
the numbers are.

Sources verified at the effective_date below:
  - Anthropic Claude Sonnet 5: https://platform.claude.com/docs/en/about-claude/pricing
  - Google Gemini Embedding (gemini-embedding-001): https://ai.google.dev/gemini-api/docs/pricing

IMPORTANT: these numbers can and will go out of date. Always check the
provider's own pricing page before trusting a dashboard figure for a
real budgeting decision -- see docs/SERVICE_USAGE_MONITORING.md for
how to update this file.
"""

CURRENCY = "USD"

# Anthropic Claude -- price per token, derived from the published
# per-million-token rate (price_per_mtok / 1_000_000). Cache reads and
# cache writes are billed at different rates than a normal ("base")
# input token -- see services/reflection_service.py's prompt-caching
# companion-conversation path, which is the only call site that can
# ever produce cache_read/cache_creation tokens today.
ANTHROPIC_PRICING = {
    "claude-sonnet-5": {
        "input_per_mtok": 2.00,
        "output_per_mtok": 10.00,
        "cache_read_per_mtok": 0.20,
        "cache_write_per_mtok": 2.50,
        "effective_date": "2026-08-24",
        "currency": CURRENCY,
    },
}

# Default model used whenever a call's model name isn't recognized
# above (keeps the dashboard from silently showing $0.00 if a model
# string ever changes) -- estimate_cost() also flags this case so it's
# visible in the admin panel rather than silently wrong.
_ANTHROPIC_FALLBACK_MODEL = "claude-sonnet-5"

# Google Gemini -- embeddings only. gemini-embedding-001 has no output
# token cost; billing is purely on input tokens.
GEMINI_PRICING = {
    "gemini-embedding-001": {
        "input_per_mtok": 0.15,
        "effective_date": "2026-08-24",
        "currency": CURRENCY,
    },
}

_GEMINI_FALLBACK_MODEL = "gemini-embedding-001"


def get_anthropic_rate(model: str):
    """Returns the pricing dict for one Claude model, falling back to
    the default model (with a flag) if the model string is unrecognized."""
    rate = ANTHROPIC_PRICING.get(model)
    if rate is not None:
        return rate, True
    return ANTHROPIC_PRICING[_ANTHROPIC_FALLBACK_MODEL], False


def get_gemini_rate(model: str):
    rate = GEMINI_PRICING.get(model)
    if rate is not None:
        return rate, True
    return GEMINI_PRICING[_GEMINI_FALLBACK_MODEL], False


def estimate_anthropic_cost(model, input_tokens=0, output_tokens=0,
                             cache_read_tokens=0, cache_creation_tokens=0):
    """
    Cost in USD for one Anthropic API call, from ACTUAL token counts
    returned by the API (never from max_tokens -- see
    services/reflection_service.py for why that would be wrong).

    Returns (cost_usd: float, model_recognized: bool).
    """
    rate, recognized = get_anthropic_rate(model)
    cost = (
        (input_tokens or 0) * rate["input_per_mtok"] / 1_000_000
        + (output_tokens or 0) * rate["output_per_mtok"] / 1_000_000
        + (cache_read_tokens or 0) * rate["cache_read_per_mtok"] / 1_000_000
        + (cache_creation_tokens or 0) * rate["cache_write_per_mtok"] / 1_000_000
    )
    return cost, recognized


def estimate_gemini_embedding_cost(model, input_tokens=0):
    """Cost in USD for one Gemini embedding call, from the ACTUAL
    token_count reported by the Google GenAI SDK response.

    Returns (cost_usd: float, model_recognized: bool).
    """
    rate, recognized = get_gemini_rate(model)
    cost = (input_tokens or 0) * rate["input_per_mtok"] / 1_000_000
    return cost, recognized


def pricing_snapshot():
    """
    Returns the full registry in a flat, display-friendly shape for
    the admin "Configuration" / documentation panels -- one row per
    (provider, model) with its billing unit and effective date.
    """
    rows = []
    for model, rate in ANTHROPIC_PRICING.items():
        rows.append({
            "provider": "Anthropic",
            "model": model,
            "billing_unit": "per 1M tokens (input / output / cache read / cache write)",
            "rate": f"${rate['input_per_mtok']:.2f} / ${rate['output_per_mtok']:.2f} / "
                    f"${rate['cache_read_per_mtok']:.2f} / ${rate['cache_write_per_mtok']:.2f}",
            "effective_date": rate["effective_date"],
            "currency": rate["currency"],
        })
    for model, rate in GEMINI_PRICING.items():
        rows.append({
            "provider": "Google Gemini",
            "model": model,
            "billing_unit": "per 1M input tokens",
            "rate": f"${rate['input_per_mtok']:.2f}",
            "effective_date": rate["effective_date"],
            "currency": rate["currency"],
        })
    return rows
