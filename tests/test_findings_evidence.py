"""Tests for services/evidence.py -- exact-quote verification.

Mocked / pure: no database, no AI provider, no network.
"""
import unicodedata
import unittest

from services.evidence import (
    verify_quotes, MIN_QUOTE_CHARS, MAX_QUOTES_PER_FINDING,
)

SOURCE_ES = (
    "Maite dice que quiere vivir cerca de su hermana.\n"
    "El equipo considera que  no está   motivada para el cambio.\n"
    "Asistió a las tres citas previstas durante el mes de mayo."
)
SOURCE_EU = (
    "Amaiak esan du bere ahizparen ondoan bizi nahi duela. "
    "Taldeak uste du ez dagoela aldaketarako prest. "
    "Hiru hitzorduetara joan da maiatzean."
)
SOURCE_EN = "She told the worker she wants to keep her job. The team thinks she is not motivated."


class ExactQuoteTests(unittest.TestCase):
    def test_exact_passage_is_verified(self):
        quote = "quiere vivir cerca de su hermana"
        verified, dropped = verify_quotes([quote], SOURCE_ES)
        self.assertEqual(verified, [{"quote": quote}])
        self.assertEqual(dropped, 0)

    def test_dict_form_from_model_is_accepted(self):
        verified, dropped = verify_quotes([{"quote": "wants to keep her job"}], SOURCE_EN)
        self.assertEqual(verified, [{"quote": "wants to keep her job"}])
        self.assertEqual(dropped, 0)

    def test_paraphrase_is_dropped_and_counted(self):
        verified, dropped = verify_quotes(["she hopes to live near her sibling"], SOURCE_EN)
        self.assertEqual(verified, [])
        self.assertEqual(dropped, 1)

    def test_changed_word_is_dropped(self):
        verified, dropped = verify_quotes(["the team thinks she is unmotivated"], SOURCE_EN)
        self.assertEqual(verified, [])
        self.assertEqual(dropped, 1)

    def test_stitched_with_ellipsis_is_dropped(self):
        verified, dropped = verify_quotes(["Maite dice ... su hermana"], SOURCE_ES)
        self.assertEqual(verified, [])
        self.assertEqual(dropped, 1)

    def test_translation_is_not_accepted_as_a_quote(self):
        verified, dropped = verify_quotes(["She says she wants to live near her sister"], SOURCE_ES)
        self.assertEqual(verified, [])
        self.assertEqual(dropped, 1)

    def test_too_short_fragment_is_dropped(self):
        short = "no"
        self.assertLess(len(short), MIN_QUOTE_CHARS)
        verified, dropped = verify_quotes([short], SOURCE_ES)
        self.assertEqual(verified, [])
        self.assertEqual(dropped, 1)

    def test_outer_quotation_marks_added_by_the_model_are_removed(self):
        for wrapped in ('"wants to keep her job"', "\u201cwants to keep her job\u201d", "\u00abwants to keep her job\u00bb"):
            verified, dropped = verify_quotes([wrapped], SOURCE_EN)
            self.assertEqual(verified, [{"quote": "wants to keep her job"}], wrapped)
            self.assertEqual(dropped, 0)

    def test_duplicates_are_collapsed_and_not_counted_as_dropped(self):
        quote = "wants to keep her job"
        verified, dropped = verify_quotes([quote, quote], SOURCE_EN)
        self.assertEqual(len(verified), 1)
        self.assertEqual(dropped, 0)

    def test_cap_on_number_of_quotes(self):
        source = " ".join(f"Frase numero {i} del documento original." for i in range(10))
        quotes = [f"Frase numero {i} del documento original." for i in range(10)]
        verified, _ = verify_quotes(quotes, source)
        self.assertEqual(len(verified), MAX_QUOTES_PER_FINDING)

    def test_non_list_means_no_evidence(self):
        for value in (None, "a string", {"quote": "x"}, 5):
            self.assertEqual(verify_quotes(value, SOURCE_EN), ([], 0))

    def test_non_string_items_are_dropped(self):
        verified, dropped = verify_quotes([None, 5, {"nope": 1}], SOURCE_EN)
        self.assertEqual(verified, [])
        self.assertEqual(dropped, 3)


class WhitespaceAndLanguageTests(unittest.TestCase):
    def test_line_break_and_extra_spaces_still_verify_and_return_source_text(self):
        # the source has a double space and runs of spaces; the model
        # normalised them. What comes back must be the SOURCE's wording.
        model_version = "El equipo considera que no está motivada para el cambio."
        verified, dropped = verify_quotes([model_version], SOURCE_ES)
        self.assertEqual(dropped, 0)
        self.assertEqual(len(verified), 1)
        returned = verified[0]["quote"]
        self.assertIn(returned, SOURCE_ES)           # exact slice of the source
        self.assertIn("que  no está   motivada", returned)  # original spacing kept

    def test_quote_spanning_a_line_break(self):
        model_version = "hermana. El equipo considera que"
        verified, _ = verify_quotes([model_version], SOURCE_ES)
        self.assertEqual(len(verified), 1)
        self.assertIn(verified[0]["quote"], SOURCE_ES)

    def test_spanish_accents_and_punctuation(self):
        quote = "no está   motivada para el cambio"
        verified, dropped = verify_quotes(["no está motivada para el cambio"], SOURCE_ES)
        self.assertEqual(dropped, 0)
        self.assertEqual(verified[0]["quote"], quote)

    def test_basque_text_passes_through_unchanged(self):
        quote = "bere ahizparen ondoan bizi nahi duela"
        verified, dropped = verify_quotes([quote], SOURCE_EU)
        self.assertEqual(verified, [{"quote": quote}])
        self.assertEqual(dropped, 0)

    def test_basque_translation_of_a_spanish_quote_is_rejected(self):
        verified, dropped = verify_quotes(["bere ahizparen ondoan bizi nahi du"], SOURCE_ES)
        self.assertEqual(verified, [])
        self.assertEqual(dropped, 1)

    def test_composed_vs_decomposed_accents_match_and_return_source_form(self):
        source_nfd = unicodedata.normalize("NFD", "Dice que está cansada por la situación en casa.")
        model_quote_nfc = unicodedata.normalize("NFC", "que está cansada por la situación")
        self.assertNotEqual(source_nfd, unicodedata.normalize("NFC", source_nfd))
        verified, dropped = verify_quotes([model_quote_nfc], source_nfd)
        self.assertEqual(dropped, 0)
        self.assertEqual(len(verified), 1)
        # unicode-equivalent to what the model gave, and no corruption
        self.assertEqual(
            unicodedata.normalize("NFC", verified[0]["quote"]), model_quote_nfc,
        )

    def test_enye_and_diaeresis_survive_unchanged(self):
        source = "El niño dijo que la cigüeña volvió al nido de la montaña."
        quote = "cigüeña volvió al nido de la montaña"
        verified, _ = verify_quotes([quote], source)
        self.assertEqual(verified, [{"quote": quote}])


if __name__ == "__main__":
    unittest.main()
