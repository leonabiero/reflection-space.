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
from services.explanation_builder import build_explanations, similarity_category
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

# Phase 3 (Practitioner UX): a short badge label per reason, shown next
# to the icon on the Better Historical Document Cards (UX Priority 6).
# Purely cosmetic -- reuses the exact same match_reasons data that was
# already being retrieved and displayed via MATCH_REASON_BADGES above.
MATCH_REASON_TEXT_KEY = {
    "must_include": "why_reason_must_include_generic",
    "semantic": "why_reason_semantic_generic",
    "recency": "why_reason_recency",
}

# Small emoji used purely to make each reflective dimension visually
# distinct on the Reflection Dashboard tabs (UX Priority 2) and the
# Reflection Coverage checklist (UX Priority 7). Cosmetic only -- does
# not affect which companions run or what they return.
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

# Localized month names for the Historical Timeline (UX Priority 5).
# Kept local to this page rather than in services/language.py, since
# it's a small, purely presentational lookup table with no reuse
# elsewhere in the app.
_MONTH_NAMES = {
    "Español": ["", "enero", "febrero", "marzo", "abril", "mayo", "junio",
                "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"],
    "Euskera": ["", "urtarrila", "otsaila", "martxoa", "apirila", "maiatza", "ekaina",
                "uztaila", "abuztua", "iraila", "urria", "azaroa", "abendua"],
    "English": ["", "January", "February", "March", "April", "May", "June",
                "July", "August", "September", "October", "November", "December"],
}


def _month_year_label(date_str):
    """'2025-03-14T...' -> 'March 2025' (localized). Falls back to the
    raw date fragment if the string can't be parsed -- purely cosmetic,
    never blocks rendering."""
    if not date_str or len(date_str) < 7:
        return date_str or ""
    try:
        year, month = date_str[:4], int(date_str[5:7])
        names = _MONTH_NAMES.get(st.session_state.lang, _MONTH_NAMES["English"])
        return f"{names[month]} {year}"
    except Exception:
        return date_str[:7]


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


def _historical_badges(h):
    """Return the ordered list of reason keys present on this historical
    document (e.g. ["must_include", "semantic"]) -- shared by both the
    checkbox label and the card renderer below."""
    reasons = h.get("match_reasons")
    if not reasons:
        reasons = [h.get("match_reason")] if h.get("match_reason") else []
    return [r for r in MATCH_REASON_ORDER if r in reasons]


def _format_historical_option(h):
    # h is a dict from rdi.context_engine.get_historical_context() --
    # now also carrying "score", "match_reason" (primary, back-compat)
    # and "match_reasons" (full list -- see rdi/retrieval_service.py),
    # used only for the transparency badge(s).
    date_part = _date_only(h.get("completed_at") or h.get("created_at"))
    edited_suffix = f" — {T['case_history_completed_label']}" if h.get("was_edited") else ""

    badges = "".join(MATCH_REASON_BADGES[r] for r in _historical_badges(h))
    badge_prefix = f"{badges} " if badges else ""
    return f"{badge_prefix}{h['doc_type']} ({date_part}){edited_suffix}"


def _render_why_included(h, current_text):
    """
    Sprint 11 (Explainability). Renders the collapsed "Why was this
    included?" panel for one historical document on the Reflection
    Context screen.

    Purely presentational -- reads only fields the retrieval pipeline
    already attaches to `h` (match_reasons/match_reason, doc_type,
    content, score) via services.explanation_builder, and makes no
    Anthropic API call. Does not change which documents are retrieved,
    their order, or whether they're included -- that stays fully
    controlled by the checkbox above this panel.

    Note on nesting: Streamlit does not support an expander nested
    inside another expander, so the optional "Technical details"
    (similarity category) is rendered as a divided sub-section INSIDE
    the same "Why was this included?" expander, rather than as a
    separate nested expander -- both stay collapsed together by
    default, which keeps the collapsed-by-default requirement intact.
    """
    explanations = build_explanations(h, current_text, T)
    if not explanations:
        return

    with st.expander(T["why_included_label"], expanded=False):
        for line in explanations:
            st.write(f"✓ {line}")

        sim_cat = similarity_category(h.get("score"))
        if sim_cat:
            st.divider()
            st.caption(T["why_technical_details_label"])
            st.write(f"{T['why_similarity_label']} {T['why_similarity_' + sim_cat]}")


# ---------------------------------------------------------------------
# Phase 3 (Practitioner UX)
# ---------------------------------------------------------------------
# Everything below this line is new for Phase 3. It is purely
# presentational: it reorganises how existing data (historical
# documents, opportunities, retrieval reasons, session progress) is
# LAID OUT on screen. It does not call the Anthropic API, does not
# change retrieval/ranking, does not change the prompts, and does not
# add, remove, or reorder any of the 8 reflective dimensions -- see the
# accompanying explanation for the full list of what was and wasn't
# touched.

JOURNEY_STEPS = ["journey_step1", "journey_step2", "journey_step3", "journey_step4"]


def _render_journey(active_step):
    """
    UX Priority 1 -- Reflection Journey.

    Renders a simple 4-step horizontal progress strip so the
    practitioner always knows where they are in the flow: which
    document(s) they picked, that historical context was gathered,
    that the AI is reasoning across both, and that reflective questions
    are what comes out the other end. `active_step` is 1-4; steps
    before it are shown as done (✓), the active one is highlighted,
    later ones are shown as upcoming.

    This explains the WORKFLOW in plain language -- it never exposes
    retrieval internals, model names, or prompt structure.
    """
    cols = st.columns(4)
    for i, (col, key) in enumerate(zip(cols, JOURNEY_STEPS), start=1):
        label = T[key]
        with col:
            if i < active_step:
                st.markdown(f"✅ **{label}**")
            elif i == active_step:
                st.markdown(f"▶️ **:blue[{label}]**")
            else:
                st.markdown(f"⚪ {label}")
    st.divider()


def _render_historical_timeline(ctx, current_text):
    """
    UX Priority 5 & 6 -- Historical Timeline + Better Historical
    Document Cards.

    Same underlying data as before (ctx.historical, already retrieved
    by rdi.context_engine.get_historical_context() -- nothing about
    retrieval, ranking, or the documents returned changes here). This
    only changes how it's laid out: chronologically, grouped by
    month/year, as visually distinct cards with badges and the
    existing "Why was this included?" panel inside each card, ending
    with a "Today's Documentation" marker.

    Selection state (which historical documents stay included in the
    reflection) is still driven by the exact same checkboxes as before
    -- this function only changes their visual grouping/container, not
    their behavior or session storage.
    """
    st.markdown(f"**{T['historical_timeline_header']}**")
    st.caption(T["historical_timeline_intro"])

    # Oldest first, so the timeline reads top-to-bottom as a real
    # chronology ending at "today".
    ordered = sorted(
        ctx.historical,
        key=lambda h: h.get("completed_at") or h.get("created_at") or "",
    )

    last_month_label = None
    for h in ordered:
        month_label = _month_year_label(h.get("completed_at") or h.get("created_at"))
        if month_label != last_month_label:
            st.markdown(f"##### 🗓️ {month_label}")
            last_month_label = month_label

        with st.container(border=True):
            badges = _historical_badges(h)
            badge_row = "  ".join(f"{MATCH_REASON_BADGES[r]}" for r in badges)
            date_part = _date_only(h.get("completed_at") or h.get("created_at"))
            edited_suffix = f" · {T['case_history_completed_label']}" if h.get("was_edited") else ""

            top_col1, top_col2 = st.columns([4, 1])
            with top_col1:
                st.markdown(f"**{h['doc_type']}**")
                st.caption(f"{date_part}{edited_suffix}")
            with top_col2:
                st.markdown(badge_row)

            hist_key = f"ctx_hist_{h['id']}"
            checked = st.checkbox(
                _format_historical_option(h),
                value=(h["id"] in ctx.selected_hist_ids),
                key=hist_key,
                label_visibility="collapsed",
            )
            ctx.set_historical_included(h["id"], checked)
            _render_why_included(h, current_text)

        st.markdown("<div style='text-align:center; opacity:0.5;'>↓</div>", unsafe_allow_html=True)

    # The chronology always ends at today's documentation, so the
    # practitioner can see where today's note sits relative to the
    # case's history.
    with st.container(border=True):
        st.markdown(f"**{T['timeline_today_label']}**")
        for d in ctx.selected:
            st.caption(f"{d[2]}")


def _render_coverage(session):
    """
    UX Priority 7 -- Reflection Coverage.

    Confirms, dimension by dimension, that the reflection actually
    considered all 8 areas -- NOT a score, NOT an assessment of the
    practitioner or the case. Every companion in rdi.companions.COMPANIONS
    always runs for every reflection (see rdi/orchestrator.py); a
    dimension only has "nothing to raise" if that companion's model
    call found nothing notable, or (rarely) failed outright. This panel
    reads only `session.failed_labels` (already returned by the
    orchestrator, see rdi/orchestrator.py's "failed_labels" key) --
    nothing new is computed, generated, or sent to the API here.
    """
    st.subheader(T["coverage_header"])
    st.caption(T["coverage_intro"])

    failed = set(session.failed_labels or [])
    cols = st.columns(2)
    for i, companion in enumerate(COMPANIONS):
        label = T["section_labels"].get(companion["key"], companion["label"])
        icon = TRIGGER_ICONS.get(companion["key"], "•")
        with cols[i % 2]:
            if companion["label"] in failed:
                st.write(f"⚠️ {icon} **{label}** — _{T['coverage_unavailable']}_")
            else:
                st.write(f"✅ {icon} **{label}** — {T['coverage_considered']}")


# ---------------------------------------------------------------------


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
    for q in opportunity.invitation:
        st.markdown(f"- {q}")

    st.caption(T["workspace_reminder"])

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

    _render_journey(active_step=2)

    if ctx.case_ref:
        st.caption(f"{T['reflection_active_case_prefix']} {ctx.case_ref}")

    st.subheader(T["reflection_context_title"])

    st.markdown(f"**{T['reflection_context_current_label']}**")
    for d in ctx.selected:
        st.checkbox(_format_draft_option(d), value=True, disabled=True, key=f"ctx_current_{d[0]}")

    if ctx.historical:
        # Sprint 11: today's selected document text, used only locally
        # by services.explanation_builder to find shared keywords with
        # each historical document for the "Why was this included?"
        # panel -- never sent anywhere, never logged.
        current_text = "\n\n".join(d[3] for d in ctx.selected)

        st.divider()
        # UX Priority 5 & 6: chronological timeline of cards, replacing
        # the flat checkbox list. Same documents, same checkboxes, same
        # "Why was this included?" panels -- just organised as a
        # timeline instead of a plain list.
        _render_historical_timeline(ctx, current_text)

    summary = ctx.strength_summary(T)
    st.divider()
    st.info(summary)
    # UX Priority 3: explicit count of historical documents currently
    # included, alongside the existing Context Confidence sentence.
    st.caption(f"{T['historical_docs_used_label']}: {len(ctx.included_historical())}")

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

            # UX Priority 1: Step 3 of the Reflection Journey, shown for
            # the duration of the (unchanged) orchestrator call.
            with st.spinner(f"{T['journey_step3']}..."):
                # Same underlying companion calls as before (see
                # rdi/orchestrator.py) -- this just also reshapes the
                # result into a ReflectionSession for display and
                # tracking.
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

    if session.has_error():
        _render_journey(active_step=3)
        st.error(T["error_parsing"])
        st.text(session.error_raw)
        st.stop()

    _render_journey(active_step=4)

    if session.case_ref:
        st.caption(f"{T['reflection_active_case_prefix']} {session.case_ref}")

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

    # UX Priority 2 & 4: Reflection Dashboard + Navigator. Each
    # reflective dimension becomes its own tab -- same content as
    # before (observation, questions, Explore, conversation), just
    # organised into clearly separated, directly-jumpable sections
    # instead of a long vertical stack of expanders.
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

    # UX Priority 7: Reflection Coverage checklist.
    _render_coverage(session)

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
_render_journey(active_step=1)

# UX Priority 8: Reflection History. Full past reflection CONTENT is
# never persisted anywhere in this app once a session ends (only the
# fact that a theme was explored, and completed document text -- see
# services/exploration_log.py and services/draft_storage.py), so this
# is a pointer to the one place that data genuinely lives: the
# practitioner's own Reflective Journey page. No new storage, no new
# database table, no schema change.
st.caption(f"{T['history_link_hint']} ")
st.page_link("pages/growth_dashboard.py", label=T["nav_growth"])
st.divider()

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