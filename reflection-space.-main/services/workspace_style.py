"""Workspace-mode accent styling.

Each work mode (Practitioner / Manager / System Administration) gets its
own accent color in the sidebar, matching the Lovable design export's
three workspace tokens: clay (Practitioner), sage (Manager), graphite
(System Administration). This is purely visual -- it has no effect on
navigation, permissions, or which links are shown to which role (see
navigation/permissions.py and navigation/menus.py for that logic, which
is unchanged).

Colors were converted from the Lovable design's OKLCH tokens
(src/styles.css in the Lovable export) to hex, then the "soft" (12%
opacity) pill backgrounds were composited onto the sidebar's own
background color (see .streamlit/config.toml [theme.sidebar]) to get a
solid fill, since Streamlit's unsafe_allow_html renders plain CSS, not
Tailwind's opacity utilities.
"""

import streamlit as st

WORKSPACE_ACCENTS = {
    "Practitioner": {
        "color": "#d58966",     # clay
        "soft_bg": "#312b36",   # clay-soft, composited onto sidebar surface (#1a1e2f)
    },
    "Manager": {
        "color": "#85b09c",     # sage
        "soft_bg": "#27303c",   # sage-soft, composited onto sidebar surface
    },
    "System Administration": {
        "color": "#aaadbb",     # graphite
        "soft_bg": "#2c2f40",   # graphite-soft, composited onto sidebar surface
    },
}


def render_workspace_badge(label: str, workspace: str) -> None:
    """Render the sidebar's workspace-mode heading as a small colored
    pill in that mode's accent color, in place of a plain
    st.sidebar.subheader.

    label:      the already-translated display text, e.g.
                T.get("workmode_practitioner", "Practitioner")
    workspace:  one of "Practitioner", "Manager", "System Administration"
                -- used ONLY to look up the accent color. Never used to
                gate access; that guard lives elsewhere and is untouched.
    """
    accent = WORKSPACE_ACCENTS.get(workspace, WORKSPACE_ACCENTS["Practitioner"])
    st.sidebar.markdown(
        f'''
        <div style="
            display:inline-block;
            padding:4px 12px;
            margin:4px 0 10px 0;
            border-radius:999px;
            background:{accent["soft_bg"]};
            color:{accent["color"]};
            font-family:'JetBrains Mono', ui-monospace, monospace;
            font-size:0.68rem;
            letter-spacing:0.08em;
            text-transform:uppercase;
            font-weight:500;
        ">{label}</div>
        ''',
        unsafe_allow_html=True,
    )