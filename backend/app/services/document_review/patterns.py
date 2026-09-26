# FILE: backend/app/services/document_review/patterns.py
# PHOENIX PROTOCOL - REGEX PATTERNS V3.5
# V3.5: UNIVERSAL FIRST-WORD + CONJUNCTION FILTERS —
#       - Kërko fjalën e parë me shkronjë të madhe (emrat shqip).
#         Eliminon "gjyqtarët Lumni Sallauka", "psikiatrër, Dr. X".
#       - LEADING_STOPWORDS: parafjalë/lidhëza universale që NUK
#         fillojnë emër ("SI TË PABAZUAR").
#       - Refuzo numra romakë ("III dhe IV").
#       - LEGAL_STOPWORDS: shtuar terma header universalë
#         ("këshillë", "udhëzim", "informacion", "njoftim", etj.).
#       Zero varësi domain-i — të gjitha listat janë universale gjuhësore.
# V3.4: ROLE-BASED FILTERING.
# V3.3: TRULY DYNAMIC.
# V3.2: SUSPECT_LINE_PATTERN.

import re


# ═══════════════════════════════════════════════════════════════════════════
# ARTICLES / LAWS / DATES / DEADLINES (të pandryshuara)
# ═══════════════════════════════════════════════════════════════════════════

ARTICLE_PATTERN = re.compile(
    r'\b(?:Neni|Nenit|Nenin|Nen[ëe]t|Artikulli|Art\.?)\s+'
    r'(\d+(?:[\.\/]\d+)*'
    r'(?:\s*[,;]\s*\d+(?:[\.\/]\d+)*)*'
    r'(?:\s+dhe\s+\d+(?:[\.\/]\d+)*)?)'
    r'(?:\s*,?\s*(?:par(?:\.|agrafi|agrafit)?|paragrafi|paragrafit)\s*(\d+))?',
    re.IGNORECASE | re.UNICODE,
)

LAW_NUMBER_PATTERN = re.compile(
    r'\b(\d{2})\s*[\/\-_\s]?\s*L\s*[\/\-_\s]?\s*(\d{2,4})\b',
    re.IGNORECASE,
)

LAW_NUMBER_LEGACY_PATTERN = re.compile(
    r'(?:Ligj(?:it|i|ji)?|Kodi)\s+'
    r'(?:Nr\.?\s*)?'
    r'(\d{4})\s*[\/\-]\s*(\d{1,4})\b',
    re.IGNORECASE | re.UNICODE,
)

LAW_NUMBER_WITH_NAME_PATTERN = re.compile(
    r'(?:Ligj(?:it|i|ji)?|Kodi)\s+'
    r'(?:Nr\.?\s*)?(\d{2}\s*[\/\-_\s]?\s*L\s*[\/\-_\s]?\s*\d{2,4})'
    r'(?:\s+(?:për|per|i|e)\s+([^.,;:()\n]{3,150}))?',
    re.IGNORECASE | re.UNICODE,
)

LAW_NAME_PATTERN = re.compile(
    r'(?:Ligj(?:it|i|ji)?|Kodi)\s+'
    r'(?:për|per|i|të|te|e)\s+'
    r'([A-ZËÇ][^.,;:()\n]{4,150}?)'
    r'(?=\s*(?:,|\.|;|\(|\n|$|\s+i\s+|\s+dhe\s+))',
    re.IGNORECASE | re.UNICODE,
)

ABBREV_PATTERN = re.compile(r'\b([A-ZËÇ]{2,6})\b')

CASE_NUMBER_PATTERN = re.compile(
    r'\b('
    r'PP\.II|PP\.I|A\.NR|PPII|PPI|KMLP|PML|ANR|PZR|'
    r'PA1|PA2|PKR|PP1|PP2|REV|KML|CML|GJK|'
    r'PP|PA|KM|GJ|KI|KZ|KE|PN|KP|CA|CM|P|K|C'
    r')'
    r'\.?\s*[Nn]r\.?\s*'
    r'(\d+[\w\/\.\-]*)',
    re.IGNORECASE,
)

DATE_PATTERN = re.compile(
    r'\b(\d{1,2})\s*[\.\/\-]\s*(\d{1,2})\s*[\.\/\-]\s*(\d{2,4})\b',
)

ALBANIAN_MONTHS = [
    'janar', 'shkurt', 'mars', 'prill', 'maj', 'qershor',
    'korrik', 'gusht', 'shtator', 'tetor', 'nëntor', 'dhjetor',
]

DATE_ALBANIAN_PATTERN = re.compile(
    r'(?<!\w)(\d{1,2})\s+(' + '|'.join(ALBANIAN_MONTHS) + r')(?:it|i|t)?,?\s+(\d{2,4})(?!\w)',
    re.IGNORECASE | re.UNICODE,
)

DEADLINE_PATTERN = re.compile(
    r'\b(\d+)\s*'
    r'(dit(?:ë|e)?(?:sh|ve)?|muaj(?:sh)?|jav(?:ë|e)?(?:sh)?|vjet|vit)'
    r'\b',
    re.IGNORECASE | re.UNICODE,
)

DEADLINE_CONTEXT_KEYWORDS = [
    "afat", "ankim", "kërkes", "padi", "rehabilitim", "ekspertiz",
    "mbrojtje", "zgjatje", "ndryshim", "refuzim", "pranim",
]

PARTY_LABEL_PATTERN = re.compile(
    r'\b(?:Pala\s+e\s+mbrojtur|Pala\s+p[eë]rgjegj[eë]se|'
    r'I\s+padituri|E\s+paditura|Padit[eë]si|Kryesi\s+i\s+dhun[eë]s|'
    r'Pala\s+kliente)\s*[:\-]?\s*'
    r'([A-ZËÇ][a-zA-ZëçËÇ0-9\s\.\-\(\)]{2,80}?)'
    r'(?=\s*(?:,|\.|;|:|\s+nga\s+|\s*$))',
    re.IGNORECASE | re.UNICODE,
)

DISPOSITIVE_POINT_PATTERN = re.compile(
    r'^\s*('
    r'IV|V|VI{0,3}|IX|XI{0,3}|XX{0,3}|XXX|I{1,3}'
    r')\s*\.\s*(.+?)$',
    re.MULTILINE,
)

ICD_CODE_PATTERN = re.compile(r'\b([A-Z]\d{2}(?:\.\d{1,2})?)\b', re.UNICODE)

DIAGNOSIS_KEYWORDS = [
    "çrregullim", "crregullim", "diagnozë", "diagnoze", "diagnostikuar",
    "vuan nga", "konstatuar", "personaliteti", "kufitar",
    "depresion", "anksiozitet", "skizofreni", "bipolar",
    "çrregullim mendor", "crregullim mendor",
    "sëmundje mendore", "semundje mendore",
]

MEDICAL_TEST_KEYWORDS = [
    "testi i drogës", "testi i droges", "test toksikologjik",
    "test toksikologjik", "testi i gjakut", "analiza e gjakut",
    "testi psikiatrik", "ekzaminim psikiatrik", "ekspertizë psikiatrike",
    "ekspertize psikiatrike", "mendim i ekspertëve", "mendim i eksperteve",
    "testi i alkoolit", "test alkooli", "analiza toksikologjike",
]

NEGATIVE_RESULT_KEYWORDS = [
    "negativ", "negative", "nuk ka rezultuar", "nuk u konstatua",
    "pa prani", "nuk është përdorues", "nuk eshte perdorues",
    "nuk e kanë konstatuar", "nuk e kane konstatuar",
]

PRIOR_CONVICTION_PATTERN = re.compile(
    r'(?:Aktgjykim(?:i)?|Vendim(?:i)?|'
    r'Dënuar\s+me\s+kusht|Denuar\s+me\s+kusht|'
    r'Dënuar|Denuar|Gjykatë)\s+'
    r'(?:me\s+)?'
    r'(P\.nr\.|K\.nr\.|C\.nr\.)[\s]*'
    r'(\d+[\w\/\.\-]*)',
    re.IGNORECASE | re.UNICODE,
)

CONVICTION_KEYWORDS = [
    "i dënuar", "i denuar", "dënuar me kusht", "denuar me kusht",
    "dënim penal", "denim penal", "vepër penale", "veper penale",
    "aktgjykim", "aktgjykimi", "është dënuar", "eshte denuar",
]

JUDGE_NAME_PATTERN = re.compile(
    r'(?:gjyqtar(?:in|i)?|gjyqtarja)\s+'
    r'('
    r'[A-ZËÇ][a-zëç]+(?:\s+[A-ZËÇ][a-zëç]+){1,3}'
    r'|'
    r'[A-ZËÇ]{2,}(?:\s+[A-ZËÇ]{2,}){1,3}'
    r')',
    re.IGNORECASE | re.UNICODE,
)

COURT_NAME_PATTERN = re.compile(
    r'(GJYKATA\s+[A-ZËÇ]+(?:\s+[A-ZËÇ]+){0,4}'
    r'|Gjykata\s+[A-ZËÇ][a-zëç]+(?:\s+[A-ZËÇ][a-zëç]+){0,4})',
    re.UNICODE,
)

APPEAL_DEADLINE_PATTERN = re.compile(
    r'afat\s+prej\s+(\d+)\s*'
    r'(dit(?:ë|e)?(?:sh)?|muaj(?:sh)?|jav(?:ë|e)?(?:sh)?)\s+'
    r'nga\s+(?:marrja|pranimi|njoftimi)',
    re.IGNORECASE | re.UNICODE,
)

PERIOD_PATTERN = re.compile(
    r'\b(\d+)\s*'
    r'(dit(?:ë|e)?(?:sh|ve)?|muaj(?:sh)?|jav(?:ë|e)?(?:sh)?|vjet|vit)'
    r'\b',
    re.IGNORECASE | re.UNICODE,
)

DISTANCE_PATTERN = re.compile(
    r'\b(\d+)\s*(metra|metër|meter|m)\b',
    re.IGNORECASE | re.UNICODE,
)

AMOUNT_PATTERN = re.compile(
    r'\b(\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2})?)\s*(EUR|€|Euro|euro)\b',
    re.IGNORECASE | re.UNICODE,
)


# ═══════════════════════════════════════════════════════════════════════════
# V3.5: STRUCTURAL FILTERS — UNIVERSAL LANGUAGE-AWARE
# ═══════════════════════════════════════════════════════════════════════════

# Lidhëzat e brendshme të emrave shqip
NAME_CONNECTORS = frozenset([
    "i", "e", "të", "te", "dhe", "me", "nga", "de", "van", "bin", "el",
])

# V3.5: Parafjalë/lidhëza UNIVERSALE — kur fillojnë fjalinë, s'është emër.
# Këto nuk varen nga domain-i (penal, civil, etj.) — janë gramatikë shqipe.
LEADING_STOPWORDS = frozenset([
    "si", "se", "sa", "ku", "kur", "pse", "që", "qe",
    "me", "nga", "në", "ne", "pa", "jo", "po", "më",
    "dhe", "ose", "por", "nëse", "ndërsa", "kurse",
    "për", "per", "sipas", "gjithashtu", "kështu", "keshtu",
    "konkretisht", "sidomos", "pra", "aty", "këtu", "ketu",
])

# V3.5: Terma universalë që NUK janë emra personash (në çdo dokument ligjor shqip).
LEGAL_STOPWORDS = frozenset([
    # ── Procedura & dokumente ──
    "neni", "nenit", "nenin", "nenet", "nenët",
    "ligji", "ligjit", "ligjin", "ligje", "ligjet", "ligjeve",
    "kodi", "kodit", "kodin", "kodet", "kod",
    "paragrafi", "paragrafit", "paragrafin", "paragraf",
    "pika", "pikat", "pikës", "pikes",
    "aktgjykim", "aktgjykimi", "aktgjykimit",
    "aktvendim", "aktvendimi", "aktvendimit",
    "vendim", "vendimi", "vendimit", "vendime", "vendimet",
    "urdhër", "urdhri", "urdhrin", "urdher",
    "padi", "padia", "padinë", "padine",
    "kallëzim", "kallzimi", "kallëzimi", "kallzim",
    "aktakuzë", "aktakuza", "aktakuze", "aktakuzes",
    "ankesë", "ankesa", "ankese", "ankimit",
    "kërkesë", "kerkesa", "kërkesa", "kërkesëpadi",
    "faturë", "fatura", "kontratë", "kontrata",
    # ── Institucione ──
    "gjykata", "gjykatës", "gjykate", "gjykatë",
    "prokuroria", "prokurorisë", "prokurorise",
    "kolegji", "kolegjit", "kolegjet",
    "departamenti", "departamentit", "departament",
    "divizioni", "divizionit", "divizion",
    "sektori", "sektorit", "sektor",
    "zyra", "zyrës", "zyre", "drejtoria", "drejtorisë",
    "ministria", "ministrisë", "ministrise",
    "qeveria", "qeverisë", "qeverise",
    "kabineti", "kabinetit", "kabinet",
    "komisioni", "komisionit", "komision",
    "inspektorati", "inspektoratit",
    "agjencia", "agjencisë", "agjencise",
    "institucioni", "institucionit", "institucione",
    "institui", "instituti", "institutit",
    # ── Strukturorë (jo-rol) ──
    "grup", "grupi", "grupit", "grupe", "grupet",
    "seksion", "seksioni", "seksionit", "seksione", "seksionet",
    "pjesa", "pjesë", "pjesës", "pjesët", "pjeset",
    "kapitull", "kapitulli", "kapitullit",
    "nr", "numri", "numrit", "numër", "numer", "numrat",
    # ── V3.5: Terma header universalë ligjorë ──
    "këshillë", "keshille", "këshilla", "keshilla",
    "udhëzim", "udhezim", "udhëzime", "udhezime",
    "informacion", "informacione", "informacioni",
    "njoftim", "njoftime", "njoftimi",
    "vërejtje", "verejtje", "vërejtjet", "verejtjet",
    "paralajmërim", "paralajmerim",
    "deklaratë", "deklarate", "deklarata",
    "vërtetim", "vertetim", "vërtetime", "vertetime",
    "rekomandim", "rekomandime", "rekomandimi",
    "konkluzion", "konkluzione", "konkluzioni",
    "arsyetim", "arsyetime", "arsyetimi",
    "hyzmet", "shërbim", "sherbim",
    "juridik", "juridike", "ligjor", "ligjore",
    # ── Kohë / sasi ──
    "data", "datat", "datës", "dates",
    "viti", "vitit", "vit", "vitet",
    "muaji", "muajit", "muaj", "muajt",
    "dita", "ditës", "dite", "ditët",
    "ora", "orës", "ore", "orët",
    "faqja", "faqes", "faqe", "faqet",
    # ── Gjeografikë/institucionalë ──
    "republika", "republikës", "republike", "republik",
    "shteti", "shtetit", "shtet", "shtetet",
    "kosova", "kosovës", "kosovë", "kosove",
    "qendra", "qendrës", "qendrave", "qendre",
    "lagja", "lagjës", "lagje", "lagjet",
    "rruga", "rrugës", "rrugë", "rruget",
    "komuna", "komunës", "komunë", "komunat",
    "regjioni", "regjionit", "regjion",
    "sistemi", "sistemit", "sistem", "sistemet",
])

# V3.5: Titull profesional (nuk është emër i plotë)
TITLE_PREFIXES = frozenset([
    "z.", "znj.", "dr.", "prof.", "mr.", "m.sc.", "msc.",
])

# V3.5: Numra romakë — refuzo nëse të gjitha fjalët "reale" janë romakë.
ROMAN_NUMERAL_RE = re.compile(r'^[IVX]+$')

# Pragje
MIN_NAME_WORDS = 2
MAX_NAME_WORDS = 5
MIN_UPPERCASE_RATIO = 0.6
MAX_NAME_LENGTH = 100


def is_valid_person_name(s: str) -> bool:
    """
    V3.5: Validim STRUKTUROR strikt.

    Refuzon:
      1. Fillim me shkronjë të vogël (emrat shqip fillojnë me kapital).
      2. Fillim me parafjalë/lidhëz (LEADING_STOPWORDS).
      3. Fillim me shkronjë + pikë ("I.", "B.", "C.").
      4. Numra romakë të vetëm (III, IV).
      5. Fjalë < 2 ose > 5.
      6. Përmban numra.
      7. Përmban ":" brenda.
      8. Fillim me titull (Dr., Z., etj.).
      9. Përmban LEGAL_STOPWORDS.
    """
    if not s:
        return False
    s = s.strip().rstrip(".,;:()[]\"'")
    if not s or len(s) > MAX_NAME_LENGTH:
        return False

    # 1. Fillim me "X." (numërime romake/latina)
    if re.match(r'^[A-Za-z]\.', s):
        return False

    # 2. ':' brenda — nuk është emër
    if ':' in s:
        return False

    words = s.split()
    if len(words) < MIN_NAME_WORDS or len(words) > MAX_NAME_WORDS:
        return False

    if any(ch.isdigit() for ch in s):
        return False

    # 3. Fjala e parë duhet të fillojë me kapital
    first_word = words[0]
    if not first_word or not first_word[0].isupper():
        return False

    # 4. Fjala e parë NUK duhet të jetë parafjalë/lidhëz
    first_lower = first_word.lower().rstrip(".,;:()")
    if first_lower in LEADING_STOPWORDS:
        return False

    # 5. Titull në fillim → refuzo
    if (first_lower + ".") in TITLE_PREFIXES:
        return False

    # 6. Ratio e shkronjave të mëdha fillestare
    uppercase_start = sum(1 for w in words if w and w[0].isupper())
    if uppercase_start < len(words) * MIN_UPPERCASE_RATIO:
        return False

    # 7. Fjalë reale (pa lidhëza)
    real_words = [w for w in words if w.lower() not in NAME_CONNECTORS]
    if len(real_words) < 2:
        return False

    # 8. Refuzo nëse të gjitha fjalët reale janë numra romakë
    if all(ROMAN_NUMERAL_RE.match(w.rstrip(".,;:()")) for w in real_words):
        return False

    # 9. Filtro fjalët ligjore universale
    low_words = {w.lower().rstrip(".,;:()") for w in real_words}
    if low_words & LEGAL_STOPWORDS:
        return False

    return True


# Numërimi opsional i linjës
NUMBERED_LINE_PATTERN = re.compile(
    r'^\s*(\d+)\s*[\.\)]\s+([^\n]+)$',
    re.MULTILINE,
)