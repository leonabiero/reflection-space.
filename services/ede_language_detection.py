"""Document-language detection for the EDE workflow (Spanish / Basque / English).

Deliberately a small, transparent word-frequency check instead of a new
third-party library (adding a dependency needs approval, and a short list
of very common function words is enough to tell these three languages
apart). It runs LOCALLY: the text never leaves the server for this step.

It is a heuristic. Very short texts, texts full of names, or heavily
mixed texts can be misjudged, which is why the professional can always
override the explanation language in the interface.
"""

import re
import unicodedata

_WORDS = {
    "es": {
        "el", "la", "los", "las", "de", "del", "que", "y", "en", "un", "una", "con", "por",
        "para", "no", "se", "su", "sus", "es", "al", "como", "pero", "más", "mas", "ha",
        "han", "fue", "son", "está", "esta", "este", "lo", "le", "les", "muy", "también",
        "sin", "sobre", "entre", "cuando", "donde", "porque", "tiene", "tienen", "hay",
        "ser", "estar", "hemos", "he", "me", "mi", "ya", "si", "sí", "desde", "hasta",
    },
    "eu": {
        "eta", "da", "dira", "du", "dute", "ez", "bat", "hori", "hau", "izan", "baina",
        "zen", "zuen", "ziren", "egin", "gara", "nire", "bere", "ere", "edo", "orain",
        "gero", "behar", "dago", "daude", "buruz", "arte", "kontra", "zuen", "dela",
        "zela", "diren", "duen", "dituen", "izango", "oso", "gabe", "batean", "hitz",
        "egun", "beti", "inoiz", "nola", "zer", "nor", "non", "noiz", "zergatik",
        "bezala", "ondoren", "aurretik", "horrek", "honek", "bati", "batek", "guk",
    },
    "en": {
        "the", "and", "of", "to", "in", "is", "was", "that", "for", "with", "not", "he",
        "she", "they", "his", "her", "their", "has", "have", "had", "are", "were", "be",
        "this", "it", "as", "on", "at", "by", "from", "but", "which", "who", "when",
        "there", "been", "also", "about", "after", "before", "said", "does", "did",
    },
}

# Words that belong to more than one list must not count for either.
_AMBIGUOUS = set.intersection(_WORDS["es"], _WORDS["en"]) | set.intersection(_WORDS["es"], _WORDS["eu"]) \
    | set.intersection(_WORDS["eu"], _WORDS["en"])
for _code in _WORDS:
    _WORDS[_code] = _WORDS[_code] - _AMBIGUOUS

_TOKEN_RE = re.compile(r"[^\W\d_]+", re.UNICODE)

# A language is "dominant" when it holds at least this share of the
# recognised function words; otherwise the text is reported as mixed.
DOMINANCE_THRESHOLD = 0.70
# Below this many recognised words there is too little evidence to decide.
MIN_RECOGNISED_WORDS = 5


def _fold(token: str) -> str:
    return unicodedata.normalize("NFC", token.lower())


def detect_language(text: str) -> dict:
    """Return {"code": "es"|"eu"|"en"|"mixed"|"unknown",
               "dominant": "es"|"eu"|"en"|None,
               "shares": {"es": float, "eu": float, "en": float}}.

    "dominant" is the most frequent language even when the text is
    mixed, so callers can still pick a sensible default."""
    counts = {"es": 0, "eu": 0, "en": 0}
    for raw in _TOKEN_RE.findall(text or ""):
        token = _fold(raw)
        for code, words in _WORDS.items():
            if token in words:
                counts[code] += 1
    total = sum(counts.values())
    if total < MIN_RECOGNISED_WORDS:
        return {"code": "unknown", "dominant": None, "shares": {k: 0.0 for k in counts}}
    shares = {k: counts[k] / total for k in counts}
    dominant = max(shares, key=shares.get)
    code = dominant if shares[dominant] >= DOMINANCE_THRESHOLD else "mixed"
    return {"code": code, "dominant": dominant, "shares": shares}
