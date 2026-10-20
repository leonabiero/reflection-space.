"""Pure-logic tests for the corpus engine (no database, no AI)."""
import random
import unittest

from services import corpus_engine as ce


SAMPLE = ("Visita domiciliaria del martes. La usuaria, madre de dos menores, abrió la puerta pero no quiso sentarse. "
          "Contestó a todas mis preguntas con monosílabos.\n\nClaramente no está motivada para trabajar con nosotros. "
          "Creo que no entiende la importancia de aprender castellano. Próxima visita en dos semanas.")


class SplitTests(unittest.TestCase):
    def test_every_passage_is_an_exact_piece_of_the_text(self):
        for text in (SAMPLE, "Kaixo. " * 200, "x" * 3000 + " fin de la frase larga sin punto " * 40,
                     "Línea uno de prueba más larga.\nLínea dos de prueba más larga.\n\n\nLínea tres de prueba."):
            passages = ce.split_passages(text)
            self.assertTrue(passages)
            for p in passages:
                self.assertIn(p, text)
                self.assertEqual(p, p.strip())
                self.assertLessEqual(len(p), ce.MAX_PASSAGE_CHARS)

    def test_sentences_are_grouped_to_about_the_target_length(self):
        passages = ce.split_passages(SAMPLE + "\n\n" + SAMPLE)
        self.assertGreaterEqual(len(passages), 2)
        self.assertTrue(all(len(p) <= ce.TARGET_PASSAGE_CHARS + 120 for p in passages))

    def test_tiny_and_empty_input(self):
        self.assertEqual(ce.split_passages(""), [])
        self.assertEqual(ce.split_passages(None), [])
        self.assertEqual(ce.split_passages("Ok."), [])
        self.assertEqual(ce.split_passages("   \n\n  "), [])

    def test_per_document_cap(self):
        text = "\n".join(f"Esta es la frase número {i} de un documento muy largo." for i in range(2000))
        self.assertEqual(len(ce.split_passages(text)), ce.MAX_PASSAGES_PER_DOCUMENT)

    def test_basque_text_splits_too(self):
        text = "Etxeko bisita egin nuen asteazkenean. Erabiltzailea ez zen eseri. Galdera guztiei hitz bakarrarekin erantzun zien."
        self.assertTrue(ce.split_passages(text))

    def test_never_cuts_mid_word_when_a_space_is_available(self):
        text = ("palabra " * 400).strip()
        for p in ce.split_passages(text):
            self.assertTrue(all(w == "palabra" for w in p.split()))

    def test_labels(self):
        self.assertEqual(ce.document_label(3), "T-003")
        self.assertEqual(ce.document_label(70), "T-070")
        self.assertEqual(ce.document_label(1234), "T-1234")


def _m(i, doc, no=None):
    return {"id": i, "document_id": doc, "doc_no": no if no is not None else doc}


class CountTests(unittest.TestCase):
    def test_passages_and_documents_are_counted_separately(self):
        counts = ce.summarise_passages([_m(1, 7), _m(2, 7), _m(3, 9)], 70)
        self.assertEqual((counts["passages"], counts["documents"], counts["total_documents"]), (3, 2, 70))
        self.assertEqual(counts["doc_numbers"], [7, 9])
        self.assertAlmostEqual(counts["share"], 2 / 70)

    def test_empty_collection_does_not_divide_by_zero(self):
        counts = ce.summarise_passages([], 0)
        self.assertEqual(counts["share"], 0.0)

    def test_total_is_never_smaller_than_the_documents_seen(self):
        self.assertEqual(ce.summarise_passages([_m(1, 1), _m(2, 2)], 1)["total_documents"], 2)

    def test_one_document_repeating_itself_never_makes_a_pattern(self):
        passages = [_m(i, 1) for i in range(6)]
        self.assertEqual(ce.select_corpus_candidates(passages, [[0, 1, 2, 3, 4, 5]], 70), [])

    def test_minimums_order_and_cap(self):
        passages = [_m(0, 1), _m(1, 2), _m(2, 3), _m(3, 4), _m(4, 4), _m(5, 5), _m(6, 6), _m(7, 7), _m(8, 8)]
        clusters = [[0, 1, 2], [3, 4], [5, 6, 7, 8]]
        result = ce.select_corpus_candidates(passages, clusters, 10, min_passages=3, min_documents=3)
        self.assertEqual([c["indices"] for c in result], [[5, 6, 7, 8], [0, 1, 2]])
        self.assertEqual(len(ce.select_corpus_candidates(passages, clusters, 10, 3, 3, max_patterns=1)), 1)


class LevelTests(unittest.TestCase):
    def test_levels_are_ordered(self):
        lv = ce.CORPUS_SIMILARITY_LEVELS
        self.assertLess(lv["broad"], lv["balanced"])
        self.assertLess(lv["balanced"], lv["strict"])
        self.assertIn(ce.DEFAULT_CORPUS_SIMILARITY_LEVEL, lv)


if __name__ == "__main__":
    unittest.main()
