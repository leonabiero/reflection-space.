import streamlit as st
from services.language import init_language
from navigation.router import render_nav
from services.identity import init_identity, render_identity_footer, require_work_mode
from services.error_log import error_boundary
from services.exploration_log import get_personal_exploration_history
from services.reflection_log import THEME_KEYS
from services.findings_store import get_my_findings_by_reflection, count_my_reflections_with_findings
from rdi.conversation_builder import CONVERSATION_ORDER
from services.findings_ui import render_evidence, render_notes_form
from services.reflection_records import get_anonymised_text, get_original_text
from services import reflection_records
from services.confirm_state import is_confirming, start_confirming, clear_confirming
from config import ORIGINAL_TEXT_RETENTION_MONTHS, ANONYMISED_TEXT_RETENTION_MONTHS, DELETION_WINDOW_HOURS

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

    # Reflections deleted more than DELETION_WINDOW_HOURS ago are erased
    # for good here (best effort -- never blocks the page).
    try:
        reflection_records.purge_expired_reflection_deletions()
    except Exception:
        pass

    flash = st.session_state.pop("_my_reflections_flash", None)
    if flash:
        st.toast(flash)

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

    # November 2026 -- grouped by reflection: ONE line per reflection
    # (code, date, how many observations, how many have notes), with its
    # observations inside. The person picks one observation at a time, in
    # the same fixed order as the cards on the Reflection Space screen.
    REFLECTIONS_PAGE_SIZE = 5
    total_reflections = count_my_reflections_with_findings(user_name)

    if total_reflections == 0:
        st.info(T["findings_journal_empty"])
    else:
        last_page = (total_reflections - 1) // REFLECTIONS_PAGE_SIZE
        page = min(max(st.session_state.get("findings_journal_page", 0), 0), last_page)

        reflections = get_my_findings_by_reflection(
            user_name, limit=REFLECTIONS_PAGE_SIZE, offset=page * REFLECTIONS_PAGE_SIZE,
        )

        st.caption(T["findings_journal_count_reflections"].format(
            total=total_reflections, page=page + 1, pages=last_page + 1,
        ))

        card_order = {key: i for i, key in enumerate(CONVERSATION_ORDER)}

        def _lens_label(module):
            return T["section_labels"].get(module, module.replace("_", " ").title())

        for reflection in reflections:
            findings = sorted(
                reflection["findings"],
                key=lambda f: (card_order.get(f["module"], len(card_order)), f["id"]),
            )
            with_notes = sum(1 for f in findings if f["feedback"])
            header = T["findings_reflection_line"].format(
                code=reflection["case_ref"] or T["reflection_no_case_ref"],
                date=(reflection["created_at"] or "")[:16].replace("T", " "),
                count=len(findings),
            )
            if with_notes:
                header += " " + T["findings_reflection_notes_suffix"].format(count=with_notes)

            with st.expander(header):
                # The saved text of this reflection. Only the author can
                # load it here. Since November 2026 that is the ORIGINAL
                # text; reflections from 4-10 November 2026 kept the
                # anonymised version instead, shown until it expires.
                if reflection["run_id"] and st.toggle(
                    T["ch_show_saved_text"], key=f"jr_anon_text_run_{reflection['run_id']}",
                ):
                    try:
                        original = get_original_text(reflection["run_id"], user_name)
                        anonymised = None if original else get_anonymised_text(
                            reflection["run_id"], user_name, user_role,
                        )
                    except Exception:
                        original = anonymised = None
                    with st.container(border=True):
                        if original:
                            st.caption(T["ch_original_text_caption"].format(months=ORIGINAL_TEXT_RETENTION_MONTHS))
                            st.write(original)
                        elif anonymised:
                            st.caption(T["ch_anonymised_text_caption"].format(months=ANONYMISED_TEXT_RETENTION_MONTHS))
                            st.write(anonymised)
                        else:
                            st.info(T["ch_saved_text_unavailable"])

                by_id = {f["id"]: f for f in findings}
                chosen_id = st.radio(
                    T["findings_pick_observation"],
                    options=list(by_id),
                    format_func=lambda fid: _lens_label(by_id[fid]["module"])
                    + (" ✔" if by_id[fid]["feedback"] else ""),
                    horizontal=True,
                    key=f"jr_pick_{reflection['run_id']}",
                )
                f = by_id[chosen_id]
                with st.container(border=True):
                    st.markdown(f"**{_lens_label(f['module'])}**")
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

    # ---------------------------------------------------------------
    # Your saved reflections -- delete and restore (November 2026)
    # ---------------------------------------------------------------
    # A professional can delete their OWN reflection. It disappears at
    # once everywhere (this page, managers' Reflection History, pattern
    # analysis), can be restored for DELETION_WINDOW_HOURS, and is then
    # erased for good (services/reflection_records.py).
    st.divider()
    st.subheader(T["my_reflections_header"])
    st.caption(T["my_reflections_intro"].format(hours=DELETION_WINDOW_HOURS))

    MY_REFLECTIONS_LIMIT = 50
    own = reflection_records.list_own_reflections(user_name, limit=MY_REFLECTIONS_LIMIT)
    total_own = reflection_records.count_own_reflections(user_name)

    if not own:
        st.info(T["my_reflections_empty"])
    else:
        if total_own > len(own):
            st.caption(T["my_reflections_showing"].format(shown=len(own), total=total_own))
        for record in own:
            confirm_key = f"confirm_delete_own_{record['run_id']}"
            with st.container(border=True):
                info_col, action_col = st.columns([4, 1])
                with info_col:
                    st.markdown(f"**{record['code']}**")
                    st.caption(T["my_reflections_line"].format(
                        date=(record["created_at"] or "")[:16].replace("T", " "), count=record["finding_count"],
                    ))
                with action_col:
                    if not is_confirming(confirm_key):
                        if st.button(T["my_reflections_delete"], key=f"delete_own_{record['run_id']}"):
                            start_confirming(confirm_key)
                            st.rerun()
                if is_confirming(confirm_key):
                    st.warning(T["my_reflections_confirm"].format(
                        code=record["code"], hours=DELETION_WINDOW_HOURS,
                    ))
                    yes_col, no_col = st.columns(2)
                    with yes_col:
                        if st.button(T["my_reflections_confirm_yes"], type="primary",
                                     key=f"yes_delete_own_{record['run_id']}"):
                            clear_confirming(confirm_key)
                            try:
                                done = reflection_records.delete_own_reflection(
                                    record["run_id"], user_name, user_role,
                                )
                            except Exception:
                                done = False
                            st.session_state["_my_reflections_flash"] = (
                                T["my_reflections_deleted"].format(code=record["code"], hours=DELETION_WINDOW_HOURS)
                                if done else T["my_reflections_failed"]
                            )
                            st.session_state["findings_journal_page"] = 0
                            st.rerun()
                    with no_col:
                        if st.button(T["my_reflections_confirm_cancel"],
                                     key=f"cancel_delete_own_{record['run_id']}"):
                            clear_confirming(confirm_key)
                            st.rerun()

    deleted = reflection_records.list_own_deleted_reflections(user_name)
    if deleted:
        st.markdown(f"**{T['my_reflections_deleted_header']}**")
        for record in deleted:
            with st.container(border=True):
                info_col, action_col = st.columns([4, 1])
                with info_col:
                    st.markdown(f"~~{record['code']}~~")
                    st.caption(T["my_reflections_erase_on"].format(date=(record["erase_at"] or "")[:16].replace("T", " ")))
                with action_col:
                    if st.button(T["my_reflections_restore"], key=f"restore_own_{record['run_id']}"):
                        try:
                            done = reflection_records.restore_own_reflection(
                                record["run_id"], user_name, user_role,
                            )
                        except Exception:
                            done = False
                        st.session_state["_my_reflections_flash"] = (
                            T["my_reflections_restored"].format(code=record["code"])
                            if done else T["my_reflections_failed"]
                        )
                        st.rerun()
