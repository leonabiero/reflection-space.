"""
Start file for the DEMO app (17 November 2026 -- see DEMO.md).

Streamlit Community Cloud allows only one app per repository + branch +
main file, and the real app already uses app.py. The demo app therefore
starts from this file instead -- and this file only hands over to app.py,
so both apps always run exactly the same code.

Do NOT add anything else here (no page configuration, no logic): every
change to the app belongs in app.py and the folders it uses. Whether an
app is the demo app is decided ONLY by the DEMO_MODE secret, never by
which start file was used.

Streamlit runs the start file again on every interaction, so app.py is
run afresh each time, exactly as when it is the start file itself. It
sits in the same folder, so the pages/ folder, the .streamlit settings
and every import work the same way.
"""

import runpy
from pathlib import Path

runpy.run_path(str(Path(__file__).resolve().with_name("app.py")), run_name="__main__")
