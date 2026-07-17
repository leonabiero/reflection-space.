import streamlit as st
from collections import defaultdict
from services.draft_storage import get_drafts, finalize_draft
from services.reflection_service import generate_reflection
from services.feedback_store import save_feedback
from services.language import init_language, render_nav
from services.visit_log import log_visit
from services.identity import init_identity, render_identity_footer

T = init_language()
log_visit("reflection_space", st.session_state.lang)
user_name, user_role = init_identity(T)
render_nav(T)
render_identity_footer(T)

st.title(T["nav_reflection"])

# Keys cleared together whenever a reflection session (per client) ends,
# whether by finishing feedback or skipping it.
_SESSION_KEYS = (
    "reflection", "reflected_drafts", "submitted_ids",
    "awaiting_feedback", "reflection_case_ref",
)


def _clear_session():
    for k in _SESSION_KEYS:
        st.session_state.pop(k, None)


def _date_only(iso_str):
    return (iso_str or "")[:10]


def _format_draft_option(d):
    # d = (id, case_ref, doc_type, content, created_at, created_by, created_by_role)
    doc_type, created_at, creator, role = d[2], d[4], d[5] or "Unknown", d[6] or ""
    role_label = T.get("role_labels", {}).get(role, role)
    role_suffix = f", {role_label}" if role_label else ""
    time_part = created_at[11:16] if created_at and len(created_at) >= 16 else ""
    return f"{doc_type} ({time_part}) — {creator}{role_suffix}"


drafts = get_drafts()

if not drafts and "reflection" not in st.session_state:
    st.info(T["no_drafts"])
    st.stop()


# --- A reflection session is already in progress for one client: show
# that instead of the folder browser, so work stays scoped to one
# client at a time. ---
if "reflection" in st.session_state:
    active_case_ref = st.session_state.get("reflection_case_ref", "")
    if active_case_ref:
        st.caption(f"{T['reflection_active_case_prefix']} {active_case_ref}")

    r = st.session_state["reflection"]
    if "error" in r:
        st.error(T["error_parsing"])
        st.text(r["raw"])
        st.stop()

    for section, content in r.items():
        label = T["section_labels"].get(section, section.replace("_", " ").title())
        st.subheader(label)
        if isinstance(content, dict):
            observation = content.get("observation", "")
            questions = content.get("questions", [])
            if observation:
                st.write(observation)
            if questions:
                for q in questions:
                    st.markdown(f"- {q}")
        else:
            st.write(content)

    st.divider()
    st.subheader(T["update_document"])

    reflected_drafts = st.session_state.get("reflected_drafts", [])
    submitted_ids = st.session_state.get("submitted_ids", set())

    if not st.session_state.get("awaiting_feedback", False):
        for draft in reflected_drafts:
            draft_id, case_ref, doc_type, draft_content = draft[0], draft[1], draft[2], draft[3]

            if draft_id in submitted_ids:
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
                submitted_ids.add(draft_id)

                all_ids_in_batch = {d[0] for d in reflected_drafts}
                if submitted_ids >= all_ids_in_batch:
                    remaining = get_drafts()
                    if not remaining:
                        st.session_state["submitted_ids"] = submitted_ids
                        st.session_state["awaiting_feedback"] = True
                    else:
                        _clear_session()
                else:
                    st.session_state["submitted_ids"] = submitted_ids

                st.rerun()

    if st.session_state.get("awaiting_feedback", False):
        st.divider()
        st.subheader(T["feedback_prompt_title"])

        rating = st.slider(T["feedback_rating_label"], min_value=1, max_value=5, value=3)
        comment = st.text_area(T["feedback_comment_label"], value="", height=80)

        col1, col2 = st.columns(2)
        with col1:
            if st.button(T["feedback_submit_button"]):
                draft_ids = [d[0] for d in reflected_drafts]
                save_feedback(draft_ids, rating, comment, user_name, user_role)
                _clear_session()
                st.success(T["feedback_thanks"])
                st.rerun()
        with col2:
            if st.button(T["feedback_skip_button"]):
                _clear_session()
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
                st.write(f"• {_format_draft_option(d)}")

        selected = st.multiselect(
            T["select_drafts"],
            options=case_drafts,
            format_func=_format_draft_option,
            key=f"select_{case_ref}",
        )

        if st.button(T["begin_reflection"], key=f"begin_{case_ref}", disabled=not selected):
            combined_text = "\n\n".join(d[3] for d in selected)
            result = generate_reflection(combined_text, st.session_state.lang)
            st.session_state["reflection"] = result
            st.session_state["reflected_drafts"] = selected
            st.session_state["reflection_case_ref"] = case_ref
            st.session_state["submitted_ids"] = set()
            st.session_state["awaiting_feedback"] = False
            st.rerun()