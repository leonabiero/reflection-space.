"""
Anonymiser mistakes seen in a Spanish home-visit note (24 November 2026).

  - "Servicio de Atención Familiar" became "Servicio de [PERSONA 1]": a
    service name made only of generic words now stays visible; one that
    also contains a name becomes [ORGANIZACIÓN].
  - "colegio de Santutxu" became "colegio de [PERSONA 7]": Bilbao
    neighbourhoods are now [LUGAR].
  - "calle Zabalbide 47, 3.º izquierda" left "3.º izquierda" visible: the
    floor and door are now part of [DIRECCIÓN].

Every fix only changes a LABEL or keeps a generic service name visible:
real people's names must still always be hidden (checked below).
"""

import re
import unittest

from services.anonymizer import anonymize, PersonNumbers

HOME_VISIT = (
    "Visita domiciliaria, derivada desde el Servicio de Atención Familiar. "
    "La madre, Lucía Ferreira, vive en la calle Zabalbide 47, 3.º izquierda, "
    "con sus dos hijos. El mayor, Mikel, va al colegio de Santutxu. "
    "Lucía explica que el ambiente familiar es tranquilo."
)


def _no_person_names(test, safe, *names):
    for name in names:
        test.assertNotIn(name, safe, f"{name!r} was left visible")


class ServiceNameTests(unittest.TestCase):

    def test_generic_service_name_stays_visible(self):
        safe = anonymize("Derivada desde el Servicio de Atención Familiar.")
        self.assertEqual(safe, "Derivada desde el Servicio de Atención Familiar.")

    def test_word_familiar_is_not_remembered_as_a_name(self):
        safe = anonymize("Viene del Servicio de Atención Familiar. Familiar cercano: ninguno.")
        self.assertIn("Familiar cercano", safe)
        self.assertNotIn("[PERSONA", safe)

    def test_other_generic_service_names_stay_visible(self):
        for text in ("Acude al Centro de Día.",
                     "La deriva la Unidad de Atención Comunitaria.",
                     "Está en el Programa de Inserción Social.",
                     "Lo valora el Equipo de Intervención Familiar."):
            self.assertEqual(anonymize(text), text)

    def test_service_name_with_a_name_in_it_becomes_an_organisation(self):
        safe = anonymize("Acude al Centro de Día Arrupe los martes.")
        self.assertEqual(safe, "Acude al [ORGANIZACIÓN] los martes.")

    def test_place_after_a_service_is_still_a_place(self):
        safe = anonymize("Acude al Centro de Salud Mental de Uribarri cada mes.")
        self.assertIn("Centro de Salud Mental", safe)
        self.assertIn("[LUGAR]", safe)
        self.assertNotIn("Uribarri", safe)

    def test_people_near_service_names_are_still_hidden(self):
        cases = (
            "La atiende Ane Goikoetxea, del Servicio de Atención Familiar.",
            "Del Servicio de Atención Familiar, Ane Goikoetxea llamó ayer.",
            "Equipo de Intervención y Mikel Etxeberria acuden juntos.",
            "Centro de Día Mikel Etxeberria.",
            "Servicio de Atención a Iratxe Larrañaga.",
        )
        for text in cases:
            safe = anonymize(text)
            _no_person_names(self, safe, "Ane", "Goikoetxea", "Mikel", "Etxeberria",
                             "Iratxe", "Larrañaga")


class NeighbourhoodTests(unittest.TestCase):

    def test_colegio_de_santutxu_is_a_place(self):
        safe = anonymize("El mayor va al colegio de Santutxu.")
        self.assertEqual(safe, "El mayor va al colegio de [LUGAR].")

    def test_other_bilbao_neighbourhoods_are_places(self):
        for hood in ("Txurdinaga", "Otxarkoaga", "Rekalde", "Indautxu", "Zorrotza",
                     "Miribilla", "Atxuri", "Basurto", "Bolueta"):
            safe = anonymize(f"Viven cerca de {hood}, en un piso pequeño.")
            self.assertNotIn(hood, safe)
            self.assertIn("[LUGAR]", safe)
            self.assertNotIn("[PERSONA", safe)
        safe = anonymize("Santutxu es un barrio tranquilo.")
        self.assertEqual(safe, "[LUGAR] es un barrio tranquilo.")
        self.assertNotIn("Santutxu", anonymize("Santutxuko ikastolara doa."))

    def test_unknown_place_after_colegio_is_still_hidden(self):
        safe = anonymize("Va al colegio de Zubialde desde septiembre.")
        self.assertNotIn("Zubialde", safe)

    def test_a_childs_name_after_colegio_stays_a_person(self):
        safe = anonymize("Ayer fui al colegio de Ane para hablar con la tutora.")
        self.assertNotIn("Ane", safe)
        self.assertIn("[PERSONA 1]", safe)

    def test_a_known_person_after_colegio_stays_a_person(self):
        safe = anonymize("Iratxe Larrañaga es la hija. Hablé en el colegio de Iratxe.")
        self.assertNotIn("Iratxe", safe)
        self.assertNotIn("[LUGAR]", safe)
        self.assertEqual(len(set(re.findall(r"\[PERSONA \d+\]", safe))), 1)

    def test_begona_is_still_treated_as_a_person(self):
        safe = anonymize("Su tía Begoña vive con ellos.")
        self.assertNotIn("Begoña", safe)
        self.assertIn("[PERSONA", safe)


class AddressFloorAndDoorTests(unittest.TestCase):

    def test_official_spelling_with_a_dot(self):
        safe = anonymize("Vive en la calle Zabalbide 47, 3.º izquierda, con sus dos hijos.")
        self.assertEqual(safe, "Vive en la [DIRECCIÓN], con sus dos hijos.")

    def test_other_floor_and_door_forms(self):
        for unit in ("3.º", "3.ª", "3.º B", "3.º dcha", "3.º-izda", "3.ª derecha",
                     "2º izquierda", "4.º izq", "3º", "bajo", "1. ezkerra", "3.º dcha.", "3.º izda."):
            ending = "" if unit.endswith(".") else "."
            safe = anonymize(f"Vive en la calle Zabalbide 47, {unit}{ending} Sin incidencias.")
            self.assertEqual(safe, "Vive en la [DIRECCIÓN]. Sin incidencias.", unit)

    def test_floor_without_a_comma(self):
        safe = anonymize("Vive en calle Zabalbide 47 3.º izquierda con su madre.")
        self.assertEqual(safe, "Vive en [DIRECCIÓN] con su madre.")


class WholeHomeVisitNoteTests(unittest.TestCase):

    def test_the_home_visit_note(self):
        safe = anonymize(HOME_VISIT)
        self.assertIn("Servicio de Atención Familiar", safe)
        self.assertIn("colegio de [LUGAR]", safe)
        self.assertIn("[DIRECCIÓN], con sus dos hijos", safe)
        self.assertIn("ambiente familiar", safe)
        _no_person_names(self, safe, "Lucía", "Ferreira", "Mikel", "Zabalbide",
                         "47", "3.º", "izquierda", "Santutxu")
        # Lucía is the same person both times; Mikel is another.
        self.assertEqual(safe.count("[PERSONA 1]"), 2)
        self.assertIn("[PERSONA 2]", safe)
        self.assertNotIn("[PERSONA 3]", safe)

    def test_same_numbers_in_basque_and_english(self):
        for lang, person, place in (("Euskera", "PERTSONA", None), ("English", "PERSON", "LOCATION")):
            safe = anonymize(HOME_VISIT, lang)
            _no_person_names(self, safe, "Lucía", "Ferreira", "Mikel", "Santutxu", "Zabalbide")
            self.assertIn(f"[{person} 1]", safe)

    def test_running_twice_changes_nothing(self):
        once = anonymize(HOME_VISIT)
        self.assertEqual(anonymize(once), once)

    def test_shared_numbering_with_the_chat(self):
        people = PersonNumbers()
        anonymize(HOME_VISIT, "Español", people)
        chat = anonymize("Lucía no quería hablar delante de Mikel.", "Español", people)
        self.assertEqual(chat, "[PERSONA 1] no quería hablar delante de [PERSONA 2].")


if __name__ == "__main__":
    unittest.main()
