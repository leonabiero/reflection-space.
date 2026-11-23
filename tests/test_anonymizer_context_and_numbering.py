"""
Anonymisation change approved by EDE (November 2026).

  - Still hidden: names, surnames, addresses, IDs, phones, emails, dates
    (and years of birth), towns of residence, organisations, political
    opinion, trade union.
  - Now visible: sex/gender, ethnicity, origin/nationality, migration
    status, religion, exact age, mental health, substance use, disability,
    sexual orientation.
  - Different people are numbered consistently: [PERSONA 1], [PERSONA 2]...
  - Placeholders follow the language chosen (Spanish default, Basque,
    English); placeholders in any language, and the old English ones, are
    recognised, so anonymising twice changes nothing.
  - Two false positives seen on the live app are fixed.
"""

import unittest

from services.anonymizer import anonymize, PersonNumbers, labels_note


class LiveFalsePositiveTests(unittest.TestCase):
    """The exact two lines seen on the live app."""

    def test_ordinary_capitalised_word_after_a_dash_is_kept(self):
        line = "Informe de seguimiento – Alojamiento social"
        self.assertEqual(anonymize(line), line)
        self.assertIn("Alojamiento social", anonymize(line, "Euskera"))

    def test_referencia_is_not_an_id_and_the_name_is_still_hidden(self):
        self.assertEqual(anonymize("Profesional de referencia: Ane Etxeberria"),
                         "Profesional de referencia: [PERSONA 1]")

    def test_real_ids_after_referencia_are_still_hidden(self):
        safe = anonymize("Número de referencia: EXP-2024-0315. Referencia 88213.")
        self.assertNotIn("2024-0315", safe)
        self.assertNotIn("88213", safe)

    def test_real_names_after_a_dash_are_still_hidden(self):
        safe = anonymize("Visita – Lucía García acude sola.")
        self.assertNotIn("Lucía", safe)
        self.assertNotIn("García", safe)


class NumberingTests(unittest.TestCase):
    def test_same_person_same_number_in_order_of_appearance(self):
        safe = anonymize("Ane Etxeberria habló con Mikel. Después Ane llamó a su madre, Lucía. Mikel no vino.")
        self.assertEqual(
            safe,
            "[PERSONA 1] habló con [PERSONA 2]. Después [PERSONA 1] llamó a su madre, [PERSONA 3]. "
            "[PERSONA 2] no vino.",
        )

    def test_capitals_keep_the_same_numbers(self):
        safe = anonymize("VISITA A NEREA AGIRRE. NEREA ESTÁ BIEN. JOHN NO.")
        self.assertIn("[PERSONA 1]", safe)
        self.assertEqual(safe.count("[PERSONA 1]"), 2)
        self.assertIn("[PERSONA 2]", safe)
        for name in ("NEREA", "AGIRRE", "JOHN"):
            self.assertNotIn(name, safe)

    def test_chat_uses_the_document_numbers(self):
        people = PersonNumbers()
        doc = anonymize("Ane habló con Mikel.", "Español", people)
        self.assertEqual(doc, "[PERSONA 1] habló con [PERSONA 2].")
        chat = anonymize("Creo que Mikel tiene razón y Pedro no.", "Español", people)
        self.assertEqual(chat, "Creo que [PERSONA 2] tiene razón y [PERSONA 3] no.")

    def test_names_on_two_lines_are_two_people_and_the_line_break_stays(self):
        safe = anonymize("Profesional de referencia: Ane Etxeberria\nFatima Benali, de 34 años.")
        self.assertEqual(safe, "Profesional de referencia: [PERSONA 1]\n[PERSONA 2], de 34 años.")

    def test_a_surname_alone_on_the_next_line_is_still_hidden(self):
        safe = anonymize("LA MADRE, LUCÍA\nGARCÍA VINO.")
        self.assertNotIn("LUCÍA", safe)
        self.assertNotIn("GARCÍA", safe)
        self.assertIn("\n", safe)
        self.assertIn("VINO", safe)

    def test_existing_numbers_are_never_reused(self):
        safe = anonymize("[PERSONA 2] vino con Jon.")
        self.assertEqual(safe, "[PERSONA 2] vino con [PERSONA 3].")


class LanguageTests(unittest.TestCase):
    TEXT = ("La usuaria, Lucía García, vive en Barakaldo, calle Mayor 5. Acude al colegio San José. "
            "DNI 12345678Z, tel 944 123 456, lucia@example.com, el 21 de marzo de 2025.")

    def test_spanish_is_the_default(self):
        safe = anonymize(self.TEXT)
        for tag in ("[PERSONA 1]", "[LUGAR]", "[DIRECCIÓN]", "[ORGANIZACIÓN]", "[IDENTIFICADOR]",
                    "[TELÉFONO]", "[CORREO]", "[FECHA]"):
            self.assertIn(tag, safe, safe)

    def test_basque(self):
        safe = anonymize(self.TEXT, "Euskera")
        for tag in ("[PERTSONA 1]", "[TOKIA]", "[HELBIDEA]", "[ERAKUNDEA]", "[IDENTIFIKATZAILEA]",
                    "[TELEFONOA]", "[POSTA]", "[DATA]"):
            self.assertIn(tag, safe, safe)

    def test_english(self):
        safe = anonymize(self.TEXT, "English")
        for tag in ("[PERSON 1]", "[LOCATION]", "[ADDRESS]", "[ORGANISATION]", "[ID]",
                    "[PHONE]", "[EMAIL]", "[DATE]"):
            self.assertIn(tag, safe, safe)

    def test_unknown_language_falls_back_to_spanish(self):
        self.assertIn("[PERSONA 1]", anonymize("Habló con Mikel.", "Klingon"))

    def test_twice_never_changes_anything_in_any_language(self):
        for lang in ("Español", "Euskera", "English"):
            once = anonymize(self.TEXT, lang)
            for other in ("Español", "Euskera", "English"):
                self.assertEqual(anonymize(once, other), once, (lang, other))

    def test_old_english_tags_are_left_as_they_are(self):
        old = "[PERSON] tiene [HEALTH] y vive en [LOCATION]. [AGE_ADULT]."
        self.assertEqual(anonymize(old), old)
        self.assertEqual(anonymize(old, "Euskera"), old)

    def test_note_lists_the_placeholders_of_the_language(self):
        self.assertIn("[PERSONA 1]", labels_note("Español"))
        self.assertIn("[DIRECCIÓN]", labels_note("Español"))
        self.assertIn("[HELBIDEA]", labels_note("Euskera"))
        self.assertIn("[ADDRESS]", labels_note("English"))


class VisibleContextTests(unittest.TestCase):
    def test_context_that_may_reveal_bias_is_kept(self):
        text = ("Mujer de 34 años, procedente de Marruecos, en situación irregular, musulmana, "
                "lesbiana, con esquizofrenia, consumo de cannabis y discapacidad intelectual. "
                "Llegó de Senegal hace un año. A Moroccan woman, a Muslim, aged 41.")
        safe = anonymize(text)
        for kept in ("34 años", "Marruecos", "situación irregular", "musulmana", "lesbiana",
                     "esquizofrenia", "cannabis", "discapacidad intelectual", "Senegal",
                     "Moroccan", "Muslim", "aged 41"):
            self.assertIn(kept, safe, f"{kept!r} was hidden: {safe!r}")

    def test_direct_identifiers_are_still_hidden(self):
        text = ("Lucía García (DNI 12345678Z) vive en la calle Gran Vía 12 de Bilbao, "
                "tel 612 345 678, lucia@example.com, nació en 1990.")
        safe = anonymize(text)
        for secret in ("Lucía", "García", "12345678Z", "Gran Vía", "Bilbao", "612 345 678",
                       "lucia@example.com", "1990"):
            self.assertNotIn(secret, safe)


if __name__ == "__main__":
    unittest.main()
