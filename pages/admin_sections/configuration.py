"""System Administration -- Section 6: Configuration.

Extracted unchanged from the original system_administration.py file.
"""
import streamlit as st

from config import EMBEDDING_MODEL, EMBEDDING_DIMENSIONS, QDRANT_COLLECTION_NAME
from rdi.context_engine import DEFAULT_HISTORY_LIMIT


def render(T):
    with st.expander(T["admin_config_header"]):
        st.markdown(f"""
- **{T['admin_rag_embedding_model']}:** {EMBEDDING_MODEL}
- **{T['admin_rag_embedding_dims']}:** {EMBEDDING_DIMENSIONS}
- **{T.get('historical_docs_used_label', 'Retrieval limit')}:** {DEFAULT_HISTORY_LIMIT}
- **{T['admin_rag_collection']}:** {QDRANT_COLLECTION_NAME}
    """)
