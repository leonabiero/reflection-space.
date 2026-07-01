import streamlit as st
from services.language import init_language

T = init_language()

st.title(T["nav_learning"])
st.write(T["learning_phase2"])
st.caption("Preview — illustrative data, not yet live")

mock_counts = {
    T["themes"][0]: 7,
    T["themes"][1]: 9,
    T["themes"][2]: 4,
    T["themes"][3]: 6,
    T["themes"][4]: 5,
}

for theme, count in mock_counts.items():
    st.write(f"**{theme}**")
    st.progress(count / 10)
    st.caption(f"Flagged in {count} of the last 10 reflections")