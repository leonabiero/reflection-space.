"""
Sensitive personal details -- GDPR "special categories" (18 November 2026).

EDE found that words such as "gay" reached the AI. The anonymizer now
replaces words that state a sensitive personal detail with a neutral label
([SEXUAL_ORIENTATION], [GENDER_IDENTITY], [HEALTH], [RELIGION_BELIEF],
[ETHNIC_ORIGIN], [POLITICAL_OPINION], [TRADE_UNION]), in Spanish, Basque and
English. Product owner's decisions: health -- only specific diagnoses,
treatments and medicines are hidden, general words are kept; nationality
is not hidden for now. Both can be switched on in config.

Also: a named mental health centre keeps "centro de salud mental" but
loses its place name.
"""

import unittest
from pathlib import Path
from unittest import mock

from services import anonymizer
from services.anonymizer import anonymize

ROOT = Path(__file__).resolve().parents[1]


class _Base(unittest.TestCase):
    def assert_label(self, text, label, *hidden):
        safe = anonymize(text)
        self.assertIn(label, safe, msg=f"{text!r} -> {safe!r}")
        for word in hidden:
            self.assertNotIn(word.lower(), safe.lower(), msg=f"{word!r} survived: {safe!r}")
        # Running the anonymizer again changes nothing.
        self.assertEqual(anonymize(safe), safe)
        return safe

    def assert_kept(self, text, *kept):
        safe = anonymize(text)
        for word in kept:
            self.assertIn(word, safe, msg=f"{word!r} should be kept: {safe!r}")
        return safe


class SexualOrientationTests(_Base):
    LABEL = "[SEXUAL_ORIENTATION]"

    def test_spanish(self):
        for text, word in (
            ("Ha contado en el instituto que es gay.", "gay"),
            ("Ella misma explica que es lesbiana.", "lesbiana"),
            ("Su pareja es bisexual.", "bisexual"),
            ("Son dos hombres homosexuales.", "homosexuales"),
            ("Participa en un grupo LGTBI+ del barrio.", "lgtbi"),
            ("Viven como pareja del mismo sexo.", "mismo sexo"),
            ("Gay desde la adolescencia, lo ha contado hoy.", "gay"),
        ):
            self.assert_label(text, self.LABEL, word)

    def test_basque(self):
        self.assert_label("Ekaitzek institutuan gaya dela esan du.", self.LABEL, "gaya")
        self.assert_label("Bere bikotekidea lesbiana da.", self.LABEL, "lesbiana")
        self.assert_label("Sexu bereko bikotea dira.", self.LABEL, "sexu bereko")

    def test_english(self):
        self.assert_label("He told the school he is gay.", self.LABEL, "gay")
        self.assert_label("She is a lesbian and lives with her partner.", self.LABEL, "lesbian")
        self.assert_label("They are a same-sex couple.", self.LABEL, "same-sex")

    def test_capitals(self):
        self.assert_label("ES GAY Y VIVE CON SU PAREJA.", self.LABEL, "gay")


class GenderIdentityTests(_Base):
    LABEL = "[GENDER_IDENTITY]"

    def test_three_languages(self):
        self.assert_label("Es una mujer trans que inició el proceso hace un año.", self.LABEL, " trans ")
        self.assert_label("Se define como persona no binaria.", self.LABEL, "no binaria")
        self.assert_label("Es transexual y su familia no lo acepta.", self.LABEL, "transexual")
        self.assert_label("Gizon transa da.", self.LABEL, "transa")
        self.assert_label("He is a transgender young man.", self.LABEL, "transgender")
        self.assert_label("They are non-binary.", self.LABEL, "non-binary")

    def test_transport_is_not_touched(self):
        self.assert_kept("Va en transporte público a la transición del ciclo.", "transporte", "transición")


class HealthSpecificTests(_Base):
    LABEL = "[HEALTH]"

    def test_diagnoses(self):
        for text, word in (
            ("Tiene diagnóstico de esquizofrenia paranoide.", "esquizofrenia"),
            ("Es VIH positivo desde hace años.", "vih"),
            ("Tiene un trastorno bipolar diagnosticado.", "bipolar"),
            ("Sufre una depresión mayor desde que murió su madre.", "depresión"),
            ("Tiene diabetes tipo 1.", "diabetes"),
            ("Su marido tiene alzhéimer.", "alzhéimer"),
            ("Diagnóstico de TDAH en el colegio.", "TDAH"),
            ("Cáncer de mama en tratamiento.", "cáncer"),
            ("Es alcohólico desde hace años.", "alcohólico"),
        ):
            self.assert_label(text, self.LABEL, word)

    def test_treatments_and_medicines(self):
        for text, word in (
            ("Toma sertralina y lorazepam.", "sertralina"),
            ("No toma la risperidona porque le da sueño.", "risperidona"),
            ("Toma litio desde el año pasado.", "litio"),
            ("Está en tratamiento antirretroviral.", "antirretroviral"),
            ("Está en el programa de metadona.", "metadona"),
            ("Empieza quimioterapia la semana que viene.", "quimioterapia"),
        ):
            self.assert_label(text, self.LABEL, word)

    def test_basque_and_english(self):
        self.assert_label("Eskizofrenia diagnostikoa du.", self.LABEL, "eskizofrenia")
        self.assert_label("Nahaste bipolarra du eta litioa hartzen du.", self.LABEL, "bipolarra", "litioa")
        self.assert_label("He has schizophrenia and takes olanzapine.", self.LABEL, "schizophrenia")
        self.assert_label("She is HIV positive.", self.LABEL, "hiv")

    def test_general_health_words_are_kept(self):
        # Product owner's decision: general words are not hidden.
        self.assert_kept(
            "Tiene una enfermedad y problemas de salud. Va al centro de salud.",
            "enfermedad", "problemas de salud", "centro de salud",
        )
        self.assert_kept("Le preocupa su salud mental.", "salud mental")
        self.assert_kept("Ha dado positivo en la prueba de nivel.", "positivo")
        self.assert_kept("Se concerta cita para el lunes.", "concerta")
        self.assert_kept("Consumo de alcohol los fines de semana.", "alcohol")


class OtherCategoryTests(_Base):
    def test_religion(self):
        self.assert_label("Ahmed, de religión musulmana, pide ayuda.", "[RELIGION_BELIEF]", "musulmana")
        self.assert_label("Su madre es católica practicante.", "[RELIGION_BELIEF]", "católica")
        self.assert_label("Es testigo de Jehová.", "[RELIGION_BELIEF]", "jehová")
        self.assert_label("Ama musulmana da.", "[RELIGION_BELIEF]", "musulmana")
        self.assert_label("The family is Muslim.", "[RELIGION_BELIEF]", "muslim")

    def test_ethnic_origin(self):
        self.assert_label("Familia gitana del barrio.", "[ETHNIC_ORIGIN]", "gitana")
        self.assert_label("Familia ijitoa da.", "[ETHNIC_ORIGIN]", "ijitoa")
        self.assert_label("A Roma family; she says they are gypsies.", "[ETHNIC_ORIGIN]", "gypsies")

    def test_political_opinion(self):
        self.assert_label("Dice que es de izquierdas y vota al PNV.", "[POLITICAL_OPINION]", "izquierdas", "PNV")
        self.assert_label("Es militante de EH Bildu.", "[POLITICAL_OPINION]", "Bildu")
        self.assert_label("Abertzalea da.", "[POLITICAL_OPINION]", "abertzale")
        self.assert_label("He is a communist.", "[POLITICAL_OPINION]", "communist")

    def test_trade_union(self):
        self.assert_label("Está afiliado a ELA desde hace años.", "[TRADE_UNION]", "ELA")
        self.assert_label("Es delegada sindical de CCOO.", "[TRADE_UNION]", "sindical", "CCOO")
        self.assert_label("LAB sindikatuko kidea da.", "[TRADE_UNION]", "LAB", "sindikatu")
        self.assert_label("She is a trade union member.", "[TRADE_UNION]", "trade union")


class FalsePositiveTests(_Base):
    def test_ordinary_words_are_kept(self):
        self.assert_kept("Atea itxita zegoen.", "Atea")                 # Basque: the door
        self.assert_kept("Podemos hablar el lunes.", "Podemos")          # we can
        self.assert_kept("Hay que sumar los ingresos.", "sumar")
        self.assert_kept("El laboratorio llamó; la tea estaba fría.", "laboratorio", "tea")

    def test_nationality_is_not_hidden_for_now(self):
        safe = self.assert_kept("Es marroquí y su vecina es rumana.", "marroquí", "rumana")
        self.assertNotIn("[NATIONALITY]", safe)


class NamedMentalHealthCentreTests(_Base):
    """The general words stay; the place name never survives."""

    def test_named_centre(self):
        cases = (
            ("Acude al Centro de Salud Mental de Uribarri cada mes.", "Centro de Salud Mental"),
            ("Le atienden en el centro de salud mental de Uribarri.", "centro de salud mental"),
            ("Tiene cita en el Centro de Salud Mental de Barakaldo.", "Centro de Salud Mental"),
        )
        for text, kept in cases:
            safe = self.assert_kept(text, kept)
            self.assertNotIn("Uribarri", safe)
            self.assertNotIn("Barakaldo", safe)
            self.assertIn("[LOCATION]", safe)
            self.assertNotIn("[PERSON]", safe)

    def test_csm_and_basque(self):
        safe = self.assert_kept("Va al CSM de Deusto.", "CSM")
        self.assertNotIn("Deusto", safe)
        self.assertIn("[LOCATION]", safe)
        safe = self.assert_kept("Zamudioko osasun mentaleko zentroan.", "osasun mentaleko zentroan")
        self.assertNotIn("Zamudio", safe)


class SettingTests(unittest.TestCase):
    def test_default_categories(self):
        self.assertEqual(anonymizer._load_special_categories(), anonymizer.DEFAULT_SPECIAL_CATEGORIES)
        self.assertNotIn("nationality", anonymizer.DEFAULT_SPECIAL_CATEGORIES)
        self.assertNotIn("health_general", anonymizer.DEFAULT_SPECIAL_CATEGORIES)
        import config
        self.assertEqual(
            tuple(n.strip() for n in config.ANONYMISER_SPECIAL_CATEGORIES.split(",")),
            anonymizer.DEFAULT_SPECIAL_CATEGORIES,
        )

    def test_switching_on_nationality_and_general_health(self):
        with mock.patch("config.ANONYMISER_SPECIAL_CATEGORIES",
                        ",".join(anonymizer.DEFAULT_SPECIAL_CATEGORIES) + ",nationality,health_general"):
            rules = anonymizer._build_special_rules(anonymizer._load_special_categories())
        safe = anonymizer._replace_special_categories("Es marroquí y tiene una enfermedad.", rules)
        self.assertIn("[NATIONALITY]", safe)
        self.assertIn("[HEALTH]", safe)

    def test_switching_a_category_off(self):
        with mock.patch("config.ANONYMISER_SPECIAL_CATEGORIES", "health_specific"):
            rules = anonymizer._build_special_rules(anonymizer._load_special_categories())
        safe = anonymizer._replace_special_categories("Es gay y toma litio.", rules)
        self.assertIn("gay", safe)
        self.assertIn("[HEALTH]", safe)

    def test_a_typo_never_switches_protection_off(self):
        for bad in ("", "   ", "sexual_orientaton", "health_specific,unknown", None):
            with mock.patch("config.ANONYMISER_SPECIAL_CATEGORIES", bad):
                self.assertEqual(anonymizer._load_special_categories(),
                                 anonymizer.DEFAULT_SPECIAL_CATEGORIES, repr(bad))

    def test_every_category_has_a_label_and_words(self):
        for key, label in anonymizer.SPECIAL_CATEGORY_LABELS.items():
            self.assertRegex(label, r"^\[[A-Z_]+\]$")
            self.assertTrue(anonymizer._SPECIAL_TERMS.get(key), key)


class AiInstructionTests(unittest.TestCase):
    """The AI is told what the labels mean, wherever anonymised text goes."""

    def test_note_is_in_every_live_prompt(self):
        note = "anonymizer import anonymize, SENSITIVE_LABELS_NOTE"
        service = (ROOT / "services" / "reflection_service.py").read_text(encoding="utf-8")
        self.assertIn(note, service)
        self.assertEqual(service.count('+ "\\n\\n" + SENSITIVE_LABELS_NOTE + "\\n\\n" + lang_instruction'), 2)
        patterns = (ROOT / "services" / "pattern_text_analysis.py").read_text(encoding="utf-8")
        self.assertIn(note, patterns)
        self.assertIn('+ SENSITIVE_LABELS_NOTE + "\\n\\n" + _lang_instruction(lang)', patterns)

    def test_note_says_never_guess(self):
        self.assertIn("Never guess, infer or ask", anonymizer.SENSITIVE_LABELS_NOTE)
        self.assertIn("[HEALTH]", anonymizer.SENSITIVE_LABELS_NOTE)

    def test_companion_call_sends_the_note(self):
        from services import reflection_service
        from rdi.companions import COMPANIONS
        sent = {}

        def fake_call(system, text):
            sent["system"] = system
            raise RuntimeError("stop here")

        with mock.patch.object(reflection_service, "_call_companion_model", side_effect=fake_call), \
                mock.patch.object(reflection_service, "_record_claude_usage"):
            with self.assertRaises(RuntimeError):
                reflection_service.generate_companion_reflection(
                    COMPANIONS[0], "[PERSON] es [SEXUAL_ORIENTATION].", "Español")
        self.assertIn(anonymizer.SENSITIVE_LABELS_NOTE, sent["system"])


class DemoTextsTests(unittest.TestCase):
    def test_sensitive_words_in_the_demo_texts_are_replaced(self):
        from services.demo_texts import DEMO_TEXTS
        joined = " ".join(anonymize(t["text"]) for t in DEMO_TEXTS).lower()
        for word in (" gay", "lesbiana", "bisexual", "esquizofrenia", "eskizofrenia", " vih",
                     "sertralina", "risperidona", "musulmana", "gitana", "bipolar", "litio"):
            self.assertNotIn(word, joined, word)


if __name__ == "__main__":
    unittest.main()
