import logging
import unittest

from services.db_time import _PrivacyFormatter
from services.rag_logging import _sanitize_message


class SecurityLoggingTests(unittest.TestCase):
    def test_general_logger_formatter_redacts_direct_identifiers(self):
        record = logging.LogRecord(
            name="test",
            level=logging.ERROR,
            pathname="test.py",
            lineno=1,
            msg="client Amina Wanjiku emailed john.smith@example.org on 14/03/2012, phone +254 712 345 678, case ref CASE-2026-00421",
            args=(),
            exc_info=None,
        )
        safe = _PrivacyFormatter("%(message)s").format(record)
        for secret in (
            "Amina Wanjiku",
            "john.smith@example.org",
            "14/03/2012",
            "+254 712 345 678",
            "CASE-2026-00421",
        ):
            self.assertNotIn(secret, safe)

    def test_rag_logger_redacts_case_reference(self):
        safe = _sanitize_message("search_similar: case_ref='CASE-2026-00421' retrieved=3")
        self.assertNotIn("CASE-2026-00421", safe)
        self.assertIn("case_ref=[REDACTED]", safe)


if __name__ == "__main__":
    unittest.main()
