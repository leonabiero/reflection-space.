import streamlit as st
from services.audit_log import get_audit_log
from services.language import init_language, render_nav
from services.visit_log import log_visit
from services.identity import init_identity, render_identity_footer, can_see_case_history

T = init_language()
log_visit("audit_log", st.session_state.lang)
user_name, user_role = init_identity(T)
render_nav(T)
render_identity_footer(T)

st.title(T["audit_log_title"])

if not can_see_case_history(user_role):
    st.info(T["audit_log_no_items"])
    st.stop()

ACTION_LABEL_KEYS = {
    "created": "audit_action_created",
    "submitted": "audit_action_submitted",
    "deleted": "audit_action_deleted",
    "restored": "audit_action_restored",
    "purged": "audit_action_purged",
}

ACTION_BADGES = {
    "created": "📝",
    "submitted": "✅",
    "deleted": "🗑️",
    "restored": "♻️",
    "purged": "🔥",
}

entries = get_audit_log()

if not entries:
    st.info(T["audit_log_no_items"])
    st.stop()

for row in entries:
    entry_id, action, draft_id, case_ref, doc_type, actor_name, actor_role, details, occurred_at = row

    label = T.get(ACTION_LABEL_KEYS.get(action, ""), action)
    badge = ACTION_BADGES.get(action, "•")
    role_label = T.get("role_labels", {}).get(actor_role, actor_role)
    timestamp = occurred_at[:16] if occurred_at else ""

    line = f"{badge} **{label}** — {case_ref or '(unknown case)'}"
    if doc_type:
        line += f" ({doc_type})"
    line += f" — {actor_name or 'Unknown'}, {role_label} — {timestamp}"

    st.write(line)
    if details:
        st.caption(details)