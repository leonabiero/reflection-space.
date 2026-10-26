import streamlit as st
from services.reflection_log import log_reflection
from services.findings_store import save_reflection_run, get_feedback_for_findings
from services.findings_ui import render_evidence, render_notes_form
from services.feedback_store import save_feedback
from services.reflection_service import continue_companion_conversation
from services.exploration_log import log_exploration
from services.language import init_language
from navigation.router import render_nav
from services.identity import init_identity, render_identity_footer, require_work_mode
from services.rag_logging import rag_log
from services.rate_limiter import check_and_record, DEFAULT_MAX_PER_HOUR
from services import request_dedup
from services import document_import
from services import reflection_records
from config import REQUEST_DEDUP_TTL_MINUTES
from rdi.orchestrator import run_reflection
from services.error_log import error_boundary, render_application_error_screen
from rdi.conversation_builder import build_conversation
from rdi.reflection_context import ReflectionContext
from rdi.reflection_session import ReflectionSession
from rdi.companions import COMPANIONS

# =====================================================================
# Reflection Space -- ONE screen, reflection on the spot
# =====================================================================
#
# Reflection-only redesign (October 2026, agreed with the EDE team --
# see REFLECTIONS.md). There is no separate Documentation screen any
# more and no documents are stored:
#
#   1. Your case        -- write, paste or upload the case text, tick a
#                          few non-personal case tags, optionally link an
#                          earlier reflection by its code.
#   2. Earlier          -- the professional's OWN linked / similar
#      reflections         earlier reflections are offered as context
#                          (each can be left out).
#   3. Professional     -- the eight reflective dimensions, exactly as
#      reflection          before (tabs, conversations, private notes).
#
# Only the REFLECTION is saved (services/findings_store.py), identified
# by a neutral app-generated code plus the case tags
# (services/reflection_records.py). The case text exists only in this
# browser session (ReflectionContext / ReflectionSession) and is
# discarded when the professional finishes, starts again or logs out.
# =====================================================================

T = init_language()
user_name, user_role = init_identity(T)
require_work_mode(T, "Practitioner")
render_nav(T, page_name="reflection_space")
render_identity_footer(T)

with error_boundary(
    "reflection_space", T=T, user_name=user_name, user_role=user_role,
):

    st.title(T["nav_reflection"])

    # trigger -> companion dict, so the workspace can look up label/focus
    # when continuing a conversation, without re-deriving it from the
    # opportunity's stored observation text.
    COMPANIONS_BY_KEY = {c["key"]: c for c in COMPANIONS}

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

    # Why an earlier reflection is being offered (badge per reason).
    SIMILAR_REASON_BADGES = {"linked": "🔗", "tags": "🏷️"}

    # Widget keys of the "Your case" form. They carry a nonce so the whole
    # form can be emptied in one go after a reflection is finished.
    FORM_NONCE_KEY = "rs_form_nonce"
    NEW_CODE_KEY = "rs_new_code"
    PREFILL_KEY = "rs_prefill"
    FLASH_KEY = "rs_flash"

    def _form_key(name):
        return f"rs_{name}_{st.session_state.get(FORM_NONCE_KEY, 0)}"

    def _tag_label(key):
        return T["case_tag_labels"].get(key, key.replace("_", " ").title())

    def _tags_line(tags):
        return ", ".join(_tag_label(t) for t in tags) if tags else T["rs_no_tags"]


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


    def _date_only(iso_str):
        return (iso_str or "")[:10]


    JOURNEY_STEPS = ["journey_step1", "journey_step2", "journey_step3"]


    def _render_journey(active_step):
        """
        Reflection Journey: a single-line horizontal progress strip
        (Your case -> Earlier reflections -> Professional reflection) so
        the practitioner always knows where they are. `active_step` is
        1-3; earlier steps show as done, later ones as upcoming. One flex
        row with nowrap so the names stay on one line (scrolls sideways
        on a very narrow phone instead of wrapping).
        """
        parts = []
        for i, key in enumerate(JOURNEY_STEPS, start=1):
            label = T[key]
            if i < active_step:
                parts.append(f'<span style="white-space:nowrap;">✅ <b>{label}</b></span>')
            elif i == active_step:
                parts.append(
                    f'<span style="white-space:nowrap; color:#1c83e1;">🟢 <b>{label}</b></span>'
                )
            else:
                parts.append(f'<span style="white-space:nowrap; opacity:0.5;">⚪ {label}</span>')

            if i < len(JOURNEY_STEPS):
                parts.append('<span style="opacity:0.35; padding:0 0.5rem;">→</span>')

        st.markdown(
            '<div style="display:flex; align-items:center; justify-content:space-between; '
            'flex-wrap:nowrap; overflow-x:auto; font-size:0.95rem; padding-bottom:0.35rem;">'
            + "".join(parts) + "</div>",
            unsafe_allow_html=True,
        )
        st.divider()


    def _render_identity_caption(code, tags, note_type=""):
        """Code + tags line shown at the top of stages 2 and 3, so the
        practitioner always sees what this reflection will be saved as."""
        st.caption(f"{T['reflection_active_case_prefix']} **{code}**")
        details = _tags_line(tags)
        if note_type:
            details = f"{note_type} · {details}"
        st.caption(f"{T['rs_tags_short_label']}: {details}")


    def _render_similar_card(ctx, record):
        """One earlier reflection on the context screen: code, date, why
        it is offered, an include checkbox and (collapsed) its
        observations. Never shows quotes or notes -- only observations."""
        with st.container(border=True):
            reasons = record.get("match_reasons") or []
            badges = " ".join(SIMILAR_REASON_BADGES[r] for r in reasons if r in SIMILAR_REASON_BADGES)
            top_col1, top_col2 = st.columns([4, 1])
            with top_col1:
                st.markdown(f"**{record['code']}**")
                caption = _date_only(record.get("created_at"))
                if record.get("note_type"):
                    caption = f"{caption} · {record['note_type']}"
                st.caption(caption)
            with top_col2:
                st.markdown(badges)

            if "linked" in reasons:
                st.caption(f"🔗 {T['rs_similar_reason_linked']}")
            if record.get("shared_tags"):
                st.caption(f"🏷️ {T['rs_similar_reason_tags']}: {_tags_line(record['shared_tags'])}")

            checked = st.checkbox(
                T["rs_similar_include_label"],
                value=(record["run_id"] in ctx.included_ids),
                key=f"ctx_sim_{record['run_id']}",
            )
            ctx.set_similar_included(record["run_id"], checked)

            with st.expander(T["rs_similar_observations_label"], expanded=False):
                for obs in record.get("observations") or []:
                    label = T["section_labels"].get(obs["module"], obs["module"].replace("_", " ").title())
                    icon = TRIGGER_ICONS.get(obs["module"], "•")
                    st.markdown(f"**{icon} {label}**")
                    st.write(obs["observation"])


    # ---------------------------------------------------------------------
    # Reflection workspace (unchanged by the redesign)
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
                                    lang=st.session_state.lang,
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
    active_context = ReflectionContext.get_active()
    active_session = ReflectionSession.get_active()


    # ---------------------------------------------------------------------
    # Stage 2 -- Earlier reflections (context), then generate
    # ---------------------------------------------------------------------
    if active_context is not None and active_session is None:
        ctx = active_context

        _render_journey(active_step=2)
        _render_identity_caption(ctx.reflection_code, ctx.case_tags, ctx.note_type)

        st.subheader(T["reflection_context_title"])

        with st.expander(T["rs_case_text_review_label"], expanded=False):
            st.caption(T["rs_case_text_not_saved_note"])
            st.write(ctx.case_text)

        st.divider()
        st.markdown(f"**{T['rs_similar_header']}**")
        if st.session_state.pop("_rs_similar_failed", False):
            st.warning(T["rs_similar_failed"])
        if ctx.similar:
            st.caption(T["rs_similar_intro"])
            for record in ctx.similar:
                _render_similar_card(ctx, record)
        else:
            st.info(T["rs_similar_none"])

        summary = ctx.strength_summary(T)
        st.divider()
        st.info(summary)
        st.caption(f"{T['rs_similar_used_label']}: {len(ctx.included_similar())}")

        # ---------------------------------------------------------------
        # Cost-safety guard (unchanged)
        # ---------------------------------------------------------------
        # Generating a reflection triggers 8 parallel Claude API calls
        # (rdi/orchestrator.py) plus automatic retries. Two protections:
        # 1. "_generating_reflection" disables the button while a
        #    generation is running, so a double click can't start a second.
        # 2. services.rate_limiter.check_and_record() enforces a generous
        #    per-person hourly cap (fails open if the database is down).
        is_generating = st.session_state.get("_generating_reflection", False)

        col1, col2 = st.columns(2)
        with col1:
            if st.button(
                T["reflection_context_continue"],
                type="primary",
                disabled=is_generating,
            ):
                with error_boundary(
                    "reflection_space (generate reflection)",
                    T=T,
                    user_name=user_name,
                    user_role=user_role,
                    context={"case_ref": getattr(ctx, "case_ref", "")},
                    reset_flags=["_generating_reflection"],
                ):
                    allowed, _count = check_and_record(user_name, max_per_hour=DEFAULT_MAX_PER_HOUR)

                    if not allowed:
                        st.session_state["_rate_limit_hit"] = True
                        st.rerun()

                    st.session_state["_generating_reflection"] = True

                    combined_text = ctx.combined_text()

                    # Backend duplicate protection (services/request_dedup.py):
                    # this person, this reflection code, this exact text.
                    reflection_request_id = request_dedup.fingerprint(
                        "reflection", user_name, getattr(ctx, "case_ref", ""), combined_text,
                    )
                    claim_status = request_dedup.claim(
                        reflection_request_id, "reflection", ttl_minutes=REQUEST_DEDUP_TTL_MINUTES,
                    )
                    if claim_status != "claimed":
                        st.session_state["_generating_reflection"] = False
                        st.session_state["_reflection_duplicate_hit"] = True
                        st.rerun()

                    ctx.log_pre_orchestrator_summary(T)

                    reflection_succeeded = False
                    try:
                        with st.spinner(f"{T['journey_step3']}..."):
                            result = run_reflection(combined_text, st.session_state.lang, context_description=summary)
                        reflection_succeeded = True
                    finally:
                        # A failed/aborted attempt must not block a retry.
                        if reflection_succeeded:
                            request_dedup.complete(reflection_request_id)
                        else:
                            request_dedup.release(reflection_request_id)

                    st.session_state["_generating_reflection"] = False

                    if "error" not in result:
                        log_reflection(ctx.case_ref, result["raw"], user_name, user_role)

                    session = ReflectionSession(
                        result,
                        reflected_drafts=[],
                        case_ref=ctx.case_ref,
                        context_summary=summary,
                        case_text=ctx.case_text,
                        case_tags=ctx.case_tags,
                        note_type=ctx.note_type,
                        previous_code=ctx.previous_code,
                    )

                    # The REFLECTION is the record: save what the AI found
                    # (with its verified anonymised passages), identified by
                    # the neutral code and case tags. The case text itself
                    # is NOT saved. Best-effort: if saving fails the
                    # reflection still works, the practitioner is told notes
                    # can't be kept for this one.
                    if "error" not in result:
                        try:
                            saved = save_reflection_run(
                                case_ref=ctx.case_ref,
                                source_draft_ids=[],
                                language=st.session_state.lang,
                                prompt_version=result.get("prompt_version", ""),
                                model=result.get("model", ""),
                                module_status=result.get("module_status", {}),
                                findings=result.get("findings", []),
                                created_by=user_name,
                                created_by_role=user_role,
                                reflection_code=ctx.reflection_code,
                                case_tags=ctx.case_tags,
                                note_type=ctx.note_type,
                                previous_code=ctx.previous_code,
                            )
                            session.attach_saved_findings(
                                saved["run_id"], saved["finding_ids"], user_name,
                            )
                        except Exception:
                            session.findings_save_failed = True

                    ReflectionContext.clear()
                    session.save()

                    # A brand-new workspace always opens with every tab
                    # collapsed and no leftover input or error state.
                    _reset_ephemeral_widget_state([
                        "workspace_open_", "convo_input_", "convo_error_",
                    ])

                    st.rerun()
        with col2:
            if st.button(T["rs_back_to_case_button"], disabled=is_generating):
                # Put the case back into the form so nothing has to be
                # retyped.
                st.session_state[PREFILL_KEY] = {
                    "text": ctx.case_text,
                    "tags": list(ctx.case_tags),
                    "note_type": ctx.note_type,
                    "previous_code": ctx.previous_code,
                }
                ReflectionContext.clear()
                st.rerun()

        if st.session_state.pop("_rate_limit_hit", False):
            st.error(T["rate_limit_exceeded_message"].format(max=DEFAULT_MAX_PER_HOUR))

        if st.session_state.pop("_reflection_duplicate_hit", False):
            st.info(T["reflection_duplicate_message"])

        st.stop()


    # ---------------------------------------------------------------------
    # Stage 3 -- Professional reflection (the workspace)
    # ---------------------------------------------------------------------
    if active_session is not None:
        session = active_session

        if session.has_error():
            _render_journey(active_step=3)
            # Complete Failure: the same numbered "Something went wrong"
            # screen as any other unexpected error (already logged once
            # by rdi/orchestrator.py:run_reflection).
            render_application_error_screen(
                T, session.issue_id, session.error_id,
                friendly_message=session.friendly_message,
            )
            if st.button(T["rs_start_over_button"], key="rs_start_over_after_error"):
                _start_fresh()
                st.rerun()
            st.stop()

        _render_journey(active_step=3)
        _render_identity_caption(session.case_ref, session.case_tags, session.note_type)

        if session.failed_count > 0:
            st.warning(T["reflection_partial_failure_notice"].format(count=session.failed_count))

        if session.findings_save_failed:
            st.info(T["findings_not_saved_notice"])

        # What this reflection is grounded in. The case text is only held
        # in this browser session and is never saved.
        with st.expander(T["workspace_document_header"], expanded=False):
            st.caption(T["rs_case_text_not_saved_note"])
            st.write(session.case_text)

        if session.context_summary:
            st.caption(f"{T['workspace_context_header']}: {session.context_summary}")

        total_opportunities = len(session.opportunities)
        if total_opportunities:
            st.progress(session.explored_count() / total_opportunities)
            st.caption(T["workspace_progress_label"].format(
                explored=session.explored_count(), total=total_opportunities
            ))

        # Reflection Dashboard + Navigator: one tab per dimension.
        st.subheader(T["workspace_opportunities_header"])
        ordered_opportunities = build_conversation(session.opportunities)

        if ordered_opportunities:
            st.caption(T["dashboard_navigator_hint"])
            tab_labels = []
            for opportunity in ordered_opportunities:
                label = T["section_labels"].get(opportunity.trigger, opportunity.trigger.replace("_", " ").title())
                icon = TRIGGER_ICONS.get(opportunity.trigger, "•")
                badge = f" {T['workspace_explored_badge']}" if opportunity.explored else ""
                tab_labels.append(f"{icon} {label}{badge}")

            tabs = st.tabs(tab_labels)
            for tab, opportunity in zip(tabs, ordered_opportunities):
                with tab:
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
    # Stage 1 -- Your case: write, paste or upload, then continue
    # ---------------------------------------------------------------------
    _render_journey(active_step=1)

    flash = st.session_state.pop(FLASH_KEY, None)
    if flash:
        st.success(flash)

    st.caption(T["rs_intro"])

    # Coming back from stage 2: refill the form before its widgets exist
    # (Streamlit does not allow writing a widget's value after it has
    # been created in the same run).
    prefill = st.session_state.pop(PREFILL_KEY, None)
    if prefill:
        st.session_state[_form_key("text")] = prefill.get("text", "")
        st.session_state[_form_key("tags")] = reflection_records.clean_tags(prefill.get("tags"))
        st.session_state[_form_key("previous_code")] = prefill.get("previous_code", "")
        if prefill.get("note_type") in T["doc_types"]:
            st.session_state[_form_key("note_type") + f"_{st.session_state.lang}"] = prefill["note_type"]

    if NEW_CODE_KEY not in st.session_state:
        st.session_state[NEW_CODE_KEY] = reflection_records.new_reflection_code()
    reflection_code = st.session_state[NEW_CODE_KEY]

    st.markdown(f"**{T['rs_code_label']}** `{reflection_code}`")
    st.caption(T["rs_code_help"])

    note_type = st.selectbox(
        T["rs_note_type_label"],
        T["doc_types"],
        key=_form_key("note_type") + f"_{st.session_state.lang}",
    )

    case_tags = st.multiselect(
        T["rs_tags_label"],
        list(reflection_records.CASE_TAGS),
        format_func=_tag_label,
        max_selections=reflection_records.MAX_TAGS,
        placeholder=T["rs_tags_placeholder"],
        help=T["rs_tags_help"].format(max=reflection_records.MAX_TAGS),
        key=_form_key("tags"),
    )

    previous_code_raw = st.text_input(
        T["rs_previous_code_label"],
        placeholder=T["rs_previous_code_placeholder"],
        help=T["rs_previous_code_help"],
        key=_form_key("previous_code"),
    )

    # Optional: bring in an existing document. Only the TEXT is read (the
    # file itself is never stored -- services/document_import.py) and it is
    # placed in the box below so the professional can check and edit it.
    text_key = _form_key("text")
    imported_key = _form_key("imported")
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
            current = st.session_state.get(text_key, "")
            st.session_state[text_key] = (current.rstrip() + "\n\n" + extracted) if current.strip() else extracted
            st.session_state[imported_key] = {"file_id": uploaded.file_id, "error": None}
        except document_import.DocumentImportError as exc:
            st.session_state[imported_key] = {"file_id": uploaded.file_id, "error": exc.reason}
    outcome = st.session_state.get(imported_key)
    if outcome:
        if outcome["error"]:
            st.error(T["doc_import_errors"].get(outcome["error"], T["doc_import_errors"]["unreadable"]).format(**import_limits))
        else:
            st.success(T["doc_import_loaded"])

    case_text = st.text_area(
        T["rs_case_text_label"],
        key=text_key,
        height=260,
        placeholder=T["rs_case_text_placeholder"],
    )
    st.caption(T["rs_case_text_not_saved_note"])

    if st.button(T["rs_continue_button"], type="primary", key="rs_continue_btn"):
        problem = None
        previous_code = ""
        if not (case_text or "").strip():
            problem = T["empty"]
        elif (previous_code_raw or "").strip():
            previous_code = reflection_records.normalize_code(previous_code_raw)
            if not previous_code:
                problem = T["rs_previous_code_invalid"]
            else:
                try:
                    if reflection_records.get_own_reflection(previous_code, user_name) is None:
                        problem = T["rs_previous_code_not_found"].format(code=previous_code)
                except Exception:
                    problem = T["rs_previous_code_check_failed"]

        if problem:
            st.warning(problem)
        else:
            rag_log(f"[RAG] Reflection started for code={reflection_code!r}")
            clean = reflection_records.clean_tags(case_tags)
            try:
                similar = reflection_records.find_similar_reflections(
                    user_name, clean, previous_code=previous_code, exclude_code=reflection_code,
                )
            except Exception:
                # Never block a reflection because the lookup failed --
                # it simply goes ahead without earlier context.
                similar = []
                st.session_state["_rs_similar_failed"] = True

            _reset_ephemeral_widget_state(["ctx_sim_"])
            ReflectionContext(
                reflection_code=reflection_code,
                case_text=case_text.strip(),
                case_tags=clean,
                note_type=note_type,
                previous_code=previous_code,
                similar=similar,
            ).save()
            st.rerun()
