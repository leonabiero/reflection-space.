"""Privacy boundary for text that may leave Reflection Space.

This module intentionally uses a layered, deterministic approach rather than
claiming that a handful of regular expressions can make arbitrary social-work
narratives anonymous. It removes common direct identifiers, contextual
identifiers, and conservative proper-name phrases before text reaches Claude,
Gemini embeddings, or Qdrant.

The final layer is deliberately conservative in the privacy direction: a
proper-looking name may be redacted even when it turns out to be a place or
organisation. That is preferable to preserving a likely client's name.
Indirect identification (for example, a unique combination of age, location,
school and rare event) cannot be reliably solved by pattern matching; callers
must therefore treat anonymization as risk reduction, not a formal guarantee
of anonymity.

October 2026 -- Spanish / Basque hardening
------------------------------------------
The app is used in Bilbao and most notes are written in Spanish or Basque,
but the original rules only understood English cue words ("client", "lives
in", "address", ...). In the System Administration "Anonymization Test" a
Spanish note such as "La madre, Lucía, vive en Barakaldo. DNI 12345678Z"
came back with the first name, the town and the DNI untouched. This version
adds, without removing any earlier rule:

* Spanish identity documents (DNI / NIE), IBAN bank accounts and Spanish /
  Basque identifier labels (DNI, NIE, NIF, pasaporte, expediente, ...).
* Spanish and Basque relationship / introduction cues ("la usuaria",
  "su hijo", "la madre,", "se llama", "ama", "izena", ...).
* Spanish and Basque address, organisation and location cues ("calle",
  "avenida", "kalea", "colegio", "ikastola", "vive en", "reside en", ...).
* Spanish and Basque courtesy titles (Don, Doña, Sr., Sra., Jn., And.).
* Single first names written in the middle of a sentence (Spanish, Basque
  and English normally only capitalise names and places there).
* A list of common Spanish and Basque first names, so a lone first name at
  the start of a sentence ("Mikel dice que ...") is also caught.
* Consistent redaction: once a name has been recognised anywhere in the
  text, every other appearance of it is redacted too -- including at the
  start of a sentence, where capitalisation alone proves nothing.
* Common public bodies ("Servicios Sociales", "Ayuntamiento", "Osakidetza",
  "Lanbide", ...) are no longer mistaken for people: they are not personal
  identifiers and the reflection needs that context.

The function is idempotent: anonymizing already-anonymized text changes
nothing (services/knowledge_assistant.py relies on this, because it
re-anonymizes excerpts that were already anonymized at index time).
"""

import re

_UPPER = "A-ZÀ-ÖØ-Þ"
_LOWER = "a-zß-öø-ÿ"
_NAME_TOKEN = r"[A-ZÀ-ÖØ-Þ][A-Za-zÀ-ÖØ-öø-ÿ]*(?:['’\-][A-ZÀ-ÖØ-Þ][A-Za-zÀ-ÖØ-öø-ÿ]*)*"
_NAME_SEQUENCE_RE = re.compile(rf"\b{_NAME_TOKEN}(?:\s+{_NAME_TOKEN}){{1,3}}\b")
_SINGLE_COMPLEX_NAME_RE = re.compile(rf"\b{_NAME_TOKEN}\b")
# A single capitalised word with at least one lower-case letter after the
# first character (so acronyms such as DNI / EDE and our own [PERSON]-style
# placeholders are never treated as names).
_SINGLE_CAPITALISED_RE = re.compile(rf"(?<![\w\[])[{_UPPER}][{_LOWER}][\w'’]*(?:-[{_UPPER}][\w'’]*)*(?![\w\]])")

_PROTECTED_PROPER_PHRASES = {
    "Social Worker",
    "Programme Manager",
    "System Administrator",
    "System Administration",
    "Social Work Report",
    "Intervention Plan",
    "Reflection Space",
    "Knowledge Assistant",
}

# Words that are capitalised mid-sentence but are NOT personal identifiers:
# our own product / organisation names, common public bodies in Bizkaia and
# the Basque Country, and English calendar / language words (English
# capitalises these). Compared in lower case.
_SAFE_CAPITALISED_WORDS = {
    # Product / organisation / tooling
    "reflection", "space", "knowledge", "assistant", "ede", "fundazioa",
    "fundación", "claude", "gemini", "qdrant", "anthropic", "google",
    # Roles and documents (also covers _PROTECTED_PROPER_PHRASES)
    "social", "worker", "programme", "manager", "system", "administrator",
    "administration", "work", "report", "intervention", "plan",
    "supervisor", "supervisora",
    # Public bodies / services commonly named in notes
    "servicios", "servicio", "sociales", "social", "ayuntamiento",
    "diputación", "diputacion", "foral", "gobierno", "vasco", "osakidetza",
    "lanbide", "ertzaintza", "policía", "policia", "municipal", "juzgado",
    "fiscalía", "fiscalia", "seguridad", "cruz", "roja", "cáritas", "caritas",
    "udala", "aldundia", "jaurlaritza", "eusko", "gizarte", "zerbitzuak",
    "ministerio", "estado", "ley", "sanidad", "salud", "mental", "infancia",
    "menores", "familia", "familias", "bizkaia", "euskadi",
    # Languages / nationalities (capitalised in English)
    "english", "spanish", "basque", "french", "euskera", "euskara",
    "castellano", "español", "inglés", "ingles", "francés",
    # English calendar words
    "monday", "tuesday", "wednesday", "thursday", "friday", "saturday",
    "sunday", "january", "february", "march", "april", "may", "june",
    "july", "august", "september", "october", "november", "december",
}

# Function words that often start a sentence (and so appear capitalised).
# They are never names, so they are never recorded or redacted as names.
_STOPWORDS = {
    # Spanish
    "el", "la", "los", "las", "un", "una", "unos", "unas", "lo", "del", "al",
    "y", "e", "o", "u", "pero", "aunque", "porque", "pues", "que", "como",
    "cuando", "donde", "mientras", "si", "no", "sí", "ya", "también",
    "tampoco", "hoy", "ayer", "mañana", "antes", "después", "despues",
    "luego", "durante", "tras", "en", "de", "desde", "hasta", "con", "sin",
    "por", "para", "sobre", "entre", "hacia", "a", "su", "sus", "mi", "mis",
    "tu", "tus", "este", "esta", "estos", "estas", "ese", "esa", "aquel",
    "ella", "él", "ellos", "ellas", "nosotros", "yo", "se", "le", "les",
    "me", "nos", "hay", "fue", "es", "está", "ha", "han", "según", "además",
    "nota", "observación", "observaciones", "usuario", "usuaria",
    # Basque
    "eta", "baina", "gaur", "atzo", "bihar", "bere", "haren", "hau", "hori",
    "hura", "ni", "zu", "gu", "ez", "bai", "ere", "orduan", "gero",
    # English
    "the", "an", "and", "but", "or", "if", "when", "while", "this", "that",
    "these", "those", "he", "she", "they", "we", "it", "his", "her", "their",
    "our", "my", "today", "yesterday", "tomorrow", "after", "before",
    "during", "then", "also", "client", "note", "notes", "on", "in", "at",
    "of", "for", "with", "from", "by", "as",
}

# Nouns that, followed by "de", introduce a place name
# ("Ayuntamiento de Bilbao", "centro de salud de Deusto").
_PLACE_NOUNS = {
    "ayuntamiento", "salud", "municipio", "pueblo", "barrio", "ciudad",
    "provincia", "zona", "comarca", "localidad", "udala", "centro",
}

# Common Spanish and Basque first names. A lone first name at the very start
# of a sentence ("Mikel dice que ...") cannot be told apart from an ordinary
# capitalised word by its position, so these are always redacted, wherever
# they appear. This list only ADDS protection; names not on it are still
# caught by every other rule above. Compared in lower case.
_COMMON_FIRST_NAMES = set("""
aitor ander andoni asier beñat eneko gorka haritz ibai iker imanol iñaki iñigo
jon josu julen koldo markel mikel oier unai urko xabier xabi ekaitz egoitz
aimar aritz igor jokin joseba kepa patxi peio unax
ainhoa ainara aintzane alaitz amaia amaya ane arantza arantxa begoña edurne
eider garazi idoia itziar irati izaskun leire maialen maite miren nerea nagore
olatz uxue ziortza haizea irantzu lorea maddi june nahia naroa
alejandro alberto alfonso alvaro álvaro andrés antonio carlos daniel david
diego eduardo enrique fernando francisco gonzalo hugo ignacio javier jesús
jesus jorge josé jose juan luis manuel marcos mario martín martin miguel
pablo pedro rafael ramón ramon raúl raul ricardo roberto rubén ruben sergio
tomás tomas víctor victor adrián adrian iván ivan óscar oscar mohamed ahmed
ana andrea ángela angela beatriz carmen carolina claudia cristina elena eva
isabel laura lucía lucia luisa marta maría maria mercedes natalia nuria
patricia paula pilar raquel rocío rocio rosa sandra sara silvia sofía sofia
susana teresa irene alba alicia inés ines julia lorena marina noelia
mónica monica verónica veronica yolanda concepción concepcion dolores
fatima fátima aicha khadija
""".split())

_LOCATION_PREPOSITIONS = {"en", "desde", "hacia", "in", "at", "from", "near", "to"}

# Courtesy titles (English, Spanish, Basque). A title followed by a name is
# always a person.
_TITLES = r"(?:Mr|Mrs|Ms|Miss|Dr|Dra|Sr|Sra|Srta|Don|Doña|Dña|D|Jn|And|Andre|Jaun)"

_PERSON_CUES_ES_EU = (
    r"(?i:usuari[oa]|cliente|paciente|menor|niñ[oa]|chic[oa]|joven|"
    r"madre|padre|hij[oa]|herman[oa]|tut(?:or|ora)|abuel[oa]|tí[oa]|ti[oa]|"
    r"prim[oa]|sobrin[oa]|niet[oa]|pareja|marido|espos[oa]|novi[oa]|"
    r"compañer[oa]|vecin[oa]|amig[oa]|cuidador[a]?|"
    r"se\s+llama|llamad[oa]|de\s+nombre|nombre|"
    r"ama|aita|semea|alaba|anaia|arreba|ahizpa|neba|amona|aitona|izena|izeneko)"
)

_CONTEXTUAL_IDENTIFIER_PATTERNS = [
    # Person labels / introductions.
    (re.compile(r"\b(?:client|patient|child|mother|father|guardian|caregiver|named|name(?:d)?\s+as)\s*[:\-]?\s+(%s(?:\s+%s){0,3})\b" % (_NAME_TOKEN, _NAME_TOKEN)), "[PERSON]"),
    # Spanish / Basque person cues: "la usuaria Ane", "su hijo Jon",
    # "la madre, Lucía,", "se llama Pedro", "ama Miren", "izena: Mikel".
    (re.compile(r"\b%s\s*[,:\-]?\s+(%s(?:\s+%s){0,3})\b" % (_PERSON_CUES_ES_EU, _NAME_TOKEN, _NAME_TOKEN)), "[PERSON]"),
    # Institution names where the type comes first ("Hospital City Eye").
    (re.compile(r"\b(?:school|hospital|clinic|organisation|organization|company|employer|university)\s*[:\-]?\s+(%s(?:\s+%s){0,4})\b" % (_NAME_TOKEN, _NAME_TOKEN)), "[ORGANISATION]"),
    # Spanish / Basque institutions where the type comes first
    # ("colegio San José", "ikastola Txantxiku", "empresa Talleres Ibarra").
    (re.compile(r"\b(?i:colegio|escuela|instituto|ikastola|ikastetxe|eskola|institutua|hospital|clínica|clinica|ambulatorio|centro\s+de\s+salud|empresa|asociación|asociacion|universidad|residencia|guardería|guarderia|haurreskola)\s*[:\-]?\s+(%s(?:\s+%s){0,4})\b" % (_NAME_TOKEN, _NAME_TOKEN)), "[ORGANISATION]"),
    # Institution names where the type is a suffix ("City Eye Hospital").
    (re.compile(r"\b(%s(?:\s+%s){0,4})\s+(?:school|hospital|clinic|organisation|organization|company|university|foundation)\b" % (_NAME_TOKEN, _NAME_TOKEN), re.IGNORECASE), "[ORGANISATION]"),
    # Places after common location cues.
    (re.compile(r"\b(?:from|near|in|at|lives?\s+in|resides?\s+in|based\s+in)\s+(%s(?:\s+%s){0,3})(?=\s*[,.;:!?)]|\s+(?:and|but|who|where|which|was|is|has|had)\b|$)" % (_NAME_TOKEN, _NAME_TOKEN)), "[LOCATION]"),
    # Spanish places after residence / origin cues ("vive en Barakaldo",
    # "natural de Getxo", "empadronada en Basauri").
    (re.compile(r"\b(?i:vive|viven|reside|residen|residente|vecin[oa]|natural|procedente|empadronad[oa]s?|nacid[oa])\s+(?i:en|de)\s+(%s(?:\s+%s){0,3})\b" % (_NAME_TOKEN, _NAME_TOKEN)), "[LOCATION]"),
    # Explicit address labels and natural-language residence/address phrases.
    (re.compile(r"\b(?:home\s+address|postal\s+address|physical\s+address|address)\s*[:\-]?\s+[^\n,.;!?]+", re.IGNORECASE), "[ADDRESS]"),
    (re.compile(r"\b(?:lives?|resides?)\s+at\s+[^\n,.;!?]+", re.IGNORECASE), "[ADDRESS]"),
    # Spanish / Basque street addresses. The street word must be followed by
    # a capitalised name or a number, so "duerme en la calle" (homelessness)
    # is left alone.
    (re.compile(r"(?:\b(?i:calle|avenida|avda|plaza|paseo|pasaje|camino|carretera|barrio|travesía|ronda|kalea|etorbidea|plaza|pasealekua|auzoa)\.?|(?<!\w)(?i:c/|av\.|pza\.))\s*(?:(?i:de|del|de\s+la|de\s+los)\s+)?(?:[A-ZÀ-ÖØ-Þ][\wÀ-ÿ'’\-]*|\d+[\wºª]*)(?:\s+(?:[A-ZÀ-ÖØ-Þ][\wÀ-ÿ'’\-]*|\d+[\wºª\-]*|(?i:de|del|la|los|las|n[º°o]\.?|s/n|bis))(?=\s|$|[,.;:!?)]))*"), "[ADDRESS]"),
    (re.compile(r"\b(?:domicilio|dirección|direccion|helbidea)\s*(?::|\s+(?:en|es|:))\s*[^\n,.;!?]+", re.IGNORECASE), "[ADDRESS]"),
]

# The complete identifier label must end at a word boundary. In particular,
# plain `ref` must NOT match the beginning of words such as "referral".
_IDENTIFIER_RE = re.compile(
    r"\b(?:case\s*(?:reference|ref|number|no|id)|client\s*(?:id|number|no)|national\s*(?:id|number|no)|identifier|reference|ref"
    r"|dni|nie|nif|pasaporte|passport|tarjeta\s+sanitaria|tis|n[º°o]\.?\s*(?:de\s+)?expediente|expediente|n[úu]mero\s+de\s+(?:caso|expediente|usuario|usuaria)|referencia|nss|n[º°o]\.?\s*(?:de\s+)?(?:la\s+)?seguridad\s+social|espediente(?:a)?|zenbakia|nan)"
    r"\b\s*[:#\-]?\s*(?:(?:es|n[º°o]\.?|número|numero)\s*[:\-]?\s*)?[A-Za-z0-9][A-Za-z0-9/_\-.]{2,}\b",
    re.IGNORECASE,
)
# Spanish DNI (8 digits + letter) and NIE (X/Y/Z + 7 digits + letter).
_DNI_NIE_RE = re.compile(r"(?<!\w)(?:\d{8}|[XYZxyz][\s\-]?\d{7})[\s\-]?[A-Za-z](?!\w)")
# IBAN bank accounts (e.g. ES91 2100 0418 4502 0005 1332).
_IBAN_RE = re.compile(r"(?<!\w)[A-Z]{2}\d{2}(?:[ ]?[A-Z0-9]{4}){3,7}(?:[ ]?[A-Z0-9]{1,4})?(?!\w)")
_EMAIL_RE = re.compile(r"\b[\w.+-]+@[\w-]+(?:\.[\w-]+)+\b", re.UNICODE)
_DATE_RE = re.compile(
    r"\b(?:\d{1,2}[/.-]\d{1,2}[/.-]\d{2,4}|\d{1,2}\s+(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:t(?:ember)?)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+\d{2,4}|\d{1,2}\s+de\s+(?:enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|setiembre|octubre|noviembre|diciembre)\s+(?:de|del)\s+\d{2,4}"
    # Basque: "2025eko martxoaren 21ean" / "2025eko martxoaren 21a".
    r"|\d{4}(?:eko|ko)\s+(?:urtarrila|otsaila|martxoa|apirila|maiatza|ekaina|uztaila|abuztua|iraila|urria|azaroa|abendua)(?:ren|aren)?\s+\d{1,2}(?:ean|an|a)?)\b",
    re.IGNORECASE,
)
_PHONE_RE = re.compile(
    r"(?<!\w)(?:\+\d{1,3}[\s.-]?)?(?:\(?\d{2,4}\)?[\s.-])?\d{3,4}[\s.-]\d{3,4}(?:[\s.-]\d{2,4})?(?!\w)"
)
_LONG_NUMERIC_ID_RE = re.compile(r"(?<!\w)\d{5,}(?!\w)")

# Characters that end a sentence (so the next capitalised word may just be
# an ordinary sentence start, not a name).
_SENTENCE_END_CHARS = ".!?:;\n"
_LEADING_PUNCT = " \t\"'«“‘(¡¿-–—•*·"


def _is_safe_word(word: str) -> bool:
    low = word.lower()
    return low in _SAFE_CAPITALISED_WORDS or low in _STOPWORDS


def _record_name_tokens(phrase: str, known_names: set) -> None:
    """Remember each real name token of a redacted person phrase."""
    for token in phrase.split():
        token = token.strip(",.;:!?()\"'«»")
        if len(token) >= 2 and not _is_safe_word(token) and not token.isupper():
            known_names.add(token)


def _replace_proper_names(text: str, known_names: set) -> str:
    """Redact conservative multi-token names plus complex single names."""
    def repl(match):
        phrase = match.group(0)
        if phrase in _PROTECTED_PROPER_PHRASES:
            return phrase
        tokens = phrase.split()
        if tokens[0].lower().rstrip(".") in {"mr", "mrs", "ms", "miss", "dr", "sr", "sra", "srta"}:
            return phrase
        # Acronym inside the phrase ("Su DNI", "EDE Fundazioa"): not a name.
        if any(len(t) >= 2 and t.isupper() for t in tokens):
            return phrase
        # Public bodies / safe words only ("Servicios Sociales",
        # "El Ayuntamiento", "Gobierno Vasco"): not a personal identifier.
        if all(_is_safe_word(t) for t in tokens):
            return phrase
        # Sentence-start function word glued to a name ("Hoy Pedro ...",
        # "La Usuaria ..."): keep the function word, redact the rest.
        lead = []
        while tokens and tokens[0].lower() in _STOPWORDS:
            lead.append(tokens.pop(0))
        if not tokens:
            return phrase
        if len(tokens) == 1 and _is_safe_word(tokens[0]):
            return phrase
        _record_name_tokens(" ".join(tokens), known_names)
        return (" ".join(lead) + " " if lead else "") + "[PERSON]"

    text = _NAME_SEQUENCE_RE.sub(repl, text)

    def complex_repl(match):
        token = match.group(0)
        if "-" in token or "'" in token or "’" in token:
            known_names.add(token)
            return "[PERSON]"
        return token

    return _SINGLE_COMPLEX_NAME_RE.sub(complex_repl, text)


def _is_sentence_start(text: str, start: int) -> bool:
    before = text[:start].rstrip(_LEADING_PUNCT)
    return not before or before[-1] in _SENTENCE_END_CHARS


def _looks_like_place(text: str, start: int) -> bool:
    words = re.findall(r"\w+", text[:start][-60:].lower())
    if not words:
        return False
    if words[-1] in _LOCATION_PREPOSITIONS:
        return True
    return len(words) >= 2 and words[-1] == "de" and words[-2] in _PLACE_NOUNS


def _replace_single_names(text: str, known_names: set) -> str:
    """Redact single capitalised words written mid-sentence.

    In Spanish, Basque and (outside a small set of calendar / language
    words) English, a capitalised word in the middle of a sentence is almost
    always a name or a place. Sentence-initial words are only redacted when
    the same word has been recognised as a name elsewhere in the text.
    """
    found = {}
    for match in _SINGLE_CAPITALISED_RE.finditer(text):
        word = match.group(0)
        if _is_safe_word(word) or _is_sentence_start(text, match.start()):
            continue
        tag = "[LOCATION]" if _looks_like_place(text, match.start()) else "[PERSON]"
        # A word seen as a person anywhere stays a person.
        if found.get(word) != "[PERSON]":
            found[word] = tag

    for match in _SINGLE_CAPITALISED_RE.finditer(text):
        word = match.group(0)
        if word.lower() in _COMMON_FIRST_NAMES:
            found[word] = "[PERSON]"

    for name in known_names:
        if name not in found and not _is_safe_word(name):
            found[name] = "[PERSON]"

    if not found:
        return text

    # Longest first so "Mari" never eats the start of "Maribel".
    names = sorted(found, key=len, reverse=True)
    pattern = re.compile(r"(?<![\w\[])(?:%s)(?![\w\]])" % "|".join(re.escape(n) for n in names))
    return pattern.sub(lambda m: found[m.group(0)], text)


def anonymize(text: str) -> str:
    """Return a privacy-hardened representation suitable for external AI."""
    if not text:
        return text

    known_names = set()

    safe = str(text)
    safe = _EMAIL_RE.sub("[EMAIL]", safe)
    safe = _IBAN_RE.sub("[ID]", safe)
    safe = _DATE_RE.sub("[DATE]", safe)
    safe = _IDENTIFIER_RE.sub("[ID]", safe)
    safe = _DNI_NIE_RE.sub("[ID]", safe)
    safe = _PHONE_RE.sub("[PHONE]", safe)
    safe = _LONG_NUMERIC_ID_RE.sub("[ID]", safe)

    for pattern, replacement in _CONTEXTUAL_IDENTIFIER_PATTERNS:
        def ctx_repl(m, r=replacement):
            if not m.groups() or m.group(1) is None:
                return r
            captured = m.group(1)
            # "in English", "en Servicios Sociales": nothing personal there.
            if all(_is_safe_word(t) for t in captured.split()):
                return m.group(0)
            if r == "[PERSON]":
                _record_name_tokens(captured, known_names)
            if m.end(1) == m.end(0):
                # Keep the cue words ("la madre, ...", "vive en ...") so the
                # sentence still makes sense; only the name is replaced.
                return m.group(0)[: m.start(1) - m.start(0)] + r
            return r
        safe = pattern.sub(ctx_repl, safe)

    def title_repl(m):
        _record_name_tokens(m.group(1), known_names)
        return "[PERSON]"

    safe = re.sub(
        rf"\b{_TITLES}\.?\s+({_NAME_TOKEN}(?:\s+{_NAME_TOKEN}){{0,3}})\b",
        title_repl,
        safe,
    )

    safe = _replace_proper_names(safe, known_names)
    return _replace_single_names(safe, known_names)
