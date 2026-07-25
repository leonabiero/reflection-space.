import time
import psycopg2
import pandas as pd
import streamlit as st

from services.language import init_language
from navigation.router import render_nav
from services.identity import init_identity, render_identity_footer
from services.qdrant_service import get_diagnostics, is_available as qdrant_available, upsert_document
from services.embedding_service import is_available as embeddings_available
from services.draft_storage import get_completed_drafts
from services.anonymizer import anonymize
from config import EMBEDDING_MODEL, EMBEDDING_DIMENSIONS, DATABASE_URL, ANTHROPIC_API_KEY, QDRANT_COLLECTION_NAME
from rdi.retrieval_service import retrieve_historical_context, retrieve_global_context
from rdi.context_engine import DEFAULT_HISTORY_LIMIT

# =============================================================================
# System Administration -- Admin Console
# =============================================================================
#
# This page is presentation-only. Every value shown here comes from
# services that already existed (services.qdrant_service,
# services.embedding_service, services.draft_storage,
# rdi.retrieval_service, config) -- nothing here makes a NEW call to
# Voyage AI or the Anthropic (Claude) API. The Retrieval Test panel
# calls rdi.retrieval_service.retrieve_historical_context() (case-
# specific mode) or rdi.retrieval_service.retrieve_global_context()
# (global mode, added alongside the optional Case Reference field) --
# both only ever call Voyage AI (embeddings) for the query text and
# Qdrant for the search; neither calls the Claude/Anthropic API at all.
# So this redesign, and the global-mode addition, have ZERO impact on
# Anthropic API cost -- see the docstring on the Retrieval Test section
# below for the one-line cost note kept alongside that button for
# transparency.
#
# Everything below only changes HOW existing data is displayed
# (tables/cards/badges instead of raw st.json(...)) -- it does not
# change what is retrieved, indexed, or computed, except for the
# Retrieval Test's new global mode, which is scoped narrowly and
# explained in that section's own comments below.


T = init_language()
init_identity(T)
render_nav(T)
render_identity_footer(T)

if st.session_state.get("user_role") != "System Administrator":
    st.stop()

st.title("🛠️ System Administration")
st.caption("Administration console for Reflection Space -- system status, indexing, and diagnostic tools.")

# --- shared badge/label helpers --------------------------------------------

MATCH_REASON_LABELS = {
    "must_include": "📌 Must Include",
    "semantic": "🔎 Semantic Match",
    "recency": "🕒 Recent",
}


def _status_badge(ok, true_label="Healthy", false_label="Unavailable"):
    return f"✅ {true_label}" if ok else f"❌ {false_label}"


def _bool_badge(ok):
    return "✅ Present" if ok else "❌ Missing"


def _check_database():
    """Cheap, best-effort connection check -- opens and immediately
    closes a connection. Does not run any query beyond the driver's
    own handshake."""
    if not DATABASE_URL:
        return False, "DATABASE_URL is not configured."
    try:
        conn = psycopg2.connect(DATABASE_URL)
        conn.close()
        return True, None
    except Exception as e:
        return False, str(e)


# =============================================================================
# 1. User Management (unchanged)
# =============================================================================
with st.expander("👥 User Management", expanded=True):
    st.info("Users are managed through Streamlit Secrets. Dynamic CRUD is intentionally unavailable because credentials and roles are configured in deployment secrets, not application tables.")
    users = dict(st.secrets.get("users", {}))
    if users:
        rows = []
        for username, info in users.items():
            rows.append({
                "Username": username,
                "Name": info.get("name", ""),
                "Role": info.get("role", ""),
            })
        st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)
    else:
        st.warning("No users are configured yet. Add them under Settings → Secrets in Streamlit Cloud.")

# =============================================================================
# 2. Document Indexing (unchanged -- backfill utility)
# =============================================================================
with st.expander("📇 Document Indexing"):
    st.caption("Hybrid RAG backfill utility -- generates Qdrant embeddings for documents completed before semantic retrieval was enabled.")
    st.caption("💰 Cost note: this calls Voyage AI (embeddings) once per completed document, never Claude. At pilot volume this is $0.00/month either way -- see config.py for the full cost breakdown.")
    if not qdrant_available():
        st.warning("Qdrant is not configured, so semantic indexing is unavailable.")
    elif st.button("Run document backfill", type="primary"):
        rows = get_completed_drafts()
        indexed = 0
        progress = st.progress(0)
        for i, row in enumerate(rows):
            draft_id, case_ref, doc_type, content, created_at, created_by, created_by_role, was_edited, completed_at = row
            if upsert_document(draft_id, case_ref, doc_type, content=content, language="", created_at=created_at, completed_at=completed_at, created_by_role=created_by_role, was_edited=was_edited):
                indexed += 1
            progress.progress((i + 1) / len(rows) if rows else 1.0)
        st.success(f"✅ Indexed {indexed} of {len(rows)} documents.")

# =============================================================================
# 3. Retrieval Test
# =============================================================================
with st.expander("🔍 Retrieval Test"):
    st.caption("Runs a real semantic search against Qdrant to verify retrieval is working end to end -- either scoped to one case, or across the entire knowledge base.")
    st.caption("💰 Cost note: this embeds your query text via Voyage AI only -- it never calls the Claude/Anthropic API, so running this test (in either mode) has no effect on Anthropic API cost.")

    # Case Reference is optional -- see the two modes below.
    #
    # - Case Reference filled in  -> CASE-SPECIFIC mode: calls
    #   rdi.retrieval_service.retrieve_historical_context(), exactly as
    #   before. Confidentiality-scoped: only ever returns documents from
    #   that one case (see services/qdrant_service.py's search_similar()).
    #
    # - Case Reference left blank -> GLOBAL mode: calls
    #   rdi.retrieval_service.retrieve_global_context(), which applies NO
    #   case filter and searches the entire Qdrant collection. This is a
    #   deliberate, admin-only exception to the app's per-case
    #   confidentiality boundary (see services/qdrant_service.py's
    #   search_global() docstring) -- results can include documents from
    #   any client's case, shown side by side, so an administrator can
    #   validate the RAG system as a whole rather than only one case at a
    #   time. This mode is only reachable from this page, gated to
    #   System Administrator above.
    case_ref = st.text_input("Case reference (optional -- leave blank to search the entire knowledge base)", key="admin_retrieval_case_ref")
    query = st.text_area("Search query", key="admin_retrieval_query")

    is_global_mode = not (case_ref or "").strip()

    if st.button("Run retrieval test", type="primary"):
        success = True
        error_message = None
        docs = []
        elapsed = 0.0

        start = time.time()
        try:
            if is_global_mode:
                docs = retrieve_global_context(query_text=query)
            else:
                docs = retrieve_historical_context(case_ref, query_text=query)
        except Exception as e:
            success = False
            error_message = str(e)
        elapsed = time.time() - start

        st.session_state["admin_last_retrieval_result"] = {
            "success": success,
            "error": error_message,
            "elapsed": elapsed,
            "case_ref": case_ref,
            "query": query,
            "docs": docs,
            "is_global_mode": is_global_mode,
        }

    result = st.session_state.get("admin_last_retrieval_result")
    if result:
        was_global = result.get("is_global_mode", not (result.get("case_ref") or "").strip())
        mode_label = "🌍 Global Knowledge Base Search" if was_global else f"📁 Case-specific ({result['case_ref']})"

        st.markdown("#### Retrieval Summary")
        summary_rows = [
            {"Item": "Status", "Value": "✅ Successful" if result["success"] else "❌ Failed"},
            {"Item": "Retrieval Mode", "Value": mode_label},
            {"Item": "Search time", "Value": f"{result['elapsed']:.2f} seconds"},
            {"Item": "Query", "Value": result["query"] or "—"},
            {"Item": "Documents returned", "Value": str(len(result["docs"]))},
            {"Item": "Embedding model", "Value": EMBEDDING_MODEL},
        ]
        st.table(pd.DataFrame(summary_rows).set_index("Item"))

        if was_global:
            st.caption("🌍 Global mode: this search applied no case filter and may return documents from more than one case.")

        if not result["success"]:
            st.error(f"Retrieval failed: {result['error']}")
        elif result["docs"]:
            st.markdown("#### Retrieved Documents")
            doc_rows = []
            for rank, d in enumerate(result["docs"], start=1):
                reasons = d.get("match_reasons") or ([d.get("match_reason")] if d.get("match_reason") else [])
                reason_label = " + ".join(MATCH_REASON_LABELS.get(r, r) for r in reasons) if reasons else "—"
                score = d.get("score")
                row_dict = {
                    "Rank": rank,
                    "Document Type": d.get("doc_type", ""),
                    "Retrieval Reason": reason_label,
                    "Similarity": f"{score:.2f}" if score is not None else "—",
                }
                # Global mode can span cases, so show which case each
                # result belongs to. Case-specific mode already implies
                # the case (shown in Retrieval Mode above), so this
                # column is omitted there to avoid a redundant, always-
                # identical column.
                if was_global:
                    row_dict["Case Reference"] = d.get("case_ref") or "—"
                doc_rows.append(row_dict)
            st.dataframe(pd.DataFrame(doc_rows), hide_index=True, use_container_width=True)
        else:
            st.info("No documents were returned for this query.")

        with st.expander("🔧 Advanced Diagnostics"):
            if st.checkbox("Show raw response", key="admin_retrieval_raw_toggle"):
                st.json({
                    "success": result["success"],
                    "error": result["error"],
                    "retrieval_mode": "global" if was_global else "case_specific",
                    "search_time_seconds": round(result["elapsed"], 3),
                    "case_reference": result["case_ref"],
                    "query": result["query"],
                    "documents": result["docs"],
                })

# =============================================================================
# 4. RAG Status (renamed from "RAG Diagnostics")
# =============================================================================
with st.expander("📡 RAG Status"):
    diagnostics = get_diagnostics()

    if diagnostics.get("error"):
        st.error(f"⚠️ {diagnostics['error']}")
    else:
        st.success("✅ Semantic retrieval layer is reachable.")

    status_rows = [
        {"Item": "Qdrant connection", "Status": _status_badge(diagnostics.get("connected"), "Connected", "Not connected")},
        {"Item": "Collection", "Status": diagnostics.get("collection_name") or "—"},
        {"Item": "Embedding model", "Status": diagnostics.get("embedding_model") or "—"},
        {"Item": "Embedding dimensions", "Status": str(diagnostics.get("embedding_dimensions") or "—")},
        {"Item": "Indexed documents", "Status": str(diagnostics.get("points_count")) if diagnostics.get("points_count") is not None else "—"},
        {"Item": "Case reference index", "Status": _bool_badge(diagnostics.get("case_ref_index_present"))},
        {"Item": "Document ID index", "Status": _bool_badge(diagnostics.get("document_id_index_present"))},
        {"Item": "Latest document ID", "Status": str(diagnostics.get("latest_document_id")) if diagnostics.get("latest_document_id") is not None else "—"},
        {"Item": "Latest case", "Status": diagnostics.get("latest_case_ref") or "—"},
        {"Item": "Latest document type", "Status": diagnostics.get("latest_doc_type") or "—"},
        {"Item": "Last indexed", "Status": (diagnostics.get("latest_completed_at") or "—")[:19]},
    ]
    st.table(pd.DataFrame(status_rows).set_index("Item"))

    with st.expander("🔧 Advanced Diagnostics"):
        if st.checkbox("Show raw response", key="admin_rag_status_raw_toggle"):
            st.json(diagnostics)

# =============================================================================
# 5. System Health
# =============================================================================
with st.expander("💚 System Health"):
    db_ok, db_error = _check_database()
    q_diag = get_diagnostics()
    qdrant_ok = bool(q_diag.get("connected"))
    embed_ok = embeddings_available()
    reflection_ok = bool(ANTHROPIC_API_KEY)
    retrieval_ok = qdrant_ok and embed_ok  # falls back gracefully if not

    if not db_ok or not reflection_ok:
        overall = "🔴 Critical"
    elif not retrieval_ok:
        overall = "🟡 Degraded (semantic retrieval not configured -- app is using date-based fallback)"
    else:
        overall = "🟢 Healthy"

    st.markdown("#### Overall Status")
    st.markdown(f"### {overall}")

    st.markdown("#### Components")
    component_rows = [
        {"Component": "Database", "Status": _status_badge(db_ok, "Healthy", "Unreachable")},
        {"Component": "Qdrant", "Status": _status_badge(qdrant_ok, "Connected", "Not connected")},
        {"Component": "Embedding service (Voyage AI)", "Status": _status_badge(embed_ok, "Available", "Not configured")},
        {"Component": "Retrieval service", "Status": "✅ Operational" if retrieval_ok else "🟡 Fallback mode (recency-based)"},
        {"Component": "Reflection engine (Claude API)", "Status": _status_badge(reflection_ok, "Operational", "Not configured")},
    ]
    st.table(pd.DataFrame(component_rows).set_index("Component"))

    if not db_ok and db_error:
        st.error(f"Database error: {db_error}")
    if not reflection_ok:
        st.error("ANTHROPIC_API_KEY is not configured -- reflections cannot be generated.")

    with st.expander("🔧 Advanced Diagnostics"):
        if st.checkbox("Show raw response", key="admin_health_raw_toggle"):
            st.json({
                "database_ok": db_ok,
                "database_error": db_error,
                "qdrant_diagnostics": q_diag,
                "embeddings_available": embed_ok,
                "reflection_engine_configured": reflection_ok,
            })

# =============================================================================
# 6. Configuration
# =============================================================================
with st.expander("⚙️ Configuration"):
    st.markdown(f"""
- **Embedding model:** {EMBEDDING_MODEL}
- **Embedding dimensions:** {EMBEDDING_DIMENSIONS}
- **Retrieval limit:** {DEFAULT_HISTORY_LIMIT} documents
- **Vector database:** Qdrant
- **Collection:** {QDRANT_COLLECTION_NAME}
""")

# =============================================================================
# 7. Administrative Tools (renamed from "Utilities")
# =============================================================================
with st.expander("🧰 Administrative Tools"):
    st.subheader("Anonymization Test")
    st.caption("Runs the same anonymize() function used before any text is sent to Claude or Voyage AI -- lets you verify what a document looks like once anonymized.")
    sample = st.text_area("Sample text", key="admin_anon_sample")
    if st.button("Run anonymization"):
        st.code(anonymize(sample))

    st.divider()
    st.caption("Future administrator tools will appear here.")