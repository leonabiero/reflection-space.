"""Shared badge/label helper functions used by several System
Administration sections.

Extracted unchanged from the original single system_administration.py
file -- the logic and wording are identical to before, only the
location moved. The only change from the original is that each
function now takes T (the language/translation object) as an explicit
argument instead of relying on it being a page-level variable, since
these functions are now shared across several separate files.
"""
import psycopg2

from config import DATABASE_URL


MATCH_REASON_LABEL_KEYS = {
    "must_include": "why_reason_must_include_generic",
    "semantic": "why_reason_semantic_generic",
    "recency": "why_reason_recency",
}
MATCH_REASON_ICONS = {
    "must_include": "📌",
    "semantic": "🔎",
    "recency": "🕒",
}


def reason_label(reason, T):
    icon = MATCH_REASON_ICONS.get(reason, "")
    text = T.get(MATCH_REASON_LABEL_KEYS.get(reason, ""), reason)
    return f"{icon} {text}".strip()


def status_badge(ok, T, true_key="admin_status_connected", false_key="admin_status_not_connected"):
    return f"✅ {T[true_key]}" if ok else f"❌ {T[false_key]}"


def bool_badge(ok, T):
    return T["admin_status_present"] if ok else T["admin_status_missing"]


def format_when(timestamp):
    """Trims a raw timestamp down to a readable 'YYYY-MM-DD HH:MM'.
    Returns '-' if there's nothing to show."""
    return (timestamp or "")[:16].replace("T", " ") or "—"


def check_database():
    """Cheap, best-effort connection check -- opens and immediately
    closes a connection. Does not run any query beyond the driver's
    own handshake."""
    if not DATABASE_URL:
        return False, "DATABASE_URL is not configured."
    try:
        conn = psycopg2.connect(DATABASE_URL)
        conn.close()
        return True, None
    except Exception as e:
        return False, str(e)
