# FILE: backend/app/services/document_review/patterns.py
# PHOENIX PROTOCOL - REGEX PATTERNS V2.9
# V2.9: SUSPECT PATTERNS — shtuar SUSPECT_PATTERN + GROUP_HEADER_PATTERN
#       për të nxjerrë persona të dyshuar nga kallëzimet penale të
#       strukturuara me "GRUPI I/II/III" + numërim + emër CAPS.
# V2.8: LOW CLEANUP (DATE_ALBANIAN, DISPOSITIVE, JUDGE, CONVICTION).
# V2.7: CASE_NUMBER_PATTERN EXPANDED.
# V2.6: LAW_NUMBER_LEGACY_PATTERN.
# V2.5: ARTICLE_PATTERN listat me presje.

import re


# ═══════════════════════════════════════════════════════════════════════════
# ARTICLES
# ═══════════════════════════════════════════════════════════════════════════

ARTICLE_PATTERN = re.compile(
    r'\b(?:Neni|Nenit|Nenin|Nen[ëe]t|Artikulli|Art\.?)\s+'
    r'(\d+(?:[\.\/]\d+)*'
    r'(?:\s*[,;]\s*\d+(?:[\.\/]\d+)*)*'
    r'(?:\s+dhe\s+\d+(?:[\.\/]\d+)*)?)'
    r'(?:\s*,?\s*(?:par(?:\.|agrafi|agrafit)?|paragrafi|paragrafit)\s*(\d+))?',
    re.IGNORECASE | re.UNICODE,
)


# ═══════════════════════════════════════════════════════════════════════════
# LAWS BY NUMBER
# ═══════════════════════════════════════════════════════════════════════════

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
    r'PP\.II|PP\.I|'
    r'A\.NR|'
    r'PPII|PPI|'
    r'KMLP|PML|ANR|PZR|'
    r'PA1|PA2|PKR|PP1|PP2|'
    r'REV|KML|CML|GJK|'
    r'PP|PA|KM|GJ|KI|KZ|KE|PN|KP|CA|CM|'
    r'P|K|C'
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
    r'(dit(?:ë|e)?(?:sh|ve)?'
    r'|muaj(?:sh)?'
    r'|jav(?:ë|e)?(?:sh)?'
    r'|vjet|vit)'
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
    r'IV|V|VI{0,3}|IX|'
    r'XI{0,3}|XX{0,3}|XXX|'
    r'I{1,3}'
    r')\s*\.\s*(.+?)$',
    re.MULTILINE,
)

ICD_CODE_PATTERN = re.compile(
    r'\b([A-Z]\d{2}(?:\.\d{1,2})?)\b',
    re.UNICODE,
)

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
    r'(dit(?:ë|e)?(?:sh|ve)?'
    r'|muaj(?:sh)?'
    r'|jav(?:ë|e)?(?:sh)?'
    r'|vjet|vit)'
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
# V2.9: SUSPECT PATTERNS — për kallëzime penale të strukturuara
# ═══════════════════════════════════════════════════════════════════════════

# Header i grupit: "GRUPI I:", "GRUPI II:", "GRUPI V — PALËT PRIVATE"
GROUP_HEADER_PATTERN = re.compile(
    r'^\s*(GRUPI\s+(?:[IVX]+))\s*[:\-—]?\s*([^\n]{0,120})$',
    re.MULTILINE,
)

# Rresht i personit: "1. NAZLIE BALA — Zyrtare e Lartë në Kabinetin..."
# Emri mund të jetë ALL CAPS ose Title Case, me hapësira dhe shenja.
SUSPECT_PATTERN = re.compile(
    r'^\s*(\d+)\.\s+'
    r'([A-ZËÇ][A-Za-zëçËÇ\.\-]{2,60}'
    r'(?:\s+[A-ZËÇ][A-Za-zëçËÇ\.\-]{2,60}){1,4})'
    r'\s*[—–\-:]\s*'
    r'([^\n]{5,200})$',
    re.MULTILINE,
)

# Fusha e pozitës: "Zyrtare e Lartë në Kabinetin e Ministrisë së Drejtësisë"
# zakonisht del pas em-dash në rreshtin e personit.

# "Kualifikimi Ligjor Penal:" — për të identifikuar blloqet e personave
QUALIFICATION_HEADER_PATTERN = re.compile(
    r'Kualifikimi\s+Ligjor\s+Penal\s*[:\-]',
    re.IGNORECASE | re.UNICODE,
)