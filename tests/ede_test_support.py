"""Shared helpers for the EDE workflow tests (all text here is SYNTHETIC)."""

import json
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from services.ede_framework import DIMENSIONS

# Synthetic follow-up reports. No real people or cases.
ES_DOC = (
    "Seguimiento mensual del mes de marzo.\n"
    "La usuaria faltó a dos citas programadas durante el mes. "
    "Parece que no está comprometida con el proceso.\n"
    "Es una persona conflictiva con el resto de residentes. "
    "Su hermana comenta que le gustaría trabajar en cocina, pero no se ha explorado esa opción."
)
EU_DOC = (
    "Hileroko jarraipena eta egoeraren berrikuspena.\n"
    "Egoitzako bizilagunekin harreman zailak ditu eta ez du parte hartzen jarduera kolektiboetan.\n"
    "Pertsonak esan zuen sukaldean lan egin nahi duela, baina ez da horretaz hitz egin oraindik."
)
MIXED_DOC = (
    "Seguimiento del mes y comentarios del equipo sobre la convivencia en la vivienda.\n"
    "Egoitzako bizilagunekin harreman zailak ditu eta ez du parte hartzen jarduera kolektiboetan, "
    "baina ere esan zuen oso gustura dagoela eta behar duela denbora gehiago.\n"
    "La persona dijo que quiere cambiar de habitación porque no duerme bien."
)

ES_QUOTE = "Parece que no está comprometida con el proceso"
ES_QUOTE_2 = "Es una persona conflictiva con el resto de residentes"
EU_QUOTE = "Egoitzako bizilagunekin harreman zailak ditu"


def make_finding(dimension="observation_vs_interpretation", quote=ES_QUOTE, **overrides):
    finding = {
        "dimension": dimension,
        "source_evidence": {"type": "direct_quote", "quote": quote, "not_documented": None},
        "observation": "El texto presenta como un hecho lo que parece una interpretación profesional.",
        "why_it_matters": "La redacción puede orientar las lecturas posteriores del caso.",
        "alternative_perspective": "Podría reflejar una impresión provisional y no una conclusión.",
        "reflection_questions": ["¿Qué hechos concretos sostienen esta lectura?"],
        "limitations": ["Un solo texto no muestra qué se sabe en otros documentos."],
    }
    finding.update(overrides)
    return finding


def make_absence(dimension="persons_voice", **overrides):
    finding = make_finding(dimension)
    finding["source_evidence"] = {
        "type": "absence_in_document", "quote": None,
        "not_documented": "No se recoge con sus propias palabras qué desea la persona.",
    }
    finding.update(overrides)
    return finding


def reply(findings_or_text, stop_reason="end_turn"):
    """A fake Anthropic message holding the given findings (list) or raw text."""
    text = findings_or_text if isinstance(findings_or_text, str) else json.dumps(
        {"findings": findings_or_text}, ensure_ascii=False)
    return SimpleNamespace(
        content=[SimpleNamespace(type="text", text=text)],
        stop_reason=stop_reason, usage=None,
    )


def fake_client(*responses):
    """A stand-in for the Anthropic client: returns/raises each item in turn."""
    client = MagicMock()
    client.messages.create.side_effect = list(responses)
    return client


class ProviderPatches:
    """Context manager: fake provider + key + no database side effects."""

    def __init__(self, *responses, api_key="test-key"):
        self.client = fake_client(*responses)
        self.api_key = api_key
        self.log_error = MagicMock(return_value=(1, 42))
        self.usage = MagicMock()

    def __enter__(self):
        self._patches = [
            patch("services.reflection_service.client", self.client),
            patch("config.ANTHROPIC_API_KEY", self.api_key),
            patch("services.ede_analysis.log_error", self.log_error),
            patch("services.reflection_service._record_claude_usage", self.usage),
            patch("time.sleep", lambda *_: None),
        ]
        for p in self._patches:
            p.start()
        return self

    def __exit__(self, *exc):
        for p in self._patches:
            p.stop()


ANALYSE_KWARGS = dict(
    programme="social_accommodation_bizkaia", document_type="follow_up_report",
    actor_name="Test Worker", actor_role="Social Worker",
)

ALL_DIMENSIONS = list(DIMENSIONS)
