"""
Anonymiser fixes of 26 November 2026 (EDE testers' reports).

  A. Identity-document numbers are hidden in every written form (NIE, DNI,
     passport; any separators; upper or lower case; glued to the next word;
     after Spanish, Basque and English labels), while phone numbers,
     postcodes, ages, years and amounts are not mistaken for them.
  B. Two different people who share a surname are never merged.
  C. One person keeps one number however she is written (full name, first
     name, "Sra." + surname, without accents, in capitals, "Mª", split over
     PDF-style line breaks), and form headings are no longer counted as
     people.

All texts here are fictional.
"""

import unittest

from services.anonymizer import anonymize, PersonNumbers


def _persons(safe, word="PERSONA"):
    import re
    return sorted(set(re.findall(r"\[%s (\d+)\]" % word, safe)), key=int)


# ---------------------------------------------------------------------------
# A. Identity-document numbers
# ---------------------------------------------------------------------------
class IdentityNumberTests(unittest.TestCase):
    TAGS = {"Español": "[IDENTIFICADOR]", "Euskera": "[IDENTIFIKATZAILEA]", "English": "[ID]"}

    def test_the_reported_line_in_every_language(self):
        for lang, tag in self.TAGS.items():
            safe = anonymize("Nº de Identificación: Y1235687X", lang)
            self.assertEqual(safe, f"Nº de Identificación: {tag}", lang)

    def test_nie_in_every_written_form(self):
        for value in ("Y1235687X", "y1235687x", "Y-1235687-X", "Y 1235687 X", "Y.1235687.X",
                      "Y–1235687–X", "Y/1235687/X", "Y 123 56 87 X", "Y‑1235687‑X",
                      "X1234567L", "Z 7654321 r"):
            safe = anonymize(f"Su NIE es {value}, según consta.")
            self.assertIn("[IDENTIFICADOR]", safe, value)
            for part in ("1235687", "123 56 87", "1234567", "7654321"):
                self.assertNotIn(part, safe, value)

    def test_nie_glued_to_the_next_label_as_in_a_pdf(self):
        safe = anonymize("Nº de Identificación: Y1235687XTeléfono: 600123456")
        self.assertNotIn("1235687", safe)
        self.assertNotIn("Y1235687X", safe)
        self.assertIn("Teléfono", safe)

    def test_dni_in_every_written_form(self):
        for value in ("12345678Z", "12345678-Z", "12.345.678-Z", "12 345 678 Z", "12 345 678 z",
                      "12345678 z"):
            safe = anonymize(f"Documento: {value}")
            self.assertNotIn("345", safe, value)
            self.assertNotRegex(safe, r"(?<![A-ZÁÉÍÓÚ\w\[])[Zz](?!\w)", value)

    def test_dni_without_any_label(self):
        safe = anonymize("Firmó con 12 345 678 Z ayer.")
        self.assertNotIn("678", safe)
        self.assertNotIn(" Z ", safe)

    def test_passports(self):
        for text in ("Pasaporte: PAA123456", "Pasaporte: AB1234567", "pasaportea: PAA123456",
                     "Passport number: PAB654321", "Pasaporte marroquí AB1234567 en vigor",
                     "Nr. de identificación | AB1234567"):
            safe = anonymize(text)
            self.assertNotIn("123456", safe, text)
            self.assertNotIn("654321", safe, text)

    def test_new_labels_keep_the_label_and_hide_the_value(self):
        cases = {
            "N.º identificación: 9988-7766-B": "N.º identificación: [IDENTIFICADOR]",
            "Número de documento: AB-99887766": "Número de documento: [IDENTIFICADOR]",
            "Número de identidad: 99887766": "Número de identidad: [IDENTIFICADOR]",
            "Nortasun agiria: 99887766B": "Nortasun agiria: [IDENTIFICADOR]",
            "ID number: 99887766B": "ID number: [IDENTIFICADOR]",
            "Identity card: 99887766B": "Identity card: [IDENTIFICADOR]",
            "Document number: 99887766B": "Document number: [IDENTIFICADOR]",
            "Nr. de expdt. | 2025- ABC-164-01 | x": "Nr. de expdt. | [IDENTIFICADOR] | x",
            "NÚMERO DE IDENTIFICACIÓN: 12345678ab": "NÚMERO DE IDENTIFICACIÓN: [IDENTIFICADOR]",
        }
        for text, expected in cases.items():
            self.assertEqual(anonymize(text), expected, text)

    def test_basque_and_english_placeholders(self):
        # "zenbakia" was already a label before; it is hidden with the value.
        safe = anonymize("NAN zenbakia: 99887766-B", "Euskera")
        self.assertIn("[IDENTIFIKATZAILEA]", safe)
        self.assertNotIn("99887766", safe)
        self.assertNotIn("-B", safe)
        self.assertEqual(anonymize("ID number: X 1234567 L", "English"), "ID number: [ID]")

    def test_existing_labels_behave_as_before(self):
        self.assertEqual(anonymize("DNI 12345678Z"), "[IDENTIFICADOR]")
        self.assertEqual(anonymize("Pasaporte: PAB123456"), "[IDENTIFICADOR]")

    def test_year_first_dates_are_hidden(self):
        self.assertEqual(anonymize("Fecha de nacimiento | 1989/11/19"), "Fecha de nacimiento | [FECHA]")
        self.assertEqual(anonymize("Nació el 1966-02-02."), "Nació el [FECHA].")


class IdentityNumberLookalikeTests(unittest.TestCase):
    """Things that look a bit like a number but must not become an ID."""

    def test_phone_numbers_stay_phone_numbers(self):
        for phone in ("600 123 456", "944 123 456", "600123456"):
            safe = anonymize(f"Su teléfono es {phone}.")
            self.assertNotIn("[IDENTIFICADOR] ", safe.replace("[IDENTIFICADOR].", ""), phone)
        self.assertIn("[TELÉFONO]", anonymize("Llamar al 600 123 456 mañana."))

    def test_ages_years_amounts_and_counts_stay_visible(self):
        text = "Tiene 42 años, en 2025 cobró 1.250,50 €, tiene 3 hijos y paga 400 euros."
        self.assertEqual(anonymize(text), text)

    def test_a_short_number_after_documento_is_not_an_id(self):
        text = "Revisé el documento 3 de la carpeta."
        self.assertEqual(anonymize(text), text)

    def test_the_word_y_after_a_number_is_kept(self):
        safe = anonymize("Documento 12 345 678 y su madre")
        self.assertTrue(safe.endswith(" y su madre"), safe)

    def test_ordinary_dashes_between_years_are_kept(self):
        text = "Pagó la cuota de 2024-25 sin problemas."
        self.assertEqual(anonymize(text), text)


# ---------------------------------------------------------------------------
# B. Two different people with the same surname
# ---------------------------------------------------------------------------
PROBLEM_B_TEXT = (
    "Informe de seguimiento – Vivienda con apoyo\n"
    "El 12 de noviembre visité a Javier Ortiz en el piso de la calle Zabalbide 99, Bilbao. "
    "Javier tiene 42 años y lleva seis meses en el programa. Como siempre, el piso estaba "
    "desordenado; es evidente que no tiene interés en cuidar la vivienda. Le dije que tiene que "
    "buscar trabajo esta semana y que, si no lo hace, informaré a la coordinadora. Javier dijo que "
    "está esperando una respuesta de Lanbide, pero no le creo, porque suele poner excusas. Su "
    "hermana, Laura Ortiz (teléfono 600 123 456), opina que necesita más apoyo, aunque la familia "
    "no suele implicarse. He decidido que la próxima visita será sin avisar."
)


def _expected_b(person, address, place, phone):
    return (
        "Informe de seguimiento – Vivienda con apoyo\n"
        f"El 12 de noviembre visité a [{person} 1] en el piso de la [{address}], [{place}]. "
        f"[{person} 1] tiene 42 años y lleva seis meses en el programa. Como siempre, el piso estaba "
        "desordenado; es evidente que no tiene interés en cuidar la vivienda. Le dije que tiene que "
        "buscar trabajo esta semana y que, si no lo hace, informaré a la coordinadora. "
        f"[{person} 1] dijo que "
        "está esperando una respuesta de Lanbide, pero no le creo, porque suele poner excusas. Su "
        f"hermana, [{person} 2] (teléfono [{phone}]), opina que necesita más apoyo, aunque la familia "
        "no suele implicarse. He decidido que la próxima visita será sin avisar."
    )


class SharedSurnameTests(unittest.TestCase):
    def test_problem_b_text_exact_output_in_every_language(self):
        expected = {
            "Español": _expected_b("PERSONA", "DIRECCIÓN", "LUGAR", "TELÉFONO"),
            "Euskera": _expected_b("PERTSONA", "HELBIDEA", "TOKIA", "TELEFONOA"),
            "English": _expected_b("PERSON", "ADDRESS", "LOCATION", "PHONE"),
        }
        for lang, text in expected.items():
            self.assertEqual(anonymize(PROBLEM_B_TEXT, lang), text, lang)

    def test_problem_b_text_twice_changes_nothing(self):
        for lang in ("Español", "Euskera", "English"):
            once = anonymize(PROBLEM_B_TEXT, lang)
            self.assertEqual(anonymize(once, lang), once)

    def test_a_surname_alone_shared_by_two_people_is_hidden_without_a_number(self):
        safe = anonymize("Javier Ortiz vino. La Sra. Ortiz llamó. Laura Ortiz no vino.")
        self.assertEqual(safe, "[PERSONA 1] vino. La [PERSONA] llamó. [PERSONA 2] no vino.")
        # Also when the surname comes before both full names.
        safe = anonymize("El Sr. Ortiz llamó. Javier Ortiz vino. Laura Ortiz no vino.")
        self.assertNotIn("Ortiz", safe)
        self.assertIn("[PERSONA]", safe)

    def test_a_surname_alone_with_one_owner_gets_that_number(self):
        safe = anonymize("Javier Ortiz vino. El Sr. Ortiz estaba cansado. Laura Pérez no vino.")
        self.assertEqual(safe, "[PERSONA 1] vino. El [PERSONA 1] estaba cansado. [PERSONA 2] no vino.")

    def test_same_first_name_different_surnames_are_two_people(self):
        safe = anonymize("María García vino con María López.")
        self.assertEqual(safe, "[PERSONA 1] vino con [PERSONA 2].")

    def test_a_first_name_shared_by_two_people_is_hidden_without_a_number(self):
        safe = anonymize("María García vino con María López. Después María se fue.")
        self.assertEqual(safe, "[PERSONA 1] vino con [PERSONA 2]. Después [PERSONA] se fue.")

    def test_chat_keeps_the_document_numbers(self):
        people = PersonNumbers()
        anonymize(PROBLEM_B_TEXT, "Español", people)
        chat = anonymize("Creo que Laura tiene razón y Javier no.", "Español", people)
        self.assertEqual(chat, "Creo que [PERSONA 2] tiene razón y [PERSONA 1] no.")


# ---------------------------------------------------------------------------
# C. One person, many ways of writing her name
# ---------------------------------------------------------------------------
# One woman written about eight ways (full name, first name, "Sra." and
# "señora" + surname, "Maria" without accent, "Mª", "Doña", CAPITALS,
# surnames first), with PDF-style line breaks inside her name and form
# headings in between. Her son Iker is the only other person.
PROBLEM_C_TEXT = """INFORME SOCIAL
Datos Personales
Nombre y Apellidos: María Goikoetxea Ruiz
Nº de Identificación: Y1235687X
Nacionalidad: marroquí
Situación Familiar
La usuaria, María Goikoetxea, convive con su hijo Iker. María
Goikoetxea refiere que la Sra. Goikoetxea no recibe ayuda de su expareja. Maria
comenta que está cansada. MARÍA GOIKOETXEA RUIZ firma el plan. La señora Goikoetxea
acude puntual. Según Mª Goikoetxea, Iker va bien en el colegio. Goikoetxea
Ruiz, María, solicita ayuda. Doña María acepta.
Valoración Técnica
Se observa que María necesita apoyo."""


class OnePersonOneNumberTests(unittest.TestCase):
    def test_she_has_exactly_one_number_and_her_son_another(self):
        safe = anonymize(PROBLEM_C_TEXT)
        self.assertEqual(_persons(safe), ["1", "2"], safe)
        self.assertNotIn("[PERSONA]", safe)
        self.assertEqual(safe.count("[PERSONA 2]"), 2, safe)

    def test_no_part_of_her_name_is_left(self):
        safe = anonymize(PROBLEM_C_TEXT)
        for secret in ("María", "Maria", "MARÍA", "Mª", "Goikoetxea", "GOIKOETXEA", "Ruiz", "RUIZ",
                       "Iker", "Y1235687X", "1235687"):
            self.assertNotIn(secret, safe)

    def test_headings_stay_visible(self):
        safe = anonymize(PROBLEM_C_TEXT)
        for heading in ("INFORME SOCIAL", "Datos Personales", "Nombre y Apellidos:",
                        "Nº de Identificación:", "Nacionalidad: marroquí", "Situación Familiar",
                        "Valoración Técnica"):
            self.assertIn(heading, safe)

    def test_line_breaks_are_kept(self):
        safe = anonymize(PROBLEM_C_TEXT)
        self.assertEqual(safe.count("\n"), PROBLEM_C_TEXT.count("\n"))

    def test_same_in_basque_and_english_placeholders(self):
        self.assertEqual(_persons(anonymize(PROBLEM_C_TEXT, "Euskera"), "PERTSONA"), ["1", "2"])
        self.assertEqual(_persons(anonymize(PROBLEM_C_TEXT, "English"), "PERSON"), ["1", "2"])

    def test_twice_changes_nothing(self):
        once = anonymize(PROBLEM_C_TEXT)
        self.assertEqual(anonymize(once), once)

    def test_accents_and_capitals_do_not_make_a_new_person(self):
        safe = anonymize("Lucía Pérez vino. Lucia dijo que sí. LUCÍA PÉREZ firmó.")
        self.assertEqual(_persons(safe), ["1"], safe)

    def test_a_name_over_a_line_break_is_one_placeholder(self):
        safe = anonymize("Acude la usuaria Ane\nEtxeberria Goñi con su hijo.")
        self.assertEqual(safe.count("[PERSONA 1]"), 1, safe)
        self.assertIn("\n", safe)

    def test_two_people_on_two_lines_are_still_two(self):
        safe = anonymize("Profesional de referencia: Ane Etxeberria\nFatima Benali, de 34 años.")
        self.assertEqual(safe, "Profesional de referencia: [PERSONA 1]\n[PERSONA 2], de 34 años.")


class FormLayoutTests(unittest.TestCase):
    """Forms and bilingual reports as they arrive from Word and PDF files."""

    def test_bilingual_labels_are_not_people(self):
        text = ("Data/Fecha\nSinadura/Firma\nIzen-abizenak/ Nombre y apellidos | KEPA ZUBIRI LARREA\n"
                "Kontaktua/ Contacto | Edurne Alonso")
        safe = anonymize(text)
        self.assertEqual(
            safe,
            "Data/Fecha\nSinadura/Firma\nIzen-abizenak/ Nombre y apellidos | [PERSONA 1]\n"
            "Kontaktua/ Contacto | [PERSONA 2]",
        )

    def test_abbreviations_are_not_people(self):
        safe = anonymize("Nortasun agiria/ Doc. de identidad: Y1235687X\n"
                         "Txostenaren egilea/ Prof. de referencia | Edurne Alonso\nFdo.: ______")
        for kept in ("Doc. de identidad", "Prof. de referencia", "Fdo.:"):
            self.assertIn(kept, safe)
        self.assertEqual(_persons(safe), ["1"])

    def test_a_word_after_a_heading_in_capitals_is_not_a_person(self):
        text = "4.2. ÁMBITO CONVIVENCIAL\n\nMantiene una buena relación con su madre."
        self.assertEqual(anonymize(text), text)

    def test_names_typed_in_small_letters_after_a_name_label_are_hidden(self):
        safe = anonymize("NOMBRE Y APELLIDOS: Rosa gomez urrutia\nApellidos: perez")
        for secret in ("Rosa", "gomez", "urrutia", "perez"):
            self.assertNotIn(secret, safe)
        self.assertIn("NOMBRE Y APELLIDOS:", safe)

    def test_label_words_in_capitals_are_kept_when_the_name_follows(self):
        self.assertEqual(anonymize("NOMBRE Y APELLIDOS   CARLOS VEGA"), "NOMBRE Y APELLIDOS   [PERSONA 1]")

    def test_name_label_does_not_swallow_the_sentence(self):
        self.assertEqual(anonymize("Nombre: Ane y su madre vinieron."), "Nombre: [PERSONA 1] y su madre vinieron.")

    def test_basque_street_written_before_its_name(self):
        safe = anonymize("DOMICILIO\nKALE NAGUSIA 78-2B\n")
        self.assertNotIn("NAGUSIA", safe)
        self.assertNotIn("78", safe)

    def test_country_of_origin_stays_visible(self):
        self.assertIn("España", anonymize("Decidió venir a España en 2019."))


if __name__ == "__main__":
    unittest.main()
