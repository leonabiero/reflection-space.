import streamlit as st
from collections import defaultdict
from services.draft_storage import get_drafts, finalize_draft, delete_pending_draft
from services.reflection_log import log_reflection
from services.feedback_store import save_feedback
from services.reflection_service import continue_companion_conversation
from services.exploration_log import log_exploration
from services.language import init_language, render_nav
from services.visit_log import log_visit
from services.identity import init_identity, render_identity_footer
from services.rag_logging import rag_log
from rdi.context_engine import get_historical_context
from rdi.orchestrator import run_reflection
from rdi.conversation_builder import build_conversation
from rdi.reflection_context import ReflectionContext
from rdi.reflection_session import ReflectionSession
from rdi.companions import COMPANIONS

T = init_language()
log_visit("reflection_space", st.session_state.lang)
user_name, user_role = init_identity(T)
render_nav(T)
render_identity_footer(T)

st.title(T["nav_reflection"])

# trigger -> companion dict, so the workspace can look up label/focus
# when continuing a conversation, without re-deriving it from the
# opportunity's stored observation text.
COMPANIONS_BY_KEY = {c["key"]: c for c in COMPANIONS}

# Hybrid RAG transparency: a short badge per retrieval reason, so the
# practitioner can see not just WHICH documents were retrieved but WHY,
# alongside the existing checkbox review/deselect controls -- this is
# additive to _format_historical_option, nothing about deselecting or
# reviewing documents changes.
#
# A document can now carry MORE THAN ONE reason (e.g. it's both the
# case's latest Assessment AND a semantic match -- see
# rdi/retrieval_service.py, "Multi-reason merge"), so
# _format_historical_option renders one badge per reason present,
# always in this fixed order, rather than a single badge.
MATCH_REASON_BADGES = {
    "must_include": "📌",
    "semantic": "🔎",
    "recency": "🕒",
}
MATCH_REASON_ORDER = ["must_include", "semantic", "recency"]


def _clear_all():
    """Leaving the reflection flow entirely, whatever stage it was at --
    resets both the context and the session objects.

    Sprint 7: before the session (and its in-memory conversations) is
    discarded, log which themes were actually explored and how many
    turns each ran to (see services.exploration_log). No conversation
    text is persisted -- only the fact that this theme was explored, by
    whom, on which case, for the Growth/Team dashboards to read later.
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


def _date_only(iso_str):
    return (iso_str or "")[:10]


def _format_draft_option(d):
    # d = (id, case_ref, doc_type, content, created_at, created_by, created_by_role)
    doc_type, created_at, creator, role = d[2], d[4], d[5] or T["unknown_label"], d[6] or ""
    role_label = T.get("role_labels", {}).get(role, role)
    role_suffix = f", {role_label}" if role_label else ""
    time_part = created_at[11:16] if created_at and len(created_at) >= 16 else ""
    return f"{doc_type} ({time_part}) — {creator}{role_suffix}"


def _format_historical_option(h):
    # h is a dict from rdi.context_engine.get_historical_context() --
    # now also carrying "score", "match_reason" (primary, back-compat)
    # and "match_reasons" (full list -- see rdi/retrieval_service.py),
    # used only for the transparency badge(s).
    date_part = _date_only(h.get("completed_at") or h.get("created_at"))
    edited_suffix = f" — {T['case_history_completed_label']}" if h.get("was_edited") else ""

    reasons = h.get("match_reasons")
    if not reasons:
        reasons = [h.get("match_reason")] if h.get("match_reason") else []
    badges = "".join(
        MATCH_REASON_BADGES[r] for r in MATCH_REASON_ORDER if r in reasons
    )
    badge_prefix = f"{badges} " if badges else ""
    return f"{badge_prefix}{h['doc_type']} ({date_part}){edited_suffix}"


def _render_opportunity_workspace(session, opportunity):
    """Sprint 6: render one reflective opportunity as an expandable
    workspace item -- the observation/questions, an Explore toggle, and
    (once opened) a conversation area."""
    label = T["section_labels"].get(opportunity.trigger, opportunity.trigger.replace("_", " ").title())
    badge = f" {T['workspace_explored_badge']}" if opportunity.explored else ""

    with st.expander(f"{label}{badge}", expanded=opportunity.explored):
        if opportunity.focus:
            st.write(opportunity.focus)
        for q in opportunity.invitation:
            st.markdown(f"- {q}")

        st.caption(T["workspace_reminder"])

        open_key = f"workspace_open_{opportunity.trigger}"
        is_open = st.session_state.get(open_key, False)

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
            message_text = st.text_area(
                T["workspace_conversation_input_label"],
                placeholder=T["workspace_conversation_placeholder"],
                key=input_key,
                height=80,
            )

            col1, col2 = st.columns([1, 1])
            with col1:
                if st.button(T["workspace_send_button"], key=f"send_btn_{opportunity.trigger}"):
                    if message_text and message_text.strip():
                        companion = COMPANIONS_BY_KEY.get(opportunity.trigger)
                        history_before = list(opportunity.conversation)
                        opportunity.add_professional_message(message_text.strip())

                        with st.spinner(T["workspace_ai_thinking"]):
                            result = continue_companion_conversation(
                                companion=companion,
                                safe_text=session.safe_text,
                                initial_observation=opportunity.focus,
                                initial_questions=opportunity.invitation,
                                conversation_history=history_before,
                                professional_message=message_text.strip(),
                                lang=st.session_state.lang,
                            )

                        if "reply" in result:
                            opportunity.add_ai_message(result["reply"])
                        else:
                            st.session_state[f"convo_error_{opportunity.trigger}"] = True

                        session.save()
                        st.rerun()
            with col2:
                if st.button(T["workspace_close_button"], key=f"close_btn_{opportunity.trigger}"):
                    st.session_state[open_key] = False
                    st.rerun()

            if st.session_state.pop(f"convo_error_{opportunity.trigger}", False):
                st.error(T["workspace_conversation_error"])


drafts = get_drafts()

active_context = ReflectionContext.get_active()
active_session = ReflectionSession.get_active()

if not drafts and active_session is None and active_context is None:
    st.info(T["no_drafts"])
    st.stop()


# --- Reflection Context step: shown after the practitioner picks
# document(s) to reflect on, before the reflection is generated. Surfaces
# relevant prior documentation for this case so it can be reviewed and
# deselected, per the Reflection Context Engine (rdi/context_engine.py). ---
if active_context is not None:
    ctx = active_context

    if ctx.case_ref:
        st.caption(f"{T['reflection_active_case_prefix']} {ctx.case_ref}")

    st.subheader(T["reflection_context_title"])

    st.markdown(f"**{T['reflection_context_current_label']}**")
    for d in ctx.selected:
        st.checkbox(_format_draft_option(d), value=True, disabled=True, key=f"ctx_current_{d[0]}")

    if ctx.historical:
        st.markdown(f"**{T['reflection_context_historical_label']}**")
        for h in ctx.historical:
            hist_key = f"ctx_hist_{h['id']}"
            checked = st.checkbox(
                _format_historical_option(h),
                value=(h["id"] in ctx.selected_hist_ids),
                key=hist_key,
            )
            ctx.set_historical_included(h["id"], checked)

    summary = ctx.strength_summary(T)
    st.info(summary)

    col1, col2 = st.columns(2)
    with col1:
        if st.button(T["reflection_context_continue"], type="primary"):
            combined_text = ctx.combined_text()

            # Development logging: capture exactly what is about to be
            # sent into the Reflection Orchestrator -- current
            # document(s), every included historical document with its
            # retrieval reason(s) and semantic score, and the resulting
            # Context Confidence sentence. See
            # rdi.reflection_context.ReflectionContext.log_pre_orchestrator_summary.
            ctx.log_pre_orchestrator_summary(T)

            # Same underlying companion calls as before (see
            # rdi/orchestrator.py) -- this just also reshapes the result
            # into a ReflectionSession for display and tracking.
            result = run_reflection(combined_text, st.session_state.lang, context_description=summary)
            if "error" not in result:
                log_reflection(ctx.case_ref, result["raw"], user_name, user_role)

            session = ReflectionSession(
                result,
                reflected_drafts=ctx.selected,
                case_ref=ctx.case_ref,
                context_summary=summary,
            )
            ReflectionContext.clear()
            session.save()
            st.rerun()
    with col2:
        if st.button(T["reflection_context_back"]):
            ReflectionContext.clear()
            st.rerun()

    st.stop()


# --- A reflection session is already in progress for one client: show
# the Reflection Workspace instead of the folder browser, so work stays
# scoped to one client at a time. ---
if active_session is not None:
    session = active_session

    if session.case_ref:
        st.caption(f"{T['reflection_active_case_prefix']} {session.case_ref}")

    if session.has_error():
        st.error(T["error_parsing"])
        st.text(session.error_raw)
        st.stop()

    if session.failed_count > 0:
        st.warning(T["reflection_partial_failure_notice"].format(count=session.failed_count))

    # --- Workspace header: document + context summary, so the
    # practitioner always sees what this reflection is grounded in. ---
    with st.expander(T["workspace_document_header"], expanded=False):
        for d in session.reflected_drafts:
            st.markdown(f"**{d[1]} - {d[2]}**")
            st.write(d[3])

    if session.context_summary:
        st.caption(f"{T['workspace_context_header']}: {session.context_summary}")

    total_opportunities = len(session.opportunities)
    if total_opportunities:
        st.progress(session.explored_count() / total_opportunities)
        st.caption(T["workspace_progress_label"].format(
            explored=session.explored_count(), total=total_opportunities
        ))

    st.subheader(T["workspace_opportunities_header"])

    for opportunity in build_conversation(session.opportunities):
        _render_opportunity_workspace(session, opportunity)

    st.divider()
    st.subheader(T["update_document"])

    if not session.awaiting_feedback:
        for draft in session.reflected_drafts:
            draft_id, case_ref, doc_type, draft_content = draft[0], draft[1], draft[2], draft[3]

            if session.is_submitted(draft_id):
                st.success(f"{case_ref} - {doc_type}: {T['submitted']}")
                continue

            st.markdown(f"**{case_ref} - {doc_type}**")
            edited_text = st.text_area(
                T["edit_document_label"],
                value=draft_content,
                height=200,
                key=f"edit_{draft_id}",
            )
            if st.button(T["submit_draft"], key=f"submit_{draft_id}"):
                finalize_draft(draft_id, edited_text)
                session.mark_submitted(draft_id)

                if session.all_batch_submitted():
                    remaining = get_drafts()
                    if not remaining:
                        session.awaiting_feedback = True
                        session.save()
                    else:
                        _clear_all()
                else:
                    session.save()

                st.rerun()

    if session.awaiting_feedback:
        st.divider()
        st.subheader(T["feedback_prompt_title"])

        rating = st.slider(T["feedback_rating_label"], min_value=1, max_value=5, value=3)
        comment = st.text_area(T["feedback_comment_label"], value="", height=80)

        col1, col2 = st.columns(2)
        with col1:
            if st.button(T["feedback_submit_button"]):
                save_feedback(session.draft_ids(), rating, comment, user_name, user_role)
                _clear_all()
                st.success(T["feedback_thanks"])
                st.rerun()
        with col2:
            if st.button(T["feedback_skip_button"]):
                _clear_all()
                st.rerun()

    st.stop()


# --- No reflection in progress: browse pending drafts as per-client
# folders. Same-day multiples are shown grouped under a date heading
# within the folder, but each document is still picked individually. ---
st.caption(T["reflection_folders_intro"])

by_case = defaultdict(list)
for d in drafts:
    key = d[1] or T["reflection_no_case_ref"]
    by_case[key].append(d)

for case_ref in sorted(by_case.keys(), key=lambda s: s.lower()):
    case_drafts = sorted(by_case[case_ref], key=lambda d: d[4] or "")

    by_date = defaultdict(list)
    for d in case_drafts:
        by_date[_date_only(d[4])].append(d)
    same_day_flag = any(len(v) > 1 for v in by_date.values())

    folder_icon = "📂" if same_day_flag else "📁"
    with st.expander(f"{folder_icon} {case_ref} — {len(case_drafts)}"):
        if same_day_flag:
            st.caption(T["reflection_same_day_notice"])

        for day in sorted(by_date.keys(), reverse=True):
            st.markdown(f"**{day}**")
            for d in by_date[day]:
                draft_id, creator = d[0], d[5] or ""
                chk_key = f"chk_{draft_id}"
                can_delete = user_role == "System Administrator" or (
                    user_name and user_name == creator
                )

                confirm_key = f"confirm_delete_pending_{draft_id}"
                if can_delete and st.session_state.get(confirm_key, False):
                    st.checkbox(_format_draft_option(d), key=chk_key, disabled=True)
                    st.warning(T["reflection_delete_confirm"])
                    cc1, cc2 = st.columns(2)
                    with cc1:
                        if st.button(T["case_history_delete_yes"], key=f"yes_delete_pending_{draft_id}"):
                            delete_pending_draft(draft_id, user_name, user_role)
                            st.session_state.pop(confirm_key, None)
                            st.session_state.pop(chk_key, None)
                            st.success(T["reflection_deleted_success"])
                            st.rerun()
                    with cc2:
                        if st.button(T["case_history_delete_cancel"], key=f"cancel_delete_pending_{draft_id}"):
                            st.session_state.pop(confirm_key, None)
                            st.rerun()
                elif can_delete:
                    chk_col, btn_col = st.columns([6, 1])
                    with chk_col:
                        st.checkbox(_format_draft_option(d), key=chk_key)
                    with btn_col:
                        if st.button("🗑️", key=f"delete_pending_{draft_id}", help=T["reflection_delete_button"]):
                            st.session_state[confirm_key] = True
                            st.rerun()
                else:
                    st.checkbox(_format_draft_option(d), key=chk_key)

        selected = [d for d in case_drafts if st.session_state.get(f"chk_{d[0]}", False)]

        if st.button(T["begin_reflection"], key=f"begin_{case_ref}", disabled=not selected):
            selected_ids = {d[0] for d in selected}

            # Development logging: mark the moment the practitioner
            # actually enters the Reflection workflow for this case,
            # before historical context retrieval or any companion
            # calls happen. See services/rag_logging.py.
            rag_log(f"[RAG] Reflection started for case_ref={case_ref!r}")

            # Hybrid RAG: use the selected document(s)' own text as the
            # semantic query, so historical retrieval finds documents
            # that are actually related to what's being reflected on
            # today -- not just whatever is most recent for this case.
            selected_text = "\n\n".join(d[3] for d in selected)
            historical = get_historical_context(
                case_ref, exclude_ids=selected_ids, query_text=selected_text,
            )
            ReflectionContext(case_ref=case_ref, selected=selected, historical=historical).save()
            # Reset this folder's checkboxes so a future visit starts clean.
            for d in case_drafts:
                st.session_state.pop(f"chk_{d[0]}", None)
            st.rerun()