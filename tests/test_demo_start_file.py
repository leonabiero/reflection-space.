"""
demo_app.py -- the demo app's start file (17 November 2026, see DEMO.md).

Streamlit Community Cloud allows only one app per repository + branch +
main file, so the demo app starts from demo_app.py instead of app.py.
These tests make sure demo_app.py only hands over to app.py (so both apps
always run the same code), adds nothing of its own, and that demo mode
still depends only on the DEMO_MODE secret.
"""

import ast
import os
import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
DEMO_START = ROOT / "demo_app.py"


def _code_without_docstring(path):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    body = tree.body
    if body and isinstance(body[0], ast.Expr) and isinstance(getattr(body[0], "value", None), ast.Constant):
        body = body[1:]
    return body


class DemoStartFileTests(unittest.TestCase):
    def test_sits_next_to_app_py(self):
        # Same folder, so pages/, .streamlit/ and every import are the same.
        self.assertTrue(DEMO_START.exists())
        self.assertEqual(DEMO_START.parent, (ROOT / "app.py").parent)

    def test_only_hands_over_to_app_py(self):
        body = _code_without_docstring(DEMO_START)
        source = DEMO_START.read_text(encoding="utf-8")
        # Two imports and one call -- nothing else.
        self.assertEqual(len(body), 3, ast.dump(ast.Module(body=body, type_ignores=[]))[:300])
        self.assertIn('runpy.run_path(str(Path(__file__).resolve().with_name("app.py")), run_name="__main__")', source)
        for forbidden in ("streamlit", "set_page_config", "DEMO_MODE", "ensure_schema", "switch_page"):
            self.assertNotIn(forbidden, ast.unparse(ast.Module(body=body, type_ignores=[])))

    def test_runs_app_py_as_the_start_file_every_time(self):
        with mock.patch("runpy.run_path") as run_path:
            code = compile(DEMO_START.read_text(encoding="utf-8"), str(DEMO_START), "exec")
            for _ in range(2):   # Streamlit re-runs the start file on every interaction
                exec(code, {"__file__": str(DEMO_START), "__name__": "__main__"})
        self.assertEqual(run_path.call_count, 2)
        args, kwargs = run_path.call_args
        self.assertEqual(Path(args[0]), (ROOT / "app.py").resolve())
        self.assertEqual(kwargs, {"run_name": "__main__"})

    def test_app_py_is_still_the_real_start_file(self):
        app = (ROOT / "app.py").read_text(encoding="utf-8")
        self.assertIn("st.set_page_config(", app)
        self.assertNotIn("demo_app.py", app)
        # Nothing in the app decides "demo or not" from the start file:
        # demo mode depends only on the DEMO_MODE secret.
        for path in list(ROOT.joinpath("services").glob("*.py")) + list(ROOT.joinpath("pages").rglob("*.py")) \
                + list(ROOT.joinpath("navigation").glob("*.py")) + [ROOT / "app.py", ROOT / "config.py"]:
            source = path.read_text(encoding="utf-8")
            for marker in ("demo_app.py", "main_script_path", "sys.argv"):
                self.assertNotIn(marker, source, f"{path}: {marker}")

    def test_same_first_screen_from_both_start_files(self):
        """Both start files, run in Streamlit's own test runner, show the
        same sign-in screen (no database or secrets needed)."""
        from streamlit.testing.v1 import AppTest

        def screen(name):
            cwd = os.getcwd()
            os.chdir(ROOT)
            if str(ROOT) not in sys.path:
                sys.path.insert(0, str(ROOT))
            try:
                with mock.patch("services.db_schema.ensure_schema"), \
                     mock.patch("services.demo_data.label_database"):
                    at = AppTest.from_file(str(ROOT / name), default_timeout=60)
                    at.run()
            finally:
                os.chdir(cwd)
            self.assertEqual(list(at.exception), [], name)
            return ([t.value for t in at.title], [e.value for e in at.error],
                    [s.value for s in at.selectbox])

        self.assertEqual(screen("demo_app.py"), screen("app.py"))


if __name__ == "__main__":
    unittest.main()
