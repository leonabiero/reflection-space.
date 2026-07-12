import streamlit as st
from services.draft_storage import get_drafts, finalize_draft
from services.reflection_service import generate_reflection
from services.language import init_language, render_nav
from services.visit_log import log_visit
from services.identity import init_identity, render_identity_footer

T = init_language()
log_visit("reflection_space", st.session_state.lang)
init_identity(T)
render_nav(T)
render_identity_footer(T)

st.title(T["nav_reflection"])

drafts = get_drafts()
if not drafts:
    st.info(T["no_drafts"])
    st.stop()


def _format_draft(x):
    # x: id, case_ref, doc_type, content, created_at, created_by, created_by_role
    creator = x[5] or "Unknown"
    role = x[6] or ""
    role_label = T.get("role_labels", {}).get(role, role)
    role_suffix = f", {role_label}" if role_label else ""
    return f"{x[1]} - {x[2]} ({x[4]}) — by {creator}{role_suffix}"


selected = st.multiselect(
    T["select_drafts"],
    options=drafts,
    format_func=_format_draft,
)

if st.button(T["begin_reflection"]):
    combined_text = "\n\n".join([d[3] for d in selected])
    result = generate_reflection(combined_text, st.session_state.lang)
    st.session_state["reflection"] = result
    # FR-028 fix: store the FULL list of selected drafts, not just the
    # first one, so every draft in this batch can be edited and saved
    # independently afterward.
    st.session_state["reflected_drafts"] = selected
    st.session_state["submitted_ids"] = set()

if "reflection" in st.session_state:
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

    # Each draft in the batch gets its own independent edit box and
    # submit button. finalize_draft() automatically detects whether the
    # text actually changed — if so, it archives the original version
    # into draft_history before saving the edit; if not, it just marks
    # the draft completed with no extra copy stored.
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
            st.session_state["submitted_ids"] = submitted_ids
            st.rerun()