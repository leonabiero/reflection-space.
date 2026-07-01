import re

def anonymize(text: str):

    # Very simple placeholder anonymization for MVP
    text = re.sub(r"\b[A-Z][a-z]+ [A-Z][a-z]+\b", "[PERSON]", text)
    text = re.sub(r"\b\d{5,}\b", "[ID]", text)

    return text