"""
Sensitive personal details -- GDPR "special categories".

18 November 2026: words that state a sensitive personal detail were
replaced by a neutral label ([SEXUAL_ORIENTATION], [GENDER_IDENTITY],
[HEALTH], [RELIGION_BELIEF], [ETHNIC_ORIGIN], [POLITICAL_OPINION],
[TRADE_UNION]), in Spanish, Basque and English.

November 2026 -- EDE's decision (approved by the project leads): this is
the context in which bias tends to appear, and the AI must see it to name
it. By default, sexual orientation, gender identity, health, religion,
ethnic origin and nationality are now LEFT VISIBLE; only political
opinion and trade union membership are still hidden. Every category still
works and can be switched back on in config.ANONYMISER_SPECIAL_CATEGORIES.

So these tests protect two things:
  - the NEW default (DefaultBehaviourTests);
  - every category still working when switched on (the other classes,
    which switch all categories on).

Also: a named mental health centre keeps "centro de salud mental" but
loses its place name.
"""

import re
import unittest
from pathlib import Path
from unittest import mock

from services import anonymizer
from services.anonymizer import anonymize as _anonymize

ROOT = Path(__file__).resolve().parents[1]
ALL_CATEGORIES = tuple(anonymizer.SPECIAL_CATEGORY_LABELS)
SWITCHED_ON = tuple(c for c in ALL_CATEGORIES if c not in ("nationality", "health_general"))


def anonymize(text):
    """English placeholders, person numbers ignored (they are tested in
    tests/test_anonymizer_context_and_numbering.py)."""
    return re.sub(r"\[PERSON \d+\]", "[PERSON]", _anonymize(text, "English"))


class _Base(unittest.TestCase):
    """All the categories that used to be on by default, switched on."""

    def setUp(self):
        patcher = mock.patch.object(anonymizer, "_SPECIAL_RULES",
                                    anonymizer._build_special_rules(SWITCHED_ON))
        patcher.start()
        self.addCleanup(patcher.stop)

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


class DefaultBehaviourTests(unittest.TestCase):
    """EDE, November 2026: context that may reveal bias stays visible."""

    def test_sensitive_context_is_left_visible_by_default(self):
        text = ("Es una mujer trans, lesbiana, musulmana, gitana, marroquí, con esquizofrenia; "
                "toma litio. He is gay and HIV positive.")
        safe = anonymize(text)
        for word in ("trans", "lesbiana", "musulmana", "gitana", "marroquí", "esquizofrenia",
                     "litio", "gay", "HIV"):
            self.assertIn(word, safe, msg=safe)
        for label in ("[SEXUAL_ORIENTATION]", "[GENDER_IDENTITY]", "[HEALTH]",
                      "[RELIGION_BELIEF]", "[ETHNIC_ORIGIN]", "[NATIONALITY]"):
            self.assertNotIn(label, safe)

    def test_political_opinion_and_trade_union_are_still_hidden(self):
        safe = anonymize("Vota al PNV y está afiliado a ELA.")
        self.assertIn("[POLITICAL_OPINION]", safe)
        self.assertIn("[TRADE_UNION]", safe)
        self.assertNotIn("PNV", safe)
        self.assertNotIn("ELA", safe)

    def test_names_are_still_hidden_next_to_visible_context(self):
        safe = anonymize("La usuaria, Lucía García, musulmana, procedente de Marruecos.")
        self.assertNotIn("Lucía", safe)
        self.assertNotIn("García", safe)
        self.assertIn("musulmana", safe)
        self.assertIn("Marruecos", safe)


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

    def test_nationality_is_not_hidden(self):
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
        self.assertEqual(anonymizer.DEFAULT_SPECIAL_CATEGORIES, ("political_opinion", "trade_union"))
        self.assertEqual(anonymizer._load_special_categories(), anonymizer.DEFAULT_SPECIAL_CATEGORIES)
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

    def test_switching_a_category_on(self):
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
    """The AI is told what the placeholders mean, in the language of the
    text, wherever anonymised text goes."""

    def test_note_is_in_every_live_prompt(self):
        service = (ROOT / "services" / "reflection_service.py").read_text(encoding="utf-8")
        self.assertIn("from services.anonymizer import anonymize, labels_note", service)
        self.assertEqual(service.count('+ "\\n\\n" + labels_note(lang) + "\\n\\n" + lang_instruction'), 3)
        patterns = (ROOT / "services" / "pattern_text_analysis.py").read_text(encoding="utf-8")
        self.assertIn("from services.anonymizer import anonymize, labels_note", patterns)
        self.assertIn('+ labels_note(lang) + "\\n\\n" + _lang_instruction(lang)', patterns)

    def test_note_says_never_guess_and_uses_the_language(self):
        for lang, person in (("Español", "[PERSONA 1]"), ("Euskera", "[PERTSONA 1]"),
                             ("English", "[PERSON 1]")):
            note = anonymizer.labels_note(lang)
            self.assertIn("Never guess, infer or ask", note)
            self.assertIn(person, note)
            self.assertIn("deliberately been left in the text", note)

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
                    COMPANIONS[0], "[PERSONA 1] es lesbiana.", "Euskera")
        self.assertIn(anonymizer.labels_note("Euskera"), sent["system"])


def _load_locale(lang):
    import importlib.util
    spec = importlib.util.spec_from_file_location(f"loc_labels_{lang}", ROOT / "services" / "locales" / f"{lang}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return next(v for v in vars(module).values() if isinstance(v, dict) and "rs_finish_button" in v)


class LabelExplanationTests(unittest.TestCase):
    """Every place that explains the placeholders to people explains them
    in its own language (November 2026)."""

    EXPLAINED = ("PERSON", "ADDRESS", "LOCATION", "ORGANISATION", "ID", "PHONE", "EMAIL", "DATE",
                 "POLITICAL_OPINION", "TRADE_UNION")
    LANGS = {"es": "Español", "eu": "Euskera", "en": "English"}

    def test_every_placeholder_is_explained_in_every_language(self):
        for code, lang in self.LANGS.items():
            texts = _load_locale(code)
            words = texts["anon_placeholders"]
            legend = texts["anon_sensitive_labels_help"]
            for tag in self.EXPLAINED:
                self.assertIn(f"[{words[tag]}", legend, f"{tag} missing from the legend in {code}")
            self.assertIn(f"[{words['PERSON']} 1]", texts["help"]["privacy_points"][1])
            # Older English labels are still explained on the admin screen.
            self.assertIn("[PERSON]", texts["admin_anon_tags_help"])

    def test_placeholder_words_match_the_agreed_ones(self):
        es, eu, en = (_load_locale(c)["anon_placeholders"] for c in ("es", "eu", "en"))
        self.assertEqual([es[t] for t in self.EXPLAINED[:8]],
                         ["PERSONA", "DIRECCIÓN", "LUGAR", "ORGANIZACIÓN", "IDENTIFICADOR",
                          "TELÉFONO", "CORREO", "FECHA"])
        self.assertEqual([eu[t] for t in self.EXPLAINED[:8]],
                         ["PERTSONA", "HELBIDEA", "TOKIA", "ERAKUNDEA", "IDENTIFIKATZAILEA",
                          "TELEFONOA", "POSTA", "DATA"])
        self.assertEqual([en[t] for t in self.EXPLAINED[:8]],
                         ["PERSON", "ADDRESS", "LOCATION", "ORGANISATION", "ID", "PHONE",
                          "EMAIL", "DATE"])
        for words in (es, eu, en):
            self.assertEqual(set(words), set(anonymizer.CANONICAL_TAGS))

    def test_labels_are_shown_where_anonymised_text_is_shown(self):
        admin = (ROOT / "pages" / "admin_sections" / "admin_tools.py").read_text(encoding="utf-8")
        self.assertIn('st.caption(T["admin_anon_tags_help"])', admin)
        self.assertIn('st.caption(T["anon_sensitive_labels_help"])', admin)
        page = (ROOT / "pages" / "reflection_space.py").read_text(encoding="utf-8")
        start = page.index('st.toggle(T["rs_anonymised_preview_label"]')
        block = page[start:start + 600]
        self.assertIn('st.caption(T["anon_sensitive_labels_help"])', block)


class DemoTextsTests(unittest.TestCase):
    def test_context_words_in_the_demo_texts_are_kept(self):
        """EDE, November 2026: the context stays visible in the demo too."""
        from services.demo_texts import DEMO_TEXTS
        originals = " ".join(t["text"] for t in DEMO_TEXTS).lower()
        joined = " ".join(_anonymize(t["text"]) for t in DEMO_TEXTS).lower()
        for word in ("lesbiana", "bisexual", "esquizofrenia", "sertralina", "risperidona",
                     "musulmana", "gitana", "bipolar"):
            if word in originals:
                self.assertIn(word, joined, word)


if __name__ == "__main__":
    unittest.main()
