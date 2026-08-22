from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class DeletionLifecycleSecurityTests(unittest.TestCase):
    def test_qdrant_deleted_window_is_not_joined_back_to_postgres_content(self):
        source = (ROOT / "services" / "draft_storage.py").read_text(encoding="utf-8")
        start = source.index("def get_drafts_by_ids")
        end = source.index("def get_failed_embedding_drafts", start)
        section = source[start:end]
        self.assertIn("status='completed'", section)
        self.assertIn("id = ANY(%s)", section)

    def test_permanent_purge_removes_postgres_history_and_qdrant_vector(self):
        source = (ROOT / "services" / "draft_storage.py").read_text(encoding="utf-8")
        start = source.index("def purge_expired_deletions")
        section = source[start:]
        self.assertIn("DELETE FROM draft_history", section)
        self.assertIn("DELETE FROM drafts", section)
        self.assertIn("delete_document(draft_id)", section)

    def test_qdrant_soft_delete_policy_is_documented(self):
        source = (ROOT / "services" / "qdrant_service.py").read_text(encoding="utf-8")
        self.assertIn("during the 48-hour restore window", source)
        self.assertIn("status='deleted'", (ROOT / "services" / "draft_storage.py").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
