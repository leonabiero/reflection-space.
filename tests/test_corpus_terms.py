"""Offline tests for the word and phrase list (no database, no AI):
how a term is checked, matched, counted and exported."""
import unittest

from services import corpus_terms as ct


def count(term, text):
    parsed = ct.parse_term(term)
    return len(list(ct.compile_term(parsed["norm"]).finditer(ct.prepare_text(text)[1])))


class ParseTests(unittest.TestCase):
    def test_tidy_and_normal_form(self):
        p = ct.parse_term("  «Atención»  ")
        self.assertEqual(p, {"term": "Atención", "norm": "atencion"})
        self.assertEqual(ct.parse_term("No   Quiere")["norm"], "no quiere")
        self.assertEqual(ct.parse_term("agresiv*")["norm"], "agresiv*")
        self.assertEqual(ct.parse_term("(Vago),")["term"], "Vago")     # outer punctuation is tidied away

    def test_unusable_terms_are_refused(self):
        for bad in ["", "   ", "a", "a*", "ab*", "x" * 61, "uno dos tres cuatro cinco seis siete",
                    "mal;bien", "a.b", "foo*bar", "*", "agre siv#", "..."]:
            self.assertIsNone(ct.parse_term(bad), bad)

    def test_two_letter_words_and_three_letter_stems_are_allowed(self):
        self.assertIsNotNone(ct.parse_term("no"))
        self.assertIsNotNone(ct.parse_term("etx*"))

    def test_enye_stays_apart_from_n(self):
        self.assertEqual(ct.parse_term("año")["norm"], "año")
        self.assertEqual(count("año", "Pasó un ano, no un año."), 1)


class MatchTests(unittest.TestCase):
    def test_capitals_and_accents_do_not_matter(self):
        self.assertEqual(count("atención", "ATENCION, atención y Atención."), 3)

    def test_whole_words_only(self):
        self.assertEqual(count("mal", "Es normal y no está mal."), 1)
        self.assertEqual(count("vago", "Un vagón vago."), 1)

    def test_star_covers_endings(self):
        self.assertEqual(count("agresiv*", "agresivo, agresiva, agresivos y no agresión"), 3)
        self.assertEqual(count("etxe*", "etxea, etxeak, etxean eta etxola"), 3)

    def test_phrase_in_order_across_spaces_and_line_breaks(self):
        self.assertEqual(count("no quiere", "No   quiere y no\nquiere pero quiere no."), 2)

    def test_phrase_does_not_cross_a_full_stop(self):
        self.assertEqual(count("no quiere", "Dice que no. Quiere ayuda."), 0)

    def test_a_typed_term_cannot_act_as_a_pattern(self):
        for risky in [".*", "(a+)+", "[a-z]+", "a|b", "\\\\w+", "(?i)abc"]:
            self.assertIsNone(ct.parse_term(risky), risky)

    def test_decomposed_accents_are_handled(self):
        decomposed = "atención"      # o + combining accent
        self.assertEqual(count("atención", decomposed), 1)


class CountTests(unittest.TestCase):
    DOCS = [
        {"doc_no": 1, "content": "Es agresivo. Muy agresivo con todos."},
        {"doc_no": 2, "content": "Nada que señalar."},
        {"doc_no": 5, "content": "Un caso agresivo y no quiere venir."},
    ]
    TERMS = [{"id": 10, "term": "agresiv*", "norm": "agresiv*"},
             {"id": 11, "term": "no quiere", "norm": "no quiere"},
             {"id": 12, "term": "ausente", "norm": "ausente"}]

    def test_texts_and_occurrences_are_counted_separately(self):
        r = ct.count_terms(self.TERMS, self.DOCS)
        by = {t["term"]: t for t in r["terms"]}
        self.assertEqual(r["total_documents"], 3)
        self.assertEqual(r["doc_numbers"], [1, 2, 5])
        self.assertEqual(by["agresiv*"]["documents"], 2)
        self.assertEqual(by["agresiv*"]["occurrences"], 3)
        self.assertEqual(by["agresiv*"]["per_doc"], {1: 2, 5: 1})
        self.assertEqual(by["no quiere"]["doc_numbers"], [5])
        self.assertEqual(by["ausente"]["documents"], 0)

    def test_counts_for_one_text(self):
        r = ct.count_terms(self.TERMS, self.DOCS)
        self.assertEqual(ct.counts_for_text(r, 1), [("agresiv*", 2)])
        self.assertEqual(ct.counts_for_text(r, 2), [])
        self.assertEqual(ct.counts_for_text(r, 5), [("agresiv*", 1), ("no quiere", 1)])

    def test_empty_inputs(self):
        self.assertEqual(ct.count_terms([], self.DOCS)["terms"], [])
        self.assertEqual(ct.count_terms(self.TERMS, [])["total_documents"], 0)

    def test_snippets_are_exact_pieces_of_the_text(self):
        text = "Hoy llegó tarde. " * 10 + "Se muestra agresivo en la reunión de equipo. " + "Luego se fue. " * 10
        snippets = ct.term_snippets("agresiv*", text, limit=2, width=40)
        self.assertEqual(len(snippets), 1)
        piece = snippets[0].strip("…")
        self.assertIn("agresivo", piece)
        self.assertIn(piece, " ".join(text.split()))

    def test_snippets_follow_accent_folding_without_shifting(self):
        text = "Él está ñoño y además muy ATENCIÓN a todo lo que pasa aquí."
        snippets = ct.term_snippets("atencion", text, limit=1, width=20)
        self.assertIn("ATENCIÓN", snippets[0])


class CsvTests(unittest.TestCase):
    def test_matrix_has_one_row_per_term_and_one_column_per_text(self):
        r = ct.count_terms(CountTests.TERMS, CountTests.DOCS)
        csv_text = ct.matrix_csv(r, lambda n: f"T-{n:03d}", ("Term", "Texts", "Times"))
        lines = csv_text.strip().split("\r\n")
        self.assertEqual(lines[0], "Term;Texts;Times;T-001;T-002;T-005")
        self.assertEqual(lines[1], "agresiv*;2;3;2;0;1")
        self.assertEqual(len(lines), 4)

    def test_cells_cannot_run_as_formulas(self):
        self.assertEqual(ct._safe_cell("=1+1"), "'=1+1")
        self.assertEqual(ct._safe_cell("normal"), "normal")


class StarterListTests(unittest.TestCase):
    def test_every_starter_term_is_valid_and_unique(self):
        norms = []
        for origin, term in ct.STARTER_TERMS:
            parsed = ct.parse_term(term)
            self.assertIsNotNone(parsed, term)
            norms.append(parsed["norm"])
            self.assertIn(origin, ("starter_es", "starter_eu"))
        self.assertEqual(len(norms), len(set(norms)))

    def test_starter_terms_find_what_they_should(self):
        self.assertEqual(count("manipul*", "Intenta manipular y es manipuladora."), 2)
        self.assertEqual(count("oldarkor*", "Oso oldarkorra da eta oldarkorrak ere badira."), 2)


if __name__ == "__main__":
    unittest.main()
