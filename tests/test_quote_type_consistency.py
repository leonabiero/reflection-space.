"""
One type per passage, everywhere (26 November 2026).

In the product owner's test, "aunque la familia no suele implicarse" was
"Estereotipo" in the analysis report but "Prejuicio" in the highlighted
text. The rule, applied in one place (services/quote_types.py):
  1. quotes that overlap in the text are the same passage;
  2. the analysis report's type wins;
  3. otherwise the type most lenses gave;
  4. on a tie, the first lens in card order.
All texts are fictional.
"""

import unittest
from pathlib import Path

from services.quote_types import agree_types
from services.analysis_report import all_quotes
from services.highlight import find_spans, highlight_html

ROOT = Path(__file__).resolve().parent.parent

TEXT = ("Javier dice que está esperando una respuesta, pero no le creo, porque suele poner "
        "excusas. Su hermana opina que necesita más apoyo, aunque la familia no suele implicarse.")
FAMILY = "aunque la familia no suele implicarse"
EXCUSES = "porque suele poner excusas"


def _types(evidence):
    return [e["type"] for e in evidence]


class AgreeTypesTests(unittest.TestCase):
    def test_the_report_type_wins_everywhere(self):
        lenses = [[{"quote": FAMILY, "type": "prejudice"}], [{"quote": FAMILY, "type": "prejudice"}]]
        report = {"items": [{"quote": FAMILY, "type": "stereotype", "why": "x"}]}
        new_lenses, new_report = agree_types(TEXT, lenses, report)
        self.assertEqual(_types(new_lenses[0]), ["stereotype"])
        self.assertEqual(_types(new_lenses[1]), ["stereotype"])
        self.assertEqual(new_report["items"][0]["type"], "stereotype")

    def test_overlapping_quotes_are_the_same_passage(self):
        lenses = [[{"quote": "la familia no suele implicarse", "type": "prejudice"}]]
        report = {"items": [{"quote": FAMILY, "type": "stereotype"}]}
        new_lenses, _ = agree_types(TEXT, lenses, report)
        self.assertEqual(_types(new_lenses[0]), ["stereotype"])

    def test_different_passages_keep_their_own_types(self):
        lenses = [[{"quote": FAMILY, "type": "prejudice"}, {"quote": EXCUSES, "type": "bias"}]]
        report = {"items": [{"quote": FAMILY, "type": "stereotype"}]}
        new_lenses, _ = agree_types(TEXT, lenses, report)
        self.assertEqual(_types(new_lenses[0]), ["stereotype", "bias"])

    def test_without_the_report_the_majority_of_lenses_wins(self):
        lenses = [[{"quote": FAMILY, "type": "bias"}],
                  [{"quote": FAMILY, "type": "prejudice"}],
                  [{"quote": FAMILY, "type": "prejudice"}]]
        new_lenses, _ = agree_types(TEXT, lenses, None)
        self.assertEqual([_types(e) for e in new_lenses], [["prejudice"]] * 3)

    def test_a_tie_goes_to_the_first_lens_in_card_order(self):
        lenses = [[{"quote": FAMILY, "type": "loaded_label"}], [{"quote": FAMILY, "type": "bias"}]]
        new_lenses, _ = agree_types(TEXT, lenses, {"items": []})
        self.assertEqual([_types(e) for e in new_lenses], [["loaded_label"]] * 2)
        reversed_lenses, _ = agree_types(TEXT, list(reversed(lenses)), None)
        self.assertEqual([_types(e) for e in reversed_lenses], [["bias"]] * 2)

    def test_the_inputs_are_never_changed(self):
        lenses = [[{"quote": FAMILY, "type": "prejudice"}]]
        report = {"items": [{"quote": FAMILY, "type": "stereotype"}]}
        agree_types(TEXT, lenses, report)
        self.assertEqual(lenses[0][0]["type"], "prejudice")

    def test_quotes_not_in_the_text_and_untyped_quotes_are_left_alone(self):
        lenses = [[{"quote": "not in the text at all", "type": "bias"},
                   {"quote": FAMILY, "type": None}]]
        report = {"items": [{"quote": FAMILY, "type": "stereotype"}]}
        new_lenses, _ = agree_types(TEXT, lenses, report)
        self.assertEqual(_types(new_lenses[0]), ["bias", None])

    def test_no_report_and_no_lenses(self):
        self.assertEqual(agree_types(TEXT, [], None), ([], None))


class AllViewsAgreeTests(unittest.TestCase):
    """The highlighted text shows the same type as the report."""

    LENSES = [{"evidence": [{"quote": FAMILY, "type": "prejudice"}]}]
    REPORT = {"items": [{"quote": FAMILY, "type": "stereotype"}]}

    def test_highlighted_text_uses_the_report_type(self):
        quotes = all_quotes(self.LENSES, self.REPORT, text=TEXT)
        spans = find_spans(TEXT, quotes)
        self.assertEqual([kind for _s, _e, kind in spans], ["stereotype"])
        html = highlight_html(TEXT, quotes, {"stereotype": "Estereotipo", "prejudice": "Prejuicio"})
        self.assertIn("[Estereotipo]", html)
        self.assertNotIn("[Prejuicio]", html)

    def test_without_text_all_quotes_behaves_as_before(self):
        quotes = all_quotes(self.LENSES, self.REPORT)
        self.assertEqual(quotes, [{"quote": FAMILY, "type": "prejudice"},
                                  {"quote": FAMILY, "type": "stereotype"}])


class OnePlaceTests(unittest.TestCase):
    """Every view on the screen and in the download reads the agreed types."""

    def setUp(self):
        self.page = (ROOT / "pages" / "reflection_space.py").read_text(encoding="utf-8")
        self.session = (ROOT / "rdi" / "reflection_session.py").read_text(encoding="utf-8")

    def test_page_uses_the_agreed_types_for_every_view(self):
        self.assertIn("session.agreed_evidence()", self.page)
        # Cards.
        self.assertIn("agreed=_agreed(session)[0].get(opportunity.trigger)", self.page)
        # Report on screen and in the download.
        self.assertIn("report = agreed_report or report", self.page)
        # Lenses in the download.
        self.assertIn('"evidence": agreed_by_trigger.get(opportunity.trigger, opportunity.evidence)', self.page)
        # Highlighted text.
        self.assertIn("by_trigger, report = _agreed(session)", self.page)

    def test_session_uses_the_one_rule(self):
        self.assertIn("from services.quote_types import agree_types", self.session)
        self.assertIn("text=getattr(self, \"safe_text\", \"\") or \"\"", self.session)


if __name__ == "__main__":
    unittest.main()
