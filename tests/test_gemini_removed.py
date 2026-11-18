"""
Google Gemini removed (18 November 2026, product owner's decision).

No text had been sent to Gemini since 15 November 2026 (Pattern Review
uses Claude). Its module, settings, package, price list, alerts and screen
rows were removed. These checks make sure it does not come back by
accident and that the screens no longer show it.
"""

import ast
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _app_python_files():
    for path in ROOT.rglob("*.py"):
        if "tests" in path.parts or ".git" in path.parts or "venv" in str(path).lower():
            continue
        yield path


class GeminiRemovedTests(unittest.TestCase):
    def test_module_and_package_are_gone(self):
        self.assertFalse((ROOT / "services" / "embedding_service.py").exists())
        requirements = (ROOT / "requirements.txt").read_text(encoding="utf-8").lower()
        self.assertNotIn("google-genai", requirements)
        self.assertNotIn("google-generativeai", requirements)

    def test_nothing_imports_google_or_the_old_module(self):
        for path in _app_python_files():
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    names = [a.name for a in node.names]
                elif isinstance(node, ast.ImportFrom):
                    names = [node.module or ""] + [a.name for a in node.names]
                else:
                    continue
                for name in names:
                    self.assertFalse(name.startswith("google"), f"{path}: {name}")
                    self.assertNotIn("embedding_service", name, str(path))

    def test_settings_are_gone(self):
        import config
        for name in ("GEMINI_API_KEY", "EMBEDDING_MODEL", "EMBEDDING_DIMENSIONS",
                     "MONTHLY_BUDGET_GEMINI_USD"):
            self.assertFalse(hasattr(config, name), name)

    def test_cost_monitor_no_longer_lists_gemini(self):
        from services import cost_pricing, usage_ledger
        self.assertFalse(hasattr(cost_pricing, "GEMINI_PRICING"))
        self.assertFalse(hasattr(cost_pricing, "estimate_gemini_embedding_cost"))
        self.assertNotIn("gemini", usage_ledger.SERVICES)
        self.assertNotIn("Google", " ".join(r["provider"] for r in cost_pricing.pricing_snapshot()))
        dashboard = (ROOT / "services" / "cost_dashboard_service.py").read_text(encoding="utf-8")
        self.assertNotIn("def get_gemini_overview", dashboard)
        self.assertNotIn('"gemini"', dashboard)
        self.assertNotIn('overviews["gemini"]', (ROOT / "services" / "usage_alerts.py").read_text(encoding="utf-8"))

    def test_screens_have_no_gemini_row(self):
        for name in ("system_health.py", "service_usage.py"):
            source = (ROOT / "pages" / "admin_sections" / name).read_text(encoding="utf-8")
            code = "\n".join(line for line in source.splitlines() if not line.lstrip().startswith("#"))
            code = code.split('"""', 2)[-1]   # skip the module docstring
            self.assertNotIn("gemini", code.lower(), name)
            self.assertNotIn("embedding", code.lower(), name)

    def test_old_gemini_texts_are_gone_in_all_languages(self):
        from services.locales.es import LANG_ES
        from services.locales.eu import LANG_EU
        from services.locales.en import LANG_EN
        for lang in (LANG_ES, LANG_EU, LANG_EN):
            for key in ("admin_health_component_embedding", "admin_backfill_unavailable",
                        "admin_health_degraded", "admin_health_available_label"):
                self.assertNotIn(key, lang)


if __name__ == "__main__":
    unittest.main()
