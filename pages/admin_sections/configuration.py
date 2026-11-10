"""System Administration -- Section 6: Configuration.

November 2026: the Qdrant collection name and the old historical-document
retrieval limit were removed together with the Qdrant search service.
"""
import streamlit as st

from config import EMBEDDING_MODEL, EMBEDDING_DIMENSIONS


def render(T):
    with st.expander(T["admin_config_header"]):
        st.markdown(f"""
- **{T['admin_rag_embedding_model']}:** {EMBEDDING_MODEL}
- **{T['admin_rag_embedding_dims']}:** {EMBEDDING_DIMENSIONS}
    """)
