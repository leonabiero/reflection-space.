import streamlit as st
from services.language import init_language
from navigation.router import render_nav
from services.identity import init_identity, render_identity_footer, require_work_mode
from services.error_log import error_boundary
from services.exploration_log import get_personal_exploration_history
from services.reflection_log import THEME_KEYS
from services.findings_store import get_my_findings, count_my_findings
from services.findings_ui import render_evidence, render_notes_form

# Professional Growth Dashboard
# ================================
#
# Sprint 8. This is the professional's own reflective journal -- NOT a
# performance evaluation.
#
# Hard privacy/product rules this page must never break (see Feature 2
# in the product requirements):
#   - No ranking of professionals against each other.
#   - No scores, percentages-of-improvement, or competence judgements
#     ("your reasoning improved by 35%" is exactly what this must NOT do).
#   - Only the logged-in professional's OWN data, queried by their own
#     name -- never anyone else's, and never a comparison to anyone
#     else's.
#   - Not restricted to supervisory roles: unlike Learning/Case
#     History/Audit Log, EVERY professional sees this page, and it
#     shows only what they personally explored.
#
# Data source: services.exploration_log, which stores WHICH theme was
# explored, how many turns it took, and when -- never the conversation
# text itself (see services/exploration_log.py for the full rationale).

T = init_language()
user_name, user_role = init_identity(T)
require_work_mode(T, "Practitioner")
render_nav(T, page_name="growth_dashboard")
render_identity_footer(T)

with error_boundary(
    "growth_dashboard", T=T, user_name=user_name, user_role=user_role,
):

    st.title(T["growth_title"])
    st.caption(T["growth_intro"])

    HISTORY_LIMIT = 50
    rows = get_personal_exploration_history(user_name, limit=HISTORY_LIMIT)
    # rows: (case_ref, trigger, turn_count, explored_at), most recent first

    if not rows:
        st.info(T["growth_no_data"])

    if rows:
        total = len(rows)
        st.write(f"**{T['growth_session_count_label']}:** {total}")

        # --- Most explored areas: personal frequency only, no comparison to
        # anyone else and no percentage-improvement framing -- just how often
        # each theme has come up for this professional, most-explored first. ---
        st.subheader(T["growth_themes_header"])
        st.caption(T["growth_themes_caption"].format(total=total))

        counts = {key: 0 for key in THEME_KEYS}
        for case_ref, trigger, turn_count, explored_at in rows:
            if trigger in counts:
                counts[trigger] += 1

        ordered_keys = sorted(THEME_KEYS, key=lambda k: counts[k], reverse=True)
        for key in ordered_keys:
            count = counts[key]
            if count == 0:
                continue
            theme_label = T["section_labels"].get(key, key.replace("_", " ").title())
            st.write(f"**{theme_label}**")
            st.progress(count / total)
            st.caption(str(count))

        st.divider()

        # --- Recent reflective moments: a personal timeline, not a report card.
        # Shows what was explored, on which of the professional's own cases,
        # and how many exchanges it took -- never the conversation content
        # itself, which was never persisted (see exploration_log.py). ---
        st.subheader(T["growth_history_header"])

        RECENT_DISPLAY_LIMIT = 15
        for case_ref, trigger, turn_count, explored_at in rows[:RECENT_DISPLAY_LIMIT]:
            theme_label = T["section_labels"].get(trigger, trigger.replace("_", " ").title())
            date_part = (explored_at or "")[:16]
            case_label = case_ref or T["reflection_no_case_ref"]
            st.write(T["growth_entry_line"].format(
                theme=theme_label, case=case_label, count=turn_count, date=date_part,
            ))


    # ---------------------------------------------------------------
    # Saved observations and your own notes (saved-findings Stage 1)
    # ---------------------------------------------------------------
    # Everything the AI observed in YOUR reflections, with the exact
    # passages it was based on, next to your own notes. Only the
    # logged-in professional's own findings are ever loaded (filtered in
    # SQL by name -- see services/findings_store.py), and notes are
    # private to their author. Nothing here is a score or an evaluation
    # of the professional.
    st.divider()
    st.subheader(T["findings_journal_header"])
    st.caption(T["findings_journal_intro"])

    FINDINGS_PAGE_SIZE = 10
    total_findings = count_my_findings(user_name)

    if total_findings == 0:
        st.info(T["findings_journal_empty"])
    else:
        last_page = (total_findings - 1) // FINDINGS_PAGE_SIZE
        page = min(max(st.session_state.get("findings_journal_page", 0), 0), last_page)

        findings = get_my_findings(
            user_name, limit=FINDINGS_PAGE_SIZE, offset=page * FINDINGS_PAGE_SIZE,
        )

        st.caption(T["findings_journal_count"].format(
            total=total_findings, page=page + 1, pages=last_page + 1,
        ))

        for f in findings:
            module_label = T["section_labels"].get(f["module"], f["module"].replace("_", " ").title())
            case_label = f["case_ref"] or T["reflection_no_case_ref"]
            date_part = (f["created_at"] or "")[:16]
            saved_mark = " ✔" if f["feedback"] else ""
            with st.expander(f"{module_label} — {case_label} — {date_part}{saved_mark}"):
                st.write(f["observation"])
                render_evidence(T, f["evidence"], f["unverified_quote_count"])
                for q in f["questions"]:
                    st.markdown(f"- {q}")
                st.divider()
                render_notes_form(
                    T, f["id"], user_name, f["feedback"], key_prefix="jr",
                )

        if page > 0:
            if st.button(T["findings_journal_newer"], key="findings_journal_newer_btn"):
                st.session_state["findings_journal_page"] = page - 1
                st.rerun()
        if page < last_page:
            if st.button(T["findings_journal_older"], key="findings_journal_older_btn"):
                st.session_state["findings_journal_page"] = page + 1
                st.rerun()
