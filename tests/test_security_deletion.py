from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class DeletionLifecycleSecurityTests(unittest.TestCase):
    def test_permanent_purge_removes_postgres_history_and_documents(self):
        source = (ROOT / "services" / "draft_storage.py").read_text(encoding="utf-8")
        start = source.index("def purge_expired_deletions")
        section = source[start:]
        self.assertIn("DELETE FROM draft_history", section)
        self.assertIn("DELETE FROM drafts", section)
        self.assertIn("delete_runs_for_drafts", section)

    def test_soft_delete_hides_documents_first(self):
        self.assertIn("status='deleted'", (ROOT / "services" / "draft_storage.py").read_text(encoding="utf-8"))


class QdrantRemovedTests(unittest.TestCase):
    """November 2026: the Qdrant search service was removed. Guard
    against it creeping back in through code or the requirements."""

    def test_no_code_imports_qdrant(self):
        offenders = []
        for folder in ("services", "rdi", "pages", "navigation", "components"):
            for path in (ROOT / folder).rglob("*.py"):
                text = path.read_text(encoding="utf-8")
                if "qdrant_service" in text or "qdrant_client" in text:
                    offenders.append(str(path.relative_to(ROOT)))
        self.assertEqual(offenders, [])

    def test_qdrant_library_not_required(self):
        requirements = (ROOT / "requirements.txt").read_text(encoding="utf-8").lower()
        self.assertNotIn("qdrant", requirements)


if __name__ == "__main__":
    unittest.main()
