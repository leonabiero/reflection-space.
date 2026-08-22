import unittest

from services.anonymizer import anonymize


class AnonymizerSecurityTests(unittest.TestCase):
    def assert_redacted(self, text, *original_values):
        safe = anonymize(text)
        for value in original_values:
            self.assertNotIn(value, safe, msg=f"PII survived anonymization: {value!r}\n{safe}")
        return safe

    def test_african_compound_and_three_part_names(self):
        safe = self.assert_redacted(
            "Client Amina Wanjiku Njeri met the worker today.",
            "Amina Wanjiku Njeri",
        )
        self.assertIn("[PERSON]", safe)

    def test_spanish_basque_accented_and_hyphenated_names(self):
        safe = self.assert_redacted(
            "María José García spoke with Jon Ander Etxeberria and Jean-Luc Martin.",
            "María José García",
            "Jon Ander Etxeberria",
            "Jean-Luc Martin",
        )
        self.assertGreaterEqual(safe.count("[PERSON]"), 3)

    def test_apostrophe_names(self):
        safe = self.assert_redacted(
            "O'Connor and N'Guessan attended the meeting.",
            "O'Connor",
            "N'Guessan",
        )
        self.assertGreaterEqual(safe.count("[PERSON]"), 2)

    def test_email_phone_dates_and_numeric_ids(self):
        safe = self.assert_redacted(
            "Email john.smith@example.org; phone +254 712 345 678; DOB 14/03/2012; case ref CASE-2026-00421; ID 123456789.",
            "john.smith@example.org",
            "+254 712 345 678",
            "14/03/2012",
            "CASE-2026-00421",
            "123456789",
        )
        self.assertIn("[EMAIL]", safe)
        self.assertIn("[PHONE]", safe)
        self.assertIn("[DATE]", safe)
        self.assertIn("[ID]", safe)

    def test_spelled_out_date(self):
        safe = self.assert_redacted("The incident occurred on 21 March 2025.", "21 March 2025")
        self.assertIn("[DATE]", safe)

    def test_school_hospital_organisation_and_address_context(self):
        safe = self.assert_redacted(
            "The child attends Olympic Primary School. The referral came from City Eye Hospital. Their address is 14 River Road. The organisation is Acme Foundation.",
            "Olympic Primary School",
            "City Eye Hospital",
            "14 River Road",
            "Acme Foundation",
        )
        self.assertIn("[ORGANISATION]", safe)
        self.assertIn("[ADDRESS]", safe)

    def test_location_context(self):
        safe = self.assert_redacted(
            "The family lives in Nairobi West, and the referral was from Bilbao.",
            "Nairobi West",
            "Bilbao",
        )
        self.assertIn("[LOCATION]", safe)

    def test_multiple_people_in_natural_sentence(self):
        safe = self.assert_redacted(
            "Jane Doe spoke with Peter Mwangi while Grace Njeri waited outside.",
            "Jane Doe",
            "Peter Mwangi",
            "Grace Njeri",
        )
        self.assertEqual(safe.count("[PERSON]"), 3)

    def test_indirect_identifier_is_not_claimed_to_be_safe_but_explicit_details_are_removed(self):
        text = "A 12-year-old girl in a small village was the only pupil in her class. Her mother Maria Lopez can be contacted on 0712 345 678."
        safe = anonymize(text)
        self.assertNotIn("Maria Lopez", safe)
        self.assertNotIn("0712 345 678", safe)
        # The unique combination itself cannot be reliably detected by a
        # deterministic anonymizer; this test documents that limitation
        # instead of pretending the system provides k-anonymity.
        self.assertIn("12-year-old", safe)


if __name__ == "__main__":
    unittest.main()
