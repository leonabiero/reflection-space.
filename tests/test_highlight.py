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


def _rgb(hex_colour):
    h = hex_colour.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def _rgba(css):
    parts = css[css.index("(") + 1:css.index(")")].split(",")
    return tuple(float(p) for p in parts[:3]), float(parts[3])


def _luminance(rgb):
    def channel(c):
        c = c / 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (channel(c) for c in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _contrast(a, b):
    la, lb = sorted((_luminance(a), _luminance(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def _hue(rgb):
    import colorsys
    return colorsys.rgb_to_hsv(*(c / 255 for c in rgb))[0] * 360


class ColourTests(unittest.TestCase):
    """24 November 2026: "Sesgo" and "Prejuicio" looked too alike."""

    # Streamlit's light and dark themes: (page background, text colour).
    THEMES = {"light": ("#FFFFFF", "#31333F"), "dark": ("#0E1117", "#FAFAFA")}

    def test_bias_is_yellow_and_prejudice_is_red(self):
        self.assertTrue(40 <= _hue(_rgb(TYPE_STYLES["bias"][2])) <= 60, "bias must be yellow")
        red_hue = _hue(_rgb(TYPE_STYLES["prejudice"][2]))
        self.assertTrue(red_hue <= 10 or red_hue >= 350, "prejudice must be red")
        self.assertNotEqual(TYPE_STYLES["bias"], TYPE_STYLES["prejudice"])

    def test_no_two_types_look_alike(self):
        hues = {k: _hue(_rgb(v[2])) for k, v in TYPE_STYLES.items()}
        kinds = list(hues)
        for i, a in enumerate(kinds):
            for b in kinds[i + 1:]:
                gap = abs(hues[a] - hues[b])
                gap = min(gap, 360 - gap)
                self.assertGreaterEqual(gap, 40, f"{a} and {b} are too close in colour")

    def test_text_stays_readable_in_light_and_dark_mode(self):
        for kind, (background, _u, _c) in TYPE_STYLES.items():
            colour, alpha = _rgba(background)
            for theme, (page, text) in self.THEMES.items():
                page_rgb = _rgb(page)
                blended = tuple(alpha * c + (1 - alpha) * p for c, p in zip(colour, page_rgb))
                self.assertGreaterEqual(_contrast(blended, _rgb(text)), 4.5, f"{kind} in {theme} mode")

    def test_legend_and_badges_use_the_one_colour_list(self):
        from services.highlight import type_badge_html
        legend = legend_html(LABELS, "Leyenda:")
        for kind, (background, underline, colour) in TYPE_STYLES.items():
            self.assertIn(background, legend)
            self.assertIn(colour, legend)
            badge = type_badge_html(kind, LABELS[kind])
            self.assertIn(background, badge)
            self.assertIn(LABELS[kind], badge)
        self.assertEqual(type_badge_html(None, "x"), "[x]")
        self.assertEqual(type_badge_html("bias", "<b>"), type_badge_html("bias", "<b>").replace("<b>", "&lt;b&gt;"))

    def test_colours_are_defined_in_one_place_only(self):
        from pathlib import Path
        root = Path(__file__).resolve().parents[1]
        for rel in (("pages", "reflection_space.py"), ("services", "reflection_report_html.py"),
                    ("services", "findings_ui.py")):
            source = root.joinpath(*rel).read_text(encoding="utf-8")
            for _bg, _u, colour in TYPE_STYLES.values():
                self.assertNotIn(colour, source, f"{colour} repeated in {rel[-1]}")
            self.assertIn("type_badge_html", source)

    def test_type_names_stay_translated(self):
        from services.locales.es import LANG_ES
        from services.locales.eu import LANG_EU
        from services.locales.en import LANG_EN
        self.assertEqual(LANG_ES["evidence_type_labels"]["bias"], "Sesgo")
        self.assertEqual(LANG_ES["evidence_type_labels"]["prejudice"], "Prejuicio")
        for texts in (LANG_ES, LANG_EU, LANG_EN):
            self.assertEqual(set(texts["evidence_type_labels"]), set(TYPE_STYLES))


if __name__ == "__main__":
    unittest.main()
