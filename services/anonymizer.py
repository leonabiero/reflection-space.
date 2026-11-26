"""Privacy boundary for text that may leave Reflection Space.

This module intentionally uses a layered, deterministic approach rather than
claiming that a handful of regular expressions can make arbitrary social-work
narratives anonymous. It removes common direct identifiers, contextual
identifiers, and conservative proper-name phrases before text reaches Claude.

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

26 November 2026 -- EDE testers' reports
----------------------------------------
* Identity-document numbers (NIE, DNI/NIF, passport) are hidden in every
  written form -- spaces, dots, dashes, slashes, small letters, glued to
  the next word as in PDFs -- and after Spanish, Basque and English labels
  ("Nº de Identificación", "Número de documento", "NAN zenbakia", "ID
  number" ...). Dates written year first ("1989/11/19") are hidden too.
* People are numbered by first name AND surname, compared without accents
  or capitals: two people who share a surname are never merged, and one
  person keeps one number however she is written (see PersonNumbers). A
  word that could belong to two people becomes [PERSON] with no number.
* A name split over a line break is one placeholder (not one per line).
* Headings and field labels of forms ("Datos Personales", "Apellidos",
  "Doc.", "Fdo.") are no longer counted as people; the names after them
  are still hidden, including names typed in small letters after a
  "Nombre y apellidos:" label.

The function is idempotent: anonymizing already-anonymized text changes
nothing (callers rely on this, because it
re-anonymizes excerpts that were already anonymized at index time).
"""

import re

_UPPER = "A-ZÀ-ÖØ-Þ"
_LOWER = "a-zß-öø-ÿ"
_NAME_TOKEN = r"[A-ZÀ-ÖØ-Þ][A-Za-zÀ-ÖØ-öø-ÿ]*(?:['’\-][A-ZÀ-ÖØ-Þ][A-Za-zÀ-ÖØ-öø-ÿ]*)*"
# (November 2026) A name may continue on the next line ("LUCÍA" / "GARCÍA"),
# so it is still matched across a line break -- but each line gets its own
# placeholder and the line break is kept (see _tag_lines).
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
    # (18 November 2026) Kinds of service, not names: "Centro de Salud
    # Mental de Uribarri" keeps "Centro de Salud Mental"; only the place
    # name after it is removed (see _PLACE_NOUNS).
    "centro", "hospital", "clínica", "clinica", "ambulatorio",
    # Languages / nationalities (capitalised in English)
    "english", "spanish", "basque", "french", "euskera", "euskara",
    "castellano", "español", "inglés", "ingles", "francés",
    # English calendar words
    "monday", "tuesday", "wednesday", "thursday", "friday", "saturday",
    "sunday", "january", "february", "march", "april", "may", "june",
    "july", "august", "september", "october", "november", "december",
    # (November 2026) Ordinary words of social-services reports that are
    # often written with a capital letter in headings ("Informe de
    # seguimiento – Alojamiento social", "Profesional de referencia: ...").
    # In the pilot "Alojamiento" was hidden as if it were a name.
    "alojamiento", "seguimiento", "informe", "profesional", "referencia",
    "intervención", "intervencion", "valoración", "valoracion", "vivienda",
    "acogida", "acompañamiento", "acompanamiento", "proyecto", "programa",
    "objetivo", "objetivos", "situación", "situacion", "área", "area",
    "equipo", "recurso", "recursos", "inclusión", "inclusion", "empleo",
    "formación", "formacion", "orientación", "orientacion", "atención",
    "atencion", "derivación", "derivacion", "diagnóstico", "diagnostico",
    "tutora", "tutor", "educadora", "educador", "trabajadora", "trabajador",
    "técnica", "tecnica", "técnico", "tecnico", "coordinadora", "coordinador",
    "fecha", "motivo", "resumen", "conclusiones", "antecedentes",
    "txostena", "jarraipena", "etxebizitza", "harrera", "erreferentzia",
    "profesionala", "egoera", "helburuak",
    "follow-up", "housing", "referral", "assessment", "summary", "background",
    # (24 November 2026, product owner) Generic words of public-service
    # names: "Servicio de Atención Familiar" became "Servicio de [PERSONA 1]"
    # because "Familiar" was not known, and every later "Familiar" was then
    # hidden too. A service name made ONLY of these words identifies nobody
    # and stays visible; one that also contains a name becomes
    # [ORGANISATION] (see _SERVICE_NAME_RE).
    "familiar", "familiares", "comunitario", "comunitaria", "comunitarios",
    "primaria", "básica", "basica", "básicos", "basicos", "base", "urgencias",
    "urgencia", "emergencia", "emergencias", "protección", "proteccion",
    "mujer", "mujeres", "igualdad", "adicciones", "drogodependencias",
    "prevención", "prevencion", "inserción", "insercion", "dependencia",
    "discapacidad", "mayores", "juventud", "adolescencia", "integral",
    "especializado", "especializada", "especializados", "psicosocial",
    "socioeducativo", "socioeducativa", "educativo", "educativa",
    "terapéutico", "terapeutico", "terapéutica", "terapeutica", "día", "dia",
    "unidad", "departamento", "oficina", "instituto", "punto", "encuentro",
    "acción", "accion", "bienestar", "servicio", "personas", "hogar",
    "zerbitzua", "zerbitzuak", "arreta", "arretarako",
    # (26 November 2026, EDE testers) Headings and field labels of forms
    # and reports ("Datos Personales", "Nombre y Apellidos:", "Nº de
    # Identificación:"). Each one was hidden as a separate new person, so
    # a report about one woman showed dozens of "people" (worse with PDF
    # uploads). They are ordinary words; the names and numbers written
    # AFTER them are still hidden by every other rule.
    "datos", "dato", "personales", "nombre", "nombres", "apellido", "apellidos",
    "identificación", "identificacion", "identidad", "nacionalidad", "domicilio",
    "teléfono", "telefono", "teléfonos", "telefonos", "móvil", "movil", "sexo",
    "género", "genero", "civil", "observaciones", "documento", "nacimiento",
    "lugar", "edad", "correo", "electrónico", "electronico", "firma", "expediente",
    "número", "numero", "contacto", "dirección", "direccion", "municipio",
    "provincia", "código", "codigo", "postal", "composición", "composicion",
    "convivencia", "ingresos", "económica", "economica", "laboral", "sanitaria",
    "personal", "pasaporte", "parentesco", "documentos", "documentación",
    "documentacion", "responsable", "firmado", "económico", "economico",
    "apoyo", "apoyos", "riesgo", "exclusión", "exclusion", "violencia",
    "machista", "género", "consulado", "embajada", "grado", "apto", "apta",
    "penales", "judicial", "jurídica", "juridica", "residencial", "convivencial",
    "ámbito", "ambito", "metodología", "metodologia", "solicitud", "propuesta",
    "izena", "abizena", "abizenak", "jaiotze", "jaioteguna", "helbidea",
    "telefonoa", "nazionalitatea", "sexua", "oharrak", "datuak", "pertsonalak",
    "nortasun", "agiria", "zenbakia", "zbkia", "identifikazio", "sinadura",
    "kontaktua", "egilea", "eskaera", "proposamena",
    "name", "surname", "surnames", "nationality", "phone", "telephone", "mobile",
    "details", "gender", "observations", "date", "birth", "identity", "document",
    "number", "address", "passport",
}

# (24 November 2026) Public-service names: a kind of service, "de", then
# capitalised words ("Servicio de Atención Familiar", "Centro de Día
# Arrupe"). Only used to spot a NAME glued to the generic words, which
# turns the whole service name into [ORGANISATION]; see _service_names.
_SERVICE_HEADS = (r"(?:Servicios?|Centro|Unidad|Programa|Equipo|Área|Area|Oficina|"
                  r"Departamento|Instituto|Punto|Plan|Comisión|Sección|Red)")
_SERVICE_CONNECTORS = {"de", "del", "la", "las", "los", "y", "e", "a", "al", "para"}
_SERVICE_NAME_RE = re.compile(
    rf"\b{_SERVICE_HEADS}\s+(?:de|del|para)\s+"
    rf"(?:la\s+|las\s+|los\s+)?{_NAME_TOKEN}"
    rf"(?:\s+(?:(?:de|del|la|las|los|y|e|a|al|para)\s+)*{_NAME_TOKEN})*"
)

# (November 2026, EDE) Origin, nationality and religion are deliberately
# LEFT VISIBLE, because they are where bias tends to hide. In English
# (and in Spanish at the start of a sentence) these words are written with
# a capital letter, so without this list "procedente de Marruecos",
# "llegó de Senegal" or "a Moroccan woman" lost the origin to [LOCATION] or
# [PERSON]. Towns and cities of residence are still hidden (_KNOWN_PLACES).
# Compared in lower case; Basque case endings are understood too
# ("Marokotik", "Errumaniako").
_ORIGIN_AND_BELIEF_WORDS = set("""
marruecos maroko morocco argelia aljeria algeria túnez tunez tunisia túnez
senegal mali malí gambia guinea nigeria ghana camerún camerun cameroon
mauritania sáhara sahara costa marfil ivory coast etiopía etiopia ethiopia
eritrea somalia sudán sudan egipto egypt libia libya kenia kenya congo angola
rumanía rumania errumania romania bulgaria ukrania ucrania ukraine ukraina
rusia errusia russia georgia moldavia moldova polonia polonia poland albania
portugal francia frantzia france italia italy alemania germany
españa espainia spain
colombia kolonbia venezuela ecuador ekuador perú peru bolivia paraguay
uruguay argentina chile txile brasil brazil honduras nicaragua guatemala
cuba kuba méxico mexico mexiko dominicana república republica dominican
republic panamá panama
pakistán pakistan bangladés banglades bangladesh india china txina siria
syria afganistán afganistan afghanistan irak iraq irán iran turquía turkey
filipinas philippines nepal
áfrica africa afrika europa europe asia américa america amerika
latinoamérica latinoamerica latinoamerika latin magreb maghreb
sudamérica sudamerica centroamérica centroamerica caribe caribbean
subsahariana subsahariano subsaharan oriente próximo medio east middle
moroccan moroccans algerian algerians romanian romanians ukrainian
ukrainians russian russians colombian colombians venezuelan venezuelans
peruvian peruvians bolivian bolivians ecuadorian ecuadorians honduran
hondurans nicaraguan nicaraguans senegalese nigerian nigerians ghanaian
malian guinean pakistani pakistanis syrian syrians afghan afghans chinese
indian african africans arab arabs arabic latino latina latinos latinas
european europeans georgian georgians bulgarian bulgarians portuguese
gitano gitana gitanos gitanas roma romani gypsy gypsies
muslim muslims musulmán musulman musulmana islam islamic islámica islámico
catholic catholics católico católica catolico catolica jewish jew jews
hindu buddhist evangelical evangelicals protestant protestants orthodox
ortodoxa ortodoxo sikh ramadán ramadan
""".split())

_ORIGIN_SUFFIXES = ("ko", "koa", "koak", "tik", "etik", "ra", "ara", "era", "n", "en",
                    "an", "rako", "ar", "arra", "tar", "tarra", "tarrak")


def _is_origin_or_belief_word(word: str) -> bool:
    low = word.lower().strip(",.;:!?()\"'«»")
    if low in _ORIGIN_AND_BELIEF_WORDS:
        return True
    return any(low.startswith(w) and low[len(w):] in _ORIGIN_SUFFIXES
               for w in _ORIGIN_AND_BELIEF_WORDS if len(w) >= 5)

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
    # 18 November 2026: services named after their place ("centro de salud
    # mental de Uribarri", "CSM de Deusto"): the place is tagged
    # [LOCATION] instead of [PERSON].
    "mental", "csm", "hospital", "clínica", "clinica", "ambulatorio",
    # 24 November 2026: "colegio de Santutxu" -- the school's neighbourhood
    # is a place, not a person. A known first name after it ("el colegio de
    # Ane", i.e. Ane's school) is still a person (_COMMON_FIRST_NAMES).
    "colegio", "escuela", "ikastola", "instituto", "guardería", "guarderia",
    "residencia",
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
santutxu deusto uribarri txurdinaga otxarkoaga rekalde errekalde errekaldeberri
abando indautxu basurto zorrotza zorroza bolueta atxuri miribilla zurbaran
zurbaranbarri iralabarri masustegi altamira ibaiondo abusu solokoetxe
zorrotzaurre elorrieta arangoiti matiko castaño zabala amezola larraskitu
uretamendi peñascal sarriko ibarrekolanda
""".split())
# (24 November 2026) Bilbao neighbourhoods were added above ("colegio de
# Santutxu" became [PERSON]). "Begoña" is left out on purpose: it is also a
# common first name, so it stays treated as a person (the safer choice).
_KNOWN_PLACE_PHRASES = {"san sebastián", "san sebastian", "vitoria-gasteiz", "castro urdiales",
                        "bilbao la vieja", "san ignacio", "ciudad jardín", "ciudad jardin",
                        "san adrián", "san adrian", "la peña", "otxarkoaga-txurdinaga"}
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
    # (26 November 2026) Also the Basque "Kale" written before the name
    # ("Kale Nagusia 12"), as on bilingual forms.
    (re.compile(r"(?:\b(?i:calle|avenida|avda|plaza|paseo|pasaje|camino|carretera|barrio|travesía|ronda|kalea|kale|etorbidea|plaza|pasealekua|auzoa)\.?|(?<!\w)(?i:c/|av\.|pza\.))\s*(?:(?i:de|del|de\s+la|de\s+los)\s+)?(?:[A-ZÀ-ÖØ-Þ][\wÀ-ÿ'’\-]*|\d+[\wºª]*)(?:\s+(?:[A-ZÀ-ÖØ-Þ][\wÀ-ÿ'’\-]*|\d+[\wºª\-]*|(?i:de|del|la|los|las|n[º°o]\.?|s/n|bis))(?=\s|$|[,.;:!?)]))*"), "[ADDRESS]"),
    (re.compile(r"\b(?:domicilio|dirección|direccion|helbidea)\s*(?::|\s+(?:en|es|:))\s*%s" % _ADDRESS_BODY_ES_EU, re.IGNORECASE), "[ADDRESS]"),
]

# (November 2026) Floor, door, staircase... right after an address are part
# of it: "[ADDRESS], 2º izquierda", "[ADDRESS] 3ºB", "[ADDRESS], bajo",
# "[ADDRESS], 2. ezkerra", "[ADDRESS], flat 4". Applied after every address
# rule above.
# (24 November 2026) Also the official spelling with a dot before the
# ordinal sign: "3.º izquierda", "3.ª", "3.º B", "3.º-izda.". A full stop
# that ends the sentence is left in place ("..., 3.º dcha. Sin cambios").
_ABBR_DOT = r"(?:\.(?!\s+[A-ZÀ-Þ]))?"
_ADDRESS_UNIT_RE = re.compile(
        r"\[ADDRESS\](?:\s*,?\s*(?:(?:\d+\s*)?\.?\s*[ºª°](?:\.(?=\s*-?\s*(?:[a-z]|[A-Z](?!\w))))?\s*-?\s*(?:[A-Za-z](?!\w)"
        rf"|(?i:izquierda|izqda{_ABBR_DOT}|izda{_ABBR_DOT}|izq{_ABBR_DOT}|derecha|dcha{_ABBR_DOT}|drcha{_ABBR_DOT}|centro|ezkerra|eskuina|ezk{_ABBR_DOT}|esk{_ABBR_DOT}))?"
        rf"|\d+\.\s*(?i:ezkerra|eskuina|ezk{_ABBR_DOT}|esk{_ABBR_DOT})"
        r"|(?i:bajo|entresuelo|ático|atico)(?!\w)"
        r"|(?i:piso|puerta|escalera|esc\.|portal|solairua|atea|flat|apartment|apt\.?)\s+[\wºª]+))+"
    )

# The complete identifier label must end at a word boundary. In particular,
# plain `ref` must NOT match the beginning of words such as "referral".
_IDENTIFIER_RE = re.compile(
    r"\b(?:case\s*(?:reference|ref|number|no|id)|client\s*(?:id|number|no)|national\s*(?:id|number|no)|identifier|reference|ref"
    r"|dni|nie|nif|pasaporte|passport|tarjeta\s+sanitaria|tis|n[º°o]\.?\s*(?:de\s+)?expediente|expediente|n[úu]mero\s+de\s+(?:caso|expediente|usuario|usuaria)|referencia|nss|n[º°o]\.?\s*(?:de\s+)?(?:la\s+)?seguridad\s+social|espediente(?:a)?|zenbakia|nan)"
    # (November 2026) The value must contain at least one digit: every
    # real identifier does, while "Profesional de referencia: Ane
    # Etxeberria" was being hidden as "[ID]" (the word after the label was
    # an ordinary word or a name, not a number).
    r"\b\s*[:#\-]?\s*(?:(?:es|n[º°o]\.?|número|numero)\s*[:\-]?\s*)?(?=[A-Za-z/_\-.]*\d)[A-Za-z0-9][A-Za-z0-9/_\-.]{2,}\b",
    re.IGNORECASE,
)
# Spanish DNI (8 digits + letter) and NIE (X/Y/Z + 7 digits + letter).
_DNI_NIE_RE = re.compile(r"(?<!\w)(?:\d{8}|[XYZxyz][\s\-]?\d{7})[\s\-]?[A-Za-z](?!\w)")

# (26 November 2026, EDE testers) Identity-document numbers in every form
# they reach us, whatever label is in front of them (or none):
#   NIE      X/Y/Z + 7 digits + letter   "Y1235687X", "y-1235687-x"
#   DNI/NIF  8 digits + letter           "12345678Z", "12.345.678-Z", "12 345 678 z"
#   passport 3 capital letters + 6 digits "PAA123456", or 2 + 7 "AB1234567"
# Spaces, dots, hyphens, dashes and slashes between the parts are allowed,
# in capitals or not, and the check letter is never checked (made-up test
# numbers are hidden too). Text copied from a PDF often glues the number
# to the next label ("Y1235687XTeléfono"), so a number followed directly
# by a capitalised word is still found. Phone numbers, postcodes, ages,
# years and amounts have no letter in the right place and are not touched.
_ID_SEP = "[ \t.\\-‐‑‒–—/]"
_ID_END = r"(?=$|[^0-9A-Za-zÀ-ÿ]|[A-ZÀ-Þ][a-zß-ÿ])"
_ID_DOCUMENT_RE = re.compile(
    r"(?<![0-9A-Za-zÀ-ÿ])(?:"
    rf"(?P<nie>(?P<nie_first>[XYZxyz])(?P<nie_gap>{_ID_SEP}?)\d(?:{_ID_SEP}?\d){{6}}(?P<nie_tail>{_ID_SEP}?)(?P<nie_last>[A-Za-z]))"
    rf"|(?P<dni>\d{{2}}[ .]?\d{{3}}[ .]?\d{{3}}(?P<dni_tail>{_ID_SEP}?)(?P<dni_last>[A-Za-z]))"
    rf"|(?P<passport>[A-Z]{{3}}{_ID_SEP}?\d{{6}}(?![0-9])|[A-Z]{{2}}{_ID_SEP}?\d{{7}}(?![0-9]))"
    rf"){_ID_END}"
)
# One small letter after a space that is more likely an ordinary word
# ("y", "a", "e", "o", "u": "12 345 678 y ...") than the check letter of
# a number.
_ID_WORD_LETTERS = set("yaeou")


def _hide_id_documents(text: str) -> str:
    def repl(m):
        if m.group("nie"):
            # "y 1234567 a ...": the Spanish word "y", not an NIE.
            if m.group("nie_first") in _ID_WORD_LETTERS and m.group("nie_gap").isspace():
                return m.group(0)
            if m.group("nie_last") in _ID_WORD_LETTERS and m.group("nie_tail").isspace():
                return m.group(0)
        if m.group("dni") and m.group("dni_last") in _ID_WORD_LETTERS and m.group("dni_tail").isspace():
            return m.group(0)
        # Glued to the next word in the original ("...XTeléfono"): keep the
        # two apart.
        glued = m.end() < len(m.string) and m.string[m.end()].isalpha()
        return "[ID] " if glued else "[ID]"
    return _ID_DOCUMENT_RE.sub(repl, text)


# Labels that name an identity document ("Nº de Identificación", "Número
# de documento", "NAN zenbakia", "ID number" ...). After one of them, a
# value with at least four digits is hidden; the label itself stays, so
# the sentence still reads "Nº de Identificación: [ID]".
_ID_LABEL_RE = re.compile(
    r"(?P<label>\b(?:"
    r"n\.?\s*[º°or]\.?\s*(?:de\s+)?identif(?:icaci[oó]n|\.)?"
    r"|n[úu]mero\s+de\s+(?:documento|identidad|identificaci[oó]n|pasaporte)(?:\s+de\s+identidad)?"
    r"|documento(?:\s+nacional)?(?:\s+de\s+identidad)?"
    r"|identificaci[oó]n|(?-i:TIE)"
    r"|pasaportea|pasaporte(?:aren)?\s+zenbakia"
    r"|nan\s+zenbakia|nortasun[\s\-]+agiri(?:a|aren\s+zenbakia)?|identifikazio[\s\-]+zenbaki(?:a)?"
    r"|(?-i:ID)\s*(?:number|no\.?|n[º°]|card)?|id\s+(?:number|no\.?|card)"
    r"|identity\s+(?:card|document|number)(?:\s+number)?|document\s+(?:number|no\.?)"
    # Short forms of "expediente" (case file) in forms: "Nr. de expdt.".
    r"|expdte?|espdt|exp"
    r")\.?(?![\wÀ-ÿ])\s*[:#|\-]?\s*(?:(?:es|n[º°o]\.?|número|numero|zenbakia|number)\s*[:\-]?\s*)?)"
    # The value: digits and letters, possibly in parts ("Y-1235687-X",
    # "2025- ABC-164-01", "12 345 678 Z"). A part without digits is only
    # taken when joined by a dash, slash or dot, so the words after the
    # number are never swallowed.
    rf"(?P<value>(?:[A-Za-z]{{1,3}}{_ID_SEP}?)?\d[0-9A-Za-z]*"
    "(?:(?:[ \t]?[\\-/‐-—][ \t]?|\\.)[0-9A-Za-z]+|[ \t]+[0-9A-Za-z]*\\d[0-9A-Za-z]*)*"
    r"(?:[ \t][A-Za-z](?![0-9A-Za-zÀ-ÿ]))?)"
    r"(?![0-9A-Za-zÀ-ÿ])",
    re.IGNORECASE,
)


def _hide_labelled_ids(text: str) -> str:
    def repl(m):
        value = m.group("value")
        if sum(c.isdigit() for c in value) < 4:
            return m.group(0)
        rest = ""
        # "... 12 345 678 y su madre": "y" is the word "y", not a letter
        # of the number.
        if len(value) >= 2 and value[-2] in " \t" and value[-1] in _ID_WORD_LETTERS:
            rest = value[-2:]
        return m.group("label") + "[ID]" + rest
    return _ID_LABEL_RE.sub(repl, text)


# The check letter left after an [ID] ("NAN: 12345678 z" -> "[ID] z").
_ID_LEFTOVER_LETTER_RE = re.compile(r"\[ID\](?:[\-.‐‑–/]|(?P<space>[ \t]))?(?P<letter>[A-Za-z])(?![0-9A-Za-zÀ-ÿ])")


def _absorb_id_letters(text: str) -> str:
    def repl(m):
        if m.group("space") and m.group("letter") in _ID_WORD_LETTERS:
            return m.group(0)
        return "[ID]"
    return _ID_LEFTOVER_LETTER_RE.sub(repl, text)
# IBAN bank accounts (e.g. ES91 2100 0418 4502 0005 1332).
_IBAN_RE = re.compile(r"(?<!\w)[A-Z]{2}\d{2}(?:[ ]?[A-Z0-9]{4}){3,7}(?:[ ]?[A-Z0-9]{1,4})?(?!\w)")
_EMAIL_RE = re.compile(r"\b[\w.+-]+@[\w-]+(?:\.[\w-]+)+\b", re.UNICODE)
_DATE_RE = re.compile(
    r"\b(?:\d{1,2}[/.-]\d{1,2}[/.-]\d{2,4}|\d{1,2}\s+(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:t(?:ember)?)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+\d{2,4}|\d{1,2}\s+de\s+(?:enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|setiembre|octubre|noviembre|diciembre)\s+(?:de|del)\s+\d{2,4}"
    # Basque: "2025eko martxoaren 21ean" / "2025eko martxoaren 21a".
    r"|\d{4}(?:eko|ko)\s+(?:urtarrila|otsaila|martxoa|apirila|maiatza|ekaina|uztaila|abuztua|iraila|urria|azaroa|abendua)(?:ren|aren)?\s+\d{1,2}(?:ean|an|a)?)\b",
    re.IGNORECASE,
)
# (26 November 2026, EDE testers) Dates written year first, as forms and
# exported files often do: "1989/11/19", "1966-02-02", "2024.05.03".
_YEAR_FIRST_DATE_RE = re.compile(r"(?<![\w/.\-])(?:19|20)\d{2}([/.\-])(?:0?[1-9]|1[0-2])\1(?:0?[1-9]|[12]\d|3[01])(?![\w/\-]|\.\d)")
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
    return (low in _SAFE_CAPITALISED_WORDS or low in _STOPWORDS
            or _is_origin_or_belief_word(low))


def _record_name_tokens(phrase: str, known_names: set) -> None:
    """Remember each real name token of a redacted person phrase."""
    for token in phrase.split():
        token = token.strip(",.;:!?()\"'«»")
        if len(token) >= 2 and not _is_safe_word(token) and not token.isupper():
            known_names.add(token)


# Accented letters and their plain letter, for COMPARING names only. An
# explicit table (not a general accent remover): accents in the text that
# is shown and sent are never touched (see tests/test_accents_preserved.py).
_FOLD_TABLE = str.maketrans("áàâäãåéèêëíìîïóòôöõúùûüçñ", "aaaaaaeeeeiiiiooooouuuucn")


def _fold(word: str) -> str:
    """A name word for COMPARING only: lower case, no accents
    ("María" / "MARIA" / "maria" -> "maria"). The text shown is never
    changed by this."""
    return str(word or "").lower().translate(_FOLD_TABLE)


# (26 November 2026) Short forms of first names, for comparing only.
_NAME_SHORT_FORMS = {"mª": "maria", "m.ª": "maria", "mª.": "maria", "m.ª.": "maria"}


class PersonNumbers:
    """Which number each person has in one text (November 2026, EDE):
    different people become [PERSON 1], [PERSON 2], ...; the same person
    always keeps the same number.

    (26 November 2026, EDE testers) Each person is remembered as first
    name(s) plus surname(s), compared without accents or capitals:
      - "Javier Ortiz" and "Laura Ortiz" are two people: different first
        names are never merged, whatever surname they share.
      - "María Goikoetxea", "María", "Maria", "MARÍA", "Sra. Goikoetxea"
        and "Goikoetxea Ruiz" are one person.
      - A word that could belong to two different people (a surname shared
        by two people, or a first name two people have) is still hidden,
        as [PERSON] with no number: the app does not guess which of them
        is meant.

    It holds real names, so it lives only in memory (the browser session
    of one reflection) and is never saved or sent anywhere. Pass the same
    object again (e.g. for the messages of "Explore with the companion")
    so the same name gets the same number as in the document."""

    def __init__(self):
        self._people = {}       # number -> {"given": set, "surnames": set, "loose": set}
        self._surname_givens = {}   # surname -> first names seen with it (from a first look at the text)
        self.last = 0           # highest number given so far

    def _state(self):
        # An object kept from an older version of the app has no _people.
        if not hasattr(self, "_people"):
            self._people = {}
        if not hasattr(self, "_surname_givens"):
            self._surname_givens = {}
        return self._people

    @staticmethod
    def _tokens(phrase):
        words = []
        for token in str(phrase or "").split():
            low = token.lower()
            if low in _NAME_SHORT_FORMS:
                words.append(_NAME_SHORT_FORMS[low])
                continue
            token = _fold(token.strip(",.;:!?()\"'«»"))
            if (token and token not in _STOPWORDS_FOLDED
                    and token.rstrip(".") not in _TITLE_WORDS_FOLDED):
                words.append(token)
        return words

    def look_ahead(self, text):
        """A first look at the whole text, before anything is replaced:
        which first names go with which surname ("Javier Ortiz", "Laura
        Ortiz"). Used only so that a surname written alone ("la Sra.
        Ortiz") is never given one person's number when the text has two
        different people with that surname, wherever they appear."""
        self._state()
        for m in _NAME_SEQUENCE_RE.finditer(str(text or "")):
            words = self._tokens(m.group(0))
            given = [w for w in words if w in _FIRST_NAMES_FOLDED]
            if not given:
                continue
            for w in words:
                if w not in _FIRST_NAMES_FOLDED:
                    self._surname_givens.setdefault(w, set()).update(given)

    def _new(self, given, surnames, loose):
        self.last += 1
        self._people[self.last] = {"given": set(given), "surnames": set(surnames), "loose": set(loose)}
        return self.last

    @staticmethod
    def _all_words(p):
        return p["given"] | p["surnames"] | p["loose"]

    def number_for(self, phrase):
        """The person's number, or None when the phrase could belong to
        more than one person (shown as [PERSON] with no number)."""
        people = self._state()
        words = self._tokens(phrase)
        if not words:
            words = [_fold(str(phrase or "").strip()) or "?"]
        wordset = set(words)

        # Same words as one known person (in any order, or fewer of them):
        # "Goikoetxea Ruiz" after "María Goikoetxea Ruiz".
        subset = [n for n, p in people.items() if wordset <= self._all_words(p)]
        given = [w for w in words if w in _FIRST_NAMES_FOLDED]

        if len(words) == 1 and not given:
            # One word that is not a known first name: a surname or an
            # unusual first name.
            word = words[0]
            if len(self._surname_givens.get(word, ())) >= 2 or len(subset) > 1:
                return None         # e.g. "Ortiz" with Javier and Laura Ortiz
            if len(subset) == 1:
                return subset[0]
            return self._new((), (), (word,))

        if not given:
            if len(subset) == 1:
                return subset[0]
            if len(subset) > 1:
                return None
            if all(w in self._surname_givens for w in words):
                # Surnames only ("Goikoetxea Ruiz"): the person whose
                # surnames they are, if there is exactly one.
                owners = set.intersection(*(self._surname_givens[w] for w in words))
                matches = [n for n, p in people.items() if p["given"] & owners
                           and wordset & p["surnames"]]
                if len(owners) >= 2 or len(matches) > 1:
                    return None
                if len(matches) == 1:
                    people[matches[0]]["surnames"].update(wordset)
                    return matches[0]
                return self._new((), wordset, ())
            # An unknown first name followed by surnames ("Oumar Diallo").
            given = [words[0]]
        given = set(given)
        surnames = wordset - given

        candidates = []
        for n, p in people.items():
            if p["given"] and not (p["given"] & given):
                continue            # different first names: never the same person
            if p["given"]:
                if p["surnames"] and surnames and not (p["surnames"] & surnames):
                    continue        # same first name, different surnames
            elif not (self._all_words(p) & wordset):
                continue
            candidates.append(n)

        if len(candidates) == 1:
            p = people[candidates[0]]
            # Learn the rest of the name, unless that would make it clash
            # with someone else.
            for w in given:
                if w in p["loose"]:
                    p["loose"].discard(w)
                p["given"].add(w)
            for w in surnames:
                if w in p["loose"]:
                    p["loose"].discard(w)
                p["surnames"].add(w)
            return candidates[0]
        if len(candidates) > 1:
            if not surnames:
                return None         # "Ane" when two people are called Ane
            exact = [n for n in candidates if surnames <= people[n]["surnames"]]
            if len(exact) == 1:
                return exact[0]
            return None
        return self._new(given, surnames, ())

    def tag(self, phrase):
        number = self.number_for(phrase)
        return "[PERSON]" if number is None else f"[PERSON {number}]"

    def renumber(self, mapping):
        """Apply {old number: new number} to everything remembered."""
        people = self._state()
        self._people = {mapping.get(n, n): p for n, p in people.items()}


_TITLE_WORDS_LOWER = {"mr", "mrs", "ms", "miss", "dr", "dra", "sr", "sra", "srta",
                      "don", "doña", "dña", "d", "jn", "and", "andre", "jaun"}
# Compared without accents (see _fold). "señor" / "señora" written in
# full count as titles here too, so "la señora Goikoetxea" is the same
# person as "Goikoetxea".
_TITLE_WORDS_FOLDED = {_fold(w) for w in _TITLE_WORDS_LOWER} | {"senor", "senora", "senorita"}
_STOPWORDS_FOLDED = {_fold(w) for w in _STOPWORDS}
_FIRST_NAMES_FOLDED = {_fold(w) for w in _COMMON_FIRST_NAMES}

_LINE_BREAK_RE = re.compile(r"(\s*\n\s*)")


def _first_names_in(words):
    return {_fold(w.strip(",.;:!?()\"'«»")) for w in words} & _FIRST_NAMES_FOLDED


def _join_name_lines(phrase, classify, people, known_names=None):
    """(26 November 2026, EDE testers) A name phrase that runs across one
    or more line breaks, as text copied from a PDF often does ("María" /
    "Goikoetxea"), becomes ONE placeholder, and the line break is kept.
    (Since 23 November each line got its own placeholder, so one person
    looked like two -- or got two numbers.) The lines are only kept apart
    when the next line starts with a DIFFERENT first name: "Ane
    Etxeberria" / "Fatima Benali" on two lines are still two people. A
    line made only of ordinary words ("Informe") is kept as it is.

    `classify(line)` returns ("keep", text) for a line that is not a name,
    ("text", replacement) for a finished replacement (e.g. a place), or
    ("name", lead, core) for a name, where `lead` is kept in front."""
    parts = _LINE_BREAK_RE.split(phrase)
    lines, seps = parts[0::2], parts[1::2]
    out = []                    # finished pieces
    group = None                # {"lead": str, "cores": [..], "seps": [..]}

    def flush():
        nonlocal group
        if group is None:
            return
        core = " ".join(group["cores"])
        if known_names is not None:
            _record_name_tokens(core, known_names)
        tag = people.tag(core)
        # The same person straight after on the previous line(s): one tag.
        if (tag != "[PERSON]" and len(out) >= 2 and out[-2].endswith(tag)
                and not out[-1].strip() and not group["lead"]):
            out[-2] = out[-2][: -len(tag)]
        out.append("".join(group["seps"]) + group["lead"] + tag)
        group = None

    for i, line in enumerate(lines):
        sep = seps[i - 1] if i else ""
        kind = classify(line) if line.strip() else ("keep", line)
        if (kind[0] == "name" and group is None and i and not kind[1]
                and len(kind[2].split()) == 1 and not _first_names_in(kind[2].split())):
            # One capitalised word at the start of a line, after a line
            # that is not a name (a heading such as "ÁMBITO PERSONAL" /
            # "Mantiene ..."): the start of a sentence, treated like any
            # other sentence start -- it is still hidden later if it is a
            # known first name or is written as a name elsewhere in the
            # text (_replace_single_names).
            kind = ("keep", line)
        if kind[0] == "name":
            lead, core = kind[1], kind[2]
            starts_other = False
            if group is not None:
                given_before = _first_names_in(" ".join(group["cores"]).split())
                first = core.split()[0] if core.split() else ""
                starts_other = (bool(given_before) and bool(_first_names_in([first]))
                                and not (_first_names_in([first]) & given_before))
            if group is not None and not lead and not starts_other:
                group["cores"].append(core)
                group["seps"].append(sep)
                continue
            flush()
            out.append(sep)
            group = {"lead": lead, "cores": [core], "seps": []}
        else:
            flush()
            out.append(sep)
            out.append(kind[1])
    flush()
    return "".join(out)


def _tag_lines(phrase, people, known_names=None):
    """The placeholder for a person phrase (see _join_name_lines for a
    phrase that runs across a line break)."""
    if "\n" not in phrase:
        return people.tag(phrase)

    def classify(line):
        if all(_is_safe_word(t.strip(",.;:!?()\"'«»")) for t in line.split()):
            return ("keep", line)
        return ("name", "", line)

    return _join_name_lines(phrase, classify, people, known_names)


def _replace_proper_names(text: str, known_names: set, people=None) -> str:
    """Redact conservative multi-token names plus complex single names."""
    people = people if people is not None else PersonNumbers()
    def repl(match):
        phrase = match.group(0)
        # (26 November 2026) A form abbreviation on the next line ("Edurne
        # Alonso" / "Fdo.: ____") is not part of the name above it.
        if "\n" in phrase and _ABBREVIATION_AFTER_RE.match(match.string, match.end()):
            cut = phrase.rfind("\n")
            last = phrase[cut + 1:].strip()
            if len(last.split()) == 1 and len(last) <= 6:
                head_end = cut
                while head_end > 0 and phrase[head_end - 1].isspace():
                    head_end -= 1
                return _process(phrase[:head_end]) + phrase[head_end:]
        return _process(phrase)

    def _process(phrase):
        if "\n" in phrase:
            # A name across line breaks: see _join_name_lines.
            return _join_name_lines(phrase, _classify, people, known_names)
        kind = _classify(phrase)
        if kind[0] == "name":
            _record_name_tokens(kind[2], known_names)
            return kind[1] + people.tag(kind[2])
        return kind[1]

    def _classify(phrase):
        if phrase in _PROTECTED_PROPER_PHRASES:
            return ("keep", phrase)
        tokens = phrase.split()
        if tokens[0].lower().rstrip(".") in {"mr", "mrs", "ms", "miss", "dr", "sr", "sra", "srta"}:
            return ("keep", phrase)
        # Acronym inside the phrase ("Su DNI", "EDE Fundazioa"): not a name.
        if any(len(t) >= 2 and t.isupper() for t in tokens):
            return ("keep", phrase)
        # Public bodies / safe words only ("Servicios Sociales",
        # "El Ayuntamiento", "Gobierno Vasco"): not a personal identifier.
        if all(_is_safe_word(t) for t in tokens):
            return ("keep", phrase)
        # Sentence-start function word glued to a name ("Hoy Pedro ...",
        # "La Usuaria ..."): keep the function word, redact the rest.
        lead = []
        while tokens and tokens[0].lower() in _STOPWORDS:
            lead.append(tokens.pop(0))
        if not tokens:
            return ("keep", phrase)
        if len(tokens) == 1 and _is_safe_word(tokens[0]):
            return ("keep", phrase)
        lead_text = " ".join(lead) + " " if lead else ""
        if " ".join(tokens).lower() in _KNOWN_PLACE_PHRASES:
            return ("text", lead_text + "[LOCATION]")
        return ("name", lead_text, " ".join(tokens))

    text = _NAME_SEQUENCE_RE.sub(repl, text)

    def complex_repl(match):
        token = match.group(0)
        if _is_known_place(token):
            return "[LOCATION]"
        if _is_safe_word(token):
            return token
        if "-" in token or "'" in token or "’" in token:
            known_names.add(token)
            return people.tag(token)
        return token

    return _SINGLE_COMPLEX_NAME_RE.sub(complex_repl, text)


def _service_names(text: str) -> str:
    """(24 November 2026) A public-service name whose generic words are
    directly followed by a name ("Centro de Día Arrupe") is hidden whole as
    [ORGANISATION]. A name made only of generic words ("Servicio de
    Atención Familiar") is left as it is (its words are safe words), and a
    name joined by "de" ("Centro de Salud Mental de Uribarri") is left to
    the place rules. Never makes anything visible that was hidden before."""
    def repl(m):
        phrase = m.group(0)
        words = list(re.finditer(r"\S+", phrase))
        # words[0] is the kind of service, words[1] "de"/"del"/"para".
        seen_generic = False
        after_connector = False
        for i in range(2, len(words)):
            tok = words[i].group(0)
            if tok.lower() in _SERVICE_CONNECTORS:
                after_connector = True
                continue
            if _is_safe_word(tok):
                seen_generic = True
                after_connector = False
                continue
            if not (seen_generic and not after_connector):
                return phrase
            # A name glued to the generic words: the whole service name
            # (up to the next small word) is an organisation.
            end = i
            while end + 1 < len(words) and words[end + 1].group(0).lower() not in _SERVICE_CONNECTORS:
                end += 1
            return "[ORGANISATION]" + phrase[words[end].end():]
        return phrase

    return _SERVICE_NAME_RE.sub(repl, text)


# What follows a form abbreviation: a dot, then a small letter, a digit,
# "/", ":", "_" or "(" ("Doc. de", "Nr. 12", "Fdo.:").
_ABBREVIATION_AFTER_RE = re.compile(r"\.[ \t]?[a-zß-ÿ0-9/:_(º]")

# (26 November 2026, EDE testers) The value of a name field in a form
# ("NOMBRE Y APELLIDOS: Rosa gomez urrutia", "Izen-abizenak | ..."). The
# surnames were sometimes typed in small letters and stayed visible,
# because every other name rule looks for a capital letter. The whole
# value is hidden as one person, whatever its capitals; the label stays.
_NAME_FIELD_RE = re.compile(
    r"(?P<label>\b(?:nombre\s+y\s+apellidos|apellidos\s+y\s+nombre|nombre\s+completo|"
    r"nombre|apellidos?|izen[\s\-]*abizenak|abizen[\s\-]*izenak|izena|abizenak?|"
    r"full\s+name|first\s+name|surname|last\s+name|name)"
    r"[ \t]*(?:[:|][ \t]*|[ \t]{2,}))"
    r"(?P<value>[A-Za-zÀ-ÖØ-öø-ÿ][A-Za-zÀ-ÖØ-öø-ÿ'’\-]*(?:[ \t]+[A-Za-zÀ-ÖØ-öø-ÿ][A-Za-zÀ-ÖØ-öø-ÿ'’\-]*){0,4})",
    re.IGNORECASE,
)


def _hide_name_fields(text: str, known_names: set, people) -> str:
    def repl(m):
        words = list(re.finditer(r"\S+", m.group("value")))
        keep = 0
        for w in words:
            token = w.group(0)
            if token.lower() in _STOPWORDS or _is_safe_word(token):
                break
            keep += 1
        if not keep:
            return m.group(0)
        value = m.group("value")
        name = value[: words[keep - 1].end()]
        rest = value[words[keep - 1].end():]
        _record_name_tokens(" ".join(t for t in name.split() if t[:1].isupper()), known_names)
        return m.group("label") + people.tag(name) + rest
    return _NAME_FIELD_RE.sub(repl, text)


def _is_sentence_start(text: str, start: int) -> bool:
    before = text[:start].rstrip(_LEADING_PUNCT)
    if not before or before[-1] in _SENTENCE_END_CHARS:
        return True
    # (November 2026) A dash between spaces starts a new part of a heading
    # ("Informe de seguimiento – Alojamiento social"): the word after it is
    # capitalised because of the heading, not because it is a name.
    gap = text[len(before):start]
    return any(d in gap for d in ("–", "—", " - ", "|"))


def _looks_like_place(text: str, start: int) -> bool:
    words = re.findall(r"\w+", text[:start][-60:].lower())
    if not words:
        return False
    if words[-1] in _LOCATION_PREPOSITIONS:
        return True
    return len(words) >= 2 and words[-1] == "de" and words[-2] in _PLACE_NOUNS


def _replace_single_names(text: str, known_names: set, people=None) -> str:
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
        # (26 November 2026) A short abbreviation in a form ("Doc. de
        # identidad", "Prof. de referencia", "Nr. de expediente", "Fdo.:")
        # is not a name.
        if len(word) <= 6 and _ABBREVIATION_AFTER_RE.match(text, match.end()):
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
        # (24 November 2026) A word recognised as a person's name elsewhere
        # in the text stays a person even after "colegio de" etc.
        if not _is_safe_word(name) and not _is_known_place(name):
            found[name] = "[PERSON]"

    # Known towns and cities: a place wherever they are, even at the start
    # of a sentence (see _KNOWN_PLACES).
    for match in _SINGLE_CAPITALISED_RE.finditer(text):
        word = match.group(0)
        if _is_known_place(word):
            found[word] = "[LOCATION]"

    if not found:
        return text

    people = people if people is not None else PersonNumbers()

    def sub(m):
        tag = found[m.group(0)]
        return people.tag(m.group(0)) if tag == "[PERSON]" else tag

    # Longest first so "Mari" never eats the start of "Maribel".
    names = sorted(found, key=len, reverse=True)
    pattern = re.compile(r"(?<![\w\[])(?:%s)(?![\w\]])" % "|".join(re.escape(n) for n in names))
    return pattern.sub(sub, text)


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
    rf"(?:\b(?:she|he|they|who|i)|\[PERSON(?:\s\d+)?\]\s*,?)(?:'s|’s|\s+is|\s+was|\s+am|\s+are)\s+(?:only\s+|just\s+|now\s+|actually\s+)?"
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
    rf"(?:\b{_PERSON_NOUNS_ES}|\[PERSON(?:\s\d+)?\])\s*,?\s+de\s+(?P<age>{_NUMLIST}\s+(?:{_YEARS_ES}|{_MONTHS_ES}))\b",
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


def _hide_birth_years(text: str) -> str:
    """A year of birth is part of a date of birth, a direct identifier:
    always replaced by [DATE], whether or not exact ages are hidden."""
    for regex in _BIRTH_YEAR_RES:
        text = regex.sub(
            lambda m: m.group(0)[: m.start("age") - m.start()] + "[DATE]"
            + m.group(0)[m.end("age") - m.start():],
            text,
        )
    return text


def _hide_exact_ages_enabled() -> bool:
    """(November 2026, EDE) Exact ages are now LEFT VISIBLE by default
    (config.ANONYMISER_HIDE_EXACT_AGES = false). The life-stage code below
    is kept and is used again if the setting is switched on."""
    try:
        from config import ANONYMISER_HIDE_EXACT_AGES
    except Exception:
        return False
    return bool(ANONYMISER_HIDE_EXACT_AGES)


def _generalise_ages(text: str, force: bool = False) -> str:
    """Replace exact ages with life-stage tags (see the section comment).
    Does nothing unless exact-age hiding is switched on (or `force`)."""
    text = _hide_birth_years(text)
    if not (force or _hide_exact_ages_enabled()):
        return text
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


# ---------------------------------------------------------------------------
# Sensitive personal details -- GDPR "special categories" (18 November 2026)
# ---------------------------------------------------------------------------
# EDE tested the anonymiser and found that words such as "gay" or
# "lesbiana" reached the AI. Words that state a sensitive personal detail
# are now replaced by a neutral label, so the AI knows such a detail was
# mentioned but never what it was:
#
#   sexual orientation        -> [SEXUAL_ORIENTATION]
#   gender identity           -> [GENDER_IDENTITY]
#   health (specific: diagnoses, treatments, medicine names) -> [HEALTH]
#   religion or beliefs       -> [RELIGION_BELIEF]
#   ethnic or racial origin   -> [ETHNIC_ORIGIN]
#   political opinions        -> [POLITICAL_OPINION]
#   trade union membership    -> [TRADE_UNION]
#
# Product owner's decisions:
#   - Health: only SPECIFIC diagnoses, treatments and medicines are hidden
#     ("esquizofrenia", "VIH", "sertralina"). General words such as
#     "enfermedad", "problema de salud" or "salud mental" are kept (category
#     "health_general", switched OFF).
#   - Nationality is NOT hidden for now (category "nationality", switched
#     OFF).
#   Both can be switched on, and any category off, with the setting
#   ANONYMISER_SPECIAL_CATEGORIES in config.py (a list of category names).
#
# Words only -- indirect hints are NOT caught ("vive con su novia", "va a la
# mezquita", "fue a la manifestación"), nor misspellings, slang or medicines
# that are not on the lists. Like the rest of this module, this reduces the
# risk; it is not a guarantee.
#
# How the lists are written: each entry is a small pattern, matched as a
# whole word and ignoring capitals. Spanish plurals / feminine forms and
# common Basque endings are written into the entries ("gay(?:s|a|ak)?").
# Only long, unambiguous stems match any ending ("esquizofreni\w*"); short
# words match their listed forms only, so "trans" never touches
# "transporte". Acronyms (ELA, LAB, PNV, TDAH ...) are matched only when
# written in capitals, so ordinary words are never caught by mistake.

SPECIAL_CATEGORY_LABELS = {
    "sexual_orientation": "[SEXUAL_ORIENTATION]",
    "gender_identity": "[GENDER_IDENTITY]",
    "health_specific": "[HEALTH]",
    "health_general": "[HEALTH]",
    "religion_belief": "[RELIGION_BELIEF]",
    "ethnic_origin": "[ETHNIC_ORIGIN]",
    "political_opinion": "[POLITICAL_OPINION]",
    "trade_union": "[TRADE_UNION]",
    "nationality": "[NATIONALITY]",
}
# (November 2026, approved by EDE) Sexual orientation, gender identity,
# health, religion and ethnic origin are now LEFT VISIBLE by default:
# they are the context in which bias tends to appear, and the AI has to
# see them to name it. Political opinion and trade union membership are
# still hidden (EDE did not ask for them). Every category still works and
# can be switched back on with ANONYMISER_SPECIAL_CATEGORIES in config.py.
DEFAULT_SPECIAL_CATEGORIES = ("political_opinion", "trade_union")

_SPECIAL_TERMS = {
    "sexual_orientation": [
        r"gay(?:s|a|ak|ari|aren|arekin|ek|en|ekin)?", r"gais",
        r"lesbian\w*", r"homosexual\w*", r"bisexual\w*", r"heterosexual\w*",
        r"pansexual\w*", r"asexual(?:es|a|ak|idad)?", r"queer",
        r"lgtbi?q?\+?", r"lgbti?q?\+?", r"lgtbiq?\+?",
        r"boller[oa]s?", r"maric[oó]n(?:es|a)?", r"maricas?", r"bisex",
        r"parejas? del mismo sexo", r"same[- ]sex (?:partner|couple|relationship|marriage)s?",
        r"sexu bereko bikote\w*",
    ],
    "gender_identity": [
        r"trans(?:a|ak|ari|aren|arekin)?", r"transexual\w*", r"transgéner\w*", r"transgener\w*",
        r"transgender\w*", r"transsexual\w*", r"intersexual\w*", r"intersex",
        r"no binari[oa]s?", r"non[- ]?binary", r"ez[- ]bitar(?:ra|rak|rra|rrak)?",
        r"cisg[eé]ner[oa]s?", r"cisgender",
        r"transici[oó]n de g[eé]nero", r"gender transition", r"genero[- ]trantsizio\w*",
        r"reasignaci[oó]n de sexo", r"cambio de sexo", r"disforia de g[eé]nero", r"gender dysphoria",
    ],
    "health_specific": [
        # Infections
        r"vih", r"hiv", r"sida(?:ren|rekin|z)?", r"hies(?:a|aren|arekin)?", r"aids",
        r"seropositiv\w*", r"hepatitis(?: [abc](?!\w))?", r"tuberculosis",
        # Mental health diagnoses
        r"esquizofreni\w*", r"eskizofreni\w*", r"schizophreni\w*", r"esquizoafectiv\w*",
        r"bipolar\w*", r"psicosis", r"psic[oó]tic[oa]s?", r"psikosi\w*", r"psychos[ie]s", r"psychotic",
        r"depresi[oó]n(?:es)?(?: mayor| severa| grave| cr[oó]nica)?", r"depresio(?:a|ak|arekin|rekin)?",
        r"depression", r"trastorno de ansiedad(?: generalizada)?", r"anxiety disorder",
        r"trastorno l[ií]mite de (?:la )?personalidad", r"trastorno de (?:la )?personalidad",
        r"trastorno obsesivo[- ]compulsivo", r"trastorno de (?:la )?conducta alimentaria",
        r"(?:trastorno de )?estr[eé]s postraum[aá]tico", r"trastorno mental grave",
        r"trastorno por d[eé]ficit de atenci[oó]n(?: e hiperactividad)?", r"d[eé]ficit de atenci[oó]n",
        r"hiperactividad", r"anorexi\w*", r"bulimi\w*",
        r"autis\w*", r"asperger\w*",
        # Neurological, chronic and other conditions
        r"epilep\w*", r"diabet\w*", r"c[aá]ncer(?:es)?", r"cancer", r"minbizi\w*", r"tumor(?:es)?",
        r"leucemi\w*", r"leukaemi\w*", r"leukemi\w*", r"linfom\w*", r"lymphom\w*", r"met[aá]stasis",
        r"alzh[eé]imer\w*", r"demenci\w*", r"dementia\w*", r"dementzi\w*", r"p[aá]rkinson\w*",
        r"esclerosis (?:m[uú]ltiple|lateral amiotr[oó]fica)", r"multiple sclerosis", r"ictus",
        r"s[ií]ndrome de down", r"down syndrome", r"par[aá]lisis cerebral", r"cerebral palsy",
        r"discapacidad intelectual", r"intellectual disability", r"adimen[- ]urritasun\w*",
        # Addictions (named conditions)
        r"alcoholism[oe]?", r"alcoh[oó]lic[oa]s?", r"alcoholics?", r"alkoholiko\w*", r"alkoholismo\w*",
        r"drogodependen\w*", r"toxic[oó]man[oa]s?", r"toxicoman[ií]a", r"ludopat\w*",
        r"adicci[oó]n(?:es)?", r"adict[oa]s?", r"addiction\w*", r"addicted", r"adikzio\w*",
        # Treatments
        r"antirretrovir\w*", r"antiretrovir\w*", r"quimioterapi\w*", r"kimioterapi\w*", r"chemotherap\w*",
        r"radioterapi\w*", r"radiotherap\w*", r"hemodi[aá]lisis", r"di[aá]lisis", r"dialysis",
        r"terapia electroconvulsiva", r"electroshock", r"metadona\w*", r"methadone",
        r"aborto(?:s)?", r"abortion\w*", r"abortu(?:a|ak|aren)?",
        r"interrupci[oó]n voluntaria del embarazo",
        # Medicines (generic and common brand names)
        r"risperidon\w*", r"risperdal", r"olanzapin\w*", r"zyprexa", r"quetiapin\w*", r"seroquel",
        r"aripiprazol\w*", r"abilify", r"haloperidol\w*", r"clozapin\w*", r"paliperidon\w*", r"xeplion",
        r"litio(?:a|arekin|z)?", r"lithium", r"plenur",
        r"sertralin\w*", r"fluoxetin\w*", r"prozac", r"paroxetin\w*", r"escitalopram\w*", r"citalopram\w*",
        r"venlafaxin\w*", r"duloxetin\w*", r"mirtazapin\w*", r"trazodon\w*",
        r"lorazepam\w*", r"orfidal", r"diazepam\w*", r"valium", r"alprazolam\w*", r"trankimazin",
        r"clonazepam\w*", r"rivotril", r"lormetazepam\w*", r"bromazepam\w*", r"tranxilium",
        # ("Concerta" is left out on purpose: "se concerta una cita".)
        r"metilfenidat\w*", r"methylphenidate", r"rubifen", r"lisdexanfetamin\w*", r"elvanse",
        r"valproat\w*", r"depakine", r"lamotrigin\w*", r"carbamazepin\w*", r"pregabalin\w*", r"lyrica",
        r"gabapentin\w*", r"buprenorfin\w*", r"buprenorphine", r"suboxone", r"naltrexon\w*",
        r"disulfiram\w*", r"antabus\w*", r"truvada", r"biktarvy", r"dolutegravir\w*", r"tenofovir\w*",
        r"insulin\w*", r"metformin\w*", r"sintrom", r"acenocumarol\w*",
        r"tramadol\w*", r"fentanil\w*", r"fentanyl", r"morfina\w*", r"morphine",
    ],
    "health_general": [
        r"enfermedad(?:es)?", r"enferm[oa]s?", r"problemas? de salud", r"salud mental",
        r"osasun[- ]arazo\w*", r"osasun mental\w*", r"gaixotasun\w*", r"gaixo(?:a|ak)?",
        r"illness(?:es)?", r"mental health", r"health problems?",
    ],
    "religion_belief": [
        r"musulm[aá]n\w*", r"muslim(?:s)?", r"isl[aá]mic[oa]s?", r"islamiko\w*", r"islamic",
        r"cat[oó]lic[oa]s?", r"katoliko\w*", r"catholic(?:s)?",
        # Lower case only: "Cristian" / "Christian" are also first names.
        r"(?-i:cristian[oa]s?)", r"kristau(?:a|ak|aren|arekin)?", r"(?-i:christians?)", r"islam",
        r"evang[eé]lic[oa]s?", r"ebanjeliko\w*", r"evangelical(?:s)?",
        r"protestante(?:s)?", r"protestant(?:s)?",
        r"jud[ií][oa]s?", r"judu(?:a|ak|aren|arekin)?", r"jewish", r"jews?",
        r"testig[oa]s? de jehov[aá]", r"jehovah'?s witness(?:es)?", r"jehobaren lekuko\w*",
        r"morm[oó]n(?:a|as|es)?", r"mormons?", r"budista(?:s)?", r"budist\w*", r"buddhist(?:s)?",
        # "atea" alone is left out on purpose: in Basque it means "the door".
        r"hind[uú](?:es|s)?", r"ateos?", r"ateo(?:a|ak)?", r"es atea", r"ateas", r"atheists?",
        r"agn[oó]stic[oa]s?", r"agnostics?",
    ],
    "ethnic_origin": [
        r"gitan[oa]s?", r"ijito\w*", r"gypsy", r"gypsies", r"roman[ií](?:es|s)?",
        r"pay[oa]s?", r"afrodescendiente(?:s)?", r"afroamerican\w*",
        r"de etnia \w+", r"de raza \w+", r"racializad[oa]s?", r"ind[ií]gena(?:s)?",
    ],
    "political_opinion": [
        r"es de (?:izquierdas|derechas)", r"(?:de )?(?:extrema|ultra) ?(?:izquierda|derecha)",
        r"independentista(?:s)?", r"independentist\w*", r"abertzale\w*",
        r"comunista\w*", r"communists?", r"anarquista(?:s)?", r"anarkista\w*", r"anarchists?",
        r"franquista(?:s)?", r"fascista\w*", r"fascists?", r"nacionalista(?:s)?",
        r"ezkertiar\w*", r"eskuindar\w*", r"(?:left|right)[- ]wing", r"far[- ](?:left|right)",
        r"izquierda unida", r"ezker batua", r"elkarrekin podemos",
    ],
    "trade_union": [
        r"sindicat[oa]s?", r"sindicalista(?:s)?", r"delegad[oa]s? sindical(?:es)?",
        r"sindikatu\w*", r"sindikalista\w*", r"trade unions?", r"union members?(?:hip)?",
        r"trade unionists?",
    ],
    "nationality": [
        r"marroqu[ií](?:es|s)?", r"argelin[oa]s?", r"ruman[oa]s?", r"magreb[ií](?:es|s)?",
        r"subsahariano?a?s?", r"senegal[eé]s(?:a|as|es)?", r"colombian[oa]s?", r"venezolan[oa]s?",
        r"hondureñ[oa]s?", r"nicarag[uü]ense(?:s)?", r"peruan[oa]s?", r"bolivian[oa]s?",
        r"ecuatorian[oa]s?", r"paquistan[ií](?:es|s)?", r"pakistan[ií](?:es|s)?",
        r"ucranian[oa]s?", r"georgian[oa]s?", r"nigerian[oa]s?", r"malienses?", r"guinean[oa]s?",
    ],
}

# Acronyms and party names: matched only exactly as written (capitals), so
# ordinary words are never caught. ("Podemos" and "Sumar" are left out on
# purpose: they are also everyday verbs.)
_SPECIAL_ACRONYMS = {
    "health_specific": ["VIH", "SIDA", "GIB", "TDAH", "TDA", "TEA", "TLP", "TOC", "TCA", "TEPT",
                        "TMG", "IVE", "PrEP", "HIV", "ADHD", "PTSD", "OCD"],
    "political_opinion": ["PNV", "EAJ", "EH Bildu", "Bildu", "PSE-EE", "PSE", "PSOE", "PP", "IU",
                          "Vox", "VOX"],
    "trade_union": ["ELA", "LAB", "CCOO", "CC.OO.", "UGT", "STEILAS", "CGT", "CNT"],
}


def _load_special_categories():
    """The categories switched on, from config.ANONYMISER_SPECIAL_CATEGORIES
    (names separated by commas). A missing or invalid value -- including
    any unknown name -- means the defaults, so a typo can never switch the
    protection off."""
    try:
        from config import ANONYMISER_SPECIAL_CATEGORIES
        names = [n.strip().lower() for n in str(ANONYMISER_SPECIAL_CATEGORIES).split(",") if n.strip()]
    except Exception:
        return DEFAULT_SPECIAL_CATEGORIES
    if not names or any(n not in SPECIAL_CATEGORY_LABELS for n in names):
        return DEFAULT_SPECIAL_CATEGORIES
    return tuple(dict.fromkeys(names))


def _build_special_rules(categories):
    """[(compiled regex, label)] for the given categories, longest phrases
    first so "trastorno bipolar" wins over "bipolar"."""
    rules = []
    for key in categories:
        label = SPECIAL_CATEGORY_LABELS[key]
        words = sorted(_SPECIAL_TERMS.get(key, []), key=len, reverse=True)
        if words:
            rules.append((re.compile(
                r"(?<![\w\[])(?:%s)(?![\w])" % "|".join(w.replace(" ", r"\s+") for w in words),
                re.IGNORECASE), label))
        acronyms = sorted(_SPECIAL_ACRONYMS.get(key, []), key=len, reverse=True)
        if acronyms:
            rules.append((re.compile(
                r"(?<![\w\[.\-])(?:%s)(?![\w\-])" % "|".join(re.escape(a).replace(r"\ ", r"\s+") for a in acronyms)),
                label))
    return rules


_SPECIAL_RULES = _build_special_rules(_load_special_categories())


def _replace_special_categories(text: str, rules=None) -> str:
    """Replace words that state a sensitive personal detail by their label
    (see the section comment above)."""
    for regex, label in (_SPECIAL_RULES if rules is None else rules):
        text = regex.sub(label, text)
    return text


# ---------------------------------------------------------------------------
# Placeholders in the language of the reflection (November 2026, EDE)
# ---------------------------------------------------------------------------
# Inside this module every replacement is made with one fixed English
# "canonical" tag ([PERSON 1], [ADDRESS], [HEALTH], ...). At the very end
# the tags are written in the language chosen for the reflection, so the
# text the AI and the professional see is entirely in that language:
#   Español: [PERSONA 1], [DIRECCIÓN], [LUGAR], ...
#   Euskera: [PERTSONA 1], [HELBIDEA], [TOKIA], ...
#   English: [PERSON 1], [ADDRESS], [LOCATION], ...
# The words come from the translation files (key "anon_placeholders" in
# services/locales/*.py), never from this file.
#
# Placeholders already in a text -- in ANY of the three languages, and the
# older English ones such as [PERSON] or [HEALTH] -- are recognised and
# left exactly as they are, so anonymising a text twice never changes it,
# and older saved texts still read the same.

CANONICAL_TAGS = (
    "PERSON", "LOCATION", "ADDRESS", "ORGANISATION", "ID", "PHONE", "EMAIL", "DATE",
    "SEXUAL_ORIENTATION", "GENDER_IDENTITY", "HEALTH", "RELIGION_BELIEF",
    "ETHNIC_ORIGIN", "POLITICAL_OPINION", "TRADE_UNION", "NATIONALITY",
    "AGE_INFANT", "AGE_CHILD", "AGE_ADOLESCENT", "AGE_YOUNG_ADULT", "AGE_ADULT",
    "AGE_OLDER_ADULT",
)

# What each placeholder means, for the note to the AI (English, like the
# rest of the AI's instructions; never shown to people).
_TAG_MEANINGS = {
    "LOCATION": "a place (town, neighbourhood)", "ADDRESS": "an address",
    "ORGANISATION": "a named centre, school or organisation",
    "ID": "an identity document, case number, account or other identifier",
    "PHONE": "a phone number", "EMAIL": "an email address", "DATE": "a date",
    "POLITICAL_OPINION": "a political opinion", "TRADE_UNION": "trade union membership",
}

_LANG_DICTS = None


def _locale_dicts():
    global _LANG_DICTS
    if _LANG_DICTS is None:
        from services.locales.es import LANG_ES
        from services.locales.eu import LANG_EU
        from services.locales.en import LANG_EN
        _LANG_DICTS = {"Español": LANG_ES, "Euskera": LANG_EU, "English": LANG_EN}
    return _LANG_DICTS


def placeholder_words(lang="Español"):
    """{canonical tag: word in `lang`}. Unknown language -> Spanish; a word
    missing from a language -> Spanish, then the canonical English tag."""
    dicts = _locale_dicts()
    chosen = dicts.get(lang, dicts["Español"]).get("anon_placeholders") or {}
    spanish = dicts["Español"].get("anon_placeholders") or {}
    return {tag: chosen.get(tag) or spanish.get(tag) or tag for tag in CANONICAL_TAGS}


def _all_placeholder_words():
    words = set(CANONICAL_TAGS)
    for lang in _locale_dicts():
        words.update(placeholder_words(lang).values())
    return words


_PLACEHOLDER_RE = None


def placeholder_regex():
    """Matches any placeholder in any of the three languages (or the old
    English tags), with or without a person number."""
    global _PLACEHOLDER_RE
    if _PLACEHOLDER_RE is None:
        words = sorted(_all_placeholder_words(), key=len, reverse=True)
        _PLACEHOLDER_RE = re.compile(
            r"\[(?:%s)(?:\s(\d+))?\]" % "|".join(re.escape(w) for w in words)
        )
    return _PLACEHOLDER_RE


def _person_words():
    words = {"PERSON"}
    for lang in _locale_dicts():
        words.add(placeholder_words(lang)["PERSON"])
    return words


def labels_note(lang="Español"):
    """The note added to the AI's instructions wherever anonymised text is
    sent, listing the placeholders in the language of the reflection."""
    w = placeholder_words(lang)
    person = w["PERSON"]
    others = "; ".join(f"[{w[t]}] = {m}" for t, m in _TAG_MEANINGS.items())
    return (
        "Details in the text that could identify someone have been replaced by "
        f"placeholders in square brackets: [{person} 1], [{person} 2], ... = different "
        "people (the same number is always the same person); "
        f"{others}. Older texts may contain other placeholders such as "
        "[PERSON] or [HEALTH]; they mean the same kind of thing. A placeholder only "
        "shows that such a detail was there. Never guess, infer or ask what the "
        "hidden detail was. Sex, gender, origin, nationality, migration status, "
        "religion, age, health, substance use, disability and sexual orientation "
        "have deliberately been left in the text, because they matter when "
        "analysing bias."
    )


# Kept for code that imports the old name: the note in Spanish placeholders
# (the default language).
SENSITIVE_LABELS_NOTE = labels_note("Español")


# Private-use characters: not letters, digits, spaces or punctuation that
# any rule above looks at, so a placeholder hidden behind them is never
# touched by those rules.
_MASK_OPEN, _MASK_CLOSE, _MASK_BASE = "", "", 0xE100


def _mask_placeholders(text):
    found = []

    def repl(m):
        found.append(m.group(0))
        return _MASK_OPEN + chr(_MASK_BASE + len(found) - 1) + _MASK_CLOSE

    return placeholder_regex().sub(repl, text), found


def _unmask_placeholders(text, found):
    if not found:
        return text
    return re.sub(
        _MASK_OPEN + "(.)" + _MASK_CLOSE,
        lambda m: found[ord(m.group(1)) - _MASK_BASE],
        text,
    )


def _highest_person_number(placeholders):
    persons = _person_words()
    best = 0
    for p in placeholders:
        m = re.match(r"\[(.+?)\s(\d+)\]$", p)
        if m and m.group(1) in persons:
            best = max(best, int(m.group(2)))
    return best


_CANONICAL_TAG_RE = re.compile(r"\[(%s)(?:\s(\d+))?\]" % "|".join(
    sorted(CANONICAL_TAGS, key=len, reverse=True)))


def _number_in_order(text, people, first_new):
    """Give the people found in THIS call numbers in the order they first
    appear in the text, starting at `first_new` (people already numbered
    earlier keep their number)."""
    order = []
    for m in _CANONICAL_TAG_RE.finditer(text):
        if m.group(1) == "PERSON" and m.group(2):
            n = int(m.group(2))
            if n >= first_new and n not in order:
                order.append(n)
    mapping = {old: first_new + i for i, old in enumerate(order)}
    if all(k == v for k, v in mapping.items()):
        return text
    people.renumber(mapping)

    def repl(m):
        if m.group(1) == "PERSON" and m.group(2):
            return f"[PERSON {mapping.get(int(m.group(2)), int(m.group(2)))}]"
        return m.group(0)

    return _CANONICAL_TAG_RE.sub(repl, text)


def _localise_tags(text, lang):
    words = placeholder_words(lang)

    def repl(m):
        word = words.get(m.group(1), m.group(1))
        return f"[{word} {m.group(2)}]" if m.group(2) else f"[{word}]"

    return _CANONICAL_TAG_RE.sub(repl, text)


def anonymize(text: str, lang: str = "Español", people: "PersonNumbers" = None) -> str:
    """Return a privacy-hardened representation suitable for external AI.

    `lang`: language of the placeholders ("Español" by default, "Euskera",
    "English"). `people`: a PersonNumbers object to share numbering with
    another text (e.g. the chat messages of one reflection use the same
    numbers as its document); a fresh one is used if not given.

    Two passes: the original rules on the text as written, then the same
    rules again on a copy where words written in CAPITAL LETTERS have been
    given ordinary capitalisation (see _anonymize_capitals). The second pass
    can only ADD redactions; anything the first pass removed stays removed.
    """
    if not text:
        return text
    people = people if people is not None else PersonNumbers()
    masked, found = _mask_placeholders(str(text))
    people.last = max(people.last, _highest_person_number(found))
    people.look_ahead(masked)
    first_new = people.last + 1
    safe = _anonymize_capitals(_anonymize_core(masked, people), people)
    safe = _number_in_order(safe, people, first_new)
    return _unmask_placeholders(_localise_tags(safe, lang), found)


def _anonymize_core(text: str, people: "PersonNumbers" = None) -> str:
    """The rule set: the original rules plus (November 2026) exact ages."""
    if not text:
        return text
    people = people if people is not None else PersonNumbers()

    known_names = set()

    safe = str(text)
    safe = _EMAIL_RE.sub("[EMAIL]", safe)
    safe = _IBAN_RE.sub("[ID]", safe)
    safe = _DATE_RE.sub("[DATE]", safe)
    safe = _YEAR_FIRST_DATE_RE.sub("[DATE]", safe)
    # (18 November 2026) Sensitive personal details, BEFORE names, so that
    # "Bildu" or a sentence-initial "Gay" gets its own label, not [PERSON].
    safe = _replace_special_categories(safe)
    safe = _generalise_ages(safe)
    safe = _IDENTIFIER_RE.sub("[ID]", safe)
    # (26 November 2026) Identity documents after any label, and in every
    # written form (see _ID_DOCUMENT_RE), BEFORE phone numbers, so that a
    # DNI written in groups is never half taken for a phone number.
    safe = _hide_labelled_ids(safe)
    safe = _hide_id_documents(safe)
    safe = _DNI_NIE_RE.sub("[ID]", safe)
    safe = _absorb_id_letters(safe)
    safe = _PHONE_RE.sub("[PHONE]", safe)
    safe = _LONG_NUMERIC_ID_RE.sub("[ID]", safe)
    safe = _service_names(safe)
    safe = _hide_name_fields(safe, known_names, people)

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
                    low = w.group(0).lower().strip(",.;:!?()\"'«»")
                    # Also a common verb in capitals ("LUCÍA GARCÍA VINO"):
                    # the name stops before it.
                    if low in _STOPWORDS or (w.group(0).isupper() and low in _NOT_SURNAMES):
                        captured = captured[:w.start()].rstrip()
                        tail = m.group(1)[len(captured):]
                        break
            # "in English", "en Servicios Sociales": nothing personal there.
            if all(_is_safe_word(t) for t in captured.split()):
                return m.group(0)
            # (26 November 2026) Ordinary words at the start of what was
            # captured stay ("NOMBRE Y APELLIDOS CARLOS VEGA": only the
            # name is hidden, not "Y APELLIDOS").
            lead_text = ""
            if m.end(1) == m.end(0):
                ws = list(re.finditer(r"\S+", captured))
                k = 0
                while k < len(ws) - 1:
                    word = ws[k].group(0).strip(",.;:!?()\"'«»")
                    if not (word.lower() in _STOPWORDS or _is_safe_word(word)):
                        break
                    k += 1
                if k:
                    lead_text = captured[: ws[k].start()]
                    captured = captured[ws[k].start():]
            if r == "[PERSON]":
                _record_name_tokens(captured, known_names)
                r = _tag_lines(captured, people)
            if m.end(1) == m.end(0):
                # Keep the cue words ("la madre, ...", "vive en ...") so the
                # sentence still makes sense; only the name is replaced.
                return m.group(0)[: m.start(1) - m.start(0)] + lead_text + r + tail
            return r
        safe = pattern.sub(ctx_repl, safe)
    safe = _ADDRESS_UNIT_RE.sub("[ADDRESS]", safe)

    def title_repl(m):
        _record_name_tokens(m.group(1), known_names)
        return _tag_lines(m.group(1), people)

    # (26 November 2026) "Mª Goikoetxea" / "M.ª José": the short form of
    # María is part of the name and is hidden with it, as the same person
    # as "María ...".
    def short_maria_repl(m):
        _record_name_tokens(m.group(1), known_names)
        return people.tag("María " + m.group(1))

    safe = re.sub(
        rf"(?<![\w\[])M\.?\s?ª\.?\s+({_NAME_TOKEN}(?:[ \t]+{_NAME_TOKEN}){{0,3}})\b",
        short_maria_repl,
        safe,
    )

    safe = re.sub(
        rf"\b{_TITLES}\.?\s+({_NAME_TOKEN}(?:\s+{_NAME_TOKEN}){{0,3}})\b",
        title_repl,
        safe,
    )

    safe = _replace_proper_names(safe, known_names, people)
    safe = _replace_single_names(safe, known_names, people)
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


def _anonymize_capitals(text: str, people=None) -> str:
    tokens = _TOKEN_RE.findall(text)
    if "".join(tokens) != text:      # defensive: never risk losing text
        return text
    shadow = _normalise_capitals(tokens)
    if shadow == tokens:
        return text

    redacted = _TOKEN_RE.findall(_anonymize_core("".join(shadow), people))
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
            # (26 November 2026) A name that ran across a line break is now
            # one tag with the line break kept in front of it, so the line
            # break can come before the tag.
            k = j
            while k < n_redacted and redacted[k].isspace():
                k += 1
            if k == j or k >= n_redacted or redacted[k] != "[":
                return None
            pieces.extend(redacted[j:k])
            j = k
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
    # "[PERSON 12]" is five tokens; "[AGE_ADULT]" three.
    for k in range(start + 1, min(len(tokens), start + 8)):
        if tokens[k] == "]":
            return k
    return None

