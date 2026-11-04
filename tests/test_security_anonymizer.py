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


    # --- October 2026: Spanish / Basque hardening ---------------------------

    def test_spanish_identity_documents_and_bank_accounts(self):
        safe = self.assert_redacted(
            "Su DNI es 12345678Z, NIE X1234567L, IBAN ES91 2100 0418 4502 0005 1332, expediente 2024/0315.",
            "12345678Z", "X1234567L", "ES91 2100 0418 4502 0005 1332", "2024/0315",
        )
        self.assertIn("[ID]", safe)

    def test_spanish_single_first_names_after_relationship_cues(self):
        safe = self.assert_redacted(
            "La usuaria Ane acude con su hijo Jon. Habló con la madre, Lucía, y su hermana Carmen.",
            "Ane", "Jon", "Lucía", "Carmen",
        )
        self.assertIn("su hijo [PERSON]", safe)

    def test_name_redacted_everywhere_including_sentence_start(self):
        safe = self.assert_redacted(
            "Hoy hablé con Pedro. Pedro dice que está cansado.",
            "Pedro",
        )
        self.assertEqual(safe.count("[PERSON]"), 2)

    def test_spanish_and_basque_locations(self):
        safe = self.assert_redacted(
            "Vive en Barakaldo y es natural de Getxo. Mikel bizi da Basaurin.",
            "Barakaldo", "Getxo", "Mikel", "Basaurin",
        )
        self.assertIn("[LOCATION]", safe)

    def test_spanish_addresses_titles_and_dates(self):
        safe = self.assert_redacted(
            "Doña Begoña Uriarte vive en la calle Gran Vía 12 con su madre desde el 21 de marzo de 2025.",
            "Begoña", "Uriarte", "Gran Vía 12", "21 de marzo de 2025",
        )
        self.assertIn("[ADDRESS]", safe)
        self.assertIn("[DATE]", safe)
        self.assertIn("con su madre", safe)

    def test_homelessness_phrase_is_not_treated_as_an_address(self):
        safe = anonymize("Duerme en la calle desde hace meses.")
        self.assertEqual(safe, "Duerme en la calle desde hace meses.")

    def test_public_bodies_and_product_terms_are_kept(self):
        safe = anonymize("Derivada por Servicios Sociales y Osakidetza. The Social Worker met the client on Monday.")
        self.assertIn("Servicios Sociales", safe)
        self.assertIn("Osakidetza", safe)
        self.assertIn("Social Worker", safe)
        self.assertIn("Monday", safe)

    def test_anonymizing_twice_changes_nothing(self):
        once = anonymize("María García vive en Bilbao, calle Gran Vía 12. Tel 612 345 678. Su hijo Jon.")
        self.assertEqual(anonymize(once), once)


class CapitalLettersTests(unittest.TestCase):
    """November 2026: notes typed with caps lock on. In the pilot,
    "HELLO, JOHN IS A HAPPY CLIENT" reached the AI unchanged."""

    CASES = [
        ("HELLO, JOHN IS A HAPPY CLIENT", ["JOHN"], "HELLO, [PERSON] IS A HAPPY CLIENT"),
        ("Visita a NEREA AGIRRE LASA en su casa.", ["NEREA", "AGIRRE", "LASA"], None),
        ("MIKEL DICE QUE NO.", ["MIKEL"], "[PERSON] DICE QUE NO."),
        ("SR. AGIRRE NO ACUDIÓ A LA CITA CON EDE.", ["AGIRRE"], None),
        ("ME REUNÍ CON DOÑA CARMEN GARCÍA Y SU HIJO.", ["CARMEN", "GARCÍA"], None),
        ("VISITA DOMICILIARIA. SE LLAMA KATTALIN LA HIJA. VIVE EN BASAURI.", ["KATTALIN", "BASAURI"], None),
        ("NEREA, ANE, UNAI Y JON VINIERON. DNI 45781236K.", ["NEREA", "ANE", "UNAI", "JON", "45781236K"], None),
        ("NEREA ESAN DU UNAI ETXEAN DAGOELA.", ["NEREA", "UNAI"], None),
    ]

    def test_names_written_in_capitals_are_removed(self):
        for text, names, expected in self.CASES:
            safe = anonymize(text)
            for name in names:
                self.assertNotIn(name, safe, f"{name!r} left in {safe!r}")
            if expected is not None:
                self.assertEqual(safe, expected)
            self.assertEqual(anonymize(safe), safe, "must stay idempotent")

    def test_ordinary_words_keep_their_capitals(self):
        safe = anonymize("VISITA EN LA CALLE ZABALBIDE 52. NEREA Y UNAI ESTABAN.")
        self.assertTrue(safe.startswith("VISITA EN LA [ADDRESS]."), safe)
        self.assertIn(" Y ", safe)

    def test_normal_text_with_acronyms_is_unchanged_by_the_new_pass(self):
        from services import anonymizer
        for text in ("Reunión con EDE y Lanbide el lunes.",
                     "The client attended the EDE workshop.",
                     "Hello, John is a happy client"):
            self.assertEqual(anonymize(text), anonymizer._anonymize_core(text))

    def test_shouted_text_without_names_is_left_as_written(self):
        text = "ATTENTION: NO RISK DETECTED IN THIS VISIT."
        self.assertEqual(anonymize(text), text)

    def test_long_note_in_capitals_is_quick_and_complete(self):
        import time
        note = "VISITA A NEREA AGIRRE EN SU CASA. LA SITUACIÓN ES ESTABLE Y JOHN COLABORA. " * 400
        started = time.monotonic()
        safe = anonymize(note)
        self.assertLess(time.monotonic() - started, 5)
        for name in ("NEREA", "AGIRRE", "JOHN"):
            self.assertNotIn(name, safe)

    def test_restoring_capitals_never_brings_a_name_back(self):
        # Every word put back in its original capitals is a word the rules
        # kept; a name the rules replaced cannot reappear.
        from services import anonymizer
        text = "NEREA Y NEREA. JOHN, JOHN AND JOHN CAME TO SEE NEREA AGIRRE."
        safe = anonymizer.anonymize(text)
        for name in ("NEREA", "JOHN", "AGIRRE"):
            self.assertNotIn(name, safe)


if __name__ == "__main__":
    unittest.main()
