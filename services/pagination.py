"""
Pagination Helper for Admin Pages
===================================

Simple, reusable pagination for rendering large lists in Streamlit.
Keeps state in st.session_state to persist across re-runs.

Usage:

    paginator = Paginator("my_list", items=list_of_100_items, items_per_page=20)
    
    st.write(f"Showing {paginator.start_idx + 1}-{paginator.end_idx} of {paginator.total}")
    
    for item in paginator.current_page():
        st.write(item)
    
    paginator.render_controls()  # Shows "Previous / Page X of Y / Next" buttons
"""

import streamlit as st
import math


class Paginator:
    """
    Simple paginator for Streamlit, backed by st.session_state.
    
    Keeps the current page number in session state so pagination persists
    across Streamlit re-runs (e.g. when you click a button or type in a filter).
    """
    
    def __init__(self, key, items, items_per_page=20):
        """
        Initialize paginator.
        
        Args:
            key: Unique identifier (e.g., "error_log", "feedback_list")
                 Used to store page number in st.session_state as f"{key}_page"
            items: List of items to paginate
            items_per_page: How many items per page (default: 20)
        """
        self.key = key
        self.items = items or []
        self.items_per_page = max(1, items_per_page)
        self.total = len(self.items)
        self.total_pages = max(1, math.ceil(self.total / self.items_per_page))
        
        # Initialize page number in session state (defaults to 1)
        page_key = f"{key}_page"
        if page_key not in st.session_state:
            st.session_state[page_key] = 1
    
    @property
    def current_page_num(self):
        """Get current page number (1-indexed)."""
        page_key = f"{self.key}_page"
        page = st.session_state.get(page_key, 1)
        # Clamp to valid range
        return max(1, min(page, self.total_pages))
    
    def set_page(self, page_num):
        """Set current page (1-indexed)."""
        page_key = f"{self.key}_page"
        st.session_state[page_key] = max(1, min(page_num, self.total_pages))
    
    def reset_page(self):
        """Reset to page 1 (useful when filters change)."""
        self.set_page(1)
    
    @property
    def start_idx(self):
        """0-indexed start position in items list."""
        return (self.current_page_num - 1) * self.items_per_page
    
    @property
    def end_idx(self):
        """0-indexed end position in items list (exclusive)."""
        return min(self.start_idx + self.items_per_page, self.total)
    
    def current_page(self):
        """Return list of items for the current page."""
        return self.items[self.start_idx:self.end_idx]
    
    def render_info(self):
        """Render a caption showing current range."""
        if self.total == 0:
            st.caption("No items to display.")
            return
        
        start_display = self.start_idx + 1
        end_display = self.end_idx
        st.caption(f"Showing {start_display}–{end_display} of {self.total} item(s) "
                   f"(page {self.current_page_num} of {self.total_pages})")
    
    def render_controls(self, columns=3):
        """
        Render pagination controls (Previous / Page selector / Next).
        
        Args:
            columns: Number of columns to use for layout (default: 3)
        """
        if self.total_pages <= 1:
            return  # No pagination needed
        
        cols = st.columns(columns)
        
        with cols[0]:
            if st.button("← Previous", key=f"{self.key}_prev"):
                self.set_page(self.current_page_num - 1)
                st.rerun()
        
        with cols[1]:
            # Page selector dropdown
            page_options = list(range(1, self.total_pages + 1))
            selected_page = st.selectbox(
                "Page",
                options=page_options,
                index=self.current_page_num - 1,
                key=f"{self.key}_selector",
                label_visibility="collapsed",
            )
            if selected_page != self.current_page_num:
                self.set_page(selected_page)
                st.rerun()
        
        with cols[2]:
            if st.button("Next →", key=f"{self.key}_next"):
                self.set_page(self.current_page_num + 1)
                st.rerun()
    
    def render_controls_compact(self):
        """
        Render compact pagination controls in a single line.
        Just shows current page info and Previous/Next buttons.
        """
        if self.total_pages <= 1:
            return  # No pagination needed
        
        col1, col2, col3 = st.columns([1, 2, 1])
        
        with col1:
            if st.button("← Prev", key=f"{self.key}_prev_compact"):
                self.set_page(self.current_page_num - 1)
                st.rerun()
        
        with col2:
            st.caption(f"Page {self.current_page_num} of {self.total_pages}")
        
        with col3:
            if st.button("Next →", key=f"{self.key}_next_compact"):
                self.set_page(self.current_page_num + 1)
                st.rerun()