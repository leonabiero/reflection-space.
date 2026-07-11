import re


def anonymize(text: str) -> str:
    """
    Pattern-based anonymization applied to professional documentation
    before it is sent to the Claude API.

    This is NOT full named-entity recognition. It is a stronger version
    of prototype-level pattern replacement, covering the categories most
    likely to appear in social work case notes:
      - Person names (Firstname Lastname, and Title + Name)
      - Email addresses
      - Phone numbers
      - Long numeric identifiers (case numbers, national IDs, etc.)
      - Dates (which can indirectly identify someone, e.g. DOB)

    Per NFR-020 / Section 18.2 of the Technical Operations Documentation,
    production-grade anonymization should eventually add named entity
    recognition and location detection, plus manual review for
    high-risk documents. This function is the interim, dependency-light
    step up from the original MVP version.
    """

    if not text:
        return text

    # Titles + name, e.g. "Mr. John Smith", "Dr Ana Garcia"
    text = re.sub(
        r"\b(Mr|Mrs|Ms|Miss|Dr|Sr|Sra|Srta)\.?\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?\b",
        "[PERSON]",
        text,
    )

    # Two-word capitalised names, e.g. "John Smith"
    text = re.sub(r"\b[A-Z][a-z]+ [A-Z][a-z]+\b", "[PERSON]", text)

    # Email addresses
    text = re.sub(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b", "[EMAIL]", text)

    # Phone numbers (international/local, spaced or dashed, 7+ digits)
    text = re.sub(
        r"\b(?:\+?\d{1,3}[\s.-]?)?(?:\(?\d{2,4}\)?[\s.-]?){2,4}\d{2,4}\b",
        lambda m: "[PHONE]" if sum(c.isdigit() for c in m.group()) >= 7 else m.group(),
        text,
    )

    # Long numeric identifiers (case refs, national IDs, etc.)
    text = re.sub(r"\b\d{5,}\b", "[ID]", text)

    # Dates: dd/mm/yyyy, dd-mm-yyyy, dd.mm.yyyy
    text = re.sub(r"\b\d{1,2}[/.-]\d{1,2}[/.-]\d{2,4}\b", "[DATE]", text)

    return text