"""
Highlighted text (November 2026, EDE): the anonymised text with every
exact quote highlighted, one colour per type, the type also in words.
"""

import unittest

from services.highlight import (
    find_spans, highlight_html, legend_html, plain_text_html, quote_html, TEXT_ON_COLOUR,
    TYPE_STYLES,
)

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
        # 24 Nov 2026: solid colours with dark text (same in light mode,
        # dark mode and on paper) instead of the theme's own text colour.
        self.assertIn(f"color:{TEXT_ON_COLOUR}", html)
        self.assertNotIn("color:inherit", html)

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

    # The app's own dark theme (.streamlit/config.toml) and a white page
    # (light mode and the printed report): page background only, because
    # the text on a coloured background is always TEXT_ON_COLOUR.
    PAGES = {"dark": "#0f1223", "light": "#FFFFFF"}

    def test_bias_is_yellow_and_prejudice_is_red(self):
        for part in (0, 2):     # the background and the underline/border colour
            self.assertTrue(40 <= _hue(_rgb(TYPE_STYLES["bias"][part])) <= 60, "bias must be yellow")
            red_hue = _hue(_rgb(TYPE_STYLES["prejudice"][part]))
            self.assertTrue(red_hue <= 10 or red_hue >= 350, "prejudice must be red")
        self.assertNotEqual(TYPE_STYLES["bias"], TYPE_STYLES["prejudice"])

    def test_bias_background_is_a_bright_yellow_not_mustard(self):
        # 24 Nov 2026: on the dark screen the old see-through yellow looked
        # mustard/orange. A solid, bright, saturated yellow cannot.
        import colorsys
        r, g, b = (c / 255 for c in _rgb(TYPE_STYLES["bias"][0]))
        _h, s, v = colorsys.rgb_to_hsv(r, g, b)
        self.assertGreaterEqual(v, 0.9, "bias yellow must be bright")
        self.assertGreaterEqual(s, 0.8, "bias yellow must be saturated")

    def test_no_two_types_look_alike(self):
        for part in (0, 2):
            hues = {k: _hue(_rgb(v[part])) for k, v in TYPE_STYLES.items()}
            kinds = list(hues)
            for i, a in enumerate(kinds):
                for b in kinds[i + 1:]:
                    gap = abs(hues[a] - hues[b])
                    gap = min(gap, 360 - gap)
                    self.assertGreaterEqual(gap, 40, f"{a} and {b} are too close in colour")

    def test_backgrounds_are_solid(self):
        # Solid (not see-through) so the colour never mixes with the page.
        for kind, (background, _u, _c) in TYPE_STYLES.items():
            self.assertRegex(background, r"^#[0-9A-Fa-f]{6}$", kind)

    def test_text_stays_readable_in_light_and_dark_mode(self):
        for kind, (background, _u, _c) in TYPE_STYLES.items():
            self.assertGreaterEqual(_contrast(_rgb(background), _rgb(TEXT_ON_COLOUR)), 4.5, kind)
        # And every colour stands out from the app's dark background.
        for kind, (background, _u, _c) in TYPE_STYLES.items():
            self.assertGreaterEqual(_contrast(_rgb(background), _rgb(self.PAGES["dark"])), 4.5,
                                    f"{kind} on the dark screen")

    def test_label_after_a_highlight_has_its_colour_too(self):
        html = highlight_html(TEXT, [{"quote": "dócil", "type": "bias"}], LABELS)
        label_span = html[html.index("</mark>"):]
        self.assertIn(f"background:{TYPE_STYLES['bias'][0]}", label_span)

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


class ReportQuoteColourTests(unittest.TestCase):
    """24 November 2026 (product owner): the quote under each finding of
    the analysis report is coloured like its type badge, on screen and in
    the download."""

    def test_quote_in_its_type_colour(self):
        for kind, (background, underline, colour) in TYPE_STYLES.items():
            html = quote_html("dócil", kind)
            self.assertIn(f"background:{background}", html)
            self.assertIn(f"border-bottom:3px {underline} {colour}", html)
            self.assertIn("«<mark", html)
            self.assertIn("dócil</mark>»", html)

    def test_unknown_type_is_not_coloured_and_text_is_escaped(self):
        self.assertEqual(quote_html("<b>x</b>", None), "«&lt;b&gt;x&lt;/b&gt;»")
        self.assertNotIn("<b>", quote_html("<b>x</b>", "bias"))

    def test_download_colours_the_report_quote(self):
        from services.locales.es import LANG_ES
        from services.reflection_report_html import build_reflection_report_html
        report = {"summary": "Resumen", "items": [
            {"type": "prejudice", "area": 5, "quote": "dócil", "why": "Porque."}],
            "questions": ["¿Pregunta?"]}
        page = build_reflection_report_html(LANG_ES, "Español", "RS-TEST", "24/11/2026",
                                            report, [], TEXT, [])
        self.assertIn("<blockquote>" + quote_html("dócil", "prejudice") + "</blockquote>", page)

    def test_screen_uses_the_same_coloured_quote(self):
        from pathlib import Path
        page = (Path(__file__).resolve().parents[1] / "pages" / "reflection_space.py").read_text(encoding="utf-8")
        self.assertIn('quote_html(quote, item.get("type"))', page)


class PlainTextPreviewTests(unittest.TestCase):
    """24 November 2026: the first "view anonymised text" preview ran
    paragraphs together (it was shown as Markdown)."""

    def test_line_breaks_and_accents_are_kept_and_nothing_is_formatting(self):
        text = "CASO SINTÉTICO\nVisita domiciliaria\n\n# no es título\n* ni lista | ni tabla\nAñorga, ESKERRIK ASKO"
        html = plain_text_html(text)
        self.assertIn("CASO SINTÉTICO<br>Visita domiciliaria<br><br>", html)
        self.assertIn("# no es título<br>* ni lista | ni tabla", html)
        self.assertIn("Añorga, ESKERRIK ASKO", html)

    def test_text_is_escaped(self):
        html = plain_text_html("<script>x</script> & [PERSONA 1]")
        self.assertNotIn("<script>", html)
        self.assertIn("&lt;script&gt;", html)
        self.assertIn("[PERSONA 1]", html)

    def test_empty_text(self):
        self.assertIn("<div", plain_text_html(None))


if __name__ == "__main__":
    unittest.main()
