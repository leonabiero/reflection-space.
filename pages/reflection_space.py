import streamlit as st
from services.draft_storage import get_drafts, update_draft, mark_completed
from services.reflection_service import generate_reflection
from services.anonymizer import anonymize
from services.language import init_language

T = init_language()

st.title(T["nav_reflection"])

drafts = get_drafts()
if not drafts:
    st.info(T["no_drafts"])
    st.stop()

selected = st.multiselect(
    T["select_drafts"],
    options=drafts,
    format_func=lambda x: f"{x[1]} - {x[2]} ({x[4]})"
)

if st.button(T["begin_reflection"]):
    combined_text = "\n\n".join([d[3] for d in selected])
    result = generate_reflection(combined_text, st.session_state.lang)
    st.session_state["reflection"] = result
    st.session_state["reflected_draft_id"] = selected[0][0] if selected else None
    st.session_state["reflected_original_text"] = combined_text

if "reflection" in st.session_state:
    r = st.session_state["reflection"]
    if "error" in r:
        st.error(r["error"])
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
    edited_text = st.text_area(
        T["edit_document_label"],
        value=st.session_state.get("reflected_original_text", ""),
        height=250,
    )

    col1, col2 = st.columns(2)
    with col1:
        if st.button(T["submit_no_edit"]):
            draft_id = st.session_state.get("reflected_draft_id")
            if draft_id:
                mark_completed(draft_id)
                st.session_state.pop("reflection", None)
                st.session_state.pop("reflected_draft_id", None)
                st.session_state.pop("reflected_original_text", None)
                st.success(T["submitted"])
                st.rerun()
    with col2:
        if st.button(T["submit_with_edit"]):
            draft_id = st.session_state.get("reflected_draft_id")
            if draft_id:
                update_draft(draft_id, edited_text)
                mark_completed(draft_id)
                st.session_state.pop("reflection", None)
                st.session_state.pop("reflected_draft_id", None)
                st.session_state.pop("reflected_original_text", None)
                st.success(T["submitted"])
                st.rerun()