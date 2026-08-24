"""
Service Usage & Cost Alerts
================================

Service Cost & Usage Monitor (September pilot hardening) -- Phase 14
of the accompanying spec.

Reuses the existing alert/email architecture (services/email_alert.py)
-- this does not introduce a second notification system. Checks the
same thresholds the System Administration dashboard displays (70% /
85% / 95% of a configured budget or capacity, plus a projected-cost-
over-budget check) and sends Leon ONE email per threshold crossing,
debounced so the same threshold never re-sends on every page load or
every reflection.

Debounce mechanism
----------------------
Uses the existing services/settings_store.py key-value table
(app_settings) -- the same table System Administration's other
settings already live in -- to remember the last tier alerted for each
service. A new email is only sent when the CURRENT tier is higher than
the last one recorded; dropping back below a threshold and crossing it
again later re-arms the alert for that tier. This is intentionally
simple (no separate alert-history table) and safe under concurrent
Streamlit sessions: at worst two sessions both send one email for the
same brand-new tier crossing, which is a harmless duplicate, not a
notification storm.

Call check_and_alert() from the System Administration page (it is
cheap -- a handful of already-computed dashboard numbers plus one
settings read/write per service) rather than from any practitioner-
facing path, so this can never add latency to a reflection.
"""

from services import settings_store
from services import email_alert
from services.db_time import get_logger
from services import cost_dashboard_service as dashboard

logger = get_logger(__name__)

_TIER_ORDER = ["green", "yellow", "orange", "red"]
_SETTINGS_KEY_PREFIX = "usage_alert_last_tier__"


def _tier_index(status):
    try:
        return _TIER_ORDER.index(status)
    except ValueError:
        return -1


def _maybe_alert(service_key, label, status, detail_lines):
    """Sends one alert email if `status` is a higher tier than the last
    one recorded for this service, then updates the recorded tier.
    Never raises -- a failure here must never affect the admin page."""
    if status not in ("yellow", "orange", "red"):
        return
    try:
        setting_key = _SETTINGS_KEY_PREFIX + service_key
        last_tier = settings_store.get_setting(setting_key, default="green")
        if _tier_index(status) <= _tier_index(last_tier):
            return  # already alerted at this tier or higher; not a new crossing

        subject = f"[Reflection Space] {label} usage at {status.upper()} level"
        body = (
            f"{label} has crossed the {status.upper()} usage threshold.\n\n"
            + "\n".join(detail_lines)
            + "\n\nThis is an automated notice from the Service Usage & Costs "
              "monitor on the System Administration page. No action is needed "
              "unless the figures above are higher than expected."
        )
        sent = email_alert.send_alert_email(subject, body)
        if sent:
            settings_store.set_setting(setting_key, status)
        # De-escalation: once usage drops back to green, re-arm for next time.
    except Exception:
        logger.warning("usage_alerts: failed to process alert for %r", service_key, exc_info=True)


def _rearm_if_green(service_key, status):
    if status != "green":
        return
    try:
        setting_key = _SETTINGS_KEY_PREFIX + service_key
        last_tier = settings_store.get_setting(setting_key, default="green")
        if last_tier != "green":
            settings_store.set_setting(setting_key, "green")
    except Exception:
        logger.warning("usage_alerts: failed to re-arm %r", service_key, exc_info=True)


def check_and_alert():
    """
    Checks every monitored service's current status and sends a
    debounced alert email for any NEW threshold crossing. Safe to call
    on every System Administration page load -- cheap, and a no-op
    unless a real crossing just happened.

    Also checks: projected monthly cost exceeding the configured
    budget (Anthropic, Gemini), and Qdrant becoming unavailable.
    Never raises.
    """
    try:
        overviews = dashboard.get_all_service_overviews()
    except Exception:
        logger.warning("usage_alerts: could not compute service overviews", exc_info=True)
        return

    anthropic = overviews["anthropic"]
    _maybe_alert(
        "anthropic", "Claude (Anthropic)", anthropic["status"],
        [
            f"Month-to-date cost: ${anthropic['cost_month_usd']:.2f}",
            f"Configured monthly budget: ${anthropic['budget_usd']:.2f}" if anthropic["budget_usd"] else "No budget configured.",
            f"Projected month-end cost: ${anthropic['projected_month_usd']:.2f}",
        ],
    )
    _rearm_if_green("anthropic", anthropic["status"])

    gemini = overviews["gemini"]
    _maybe_alert(
        "gemini", "Gemini Embeddings (Google)", gemini["status"],
        [
            f"Month-to-date cost: ${gemini['cost_month_usd']:.2f}",
            f"Configured monthly budget: ${gemini['budget_usd']:.2f}" if gemini["budget_usd"] else "No budget configured.",
        ],
    )
    _rearm_if_green("gemini", gemini["status"])

    qdrant = overviews["qdrant"]
    if qdrant.get("configured") and not qdrant.get("connected"):
        _maybe_alert(
            "qdrant_unavailable", "Qdrant", "red",
            [f"Qdrant is configured but not reachable. Error: {qdrant.get('error') or 'unknown'}"],
        )
    else:
        _rearm_if_green("qdrant_unavailable", "green")

    if qdrant.get("budget_pct_used") is not None:
        _maybe_alert(
            "qdrant_capacity", "Qdrant vector capacity", qdrant["status"],
            [f"{qdrant.get('points_count')} of {qdrant.get('capacity')} vectors used "
             f"({qdrant['budget_pct_used']}%)."],
        )
        _rearm_if_green("qdrant_capacity", qdrant["status"])

    postgres = overviews["postgres"]
    _maybe_alert(
        "postgres_pool", "PostgreSQL connection pool", postgres["status"],
        [f"{postgres.get('active_conn')} of {postgres.get('max_conn')} pooled connections in use "
         f"({postgres.get('budget_pct_used')}%)."],
    )
    _rearm_if_green("postgres_pool", postgres["status"])
