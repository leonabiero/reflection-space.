import streamlit as st
from services.visit_log import get_visits, clear_visits
from services.anonymizer import anonymize
from services.language import get_lang
from services.draft_storage import get_completed_drafts
from services.qdrant_service import upsert_document, is_available as qdrant_available
from config import ADMIN_PASSWORD

st.set_page_config(page_title="Visit Log", layout="centered")

# Deliberately NOT calling init_language() here (its sidebar selectbox
# reliably segfaults this specific page — confirmed by testing).
# Falls back to Spanish if this tab hasn't set a language yet, matching
# the same "always defaults to Spanish" behavior as every other page.
current_lang = st.session_state.get("lang", "Español")
T = get_lang(current_lang)

st.title(T["admin_title"])

if "admin_authed" not in st.session_state:
    st.session_state.admin_authed = False

if not st.session_state.admin_authed:
    pw = st.text_input(T["admin_password_label"], type="password")
    if st.button(T["admin_enter_button"]):
        if ADMIN_PASSWORD and pw == ADMIN_PASSWORD:
            st.session_state.admin_authed = True
            st.rerun()
        else:
            st.error(T["admin_incorrect_password"])
    st.stop()

st.header(T["admin_visit_log"])
visits = get_visits()

if not visits:
    st.info(T["admin_no_visits"])
else:
    st.write(f"**{len(visits)} {T['admin_total_views_label']}**")

    rows_html = "".join(
        f"<tr><td>{page}</td><td>{lang}</td><td>{ts}</td></tr>"
        for page, lang, ts in visits
    )
    page_h = T["admin_table_page"]
    lang_h = T["admin_table_language"]
    visited_h = T["admin_table_visited"]
    table_html = f"""
    <table style="width:100%; border-collapse: collapse;">
        <thead>
            <tr style="text-align:left; border-bottom: 1px solid #444;">
                <th style="padding:6px;">{page_h}</th>
                <th style="padding:6px;">{lang_h}</th>
                <th style="padding:6px;">{visited_h}</th>
            </tr>
        </thead>
        <tbody>
            {rows_html}
        </tbody>
    </table>
    """
    st.markdown(table_html, unsafe_allow_html=True)

st.write("")
if st.button(T["admin_clear_log"]):
    clear_visits()
    st.rerun()

st.divider()

# --- Hybrid RAG: Qdrant backfill ----------------------------------------
# One-off utility for documents that were completed BEFORE the semantic
# retrieval upgrade existed -- those rows are in Postgres (the system of
# record, untouched) but were never embedded/indexed in Qdrant, since
# indexing only started happening at finalize_draft() going forward.
# Safe to run more than once: upsert_document() overwrites by draft id
# rather than duplicating, so re-running just re-embeds everything.
st.header(T["admin_backfill_header"])
st.caption(T["admin_backfill_caption"])

if not qdrant_available():
    st.warning(T["admin_backfill_unavailable"])
else:
    if st.button(T["admin_backfill_button"]):
        completed = get_completed_drafts()
        progress = st.progress(0)
        status = st.empty()
        indexed = 0

        for i, row in enumerate(completed):
            draft_id, case_ref, doc_type, content, created_at, created_by, created_by_role, was_edited, completed_at = row
            status.write(T["admin_backfill_running"].format(current=i + 1, total=len(completed)))
            ok = upsert_document(
                draft_id, case_ref, doc_type,
                content=content,
                language="",
                created_at=created_at,
                completed_at=completed_at,
                created_by_role=created_by_role,
                was_edited=was_edited,
            )
            if ok:
                indexed += 1
            progress.progress((i + 1) / len(completed) if completed else 1.0)

        st.success(T["admin_backfill_done"].format(indexed=indexed, total=len(completed)))

st.divider()

st.header(T["admin_anon_header"])
st.caption(T["admin_anon_caption"])

sample_default = T["admin_sample_default"]

demo_text = st.text_area(T["admin_sample_label"], value=sample_default, height=150)

if st.button(T["admin_run_button"]):
    result = anonymize(demo_text)
    st.markdown(f"**{T['admin_output_label']}**")
    st.code(result, language=None, wrap_lines=True)