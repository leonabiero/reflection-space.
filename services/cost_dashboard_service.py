"""
Service Usage & Costs -- Dashboard Aggregation
====================================================

Service Cost & Usage Monitor (September pilot hardening) -- Phases
10-13 of the accompanying spec.

This module is the ONLY place that turns raw usage_ledger rows into
what the System Administration "Service Usage & Costs" panel actually
displays: status colors, percentages, monthly projections, cost per
reflection, and the user-volume scenario forecast. Keeping this out of
pages/system_administration.py means the page stays presentation-only
(consistent with every other section on that page -- see its module
docstring) and this logic can be unit-tested on its own (see
tests/test_service_usage_monitoring.py).

Every number here traces back to either:
  - a real row in service_usage (services/usage_ledger.py), or
  - an existing, already-audited service (services.reflection_log,
    services.qdrant_service.get_diagnostics(), services.db_pool.get_pool_stats()).

Nothing here invents a limit, a price, or a percentage that the
underlying data doesn't support -- see _status_for_pct() and every
"Limit unavailable" branch below.
"""

from datetime import datetime, timezone
import calendar

import config
from services import usage_ledger
from services.qdrant_service import get_diagnostics as qdrant_diagnostics
from services.embedding_service import is_available as gemini_available
from services.db_pool import get_pool_stats
from services.reflection_log import get_total_reflection_count
from services.cost_pricing import pricing_snapshot

STATUS_GREEN = "green"
STATUS_YELLOW = "yellow"
STATUS_ORANGE = "orange"
STATUS_RED = "red"
STATUS_UNKNOWN = "unknown"  # "Limit unavailable" -- never fabricated


def _status_for_pct(pct):
    """GREEN 0-70 / YELLOW 70-85 / ORANGE 85-95 / RED 95+ -- or
    STATUS_UNKNOWN if pct is None (no real limit/budget to compare
    against, per the spec's Phase 10: never calculate a fake
    percentage)."""
    if pct is None:
        return STATUS_UNKNOWN
    if pct >= 95:
        return STATUS_RED
    if pct >= 85:
        return STATUS_ORANGE
    if pct >= 70:
        return STATUS_YELLOW
    return STATUS_GREEN


def _days_in_current_month():
    now = datetime.now(timezone.utc)
    return calendar.monthrange(now.year, now.month)[1], now.day


def _projected_month_cost(month_to_date_cost):
    """Simple, clearly-labeled linear projection: (cost so far / days so
    far) * days in month. Deliberately not more sophisticated than
    this -- see the spec's Phase 13, projections must be labeled as
    estimates, not treated as precise."""
    days_in_month, day_of_month = _days_in_current_month()
    if day_of_month <= 0 or month_to_date_cost <= 0:
        return 0.0
    return (month_to_date_cost / day_of_month) * days_in_month


# ---------------------------------------------------------------------
# Phase 10/11 -- per-service overview + monthly cost
# ---------------------------------------------------------------------

def get_anthropic_overview():
    today = usage_ledger.get_today_summary("anthropic")
    month = usage_ledger.get_month_summary("anthropic")
    budget = config.MONTHLY_BUDGET_ANTHROPIC_USD
    projected = _projected_month_cost(month["estimated_cost_usd"])
    pct = round(100.0 * month["estimated_cost_usd"] / budget, 1) if budget > 0 else None
    return {
        "service": "Claude (Anthropic)",
        "configured": bool(config.ANTHROPIC_API_KEY),
        "requests_today": today["request_count"],
        "requests_month": month["request_count"],
        "fail_count_month": month["fail_count"],
        "retry_count_month": month["retry_count"],
        "input_tokens_month": month["input_tokens"],
        "output_tokens_month": month["output_tokens"],
        "cost_today_usd": today["estimated_cost_usd"],
        "cost_month_usd": month["estimated_cost_usd"],
        "projected_month_usd": projected,
        "budget_usd": budget if budget > 0 else None,
        "budget_pct_used": pct,
        "status": _status_for_pct(pct),
        "cost_is_estimate": month["cost_is_estimate"],
    }


def get_gemini_overview():
    today = usage_ledger.get_today_summary("gemini")
    month = usage_ledger.get_month_summary("gemini")
    budget = config.MONTHLY_BUDGET_GEMINI_USD
    projected = _projected_month_cost(month["estimated_cost_usd"])
    pct = round(100.0 * month["estimated_cost_usd"] / budget, 1) if budget > 0 else None
    return {
        "service": "Gemini Embeddings (Google)",
        "configured": gemini_available(),
        "requests_today": today["request_count"],
        "requests_month": month["request_count"],
        "fail_count_month": month["fail_count"],
        "input_tokens_month": month["input_tokens"],
        "cost_today_usd": today["estimated_cost_usd"],
        "cost_month_usd": month["estimated_cost_usd"],
        "projected_month_usd": projected,
        "budget_usd": budget if budget > 0 else None,
        "budget_pct_used": pct,
        "status": _status_for_pct(pct),
        "cost_is_estimate": month["cost_is_estimate"],
    }


def get_qdrant_overview():
    """Qdrant exposes no billing API -- usage/capacity only, never a
    fabricated dollar cost (spec Phase 5)."""
    diag = qdrant_diagnostics()
    points = diag.get("points_count")
    capacity = config.QDRANT_CAPACITY_VECTORS or None
    pct = round(100.0 * points / capacity, 1) if (points is not None and capacity) else None
    month = usage_ledger.get_window_summary("qdrant", window_days=30)
    return {
        "service": "Qdrant",
        "configured": diag.get("configured", False),
        "connected": diag.get("connected", False),
        "points_count": points,
        "capacity": capacity,
        "budget_pct_used": pct,
        "status": _status_for_pct(pct) if diag.get("connected") else (
            STATUS_RED if diag.get("configured") else STATUS_UNKNOWN
        ),
        "dimension_mismatch": diag.get("dimension_mismatch"),
        "requests_30d": month["request_count"],
        "fail_count_30d": month["fail_count"],
        "error": diag.get("error"),
    }


def get_postgres_overview():
    """APPLICATION-level pool metrics only -- explicitly NOT Neon's own
    billing/compute data, which this app cannot retrieve (spec Phase
    6). connection-pool utilization is the only number given a
    GREEN/YELLOW/ORANGE/RED status here; the rest is informational."""
    stats = get_pool_stats()
    pct = stats.get("utilization_pct")
    return {
        "service": "PostgreSQL (Neon)",
        "configured": stats.get("configured", False),
        "pool_created": stats.get("pool_created", False),
        "max_conn": stats.get("max_conn"),
        "active_conn": stats.get("active_conn"),
        "idle_conn": stats.get("idle_conn"),
        "budget_pct_used": pct,
        "status": _status_for_pct(pct),
        "provider_billing_note": "Provider billing data unavailable -- Neon compute/storage "
                                  "usage is not retrievable through this app's configuration. "
                                  "The figures above are this application's own connection-pool "
                                  "usage, not a Neon bill.",
    }


def get_streamlit_overview():
    """Application-level metrics only where reliably measurable -- no
    fabricated CPU/RAM/hosting cost (spec Phase 7)."""
    from services.draft_storage import get_active_users
    try:
        active = len(get_active_users() or [])
    except Exception:
        active = None
    return {
        "service": "Streamlit (application)",
        "active_sessions_recent": active,
        "budget_pct_used": None,
        "status": STATUS_UNKNOWN,
        "note": "Hosting CPU/RAM/billing metrics are not reliably available from this "
                "deployment environment and are not shown rather than estimated.",
    }


def get_smtp_overview():
    month = usage_ledger.get_smtp_summary(window_days=30)
    return {
        "service": "SMTP (email alerts)",
        "configured": bool(config.SMTP_HOST and config.ALERT_EMAIL_TO),
        "emails_sent_30d": month["success_count"],
        "emails_failed_30d": month["fail_count"],
        "budget_pct_used": None,
        "status": STATUS_UNKNOWN,
    }


def get_all_service_overviews():
    """One row per monitored service, in the fixed display order used
    by the Phase 10 SERVICE | USAGE | LIMIT | % USED | COST | STATUS
    table."""
    return {
        "anthropic": get_anthropic_overview(),
        "gemini": get_gemini_overview(),
        "qdrant": get_qdrant_overview(),
        "postgres": get_postgres_overview(),
        "streamlit": get_streamlit_overview(),
        "smtp": get_smtp_overview(),
    }


# ---------------------------------------------------------------------
# Phase 12 -- cost per successful reflection
# ---------------------------------------------------------------------

def get_cost_per_reflection(window_days=30):
    """
    Average Claude cost per successful reflection over the last
    `window_days`, from ACTUAL recorded usage -- accounts for the
    8-companion fan-out and any retries (every companion attempt,
    including retried ones, is its own row in service_usage; see
    rdi/orchestrator.py + services/reflection_service.py).

    Returns:
        {
            "window_days": int,
            "reflections_generated": int,
            "companion_calls": int,          # includes retried attempts
            "companion_cost_usd": float,
            "avg_cost_per_reflection_usd": float | None,
            "retry_rate_pct": float | None,
            "cost_is_estimate": bool,
            "note": str | None,              # set when data is too sparse to trust
        }

    Median is intentionally omitted: this app does not currently tag
    each companion-call row with which reflection it belongs to, so a
    genuine per-reflection distribution (needed for a median) isn't
    available -- only the aggregate mean. This is stated explicitly
    rather than approximated.
    """
    breakdown = usage_ledger.get_operation_breakdown("anthropic", window_days=window_days)
    companion_rows = [r for r in breakdown if r["operation"] == "companion_reflection"]
    companion_calls = sum(r["request_count"] for r in companion_rows)
    companion_fail = sum(r["fail_count"] for r in companion_rows)
    companion_cost = sum(r["estimated_cost_usd"] for r in companion_rows)

    reflections_generated = get_total_reflection_count() or 0

    avg_cost = None
    if reflections_generated > 0:
        avg_cost = companion_cost / reflections_generated

    retry_rate = None
    if companion_calls > 0:
        retry_rate = round(100.0 * companion_fail / companion_calls, 1)

    note = None
    if reflections_generated == 0:
        note = "No completed reflections recorded in this window yet -- average cost cannot be computed."

    month_summary = usage_ledger.get_month_summary("anthropic", operation_prefix="companion_reflection")

    return {
        "window_days": window_days,
        "reflections_generated": reflections_generated,
        "companion_calls": companion_calls,
        "companion_cost_usd": companion_cost,
        "avg_cost_per_reflection_usd": avg_cost,
        "retry_rate_pct": retry_rate,
        "cost_is_estimate": month_summary["cost_is_estimate"],
        "note": note,
    }


# ---------------------------------------------------------------------
# Phase 13 -- user-volume scenario forecast
# ---------------------------------------------------------------------

def forecast_scenario(users, reflections_per_user_per_month):
    """
    ESTIMATE ONLY (labeled as such everywhere this is displayed).
    Projects total monthly cost at a hypothetical user/volume level,
    using the CURRENT measured average cost per reflection (Phase 12)
    and average embeddings-per-reflection ratio observed in the ledger.
    If there isn't yet enough real usage to derive an average, this
    returns None fields rather than guessing.
    """
    per_reflection = get_cost_per_reflection(window_days=30)
    avg_cost = per_reflection["avg_cost_per_reflection_usd"]

    total_reflections = max(0, users) * max(0, reflections_per_user_per_month)

    projected_claude_cost = None
    if avg_cost is not None:
        projected_claude_cost = avg_cost * total_reflections

    # Gemini: one document embedding is generated per completed
    # document, roughly one per reflection at this app's current
    # workflow (draft -> reflect -> finalize -> index). Derive the
    # observed average Gemini cost per reflection the same way, from
    # real ledger data, rather than a second guessed ratio.
    gemini_month = usage_ledger.get_month_summary("gemini")
    reflections_this_month = get_total_reflection_count() or 0
    avg_gemini_cost_per_reflection = None
    if reflections_this_month > 0:
        avg_gemini_cost_per_reflection = gemini_month["estimated_cost_usd"] / reflections_this_month
    projected_gemini_cost = None
    if avg_gemini_cost_per_reflection is not None:
        projected_gemini_cost = avg_gemini_cost_per_reflection * total_reflections

    qdrant = get_qdrant_overview()
    projected_vector_count = None
    if qdrant.get("points_count") is not None:
        # Roughly one new vector per newly completed document/reflection.
        projected_vector_count = qdrant["points_count"] + total_reflections

    return {
        "users": users,
        "reflections_per_user_per_month": reflections_per_user_per_month,
        "total_reflections_per_month": total_reflections,
        "projected_claude_cost_usd": projected_claude_cost,
        "projected_gemini_cost_usd": projected_gemini_cost,
        "projected_vector_count": projected_vector_count,
        "qdrant_capacity": qdrant.get("capacity"),
        "basis_note": (
            "Estimate only -- based on this pilot's current measured average "
            "cost per reflection, projected linearly to the volumes above. "
            "Real cost at higher volume can differ (prompt caching hit rate, "
            "retry rate, and document length can all vary)."
            if avg_cost is not None else
            "Not enough real usage recorded yet to derive a reliable "
            "cost-per-reflection average -- generate a few reflections first."
        ),
    }


def get_pricing_table():
    """For the Configuration / documentation panel -- see
    services/cost_pricing.py, the single source of truth."""
    return pricing_snapshot()
