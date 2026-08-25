"""System Administration -- Section 2: Document Indexing (backfill utility).

Extracted unchanged from the original system_administration.py file.
"""
import streamlit as st

from services.qdrant_service import is_available as qdrant_available, upsert_document
from services.draft_storage import (
    get_completed_drafts,
    get_failed_embedding_drafts,
    count_failed_embedding_drafts,
    record_embedding_outcome,
)

def render(T):
    with st.expander(T["admin_doc_indexing_header"]):
        st.caption(T["admin_doc_indexing_caption"])
        st.caption(T["admin_doc_indexing_cost"])
        if not qdrant_available():
            st.warning(T["admin_doc_indexing_unavailable"])
        else:
            if st.button(T["admin_doc_indexing_button"], type="primary"):
                rows = get_completed_drafts()
                indexed = 0
                progress = st.progress(0)
                for i, row in enumerate(rows):
                    draft_id, case_ref, doc_type, content, created_at, created_by, created_by_role, was_edited, completed_at = row
                    ok, reason = upsert_document(draft_id, case_ref, doc_type, content=content, language="", created_at=created_at, completed_at=completed_at, created_by_role=created_by_role, was_edited=was_edited)
                    record_embedding_outcome(draft_id, case_ref, ok, reason)
                    if ok:
                        indexed += 1
                    progress.progress((i + 1) / len(rows) if rows else 1.0)
                st.success(T["admin_doc_indexing_success"].format(indexed=indexed, total=len(rows)))

            # Data-integrity fix: a document that saves fine but fails to
            # index in Qdrant (rate limit, timeout, outage, network error)
            # used to leave zero trace anywhere in the app. Every such
            # failure is now recorded on the document (embedding_status)
            # and logged to the AI Diagnostic Centre below -- this section
            # is the fast path for actually fixing it, without re-running
            # the full backfill above over every completed document.
            st.divider()
            failed_count = count_failed_embedding_drafts()
            if failed_count == 0:
                st.success(T["admin_doc_indexing_none_failed"])
            else:
                st.warning(T["admin_doc_indexing_failed_label"].format(failed=failed_count))
                st.caption(T["admin_doc_indexing_failed_caption"])
                if st.button(T["admin_doc_indexing_retry_button"]):
                    rows = get_failed_embedding_drafts()
                    indexed = 0
                    progress = st.progress(0)
                    for i, row in enumerate(rows):
                        draft_id, case_ref, doc_type, content, created_at, created_by, created_by_role, was_edited, completed_at = row
                        ok, reason = upsert_document(draft_id, case_ref, doc_type, content=content, language="", created_at=created_at, completed_at=completed_at, created_by_role=created_by_role, was_edited=was_edited)
                        record_embedding_outcome(draft_id, case_ref, ok, reason)
                        if ok:
                            indexed += 1
                        progress.progress((i + 1) / len(rows) if rows else 1.0)
                    st.success(T["admin_doc_indexing_retry_success"].format(indexed=indexed, total=len(rows)))
