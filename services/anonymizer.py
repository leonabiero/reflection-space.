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
    # November 2026: places of work / everyday places ("una tienda de
    # Barakaldo"). "casa de X" is left out on purpose: that is a person.
    "tienda", "bar", "fábrica", "fabrica", "supermercado", "mercado",
    "oficina", "polideportivo", "biblioteca", "estación", "estacion", "parque",
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
john mary james michael sarah emma olivia william thomas george emily jessica
jennifer robert richard christopher matthew joseph elizabeth peter paul kevin
brian susan linda karen nancy lisa michelle mohammed muhammad omar amina
""".split())

_LOCATION_PREPOSITIONS = {"en", "desde", "hacia", "in", "at", "from", "near", "to"}

# November 2026 -- towns and cities named in notes are tagged [LOCATION]
# (not [PERSON]) wherever they appear, so the AI is not told that "a shop
# in Barakaldo" is "a shop belonging to a person". Bizkaia municipalities,
# the other Basque capitals and nearby / large cities, in Spanish and
# Basque spellings. Basque case endings are understood too ("Bilboko",
# "Barakaldon", "Getxora", "Donostiatik"). This list only changes the LABEL
# of something that is removed anyway; a town not on it is still removed.
# Compared in lower case.
_KNOWN_PLACES = set("""
bilbao bilbo barakaldo baracaldo getxo portugalete santurtzi santurce sestao
basauri leioa lejona durango erandio galdakao galdácano bermeo gernika guernica
mungia amorebieta zornotza etxebarri echevarri ermua balmaseda sopela sopelana
berriz elorrio abadiño abadiano iurreta ondarroa lekeitio markina zalla gordexola
güeñes muskiz trapagaran trapaga ortuella derio zamudio sondika loiu lezama
arrigorriaga ugao miravalles orozko igorre laukiz plentzia gorliz barrika urduliz
berango lemoa bedia amurrio llodio laudio
donostia gasteiz vitoria iruña iruñea pamplona eibar irun hondarribia zarautz
tolosa errenteria arrasate mondragón mondragon bergara azpeitia beasain
santander logroño burgos madrid barcelona zaragoza valencia sevilla
""".split())
_KNOWN_PLACE_PHRASES = {"san sebastián", "san sebastian", "vitoria-gasteiz", "castro urdiales"}
_BASQUE_PLACE_SUFFIXES = ("ko", "koa", "koak", "n", "an", "en", "ra", "ara", "era",
                          "rako", "tik", "etik", "raino", "rantz", "ean")


def _is_known_place(word: str) -> bool:
    low = word.lower()
    if low in _KNOWN_PLACES or low in _KNOWN_PLACE_PHRASES:
        return True
    return any(low.startswith(place) and low[len(place):] in _BASQUE_PLACE_SUFFIXES
               for place in _KNOWN_PLACES if len(place) >= 4)

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

# The text of an address after its cue: up to punctuation, or up to a word
# that starts a new piece of information.
_ADDRESS_STOP_EN = r"(?:with|and|since|where|together|alone|for|but|who|which|because|until|while|when)"
_ADDRESS_STOP_ES_EU = r"(?:con|y|desde|donde|junto|sol[oa]|para|pero|que|porque|hasta|cuando|eta|bere|baina|non)"
_ADDRESS_BODY_EN = r"(?:(?!\s+%s\b)[^\n,.;!?:])+" % _ADDRESS_STOP_EN
_ADDRESS_BODY_ES_EU = r"(?:(?!\s+%s\b)[^\n,.;!?:])+" % _ADDRESS_STOP_ES_EU

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
    # (November 2026) The address ends where a new piece of information
    # starts ("lives at 14 River Road with her two children"), so the
    # household details after it are no longer swallowed with it.
    (re.compile(r"\b(?:home\s+address|postal\s+address|physical\s+address|address)\s*[:\-]?\s+%s" % _ADDRESS_BODY_EN, re.IGNORECASE), "[ADDRESS]"),
    (re.compile(r"\b(?:lives?|resides?)\s+at\s+%s" % _ADDRESS_BODY_EN, re.IGNORECASE), "[ADDRESS]"),
    # Spanish / Basque street addresses. The street word must be followed by
    # a capitalised name or a number, so "duerme en la calle" (homelessness)
    # is left alone.
    (re.compile(r"(?:\b(?i:calle|avenida|avda|plaza|paseo|pasaje|camino|carretera|barrio|travesía|ronda|kalea|etorbidea|plaza|pasealekua|auzoa)\.?|(?<!\w)(?i:c/|av\.|pza\.))\s*(?:(?i:de|del|de\s+la|de\s+los)\s+)?(?:[A-ZÀ-ÖØ-Þ][\wÀ-ÿ'’\-]*|\d+[\wºª]*)(?:\s+(?:[A-ZÀ-ÖØ-Þ][\wÀ-ÿ'’\-]*|\d+[\wºª\-]*|(?i:de|del|la|los|las|n[º°o]\.?|s/n|bis))(?=\s|$|[,.;:!?)]))*"), "[ADDRESS]"),
    (re.compile(r"\b(?:domicilio|dirección|direccion|helbidea)\s*(?::|\s+(?:en|es|:))\s*%s" % _ADDRESS_BODY_ES_EU, re.IGNORECASE), "[ADDRESS]"),
]

# (November 2026) Floor, door, staircase... right after an address are part
# of it: "[ADDRESS], 2º izquierda", "[ADDRESS] 3ºB", "[ADDRESS], bajo",
# "[ADDRESS], 2. ezkerra", "[ADDRESS], flat 4". Applied after every address
# rule above.
_ADDRESS_UNIT_RE = re.compile(
        r"\[ADDRESS\](?:\s*,?\s*(?:\d+\s*[ºª°]\.?\s*(?:[A-Za-z](?!\w)|(?i:izquierda|izda\.?|izq\.?|derecha|dcha\.?|centro|ezkerra|eskuina|ezk\.?|esk\.?))?"
        r"|\d+\.\s*(?i:ezkerra|eskuina|ezk\.?|esk\.?)"
        r"|(?i:bajo|entresuelo|ático|atico)(?!\w)"
        r"|(?i:piso|puerta|escalera|esc\.|portal|solairua|atea|flat|apartment|apt\.?)\s+[\wºª]+))+"
    )

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
        if " ".join(tokens).lower() in _KNOWN_PLACE_PHRASES:
            return (" ".join(lead) + " " if lead else "") + "[LOCATION]"
        _record_name_tokens(" ".join(tokens), known_names)
        return (" ".join(lead) + " " if lead else "") + "[PERSON]"

    text = _NAME_SEQUENCE_RE.sub(repl, text)

    def complex_repl(match):
        token = match.group(0)
        if _is_known_place(token):
            return "[LOCATION]"
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
        if name not in found and not _is_safe_word(name) and not _is_known_place(name):
            found[name] = "[PERSON]"

    # Known towns and cities: a place wherever they are, even at the start
    # of a sentence (see _KNOWN_PLACES).
    for match in _SINGLE_CAPITALISED_RE.finditer(text):
        word = match.group(0)
        if _is_known_place(word):
            found[word] = "[LOCATION]"

    if not found:
        return text

    # Longest first so "Mari" never eats the start of "Maribel".
    names = sorted(found, key=len, reverse=True)
    pattern = re.compile(r"(?<![\w\[])(?:%s)(?![\w\]])" % "|".join(re.escape(n) for n in names))
    return pattern.sub(lambda m: found[m.group(0)], text)


# ---------------------------------------------------------------------------
# Exact ages (November 2026)
# ---------------------------------------------------------------------------
# An exact age is an identifier: together with a town, a service and a date
# it can single one person out ("a 30-year-old woman who came to the centre
# on Monday"). In the pilot, "her actual age is 30 not 29" reached the AI
# untouched. Every exact age is now replaced by a life-stage tag
# ([AGE_CHILD], [AGE_ADULT], ...; see config.AGE_BAND_LIMITS), in Spanish,
# Basque and English, written in digits or in words, including corrections
# ("30, not 29", "de 29 a 30") and years of birth ("born in 1996",
# "nació en 1996", "1996an jaio zen" -> [DATE]).
#
# A number is only treated as an age when the words around it say so
# ("years old", "tiene ... años", "urte ditu", "age", "edad", "adina",
# "a woman of ..."). Durations and quantities -- "hace 3 años",
# "lleva 2 años en el piso", "duela 3 urte", "2 hijos", "30 euros" -- are
# left alone, because the reflection needs them.
#
# The minor / adult distinction is always kept exact (the adolescent group
# always ends at 17), because it matters for safeguarding.

_DEFAULT_AGE_LIMITS = (2, 12, 17, 25, 64)
_AGE_BAND_NAMES = ("INFANT", "CHILD", "ADOLESCENT", "YOUNG_ADULT", "ADULT", "OLDER_ADULT")
_MAX_PLAUSIBLE_AGE = 120


def _load_age_limits():
    """Age limits from config.AGE_BAND_LIMITS, or the defaults if that is
    missing or invalid (never a reason to switch age protection off)."""
    try:
        from config import AGE_BAND_LIMITS
        limits = tuple(int(p) for p in str(AGE_BAND_LIMITS).split(","))
    except Exception:
        return _DEFAULT_AGE_LIMITS
    valid = (
        len(limits) == 5
        and all(a < b for a, b in zip(limits, limits[1:]))
        and limits[0] >= 0
        and limits[2] == 17
        and limits[4] < _MAX_PLAUSIBLE_AGE
    )
    return limits if valid else _DEFAULT_AGE_LIMITS


_AGE_LIMITS = _load_age_limits()


def age_band_tag(years: float) -> str:
    """The life-stage tag for an age in years, e.g. 30 -> "[AGE_ADULT]"."""
    for limit, name in zip(_AGE_LIMITS, _AGE_BAND_NAMES):
        if years < limit + 1:
            return f"[AGE_{name}]"
    return f"[AGE_{_AGE_BAND_NAMES[-1]}]"


def _build_number_words():
    words = {}
    # English
    units = ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight",
             "nine", "ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen",
             "sixteen", "seventeen", "eighteen", "nineteen"]
    tens = {20: "twenty", 30: "thirty", 40: "forty", 50: "fifty", 60: "sixty",
            70: "seventy", 80: "eighty", 90: "ninety"}
    for n, w in enumerate(units):
        words[w] = n
    for t, w in tens.items():
        words[w] = t
        for u in range(1, 10):
            words[f"{w}-{units[u]}"] = t + u
            words[f"{w} {units[u]}"] = t + u
    # Spanish
    es = ["cero", "un", "dos", "tres", "cuatro", "cinco", "seis", "siete", "ocho",
          "nueve", "diez", "once", "doce", "trece", "catorce", "quince", "dieciséis",
          "diecisiete", "dieciocho", "diecinueve", "veinte", "veintiuno", "veintidós",
          "veintitrés", "veinticuatro", "veinticinco", "veintiséis", "veintisiete",
          "veintiocho", "veintinueve"]
    for n, w in enumerate(es):
        words[w] = n
    words.update({"uno": 1, "una": 1, "dieciseis": 16, "veintidos": 22,
                  "veintitres": 23, "veintiseis": 26, "veintiún": 21, "veintiun": 21})
    es_tens = {30: "treinta", 40: "cuarenta", 50: "cincuenta", 60: "sesenta",
               70: "setenta", 80: "ochenta", 90: "noventa"}
    for t, w in es_tens.items():
        words[w] = t
        for u in range(1, 10):
            words[f"{w} y {es[u]}"] = t + u
        words[f"{w} y uno"] = t + 1
    # Basque (vigesimal: 20 hogei, 40 berrogei, 60 hirurogei, 80 laurogei)
    eu = ["zero", "bat", "bi", "hiru", "lau", "bost", "sei", "zazpi", "zortzi",
          "bederatzi", "hamar", "hamaika", "hamabi", "hamahiru", "hamalau", "hamabost",
          "hamasei", "hamazazpi", "hemezortzi", "hemeretzi"]
    for n, w in enumerate(eu):
        words.setdefault(w, n)
    for base, w in {20: "hogei", 40: "berrogei", 60: "hirurogei", 80: "laurogei"}.items():
        words[w] = base
        for u in range(1, 20):
            words[f"{w}ta {eu[u]}"] = base + u
    words.pop("zero", None)
    words.pop("cero", None)
    return words


_NUMBER_WORDS = _build_number_words()
_NUMBER_WORDS_RE = "|".join(
    re.escape(w).replace(r"\ ", r"\s+").replace(r"\-", r"[\s\-]")
    for w in sorted(_NUMBER_WORDS, key=len, reverse=True)
)
# One age as digits (1-3, optionally "30-year") or words.
_NUM = rf"(?:(?<!\d)(?<!\d[.,:/])\d{{1,3}}(?![\d.,:/]?\d)|(?<![\w])(?:{_NUMBER_WORDS_RE})(?![\w]))"
# Several ages at once: "5 y 7", "5, 7 and 9", "bost eta zazpi".
_NUMLIST = rf"{_NUM}(?:\s*(?:,|\by\b|\be\b|\band\b|\bor\b|\bo\b|\beta\b|\bedo\b)\s*{_NUM})*"
_NUM_FIND_RE = re.compile(_NUM, re.IGNORECASE)

_YEARS_EN = r"(?:years?|yrs?)"
_MONTHS_EN = r"(?:months?|weeks?)"
_YEARS_ES = r"(?:años|año|añitos)"
_MONTHS_ES = r"(?:meses|mes|semanas)"
_YEARS_EU = r"(?:urte)"
_MONTHS_EU = r"(?:hilabete|aste)"
_UNIT = rf"(?:{_YEARS_EN}|{_MONTHS_EN}|{_YEARS_ES}|{_MONTHS_ES}|{_YEARS_EU}|{_MONTHS_EU})"

# Not an age when a duration / quantity word follows a bare number.
_NOT_AGE_AFTER = (
    r"(?!\s*(?:%|€|\$|euros?|percent|por\s+ciento|minutes?|minutos?|hours?|horas?|"
    r"days?|días?|dias?|times|veces|people|personas|pm|am|h\b|:\d))"
)

_PERSON_NOUNS_ES = (
    r"(?:mujer|hombre|chic[oa]|niñ[oa]|joven|menor|usuari[oa]|persona|señor[a]?|"
    r"hij[oa]|beb[ée]|adolescente|madre|padre|herman[oa]|chaval[a]?|muchach[oa]|"
    r"ancian[oa]|abuel[oa]|niet[oa]|pareja|marido|espos[oa]|varón|cliente|"
    r"chiquill[oa]|criatura|pequeñ[oa]|mayor|tí[oa]|prim[oa]|sobrin[oa]|vecin[oa])e?s?"
)
_PERSON_NOUNS_EN = (
    r"(?:woman|women|man|men|girl|boy|child|children|kid|baby|infant|teenager|teen|"
    r"person|client|mother|father|son|daughter|brother|sister|adult|minor|youth|"
    r"partner|husband|wife|grandmother|grandfather|toddler|student|pupil|resident)s?"
)

# Each pattern marks the part to replace as the named group "age".
_AGE_PATTERNS = [
    # --- English -----------------------------------------------------------
    # "30 years old", "30-year-old", "6 months old", "thirty years of age"
    rf"(?P<age>{_NUMLIST}[\s\-]*(?:{_YEARS_EN}|{_MONTHS_EN})[\s\-]*(?:old|of\s+age)\b)",
    # "30 y/o", "30yo"
    rf"(?P<age>{_NUM}\s*(?:y/o|y\.o\.|yo)\b)",
    # "age 30", "aged 30", "age: 30", "her actual age is 30", "age of 30"
    rf"\bage[ds]?\b(?:\s*(?:is|was|of|now|actually|really|about|around|approximately|"
    rf"approx\.?|:|=|-|–)\s*)*\s*(?P<age>{_NUMLIST}(?:\s*{_YEARS_EN})?)\b{_NOT_AGE_AFTER}",
    # "turned 30", "turns eighteen", "will be 18"
    rf"\b(?:turned|turns|turning|will\s+be|is\s+now|was\s+then)\s+(?P<age>{_NUM})\b"
    rf"{_NOT_AGE_AFTER}(?!\s*(?:{_YEARS_EN}|{_MONTHS_EN})?\s*(?:later|ago|before|after)\b)",
    # "she is 30, not 29", "he's 17.", "who is 67 and"
    # (also after a name already replaced: "[PERSON], is 41", "[PERSON] was 67")
    rf"(?:\b(?:she|he|they|who|i)|\[PERSON\]\s*,?)(?:'s|’s|\s+is|\s+was|\s+am|\s+are)\s+(?:only\s+|just\s+|now\s+|actually\s+)?"
    rf"(?P<age>{_NUM})(?=\s*(?:[,.;!?)]|$|\s+(?:not|and|but|now|or|this|so)\b))",
    # "a woman of 30", "children of 5 and 7"
    rf"\b{_PERSON_NOUNS_EN}\s+(?:aged\s+|of\s+)(?P<age>{_NUMLIST}(?:\s*{_YEARS_EN})?)\b{_NOT_AGE_AFTER}",
    # --- Spanish -----------------------------------------------------------
    # "tiene 30 años", "cumplió 18 años", "con 17 años", "tiene 8 meses"
    rf"\b(?:tiene|tenía|tenia|tendrá|tendra|tienen|tenían|cumple|cumplió|cumplio|cumplirá|"
    rf"cumplira|cumplen|ha\s+cumplido|había\s+cumplido|habia\s+cumplido|con|a\s+los)\s+"
    rf"(?P<age>{_NUMLIST}\s+(?:{_YEARS_ES}|{_MONTHS_ES}))\b"
    # ... but not a duration: "con 3 años de experiencia", "tiene 2 años
    # trabajando", "a los 3 meses de llegar" ("de edad" is still an age).
    rf"(?!\s+(?:de\s+(?!edad\b)\w|trabajando|viviendo|en\s+(?:el|la|este|esta|su)\b))",
    # "tiene 30, no 29", "cumple 18."
    rf"\b(?:tiene|tenía|tenia|cumple|cumplió|cumplio|cumplirá)\s+(?P<age>{_NUM})"
    rf"(?=\s*(?:[,.;!?)]|$|\s+(?:y\s+)?no\b))",
    # "30 años de edad"
    rf"(?P<age>{_NUMLIST}\s+(?:{_YEARS_ES}|{_MONTHS_ES})\s+de\s+edad)\b",
    # "una mujer de 30 años", "hijos de 5 y 7 años", "menor de 17 años"
    rf"(?:\b{_PERSON_NOUNS_ES}|\[PERSON\])\s*,?\s+de\s+(?P<age>{_NUMLIST}\s+(?:{_YEARS_ES}|{_MONTHS_ES}))\b",
    # "edad: 30", "su edad real es 30", "edad de 30 años", "edad, 30"
    rf"\bedad(?:es)?\b(?:\s*(?:real|actual|verdadera|correcta|es|era|sería|seria|de|"
    rf"aproximada|aprox\.?|unos|unas|:|=|-|–|,)\s*)*\s*(?P<age>{_NUM}(?:\s+{_YEARS_ES})?)\b{_NOT_AGE_AFTER}",
    # "su edad pasó de 29 a 30", "age changed from 29 to 30" (the second
    # number is caught by the correction rule below)
    rf"\b(?:age[ds]?|edad(?:es)?|adin(?:a|ak)?)\b[^.\n;]{{0,30}}?\b(?:from|de)\s+"
    rf"(?P<age>{_NUM})(?=\s+(?:to|a)\s+{_NUM})",
    # --- Basque ------------------------------------------------------------
    # "30 urte ditu", "17 urte zituen", "18 urte bete ditu", "8 hilabete ditu"
    rf"(?P<age>{_NUMLIST}\s+(?:{_YEARS_EU}|{_MONTHS_EU}))\s+(?=(?:ditu|dauzka|zituen|"
    rf"zeuzkan|dituela|zituela|dituen|zituen|dituzte|zituzten|izango\s+ditu|bete\b|"
    rf"beteko\b|betetzen\b|betetakoan\b|bete\s+berri\b))",
    # "30 urteko emakumea", "17 urterekin", "6 hilabeteko haurra"
    rf"(?P<age>{_NUMLIST}\s+(?:{_YEARS_EU}|{_MONTHS_EU})(?:ko|rekin|tan)\b)",
    # "adina: 30", "benetako adina 30 da", "adinez 30"
    rf"\badin(?:a|ak|aren|ez|eko)?\b(?:\s*(?:erreala|benetakoa|zuzena|da|zen|:|=|-|–|,)\s*)*\s*"
    rf"(?P<age>{_NUM}(?:\s+{_YEARS_EU})?)\b{_NOT_AGE_AFTER}",
]
_AGE_RES = [re.compile(p, re.IGNORECASE) for p in _AGE_PATTERNS]

_AGE_TAG_RE = r"\[AGE_[A-Z_]+\]"
# A second number joined to an age by a correction or a list:
# "[AGE_ADULT] not 29", "[AGE_ADULT], no 29 años", "ez 29", "from 29 to [AGE_ADULT]".
_AGE_LINK = (
    r"(?:not|no|ez|nor|ni|or|o|edo|to|a|instead\s+of|rather\s+than|en\s+vez\s+de|"
    r"en\s+lugar\s+de|y\s+no|and\s+not|eta\s+ez|but|pero|baina|ordez|then|now|ahora|"
    r"orain|luego|from|de|tik)"
)
_AGE_FORWARD_RE = re.compile(
    rf"(?P<tag>{_AGE_TAG_RE})(?P<link>(?:\s+(?:da|zen|is|was|es|era|años|urte))?\s*[,;]?\s*{_AGE_LINK}\s+)"
    rf"(?P<age>{_NUM}(?:\s*{_UNIT}(?:\s+old)?)?)\b{_NOT_AGE_AFTER}",
    re.IGNORECASE,
)
_AGE_BACKWARD_RE = re.compile(
    rf"(?<![\w\[])(?P<age>{_NUM}(?:\s*{_UNIT})?)(?P<link>\s*[,;]?\s*{_AGE_LINK}\s+)(?=(?P<tag>{_AGE_TAG_RE}))",
    re.IGNORECASE,
)

_YEAR = r"(?:19|20)\d{2}"
_BIRTH_YEAR_RES = [
    re.compile(p, re.IGNORECASE) for p in (
        rf"\bborn\s+(?:in\s+)?(?:the\s+year\s+)?(?P<age>{_YEAR})\b",
        rf"\b(?:year\s+of\s+birth|birth\s+year|DOB|d\.o\.b\.?)\s*[:\-]?\s*(?:is\s+)?(?P<age>{_YEAR})\b",
        rf"\b(?:nacid[oa]s?|naci[óo]|nace)\s+(?:en\s+)?(?:el\s+(?:año\s+)?)?(?P<age>{_YEAR})\b",
        rf"\baño\s+de\s+nacimiento\s*[:\-]?\s*(?:es\s+)?(?:el\s+)?(?P<age>{_YEAR})\b",
        rf"\b(?P<age>{_YEAR})(?:-?an|-?ean)?\s+jaio(?:a|tako|takoa|zen|ziren|nintzen)?\b",
        rf"\bjaio(?:a|tako|takoa|zen|ziren|nintzen)?\s+(?P<age>{_YEAR})(?:an|ean)?\b",
        rf"\bjaiotze[\s\-]*(?:urtea|data)\s*[:\-]?\s*(?P<age>{_YEAR})(?:\s*(?:da|zen))?\b",
    )
]


def _lookup_number_word(token: str):
    token = re.sub(r"\s+", " ", token.strip().lower())
    for candidate in (token, token.replace(" ", "-"), token.replace("-", " ")):
        if candidate in _NUMBER_WORDS:
            return _NUMBER_WORDS[candidate]
    return None


def _age_span_to_tags(span: str):
    """Replace every number in an age phrase with its life-stage tag and
    drop the unit words. Returns None if a number is not a plausible age."""
    in_months = bool(re.search(rf"\b(?:{_MONTHS_EN}|{_MONTHS_ES}|{_MONTHS_EU})", span, re.IGNORECASE))
    in_weeks = bool(re.search(r"\b(?:weeks?|semanas|aste)", span, re.IGNORECASE))
    pieces = []
    last = 0
    numbers = list(_NUM_FIND_RE.finditer(span))
    if not numbers:
        return None
    for m in numbers:
        raw = m.group(0)
        value = int(raw) if raw.isdigit() else _lookup_number_word(raw)
        if value is None or value > _MAX_PLAUSIBLE_AGE:
            return None
        years = value / 52 if in_weeks else value / 12 if in_months else value
        pieces.append(span[last:m.start()])
        pieces.append(age_band_tag(years))
        last = m.end()
    # Text after the last number is the unit ("años", "-year-old", "urteko"):
    # dropped, since the tag already says it is an age.
    return "".join(pieces)


def _replace_age_group(match):
    start, end = match.span("age")
    tags = _age_span_to_tags(match.group("age"))
    if tags is None:
        return match.group(0)
    whole_start = match.start()
    text = match.group(0)
    return text[: start - whole_start] + tags + text[end - whole_start:]


def _generalise_ages(text: str) -> str:
    """Replace exact ages with life-stage tags (see the section comment)."""
    for regex in _BIRTH_YEAR_RES:
        text = regex.sub(
            lambda m: m.group(0)[: m.start("age") - m.start()] + "[DATE]"
            + m.group(0)[m.end("age") - m.start():],
            text,
        )
    for regex in _AGE_RES:
        text = regex.sub(_replace_age_group, text)
    # Corrections and lists linked to an age that was just replaced. A few
    # rounds, so "29 to 30 or 31" is fully covered.
    for _ in range(4):
        before = text
        text = _AGE_FORWARD_RE.sub(_replace_age_group, text)
        text = _AGE_BACKWARD_RE.sub(_replace_age_group, text)
        if text == before:
            break
    return text


def anonymize(text: str) -> str:
    """Return a privacy-hardened representation suitable for external AI.

    Two passes: the original rules on the text as written, then the same
    rules again on a copy where words written in CAPITAL LETTERS have been
    given ordinary capitalisation (see _anonymize_capitals). The second pass
    can only ADD redactions; anything the first pass removed stays removed.
    """
    if not text:
        return text
    return _anonymize_capitals(_anonymize_core(text))


def _anonymize_core(text: str) -> str:
    """The rule set: the original rules plus (November 2026) exact ages."""
    if not text:
        return text

    known_names = set()

    safe = str(text)
    safe = _EMAIL_RE.sub("[EMAIL]", safe)
    safe = _IBAN_RE.sub("[ID]", safe)
    safe = _DATE_RE.sub("[DATE]", safe)
    safe = _generalise_ages(safe)
    safe = _IDENTIFIER_RE.sub("[ID]", safe)
    safe = _DNI_NIE_RE.sub("[ID]", safe)
    safe = _PHONE_RE.sub("[PHONE]", safe)
    safe = _LONG_NUMERIC_ID_RE.sub("[ID]", safe)

    for pattern, replacement in _CONTEXTUAL_IDENTIFIER_PATTERNS:
        def ctx_repl(m, r=replacement):
            if not m.groups() or m.group(1) is None:
                return r
            captured = m.group(1)
            tail = ""
            if m.end(1) == m.end(0):
                # (November 2026) In text written in CAPITALS every word
                # looks like a name, so "VIVE EN BILBAO CON SU MADRE" used
                # to swallow "CON SU MADRE". The name now stops at the
                # first small word ("con", "su", "and", "with", ...); the
                # rest is kept.
                words = list(re.finditer(r"\S+", captured))
                for w in words[1:]:
                    if w.group(0).lower().strip(",.;:!?()\"'«»") in _STOPWORDS:
                        captured = captured[:w.start()].rstrip()
                        tail = m.group(1)[len(captured):]
                        break
            # "in English", "en Servicios Sociales": nothing personal there.
            if all(_is_safe_word(t) for t in captured.split()):
                return m.group(0)
            if r == "[PERSON]":
                _record_name_tokens(captured, known_names)
            if m.end(1) == m.end(0):
                # Keep the cue words ("la madre, ...", "vive en ...") so the
                # sentence still makes sense; only the name is replaced.
                return m.group(0)[: m.start(1) - m.start(0)] + r + tail
            return r
        safe = pattern.sub(ctx_repl, safe)
    safe = _ADDRESS_UNIT_RE.sub("[ADDRESS]", safe)

    def title_repl(m):
        _record_name_tokens(m.group(1), known_names)
        return "[PERSON]"

    safe = re.sub(
        rf"\b{_TITLES}\.?\s+({_NAME_TOKEN}(?:\s+{_NAME_TOKEN}){{0,3}})\b",
        title_repl,
        safe,
    )

    safe = _replace_proper_names(safe, known_names)
    safe = _replace_single_names(safe, known_names)
    # Ages again, now that names are tags: "John Hughes, is 41" only
    # looks like an age once the name has become "[PERSON], is 41".
    return _generalise_ages(safe)


# ---------------------------------------------------------------------------
# Text written in CAPITAL LETTERS (November 2026)
# ---------------------------------------------------------------------------
# Most of the rules above recognise a name by its SHAPE: a capital letter
# followed by small letters ("John", "Lucía"). Notes typed with caps lock on
# ("HELLO, JOHN IS A HAPPY CLIENT", "Visita a NEREA AGIRRE") defeat that:
# every word has the same shape, so the name was left in the pilot. (Rules
# with a clear cue -- "LA MADRE, LUCÍA", "VIVE EN BARAKALDO", e-mails, phone
# numbers, DNI -- already worked, because they do not depend on shape.)
#
# This pass builds a copy of the text in which words written in capitals are
# given ordinary capitalisation: known first names and courtesy titles get a
# capital letter, the (up to three) capitalised words that directly follow
# them get one too (surnames), and every other word is put in lower case.
# The original rules then run on that copy, and every word they did NOT
# replace is put back exactly as the practitioner wrote it.
#
# Words in capitals are only touched when they look like shouting: two or
# more of them next to each other, or a single one that is a known first
# name or title. Lone acronyms in normal text (DNI, EDE, NIE) are left alone,
# so ordinary notes behave exactly as before.

_TOKEN_RE = re.compile(r"\w+|[^\w]", re.UNICODE)
# Courtesy titles written in capitals. "DON" and "AND" are left out on
# purpose: in capitals they are far more often English words ("DON'T",
# "JOHN AND MARY") than titles.
_TITLE_WORDS = {"mr", "mrs", "ms", "miss", "dr", "dra", "sr", "sra", "srta",
                "doña", "dña", "jn", "andre", "jaun"}
_MAX_SURNAMES = 3

# Very common words that follow a name in a sentence ("JOHN IS", "MIKEL
# DICE", "NEREA ESAN DU") and so must never be mistaken for a surname.
_NOT_SURNAMES = set("""
is are was were be been has have had will would can could should may might
does did do not very said says told went came lives feels seems wants needs
arrived attended agreed refused called asked explained mentioned reported
also again still always never often now here there who which what why how
dice dijo decía es está estaba era fue ha había han tiene tenía va iba vive
viene vino quiere quería puede podía comenta comentó refiere refirió
manifiesta manifestó explica explicó acude acudió llega llegó trabaja
estudia siente parece necesita pide pidió muy siempre nunca todavía ahora
aquí allí quien quién cual cuál qué cómo cuándo
da dago zen zegoen du zuen dio esan dauka zeukan nahi oso beti inoiz orain
hemen han nor zer nola noiz
""".split())


def _is_caps_word(token: str) -> bool:
    return len(token) >= 2 and token.isalpha() and token.isupper()


def _normalise_capitals(tokens):
    """Same-length list of tokens with shouted words re-cased (see above)."""
    word_positions = [i for i, t in enumerate(tokens) if t.isalpha()]
    shouted = set()
    for n, i in enumerate(word_positions):
        token = tokens[i]
        if not token.isupper() or (i > 0 and tokens[i - 1] == "["):
            continue
        low = token.lower()
        prev_caps = n > 0 and _is_caps_word(tokens[word_positions[n - 1]])
        next_caps = n + 1 < len(word_positions) and _is_caps_word(tokens[word_positions[n + 1]])
        if len(token) == 1:
            # "Y", "A", "O" between shouted words: an ordinary short word.
            if prev_caps and next_caps:
                shouted.add(i)
            continue
        if prev_caps or next_caps or low in _COMMON_FIRST_NAMES or low in _TITLE_WORDS:
            shouted.add(i)

    if not shouted:
        return tokens

    result = list(tokens)
    surnames_left = 0
    for i in word_positions:
        if i not in shouted:
            surnames_left = 0
            continue
        low = tokens[i].lower()
        if len(low) == 1:
            result[i] = low
            surnames_left = 0
        elif low in _COMMON_FIRST_NAMES or low in _TITLE_WORDS:
            result[i] = low.capitalize()
            surnames_left = _MAX_SURNAMES
        elif surnames_left and not _is_safe_word(low) and low not in _NOT_SURNAMES:
            result[i] = low.capitalize()
            surnames_left -= 1
        else:
            result[i] = low
            surnames_left = 0
    return result


def _anonymize_capitals(text: str) -> str:
    tokens = _TOKEN_RE.findall(text)
    if "".join(tokens) != text:      # defensive: never risk losing text
        return text
    shadow = _normalise_capitals(tokens)
    if shadow == tokens:
        return text

    redacted = _TOKEN_RE.findall(_anonymize_core("".join(shadow)))
    restored = _restore_original_case(tokens, shadow, redacted)
    # If the two versions cannot be lined up with certainty, keep the
    # protected copy (in lower case) rather than risk putting a name back.
    return restored if restored is not None else "".join(redacted)


_RESYNC_WINDOW = 400   # tokens one replacement may cover (addresses are long)
_RESYNC_LENGTH = 4     # tokens that must match again after a replacement


def _restore_original_case(original, shadow, redacted):
    """Walk the copy and its redacted version side by side (one pass, so
    even a very long note is quick). Identical tokens are taken from the
    ORIGINAL (capitals as written); each replacement made by the rules is a
    bracketed tag such as [PERSON], taken from the redacted version, after
    which the two are lined up again. Returns None if they cannot be."""
    pieces = []
    i = j = 0
    n_shadow, n_redacted = len(shadow), len(redacted)
    while i < n_shadow and j < n_redacted:
        if shadow[i] == redacted[j]:
            pieces.append(original[i])
            i += 1
            j += 1
            continue
        # A replacement starts here: copy the tag from the redacted text.
        if redacted[j] != "[":
            return None
        close = _find_tag_end(redacted, j)
        if close is None:
            return None
        pieces.extend(redacted[j:close + 1])
        j = close + 1
        # The few tokens after the tag, up to the next tag, show where the
        # copy picks up again. A replacement always covers at least one
        # token, so the search starts one token further on.
        tail = []
        k = j
        while k < n_redacted and len(tail) < _RESYNC_LENGTH and redacted[k] != "[":
            tail.append(redacted[k])
            k += 1
        if not tail:
            if j >= n_redacted:
                i = n_shadow
                break
            continue          # another tag follows straight away
        for ii in range(i + 1, min(n_shadow, i + _RESYNC_WINDOW) + 1):
            if shadow[ii:ii + len(tail)] == tail:
                i = ii
                break
        else:
            return None
    if j < n_redacted:
        pieces.extend(redacted[j:])
    elif i < n_shadow:
        pieces.extend(original[i:])
    return "".join(pieces)


def _find_tag_end(tokens, start):
    """Index of the "]" closing the tag that starts at tokens[start]."""
    for k in range(start + 1, min(len(tokens), start + 4)):
        if tokens[k] == "]":
            return k
    return None

