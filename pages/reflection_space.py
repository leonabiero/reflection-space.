import streamlit as st
from services.reflection_log import log_reflection
from services.findings_store import save_reflection_run, get_feedback_for_findings
from services.findings_ui import render_evidence, render_notes_form
from services.feedback_store import save_feedback
from services.reflection_service import continue_companion_conversation
from services.exploration_log import log_exploration
from services.language import init_language, LANGUAGE_ORDER
from navigation.router import render_nav
from services.identity import init_identity, render_identity_footer, require_work_mode
from services.rag_logging import rag_log
from services.rate_limiter import check_and_record, DEFAULT_MAX_PER_HOUR
from services import request_dedup
from services import document_import
from services import reflection_records
from config import (
    REQUEST_DEDUP_TTL_MINUTES, SAVE_ANONYMISED_TEXT, ANONYMISED_TEXT_RETENTION_MONTHS,
)
from rdi.orchestrator import run_reflection
from services.anonymizer import anonymize
from services.error_log import error_boundary, render_application_error_screen, log_error
from rdi.conversation_builder import build_conversation
from rdi.reflection_context import ReflectionContext
from rdi.reflection_session import ReflectionSession
from rdi.companions import COMPANIONS

# =====================================================================
# Reflection Space -- write, choose a language, press Reflect
# =====================================================================
#
# Simplified practitioner screen (November 2026, agreed with the EDE
# team -- see REFLECTIONS.md). Practitioners give NO metadata: no
# reference, no type of text, no case themes, no earlier-reflection code.
#
#   1. Let's reflect   -- write, paste and/or upload the text, choose the
#                         language of the reflection, press Reflect.
#                         (If there is typed text AND a document, the
#                         practitioner is asked which one to use.)
#   2. Automatically   -- the text is anonymised HERE, before anything
#                         else happens. If that fails, nothing is sent to
#                         any AI and the text stays on screen. Only the
#                         anonymised text is passed to the existing
#                         8-companion reflection (rdi/orchestrator.py).
#   3. Professional    -- the eight reflective dimensions, exactly as
#      reflection         before (tabs, conversations, private notes),
#                         plus a collapsed "View anonymised text" preview
#                         showing exactly what the AI received.
#
# Only the REFLECTION is saved (services/findings_store.py), identified
# by a neutral app-generated code that is created silently
# (services/reflection_records.py). The case text exists only in this
# browser session (ReflectionSession) and is discarded when the
# professional finishes, starts again or logs out.
#
# The earlier-reflections step (rdi/reflection_context.py,
# reflection_records.find_similar_reflections) is no longer shown: it
# matched on case themes / earlier codes, which practitioners no longer
# give. The services are kept intact so it can be brought back.
# =====================================================================

T = init_language()
user_name, user_role = init_identity(T)
require_work_mode(T, "Practitioner")
render_nav(T, page_name="reflection_space")
render_identity_footer(T)

with error_boundary(
    "reflection_space", T=T, user_name=user_name, user_role=user_role,
):

    # (Each stage below sets its own heading -- "Let's reflect." on the
    # form, "Reflection Space" on the results -- so there is no shared
    # page title here; it used to appear twice on the results.)

    # trigger -> companion dict, so the workspace can look up label/focus
    # when continuing a conversation, without re-deriving it from the
    # opportunity's stored observation text.
    COMPANIONS_BY_KEY = {c["key"]: c for c in COMPANIONS}

    # Card dots (November 2026): what each companion produced. The same
    # meaning is also given in words (tooltip and key under the cards).
    CARD_DOT_COLOURS = {
        ReflectionSession.STATUS_FINDING: "#639922",      # green
        ReflectionSession.STATUS_NONE: "#B4B2A9",         # grey
        ReflectionSession.STATUS_UNAVAILABLE: "#EF9F27",  # amber
    }
    CARD_DOT_SYMBOLS = {
        ReflectionSession.STATUS_FINDING: "🟢",
        ReflectionSession.STATUS_NONE: "⚪",
        ReflectionSession.STATUS_UNAVAILABLE: "🟠",
    }

    # Small emoji used purely to make each reflective dimension visually
    # distinct on the Reflection Dashboard tabs (UX Priority 2). Cosmetic
    # only -- does not affect which companions run or what they return.
    TRIGGER_ICONS = {
        "client_voice": "🗣️",
        "observation_vs_interpretation": "🔍",
        "labels_and_language": "🏷️",
        "possible_bias": "⚖️",
        "evidence_for_decisions": "📋",
        "missing_information": "❔",
        "strengths_and_deficits": "🌱",
        "continuity": "🔗",
    }

    # Widget keys of the "Your case" form. They carry a nonce so the whole
    # form can be emptied in one go after a reflection is finished.
    FORM_NONCE_KEY = "rs_form_nonce"
    NEW_CODE_KEY = "rs_new_code"
    PREFILL_KEY = "rs_prefill"
    FLASH_KEY = "rs_flash"
    GENERATING_KEY = "_generating_reflection"

    def _form_key(name):
        return f"rs_{name}_{st.session_state.get(FORM_NONCE_KEY, 0)}"

    def _language_name(lang_key):
        """Display name of a reflection language (Español / Euskara /
        English). The internal keys are the app's existing language keys
        (services/language.py: LANGUAGE_ORDER)."""
        return T["rs_language_names"].get(lang_key, lang_key)


    # ---------------------------------------------------------------------
    # Session-state hygiene
    # ---------------------------------------------------------------------
    # Several widgets on this page use keys that are scoped only to an
    # earlier reflection's id or a dimension "trigger" (e.g. "ctx_sim_42",
    # "workspace_open_client_voice"). Both can legitimately repeat across
    # DIFFERENT reflection sessions, and Streamlit keeps a widget's value
    # for as long as its key exists -- so without an explicit reset, a
    # checkbox unticked (or a dimension expanded) in one reflection would
    # silently carry into a later, unrelated one. This removes every
    # session_state key starting with one of the given prefixes, so each
    # new reflection starts from a clean slate.
    def _reset_ephemeral_widget_state(prefixes):
        for key in list(st.session_state.keys()):
            if any(key.startswith(prefix) for prefix in prefixes):
                del st.session_state[key]


    def _clear_all():
        """Leaving the reflection flow entirely, whatever stage it was at.

        Before the session (and its in-memory conversations AND the case
        text) is discarded, log which themes were actually explored and
        how many turns each ran to (services.exploration_log). No
        conversation text and no case text is persisted -- only the fact
        that this theme was explored, by whom, on which reflection code.
        """
        session = ReflectionSession.get_active()
        if session is not None:
            for opportunity in session.opportunities:
                turn_count = sum(1 for turn in opportunity.conversation if turn.get("role") == "professional")
                if turn_count > 0:
                    log_exploration(
                        session.case_ref, opportunity.trigger, turn_count,
                        user_name, user_role,
                    )

        ReflectionContext.clear()
        ReflectionSession.clear()
        st.session_state.pop("_finding_feedback_cache", None)

        _reset_ephemeral_widget_state([
            "ctx_sim_", "workspace_open_", "convo_input_", "convo_error_",
        ])


    def _start_fresh(flash=None):
        """Forget everything about the current reflection -- including the
        case text -- and present an empty "Your case" form with a new
        reflection code."""
        _clear_all()
        st.session_state.pop(NEW_CODE_KEY, None)
        st.session_state.pop(PREFILL_KEY, None)
        st.session_state[FORM_NONCE_KEY] = st.session_state.get(FORM_NONCE_KEY, 0) + 1
        if flash:
            st.session_state[FLASH_KEY] = flash


    def _render_identity_caption(code):
        """Small line at the top of the results with the neutral
        reflection code (created automatically -- the practitioner never
        has to type or choose it)."""
        st.caption(f"{T['reflection_active_case_prefix']} **{code}**")


    # ---------------------------------------------------------------------
    # Reflection workspace (content of one opportunity card)
    # ---------------------------------------------------------------------
    # Everything from here to the stage logic renders the eight reflective
    # dimensions, the follow-up conversations and the professional's own
    # notes exactly as before.

    def _feedback_for(session, opportunity):
        """This professional's saved notes for one observation. Loaded
        once per reflection (one query for all eight observations) and
        kept in the session, then updated in place after each save."""
        cache = st.session_state.setdefault("_finding_feedback_cache", {})
        if session.run_id not in cache:
            finding_ids = [o.finding_id for o in session.opportunities if o.finding_id]
            try:
                cache[session.run_id] = get_feedback_for_findings(user_name, finding_ids)
            except Exception:
                cache[session.run_id] = {}
        return cache[session.run_id].get(opportunity.finding_id, {})


    def _render_finding_notes(session, opportunity):
        """The professional's OWN response to one observation. Saved
        separately from the AI's text (services/findings_store.py) and
        private to this person; the form itself is shared with the
        personal journal (services/findings_ui.py)."""
        if not opportunity.finding_id:
            return

        saved = _feedback_for(session, opportunity)
        header = T["findings_notes_header"]
        if saved:
            header = f"{header} ✔"

        with st.expander(header, expanded=False):
            updated = render_notes_form(
                T, opportunity.finding_id, user_name, saved, key_prefix="ws",
            )
            if updated is not None:
                st.session_state.setdefault("_finding_feedback_cache", {}).setdefault(
                    session.run_id, {}
                )[opportunity.finding_id] = updated


    def _render_opportunity_tab_body(session, opportunity):
        """
        UX Priority 2 & 4 -- Reflection Dashboard + Navigator.

        Same content and same behavior as the previous per-opportunity
        expander (observation, questions, Explore toggle, conversation) --
        only the container changed, from a stacked st.expander to the body
        of one st.tabs() tab (see the call site below), so practitioners
        can jump directly to a dimension instead of scrolling past seven
        others to find it.
        """
        if opportunity.focus:
            st.write(opportunity.focus)

        # Saved-findings Stage 1: the exact passage(s) this observation is
        # based on. Only passages verified word for word against the text
        # the AI was given are ever shown (services/evidence.py).
        render_evidence(T, opportunity.evidence, opportunity.unverified_quote_count)

        for q in opportunity.invitation:
            st.markdown(f"- {q}")

        st.caption(T["workspace_reminder"])

        _render_finding_notes(session, opportunity)

        open_key = f"workspace_open_{opportunity.trigger}"
        is_open = st.session_state.get(open_key, opportunity.explored)

        if not is_open:
            if st.button(T["workspace_explore_button"], key=f"explore_btn_{opportunity.trigger}"):
                opportunity.mark_explored()
                st.session_state[open_key] = True
                session.save()
                st.rerun()
        else:
            st.divider()
            for turn in opportunity.conversation:
                role_label = "🧑‍💼" if turn["role"] == "professional" else "💬"
                st.markdown(f"**{role_label}** {turn['content']}")

            input_key = f"convo_input_{opportunity.trigger}"
            clear_flag_key = f"clear_convo_input_{opportunity.trigger}"

            # If the previous run flagged this input for clearing (after a
            # message was sent), reset it here -- BEFORE the widget below
            # is instantiated. Streamlit does not allow writing to a
            # widget's session_state key after that widget has already
            # been created in the same script run, so the clear has to
            # happen up front, on the run that follows the st.rerun().
            if st.session_state.pop(clear_flag_key, False):
                st.session_state[input_key] = ""

            message_text = st.text_area(
                T["workspace_conversation_input_label"],
                placeholder=T["workspace_conversation_placeholder"],
                key=input_key,
                height=80,
            )

            # Reliability-hardening pass (September pilot): same
            # in-flight-lock idea already used for reflection generation
            # (see the "Generate" button further down this page), scoped
            # per opportunity so replying to one dimension's conversation
            # doesn't lock the others. Backend duplicate protection
            # (services.request_dedup, via continue_companion_conversation's
            # requested_by parameter) is the backstop for whatever this
            # lock can't see on its own (e.g. two browser tabs).
            convo_generating_key = f"_convo_generating_{opportunity.trigger}"
            convo_is_generating = st.session_state.get(convo_generating_key, False)

            col1, col2 = st.columns([1, 1])
            with col1:
                if st.button(
                    T["workspace_send_button"],
                    key=f"send_btn_{opportunity.trigger}",
                    disabled=convo_is_generating,
                ):
                    if message_text and message_text.strip():
                        companion = COMPANIONS_BY_KEY.get(opportunity.trigger)
                        history_before = list(opportunity.conversation)
                        sent_message = message_text.strip()

                        st.session_state[convo_generating_key] = True
                        try:
                            with st.spinner(T["workspace_ai_thinking"]):
                                result = continue_companion_conversation(
                                    companion=companion,
                                    safe_text=session.safe_text,
                                    initial_observation=opportunity.focus,
                                    initial_questions=opportunity.invitation,
                                    conversation_history=history_before,
                                    professional_message=sent_message,
                                    lang=getattr(session, "reflection_lang", None) or st.session_state.lang,
                                    requested_by=user_name,
                                )
                        finally:
                            st.session_state[convo_generating_key] = False

                        if result.get("duplicate"):
                            # This exact message is already being (or was
                            # just) answered elsewhere -- don't add it to
                            # the visible conversation a second time, and
                            # don't make a second Claude call.
                            pass
                        elif "reply" in result:
                            opportunity.add_professional_message(sent_message)
                            opportunity.add_ai_message(result["reply"])
                        else:
                            opportunity.add_professional_message(sent_message)
                            st.session_state[f"convo_error_{opportunity.trigger}"] = True
                            st.session_state[f"convo_error_ref_{opportunity.trigger}"] = (
                                result.get("issue_id"), result.get("error_id"),
                            )

                        # Flag the conversation input box to be cleared on
                        # the next run (right before it's re-instantiated
                        # above), so it doesn't sit there holding onto the
                        # just-sent text. This only affects the input
                        # widget's own state -- the conversation history
                        # itself (opportunity.conversation, saved just
                        # above) is completely untouched.
                        st.session_state[clear_flag_key] = True

                        session.save()
                        st.rerun()
            with col2:
                if st.button(
                    T["workspace_close_button"],
                    key=f"close_btn_{opportunity.trigger}",
                    disabled=convo_is_generating,
                ):
                    st.session_state[open_key] = False
                    st.rerun()

            if st.session_state.pop(f"convo_error_{opportunity.trigger}", False):
                convo_issue_id, convo_error_id = st.session_state.pop(
                    f"convo_error_ref_{opportunity.trigger}", (None, None),
                )
                render_application_error_screen(
                    T, convo_issue_id, convo_error_id,
                    friendly_message=T["workspace_conversation_error"],
                )



    # =====================================================================
    # Which stage are we in?
    # =====================================================================
    active_session = ReflectionSession.get_active()

    # A context left over from the retired "earlier reflections" step
    # (e.g. someone mid-way when this version was deployed): bring the
    # text back into the form so nothing has to be retyped.
    leftover_context = ReflectionContext.get_active()
    if leftover_context is not None:
        if active_session is None:
            st.session_state[PREFILL_KEY] = {"text": leftover_context.case_text}
        ReflectionContext.clear()


    # ---------------------------------------------------------------------
    # Results -- Professional reflection (the workspace)
    # ---------------------------------------------------------------------
    if active_session is not None:
        session = active_session

        st.title(T["nav_reflection"])

        if session.has_error():
            # Complete Failure: the same numbered "Something went wrong"
            # screen as any other unexpected error (already logged once
            # by rdi/orchestrator.py:run_reflection).
            render_application_error_screen(
                T, session.issue_id, session.error_id,
                friendly_message=session.friendly_message,
            )
            col1, col2 = st.columns(2)
            with col1:
                if st.button(T["rs_try_again_button"], type="primary", key="rs_try_again_after_error"):
                    # Put the same text and language back into the form,
                    # so trying again is one click on Reflect.
                    prefill = {
                        "text": session.case_text,
                        "lang": getattr(session, "reflection_lang", None),
                    }
                    _start_fresh()
                    st.session_state[PREFILL_KEY] = prefill
                    st.rerun()
            with col2:
                if st.button(T["rs_start_over_button"], key="rs_start_over_after_error"):
                    _start_fresh()
                    st.rerun()
            st.stop()

        _render_identity_caption(session.case_ref)
        st.caption(
            f"{T['rs_language_label']}: "
            f"{_language_name(getattr(session, 'reflection_lang', st.session_state.lang))}"
        )

        if session.failed_count > 0:
            st.warning(T["reflection_partial_failure_notice"].format(count=session.failed_count))

        if session.findings_save_failed:
            st.info(T["findings_not_saved_notice"])

        # Transparency: exactly the protected text the AI received
        # (the orchestrator returns it as "safe_text"). Collapsed by
        # default; never shows the original text.
        if session.safe_text:
            with st.expander(T["rs_anonymised_preview_label"], expanded=False):
                st.caption(T["rs_anonymised_preview_help"])
                if SAVE_ANONYMISED_TEXT and session.run_id:
                    st.caption(T["rs_saved_anonymised_note"].format(months=ANONYMISED_TEXT_RETENTION_MONTHS))
                st.write(session.safe_text)

        # What this reflection is grounded in. The case text is only held
        # in this browser session and is never saved.
        with st.expander(T["workspace_document_header"], expanded=False):
            st.caption(T["rs_case_text_not_saved_note"])
            st.write(session.case_text)

        if session.context_summary:
            st.caption(f"{T['workspace_context_header']}: {session.context_summary}")

        # -----------------------------------------------------------------
        # Reflection opportunities -- all eight as cards in one view
        # (November 2026, replaces the tabs). Each card is a button; the
        # chosen one opens below the grid. A dot in the top-right corner
        # shows what that companion produced:
        #   green = something to reflect on, grey = nothing notable,
        #   amber = temporarily unavailable (Retry inside).
        # The order is fixed (rdi/conversation_builder.py) so practitioners
        # learn where each one is. Nothing is open at first.
        # -----------------------------------------------------------------
        st.subheader(T["workspace_opportunities_header"])
        ordered_opportunities = build_conversation(session.opportunities)

        if ordered_opportunities:
            total_opportunities = len(ordered_opportunities)
            st.caption(
                f"{T['rs_cards_hint']} "
                + T["workspace_progress_label"].format(
                    explored=session.explored_count(), total=total_opportunities
                )
            )

            # Starts with "workspace_open_" so it is cleared together with
            # the other per-reflection widget state.
            selected_key = "workspace_open_card"
            selected = st.session_state.get(selected_key)
            if selected not in {o.trigger for o in ordered_opportunities}:
                selected = None

            css_rules = [
                # Same height for every card; two per row on a phone
                # (Streamlit would otherwise stack them one per row).
                "@media (max-width: 640px) {div[data-testid='stHorizontalBlock']"
                ":has(div[class*='st-key-rs_card_']) {flex-wrap:wrap !important; gap:0.6rem;}"
                " div[data-testid='stHorizontalBlock']:has(div[class*='st-key-rs_card_'])"
                " > div[data-testid='stColumn'] {flex:1 1 calc(50% - 0.6rem) !important;"
                " min-width:calc(50% - 0.6rem) !important; width:calc(50% - 0.6rem) !important;}}",
                "div[class*='st-key-rs_card_'] button {min-height:6.6rem; position:relative;"
                " white-space:normal; text-align:left; justify-content:flex-start;"
                " align-items:flex-start; padding:0.75rem 1.6rem 0.6rem 0.8rem;}",
                "div[class*='st-key-rs_card_'] button::after {content:''; position:absolute;"
                " top:0.55rem; right:0.55rem; width:0.7rem; height:0.7rem; border-radius:50%;}",
            ]
            for opportunity in ordered_opportunities:
                status = session.status_of(opportunity.trigger)
                css_rules.append(
                    f"div.st-key-rs_card_{opportunity.trigger} button::after "
                    f"{{background:{CARD_DOT_COLOURS[status]};}}"
                )
            st.markdown(f"<style>{' '.join(css_rules)}</style>", unsafe_allow_html=True)

            per_row = 4
            for start in range(0, total_opportunities, per_row):
                row = ordered_opportunities[start:start + per_row]
                columns = st.columns(per_row)
                for column, opportunity in zip(columns, row):
                    trigger = opportunity.trigger
                    status = session.status_of(trigger)
                    label = T["section_labels"].get(trigger, trigger.replace("_", " ").title())
                    icon = TRIGGER_ICONS.get(trigger, "•")
                    text = f"{icon} {label}"
                    if opportunity.explored:
                        text += f"  \n{T['rs_card_explored']}"
                    with column:
                        if st.button(
                            text,
                            key=f"rs_card_{trigger}",
                            type="primary" if trigger == selected else "secondary",
                            # The colour of the dot is also given in words,
                            # so it does not rely on colour alone.
                            help=T["rs_card_status"][status],
                            use_container_width=True,
                        ):
                            st.session_state[selected_key] = None if trigger == selected else trigger
                            st.rerun()

            st.caption(
                " · ".join(
                    f"{CARD_DOT_SYMBOLS[status]} {T['rs_card_status'][status]}"
                    for status in (
                        ReflectionSession.STATUS_FINDING,
                        ReflectionSession.STATUS_NONE,
                        ReflectionSession.STATUS_UNAVAILABLE,
                    )
                )
            )

            if selected is None:
                st.info(T["rs_cards_choose"])
            else:
                opportunity = next(o for o in ordered_opportunities if o.trigger == selected)
                label = T["section_labels"].get(selected, selected.replace("_", " ").title())
                with st.container(border=True):
                    st.markdown(f"#### {TRIGGER_ICONS.get(selected, '•')} {label}")
                    _render_opportunity_tab_body(session, opportunity)

        st.divider()

        if not session.awaiting_feedback:
            st.subheader(T["rs_finish_header"])
            if session.run_id:
                st.caption(T["rs_finish_caption"].format(code=session.case_ref))
            else:
                st.caption(T["rs_finish_caption_unsaved"])
            if st.button(T["rs_finish_button"], type="primary", key="rs_finish_btn"):
                session.awaiting_feedback = True
                session.save()
                st.rerun()

        if session.awaiting_feedback:
            st.subheader(T["feedback_prompt_title"])

            rating = st.slider(T["feedback_rating_label"], min_value=1, max_value=5, value=3)
            comment = st.text_area(T["feedback_comment_label"], value="", height=80)

            col1, col2 = st.columns(2)
            with col1:
                if st.button(T["feedback_submit_button"]):
                    # The feedback row records the reflection code(s) it
                    # is about (the column kept its historical name).
                    save_feedback([session.case_ref], rating, comment, user_name, user_role)
                    _start_fresh(flash=T["feedback_thanks"])
                    st.rerun()
            with col2:
                if st.button(T["feedback_skip_button"]):
                    _start_fresh(flash=T["rs_finished_success"])
                    st.rerun()

        st.stop()


    # ---------------------------------------------------------------------
    # Let's reflect -- write, paste or upload, choose a language, Reflect
    # ---------------------------------------------------------------------
    st.title(T["rs_heading"])
    st.markdown(T["rs_subheading"])

    # After "Finish reflection" the form is already empty and ready; the
    # thank-you is a small pop-up that disappears on its own, so nothing
    # from the previous reflection stays on the screen.
    flash = st.session_state.pop(FLASH_KEY, None)
    if flash:
        st.toast(flash)

    text_key = _form_key("text")
    imported_key = _form_key("imported")
    lang_key = _form_key("lang")
    source_key = _form_key("source")

    # Coming back after a failed reflection ("Try again"): refill the
    # form before its widgets exist (Streamlit does not allow writing a
    # widget's value after it has been created in the same run).
    prefill = st.session_state.pop(PREFILL_KEY, None)
    if prefill:
        st.session_state[text_key] = prefill.get("text", "")
        if prefill.get("lang") in LANGUAGE_ORDER:
            st.session_state[lang_key] = prefill["lang"]

    # The neutral reflection code is created silently -- practitioners
    # never type or choose anything to identify the case.
    if NEW_CODE_KEY not in st.session_state:
        st.session_state[NEW_CODE_KEY] = reflection_records.new_reflection_code()
    reflection_code = st.session_state[NEW_CODE_KEY]

    case_text = st.text_area(
        T["rs_material_label"],
        key=text_key,
        height=320,
        placeholder=T["rs_material_placeholder"],
    )

    # Optional: bring in an existing document instead. Only the TEXT is
    # read (the file itself is never stored -- services/document_import.py).
    # Its text is kept SEPARATE from the box above; nothing is overwritten.
    # Streamlit's uploader shows the file name and a ✕ to remove it;
    # uploading another file replaces it.
    import_limits = dict(
        max_mb=document_import.MAX_FILE_BYTES // (1024 * 1024),
        max_pages=document_import.MAX_PDF_PAGES,
        max_chars=document_import.MAX_CHARS,
    )
    uploaded = st.file_uploader(
        T["doc_import_label"],
        type=list(document_import.ALLOWED_EXTENSIONS),
        key=_form_key("upload"),
        help=T["doc_import_help"].format(**import_limits),
    )
    if uploaded is None:
        st.session_state.pop(imported_key, None)
    elif st.session_state.get(imported_key, {}).get("file_id") != uploaded.file_id:
        try:
            extracted = document_import.extract_text(uploaded.name, uploaded.getvalue())
            st.session_state[imported_key] = {
                "file_id": uploaded.file_id, "name": uploaded.name,
                "text": extracted, "error": None,
            }
        except document_import.DocumentImportError as exc:
            st.session_state[imported_key] = {
                "file_id": uploaded.file_id, "name": uploaded.name,
                "text": "", "error": exc.reason,
            }

    file_text = ""
    outcome = st.session_state.get(imported_key)
    if outcome:
        if outcome["error"]:
            st.error(T["doc_import_errors"].get(outcome["error"], T["doc_import_errors"]["unreadable"]).format(**import_limits))
        else:
            file_text = outcome["text"]
            st.success(T["rs_file_loaded"].format(name=outcome["name"]))

    # Typed text AND a document: ask, never combine or overwrite silently.
    source_choice = None
    if document_import.has_both(case_text, file_text):
        st.info(T["rs_both_inputs_notice"])
        source_choice = st.radio(
            T["rs_source_label"],
            list(document_import.SOURCE_CHOICES),
            format_func=lambda key: T["rs_source_options"].get(key, key),
            index=None,
            key=source_key,
        )

    # Language of the REFLECTION (not of the menus). Starts on the app's
    # current language.
    # (The starting value is put in session state rather than passed as
    # `index`, so "Try again" can restore the earlier choice without
    # Streamlit warning about two competing defaults.)
    if st.session_state.get(lang_key) not in LANGUAGE_ORDER:
        current_lang = st.session_state.get("lang", "Español")
        st.session_state[lang_key] = current_lang if current_lang in LANGUAGE_ORDER else LANGUAGE_ORDER[0]
    reflect_lang = st.radio(
        T["rs_language_label"],
        LANGUAGE_ORDER,
        format_func=_language_name,
        horizontal=True,
        key=lang_key,
    )

    st.caption(f"{T['rs_privacy_note']} {T['rs_case_text_not_saved_note']}")
    if SAVE_ANONYMISED_TEXT:
        st.caption(T["rs_saved_anonymised_note"].format(months=ANONYMISED_TEXT_RETENTION_MONTHS))

    # -------------------------------------------------------------------
    # Cost-safety guard (unchanged)
    # -------------------------------------------------------------------
    # Generating a reflection triggers 8 parallel Claude API calls
    # (rdi/orchestrator.py) plus automatic retries. Protections:
    # 1. GENERATING_KEY disables the button while a generation is
    #    running, so a double click can't start a second.
    # 2. services.rate_limiter.check_and_record() enforces a generous
    #    per-person hourly cap (fails open if the database is down).
    # 3. services.request_dedup blocks the exact same request arriving
    #    twice (e.g. from two browser tabs).
    is_generating = st.session_state.get(GENERATING_KEY, False)

    reflect_clicked = st.button(
        T["rs_reflect_button"],
        type="primary",
        disabled=is_generating,
        use_container_width=True,
        key="rs_reflect_btn",
    )

    if reflect_clicked:
        material, problem = document_import.pick_material(case_text, file_text, source_choice)
        if problem == document_import.MATERIAL_CHOOSE:
            st.warning(T["rs_choose_source_warning"])
        elif problem:
            st.warning(T["rs_need_material"])
        else:
            with error_boundary(
                "reflection_space (generate reflection)",
                T=T,
                user_name=user_name,
                user_role=user_role,
                context={"case_ref": reflection_code},
                reset_flags=[GENERATING_KEY],
            ):
                # ---------------------------------------------------------
                # PRIVACY BOUNDARY: anonymise first, before ANYTHING else.
                # From here on only `safe_text` is used for the AI. If this
                # fails, stop: nothing is sent anywhere and there is no
                # fallback to the original text. The error record carries
                # no text at all -- only the kind of failure.
                # ---------------------------------------------------------
                safe_text = None
                try:
                    safe_text = anonymize(material)
                except Exception as exc:
                    safe_text = None
                    log_error(
                        page="reflection_space (anonymise)",
                        error_type="AnonymisationFailed",
                        message=(
                            f"Anonymisation raised {type(exc).__name__}. The reflection "
                            "was stopped and nothing was sent to any AI provider."
                        ),
                        traceback_text=None,
                        traceback_unavailable_reason=(
                            "Deliberately not recorded: a traceback could contain "
                            "parts of the practitioner's original text."
                        ),
                        user_name=user_name,
                        user_role=user_role,
                        context={"case_ref": reflection_code, "chars": len(material)},
                    )

                if not (safe_text or "").strip():
                    st.error(T["rs_anonymise_failed"])
                else:
                    allowed, _count = check_and_record(user_name, max_per_hour=DEFAULT_MAX_PER_HOUR)
                    if not allowed:
                        st.session_state["_rate_limit_hit"] = True
                        st.rerun()

                    st.success(T["rs_anonymised_status"])
                    st.session_state[GENERATING_KEY] = True

                    # Backend duplicate protection: this person, this
                    # reflection code, this exact (anonymised) text and
                    # language. Only a one-way fingerprint is stored.
                    reflection_request_id = request_dedup.fingerprint(
                        "reflection", user_name, reflection_code, safe_text, reflect_lang,
                    )
                    claim_status = request_dedup.claim(
                        reflection_request_id, "reflection", ttl_minutes=REQUEST_DEDUP_TTL_MINUTES,
                    )
                    if claim_status != "claimed":
                        st.session_state[GENERATING_KEY] = False
                        st.session_state["_reflection_duplicate_hit"] = True
                        st.rerun()

                    # Codes and counts only -- never any text.
                    rag_log(
                        f"[RAG] Reflection started for code={reflection_code!r} "
                        f"| lang={reflect_lang!r} | chars={len(safe_text)}"
                    )

                    reflection_succeeded = False
                    try:
                        with st.spinner(T["rs_preparing_status"]):
                            # Only the ANONYMISED text goes in. (The
                            # orchestrator anonymises again; that is
                            # harmless because anonymize() is idempotent.)
                            result = run_reflection(safe_text, reflect_lang, context_description="")
                        reflection_succeeded = True
                    finally:
                        # A failed/aborted attempt must not block a retry.
                        if reflection_succeeded:
                            request_dedup.complete(reflection_request_id)
                        else:
                            request_dedup.release(reflection_request_id)

                    st.session_state[GENERATING_KEY] = False

                    if "error" not in result:
                        log_reflection(reflection_code, result["raw"], user_name, user_role)

                    session = ReflectionSession(
                        result,
                        reflected_drafts=[],
                        case_ref=reflection_code,
                        context_summary="",
                        case_text=material,
                        reflection_lang=reflect_lang,
                    )

                    # The REFLECTION is the record: save what the AI found
                    # (with its verified anonymised passages), identified by
                    # the neutral code. The case text itself is NOT saved.
                    # Best-effort: if saving fails the reflection still
                    # works, the practitioner is told notes can't be kept.
                    if "error" not in result:
                        try:
                            saved = save_reflection_run(
                                case_ref=reflection_code,
                                source_draft_ids=[],
                                language=reflect_lang,
                                prompt_version=result.get("prompt_version", ""),
                                model=result.get("model", ""),
                                module_status=result.get("module_status", {}),
                                findings=result.get("findings", []),
                                created_by=user_name,
                                created_by_role=user_role,
                                reflection_code=reflection_code,
                                case_tags=[],
                                note_type="",
                                previous_code="",
                                # Only the ANONYMISED text the AI received is
                                # ever kept (never `material`), for later
                                # pattern analysis -- see REFLECTIONS.md.
                                anonymised_text=(
                                    session.safe_text if SAVE_ANONYMISED_TEXT else None
                                ),
                            )
                            session.attach_saved_findings(
                                saved["run_id"], saved["finding_ids"], user_name,
                            )
                        except Exception:
                            session.findings_save_failed = True

                        # Retention: clear saved anonymised text that has
                        # passed its time limit. Best effort -- never
                        # blocks the reflection.
                        try:
                            reflection_records.purge_expired_anonymised_text()
                        except Exception:
                            pass

                    session.save()

                    # A brand-new workspace always opens with every tab
                    # collapsed and no leftover input or error state.
                    _reset_ephemeral_widget_state([
                        "workspace_open_", "convo_input_", "convo_error_",
                    ])

                    st.rerun()

    if st.session_state.pop("_rate_limit_hit", False):
        st.error(T["rate_limit_exceeded_message"].format(max=DEFAULT_MAX_PER_HOUR))

    if st.session_state.pop("_reflection_duplicate_hit", False):
        st.info(T["reflection_duplicate_message"])
