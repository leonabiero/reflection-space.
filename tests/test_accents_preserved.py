"""
Accents are never stripped (24 November 2026).

After a Word document was uploaded, the first "view anonymised text"
preview showed "SINTETICO" instead of "SINTÉTICO" and ran the paragraphs
together. These tests follow Spanish and Basque text with capitals and
accents through the whole chain -- Word document -> cleaning ->
anonymiser -> preview -- and check that every accent and every paragraph
break survives. They also make sure no code that removes accents is ever
added.
"""

import io
import re
import unicodedata
import unittest
from pathlib import Path

from services.anonymizer import anonymize
from services.document_import import extract_text, clean_text
from services.highlight import highlight_html, plain_text_html

ROOT = Path(__file__).resolve().parents[1]

PARAGRAPHS = [
    "CASO SINTÉTICO",
    "Visita domiciliaria — Información general",
    "La situación económica es difícil; la vivienda está en mal estado.",
    "EUSKADIKO GIZARTE ZERBITZUAK — AÑORGAKO EGOERA",
    "Ama oso kezkatuta dago; etxean giro lasaia dago.",
    "ÚLTIMA VALORACIÓN: AÚN SIN DECISIÓN. ¿Qué opina la niña? ¡Ñandú!",
]
ACCENTED_WORDS = ["SINTÉTICO", "Información", "situación", "económica", "difícil",
                  "está", "AÑORGAKO", "ÚLTIMA", "VALORACIÓN", "AÚN", "DECISIÓN",
                  "¿Qué", "¡Ñandú!"]


def _docx_bytes(paragraphs):
    import docx
    document = docx.Document()
    for i, text in enumerate(paragraphs):
        if i == 0:
            document.add_heading(text, level=1)
        else:
            document.add_paragraph(text)
    buffer = io.BytesIO()
    document.save(buffer)
    return buffer.getvalue()


class AccentChainTests(unittest.TestCase):

    def test_word_document_keeps_accents_and_paragraphs(self):
        text = extract_text("caso.docx", _docx_bytes(PARAGRAPHS))
        for word in ACCENTED_WORDS:
            self.assertIn(word, text)
        self.assertEqual(text.split("\n"), PARAGRAPHS)

    def test_decomposed_accents_are_joined_not_dropped(self):
        # "É" written as "E" + a separate accent mark (some programs do this).
        decomposed = unicodedata.normalize("NFD", "CASO SINTÉTICO")
        self.assertNotEqual(decomposed, "CASO SINTÉTICO")
        self.assertEqual(clean_text(decomposed), "CASO SINTÉTICO")

    def test_anonymiser_keeps_accents_in_every_language(self):
        source = "\n".join(PARAGRAPHS)
        for lang in ("Español", "Euskera", "English"):
            safe = anonymize(source, lang)
            for word in ACCENTED_WORDS:
                self.assertIn(word, safe, f"{word!r} changed ({lang})")
            self.assertEqual(safe.count("\n"), source.count("\n"), lang)

    def test_previews_keep_accents_and_paragraphs(self):
        safe = anonymize(extract_text("caso.docx", _docx_bytes(PARAGRAPHS)))
        for html in (plain_text_html(safe), highlight_html(safe, [], {})):
            for word in ACCENTED_WORDS:
                self.assertIn(word, html)
            self.assertIn("CASO SINTÉTICO<br>", html)
            self.assertEqual(html.count("<br>"), len(PARAGRAPHS) - 1)

    def test_capitals_with_a_name_keep_accents(self):
        safe = anonymize("INFORME SINTÉTICO DE LUCÍA GARCÍA: SITUACIÓN DIFÍCIL")
        self.assertIn("SINTÉTICO", safe)
        self.assertIn("SITUACIÓN DIFÍCIL", safe)
        self.assertNotIn("LUCÍA", safe)
        self.assertNotIn("GARCÍA", safe)


class NoAccentStrippingCodeTests(unittest.TestCase):
    """No program file may contain the usual ways of removing accents."""

    FORBIDDEN = (
        r"normalize\(\s*[\"']NFK?D[\"']",
        r"\bunidecode\b",
        r"encode\(\s*[\"']ascii[\"']\s*,\s*[\"']ignore[\"']",
        r"\bcombining\(",
    )

    def test_no_accent_stripping_anywhere(self):
        for folder in ("services", "rdi", "pages", "navigation"):
            for path in (ROOT / folder).rglob("*.py"):
                source = path.read_text(encoding="utf-8")
                for pattern in self.FORBIDDEN:
                    self.assertIsNone(re.search(pattern, source), f"{pattern} in {path.name}")
        for path in (ROOT / "app.py", ROOT / "demo_app.py"):
            if path.exists():
                source = path.read_text(encoding="utf-8")
                for pattern in self.FORBIDDEN:
                    self.assertIsNone(re.search(pattern, source), f"{pattern} in {path.name}")


if __name__ == "__main__":
    unittest.main()
