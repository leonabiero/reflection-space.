import time
import streamlit as st
from services.language import init_language
from navigation.router import render_nav
from services.identity import init_identity, render_identity_footer
from services.qdrant_service import get_diagnostics, is_available as qdrant_available, upsert_document
from services.draft_storage import get_completed_drafts
from services.anonymizer import anonymize
from config import EMBEDDING_MODEL
from rdi.retrieval_service import retrieve_historical_context

T = init_language()
init_identity(T)
render_nav(T)
render_identity_footer(T)

if st.session_state.get("user_role") != "System Administrator":
    st.stop()

st.title("System Administration")

with st.expander("User Management", expanded=True):
    st.info("Users are managed through Streamlit Secrets. Dynamic CRUD is intentionally unavailable because credentials and roles are configured in deployment secrets, not application tables.")
    st.write(st.secrets.get("users", {}))

with st.expander("Document Indexing"):
    st.caption("Hybrid RAG backfill utility migrated from zz_admin.")
    if not qdrant_available():
        st.warning("Qdrant is not configured.")
    elif st.button("Run document backfill"):
        rows = get_completed_drafts()
        indexed = 0
        for row in rows:
            draft_id, case_ref, doc_type, content, created_at, created_by, created_by_role, was_edited, completed_at = row
            if upsert_document(draft_id, case_ref, doc_type, content=content, language="", created_at=created_at, completed_at=completed_at, created_by_role=created_by_role, was_edited=was_edited):
                indexed += 1
        st.success(f"Indexed {indexed}/{len(rows)} documents")

with st.expander("RAG Diagnostics"):
    st.json(get_diagnostics())

with st.expander("Retrieval Test"):
    case_ref = st.text_input("Case reference")
    query = st.text_area("Search query")
    if st.button("Run retrieval test"):
        start=time.time()
        docs=retrieve_historical_context(case_ref, query_text=query)
        elapsed=time.time()-start
        st.write({"search_time_seconds": round(elapsed,3), "embedding_model": EMBEDDING_MODEL, "documents_searched": case_ref, "documents_returned": len(docs)})
        for d in docs:
            st.json({"similarity_score": d.get("score"), "case_reference": case_ref, "document_type": d.get("doc_type"), "retrieval_reason": d.get("match_reason") or d.get("match_reasons")})

with st.expander("System Health"):
    st.write("Application health checks are available through database and Qdrant diagnostics.")
    st.json(get_diagnostics())

with st.expander("Configuration"):
    st.write({"embedding_model": EMBEDDING_MODEL})

with st.expander("Utilities"):
    st.subheader("Anonymization Test")
    sample=st.text_area("Sample text")
    if st.button("Run anonymization"):
        st.code(anonymize(sample))
