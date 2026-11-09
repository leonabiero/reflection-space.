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
        # November 2026: the exact age is now generalised to a life stage
        # (the minor / adult distinction is kept).
        self.assertNotIn("12-year-old", safe)
        self.assertIn("[AGE_CHILD]", safe)
        # The unique combination itself ("small village", "only pupil")
        # cannot be reliably detected by a deterministic anonymizer; this
        # test documents that limitation instead of pretending the system
        # provides k-anonymity.
        self.assertIn("small village", safe)


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


class AnonymizerAgeProtectionTests(unittest.TestCase):
    """November 2026: exact ages never reach an AI provider. Each one is
    replaced by a life-stage tag (see config.AGE_BAND_LIMITS)."""

    def safe(self, text):
        return anonymize(text)

    def assert_no_digits(self, safe, *numbers):
        for n in numbers:
            self.assertNotRegex(safe, rf"(?<!\d){n}(?!\d)", msg=f"Age {n} survived:\n{safe}")

    # --- The pilot example ---------------------------------------------------
    def test_pilot_example_name_and_both_ages_are_protected(self):
        safe = self.safe(
            "Ashley Rose was here at the center and she wanted accommodation, she also "
            "told us her actual age is 30 not 29 as we had indicated earlier, she did not "
            "give reasons for needing new accommodation."
        )
        self.assertNotIn("Ashley", safe)
        self.assertNotIn("Rose", safe)
        self.assert_no_digits(safe, 30, 29)
        self.assertIn("[AGE_ADULT]", safe)
        # The professional meaning stays.
        self.assertIn("wanted accommodation", safe)
        self.assertIn("did not give reasons", safe)

    # --- English -------------------------------------------------------------
    def test_english_age_forms(self):
        cases = {
            "She is 30 years old.": "[AGE_ADULT]",
            "A 24-year-old woman asked for help.": "[AGE_YOUNG_ADULT]",
            "He is 67 years old.": "[AGE_OLDER_ADULT]",
            "A child aged 8 was present.": "[AGE_CHILD]",
            "Age: 45.": "[AGE_ADULT]",
            "She turned 18 last month.": "[AGE_YOUNG_ADULT]",
            "A 6-month-old baby.": "[AGE_INFANT]",
            "She is 30, not 29.": "[AGE_ADULT]",
        }
        for text, tag in cases.items():
            safe = self.safe(text)
            self.assertIn(tag, safe, msg=text)
            self.assertNotRegex(safe, r"\d", msg=f"{text!r} -> {safe!r}")

    def test_age_correction_from_29_to_30_exposes_neither_number(self):
        for text in ("She corrected her age from 29 to 30.",
                     "Su edad pasó de 29 a 30 años.",
                     "Tiene 30, no 29 como indicamos.",
                     "Benetako adina 30 da, ez 29."):
            safe = self.safe(text)
            self.assert_no_digits(safe, 30, 29)

    def test_age_written_as_words(self):
        for text in ("She is thirty-two years old.",
                     "Tiene treinta y cinco años.",
                     "Hogeita hamar urte ditu.",
                     "He is seventeen years old."):
            safe = self.safe(text)
            self.assertIn("[AGE_", safe, msg=f"{text!r} -> {safe!r}")
            for word in ("thirty", "treinta", "hogeita", "seventeen"):
                self.assertNotIn(word, safe.lower())

    # --- Spanish -------------------------------------------------------------
    def test_spanish_age_forms(self):
        cases = {
            "La usuaria tiene 30 años.": "[AGE_ADULT]",
            "Una mujer de 24 años acudió al servicio.": "[AGE_YOUNG_ADULT]",
            "La menor, de 17 años, vive con su madre.": "[AGE_ADOLESCENT]",
            "Edad: 70.": "[AGE_OLDER_ADULT]",
            "El bebé de 8 meses.": "[AGE_INFANT]",
            "Cumplió 18 años en marzo.": "[AGE_YOUNG_ADULT]",
        }
        for text, tag in cases.items():
            safe = self.safe(text)
            self.assertIn(tag, safe, msg=text)
            self.assertNotRegex(safe, r"\d", msg=f"{text!r} -> {safe!r}")

    def test_spanish_lists_of_ages(self):
        safe = self.safe("Tiene dos hijos de 5 y 7 años.")
        self.assert_no_digits(safe, 5, 7)
        self.assertEqual(safe.count("[AGE_CHILD]"), 2)
        self.assertIn("dos hijos", safe)

    # --- Basque --------------------------------------------------------------
    def test_basque_age_forms(self):
        cases = {
            "Anek 17 urte ditu.": "[AGE_ADOLESCENT]",
            "30 urteko emakumea da.": "[AGE_ADULT]",
            "Adina: 45.": "[AGE_ADULT]",
            "18 hilabeteko haurra.": "[AGE_INFANT]",
            "70 urte zituen.": "[AGE_OLDER_ADULT]",
        }
        for text, tag in cases.items():
            safe = self.safe(text)
            self.assertIn(tag, safe, msg=text)
            self.assertNotRegex(safe, r"\d", msg=f"{text!r} -> {safe!r}")

    def test_equivalent_ages_in_three_languages_get_the_same_tag(self):
        for text in ("She is 30 years old.", "Tiene 30 años.", "30 urte ditu."):
            self.assertIn("[AGE_ADULT]", self.safe(text), msg=text)

    # --- Minors --------------------------------------------------------------
    def test_minor_stays_a_minor_without_the_exact_age(self):
        for text, tag in (("He is 17 years old.", "[AGE_ADOLESCENT]"),
                          ("Tiene 17 años.", "[AGE_ADOLESCENT]"),
                          ("17 urte ditu.", "[AGE_ADOLESCENT]"),
                          ("A child aged 8.", "[AGE_CHILD]"),
                          ("He is 18 years old.", "[AGE_YOUNG_ADULT]")):
            safe = self.safe(text)
            self.assertIn(tag, safe, msg=text)
            self.assertNotIn("17", safe)

    def test_age_groups_follow_the_documented_limits(self):
        from services.anonymizer import age_band_tag
        expected = {0: "INFANT", 2: "INFANT", 3: "CHILD", 12: "CHILD", 13: "ADOLESCENT",
                    17: "ADOLESCENT", 18: "YOUNG_ADULT", 25: "YOUNG_ADULT", 26: "ADULT",
                    64: "ADULT", 65: "OLDER_ADULT", 99: "OLDER_ADULT"}
        for age, name in expected.items():
            self.assertEqual(age_band_tag(age), f"[AGE_{name}]", msg=age)

    def test_invalid_age_configuration_falls_back_to_safe_defaults(self):
        from unittest.mock import patch
        import config
        from services import anonymizer
        for bad in ("nonsense", "2,12,16,25,64", "1,2,3", "64,25,17,12,2"):
            with patch.object(config, "AGE_BAND_LIMITS", bad):
                self.assertEqual(anonymizer._load_age_limits(), anonymizer._DEFAULT_AGE_LIMITS, msg=bad)

    # --- Dates of birth ------------------------------------------------------
    def test_date_and_year_of_birth_are_removed(self):
        for text, secret in (("Born on 12 March 1996.", "1996"),
                             ("Born in 1996.", "1996"),
                             ("Nació el 12 de marzo de 1996.", "1996"),
                             ("Nació en 1996.", "1996"),
                             ("1996an jaio zen.", "1996")):
            safe = self.safe(text)
            self.assertNotIn(secret, safe, msg=text)
            self.assertIn("[DATE]", safe)

    # --- Numbers that are NOT ages must stay ----------------------------------
    def test_unrelated_numbers_are_kept(self):
        text = ("Hace 3 años llegó; lleva 2 años en el piso. Tiene 3 hijos y paga 30 euros. "
                "Con 3 años de experiencia. Duela 3 urte etorri zen. She has lived here "
                "for 5 years. She has 2 children. The meeting lasted 45 minutes. "
                "2 de cada 10 personas.")
        safe = self.safe(text)
        self.assertNotIn("[AGE_", safe)
        for kept in ("Hace 3 años", "lleva 2 años", "3 hijos", "30 euros", "3 años de experiencia",
                     "Duela 3 urte", "for 5 years", "2 children", "45 minutes", "2 de cada 10"):
            self.assertIn(kept, safe)

    # --- Capitals and idempotency ----------------------------------------------
    def test_ages_in_capital_letters(self):
        safe = self.safe("MIKEL TIENE 17 AÑOS.")
        self.assertNotIn("17", safe)
        self.assertNotIn("MIKEL", safe)
        self.assertIn("[AGE_ADOLESCENT]", safe)

    def test_age_protection_is_idempotent(self):
        for text in ("Her actual age is 30 not 29.", "Tiene dos hijos de 5 y 7 años.",
                     "30 urteko emakumea da.", "Born in 1996."):
            once = self.safe(text)
            self.assertEqual(self.safe(once), once, msg=text)

    def test_mixed_language_text(self):
        safe = self.safe(
            "La usuaria Ane tiene 30 años; her son is 8 years old eta alabak 17 urte ditu. "
            "Email ane@example.com, tel +34 612 345 678."
        )
        for secret in ("Ane", "30", " 8 ", "17", "ane@example.com", "612 345 678"):
            self.assertNotIn(secret, safe)


class AnonymizerSyntheticCaseRegressionTests(unittest.TestCase):
    """Found by testing a synthetic English case (November 2026)."""

    def test_age_straight_after_a_name_is_protected(self):
        for text in ("Her ex-partner, John Hughes, is 41 and still contacts her.",
                     "Juan Pérez, de 41 años, acudió al servicio."):
            safe = anonymize(text)
            self.assertNotIn("41", safe, msg=safe)
            self.assertIn("[AGE_ADULT]", safe)

    def test_address_does_not_swallow_the_household_details_after_it(self):
        safe = anonymize("She lives at 14 River Road with her two children: her son Daniel, aged 9.")
        self.assertNotIn("14 River Road", safe)
        self.assertNotIn("Daniel", safe)
        self.assertIn("with her two children", safe)
        self.assertIn("[AGE_CHILD]", safe)
        safe = anonymize("Su domicilio es Calle Mayor 5 con su madre.")
        self.assertNotIn("Mayor 5", safe)
        self.assertIn("con su madre", safe)


class AnonymizerSpanishSyntheticCaseTests(unittest.TestCase):
    """Found by testing a synthetic Spanish case (November 2026)."""

    CASE = (
        "La usuaria, Lucía Fernández Etxebarria, acudió al servicio el 5 de noviembre de 2026 "
        "para pedir ayuda con el alquiler. Nos dijo que tiene 42 años, no 40 como consta en su "
        "expediente, y que nació en 1984. Vive en la calle Iparraguirre 23, 2º izquierda, con su "
        "hijo Unai, de 14 años, y su madre, Carmen, que tiene 78 años y necesita cuidados. Su DNI "
        "es 12345678Z y su teléfono 688 123 456. Trabaja a media jornada en una tienda de "
        "Barakaldo y cobra 900 euros al mes. Lleva 3 años en el piso y debe dos mensualidades."
    )

    def test_whole_case(self):
        safe = anonymize(self.CASE)
        for secret in ("Lucía", "Fernández", "Etxebarria", "42", "40", "1984", "Iparraguirre",
                       "2º", "izquierda", "Unai", "14", "Carmen", "78", "12345678Z",
                       "688 123 456", "Barakaldo"):
            self.assertNotIn(secret, safe, msg=secret)
        self.assertIn("una tienda de [LOCATION]", safe)
        self.assertIn("con su hijo [PERSON], de [AGE_ADOLESCENT]", safe)
        for kept in ("900 euros", "Lleva 3 años en el piso", "dos mensualidades"):
            self.assertIn(kept, safe)

    def test_floor_and_door_belong_to_the_address(self):
        for text in ("Su domicilio es Calle Mayor 5, 3ºB, con su madre.",
                     "Vive en la calle Mayor 5, bajo, sola.",
                     "Kalea Nagusia 4, 2. ezkerra."):
            safe = anonymize(text)
            for secret in ("3ºB", "bajo", "ezkerra", "Mayor", "Nagusia"):
                self.assertNotIn(secret, safe, msg=f"{text!r} -> {safe!r}")

    def test_known_towns_are_places_not_people(self):
        cases = {
            "Trabaja en una tienda de Barakaldo.": "[LOCATION]",
            "Barakaldo es donde vive.": "[LOCATION]",
            "Bilboko zentroan dago.": "[LOCATION]",
            "Se mudó a San Sebastián y luego a Vitoria-Gasteiz.": "[LOCATION]",
        }
        for text, tag in cases.items():
            safe = anonymize(text)
            self.assertIn(tag, safe, msg=text)
            self.assertNotIn("[PERSON]", safe, msg=f"{text!r} -> {safe!r}")
        # "la casa de Carmen" is still a person.
        self.assertIn("[PERSON]", anonymize("La casa de Carmen está lejos."))

    def test_capitals_place_does_not_swallow_the_rest(self):
        safe = anonymize("VIVE EN BILBAO CON SU MADRE.")
        self.assertNotIn("BILBAO", safe)
        self.assertIn("CON SU MADRE", safe)


if __name__ == "__main__":
    unittest.main()
