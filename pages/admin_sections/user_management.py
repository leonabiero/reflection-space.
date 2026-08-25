"""System Administration -- Section 1: User Management.

Shows the list of configured users (from st.secrets) and their roles.
Extracted unchanged from the original system_administration.py file.
"""
import pandas as pd
import streamlit as st


def render(T):
    with st.expander(T["admin_user_mgmt_header"], expanded=False):
        st.info(T["admin_user_mgmt_info"])
        users = dict(st.secrets.get("users", {}))
        if users:
            rows = []
            for username, info in users.items():
                rows.append({
                    T["admin_user_col_username"]: username,
                    T["admin_user_col_name"]: info.get("name", ""),
                    T["admin_user_col_role"]: T.get("role_labels", {}).get(info.get("role", ""), info.get("role", "")),
                })
            users_table = pd.DataFrame(rows)
            users_table.index = range(1, len(users_table) + 1)
            st.table(users_table)
        else:
            st.warning(T["admin_user_mgmt_empty"])
