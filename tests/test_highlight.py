"""
Highlighted text (November 2026, EDE): the anonymised text with every
exact quote highlighted, one colour per type, the type also in words.
"""

import unittest

from services.highlight import find_spans, highlight_html, legend_html, TYPE_STYLES

LABELS = {"bias": "Sesgo", "stereotype": "Estereotipo", "prejudice": "Prejuicio",
          "loaded_label": "Etiqueta cargada"}
TEXT = "[PERSONA 1] es dócil y agradecida.\nSu [DIRECCIÓN] es <segura> & limpia."


class HighlightTests(unittest.TestCase):
    def test_only_exact_quotes_are_highlighted(self):
        spans = find_spans(TEXT, [
            {"quote": "dócil", "type": "loaded_label"},
            {"quote": "agradecida", "type": "bias"},
            {"quote": "no está en el texto", "type": "prejudice"},
            {"quote": "dócil", "type": None},          # no type: not coloured
        ])
        self.assertEqual([TEXT[s:e] for s, e, _ in spans], ["dócil", "agradecida"])

    def test_translated_placeholders_inside_quotes_work(self):
        spans = find_spans(TEXT, [{"quote": "[PERSONA 1] es dócil", "type": "stereotype"}])
        self.assertEqual(len(spans), 1)
        spans = find_spans(TEXT, [{"quote": "Su [DIRECCIÓN] es <segura>", "type": "bias"}])
        self.assertEqual(len(spans), 1)

    def test_overlaps_longer_wins(self):
        spans = find_spans(TEXT, [
            {"quote": "dócil", "type": "loaded_label"},
            {"quote": "es dócil y agradecida", "type": "stereotype"},
        ])
        self.assertEqual(len(spans), 1)
        self.assertEqual(spans[0][2], "stereotype")

    def test_html_is_escaped_and_type_is_in_words(self):
        html = highlight_html(TEXT, [{"quote": "dócil", "type": "loaded_label"}], LABELS)
        self.assertIn("&lt;segura&gt; &amp; limpia", html)
        self.assertNotIn("<segura>", html)
        self.assertIn("[Etiqueta cargada]", html)
        self.assertIn("<br>", html)
        self.assertIn(TYPE_STYLES["loaded_label"][2], html)
        # Text keeps the theme's colour (readable in light and dark mode).
        self.assertIn("color:inherit", html)

    def test_every_type_has_its_own_colour_and_underline(self):
        self.assertEqual(len({s[0] for s in TYPE_STYLES.values()}), 4)
        self.assertEqual(len({s[1] for s in TYPE_STYLES.values()}), 4)

    def test_legend_names_all_four_types(self):
        legend = legend_html(LABELS, "Leyenda:")
        for label in LABELS.values():
            self.assertIn(f"[{label}]", legend)


if __name__ == "__main__":
    unittest.main()
