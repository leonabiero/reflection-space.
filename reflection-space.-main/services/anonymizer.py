import re


def anonymize(text: str) -> str:
    """
    Pattern-based anonymization applied to professional documentation
    before it is sent to the Claude API.
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

    # Dates: dd/mm/yyyy, dd-mm-yyyy, dd.mm.yyyy — run BEFORE phone numbers
    # so a date like 22-08-2026 isn't swallowed as a phone number first.
    text = re.sub(r"\b\d{1,2}[/.-]\d{1,2}[/.-]\d{2,4}\b", "[DATE]", text)

    # Phone numbers: require at least one separator-joined group so a
    # bare digit block (e.g. a case/ID number) is NOT matched here —
    # that's handled separately by the ID pattern below.
    text = re.sub(
        r"\b(?:\+\d{1,3}[\s.-]?)?\(?\d{2,4}\)?(?:[\s.-]\d{2,4}){1,3}\b",
        "[PHONE]",
        text,
    )

    # Long bare numeric identifiers (case refs, national IDs, etc.)
    text = re.sub(r"\b\d{5,}\b", "[ID]", text)

    return text