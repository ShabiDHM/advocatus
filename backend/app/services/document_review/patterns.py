# FILE: backend/app/services/document_review/patterns.py
# PHOENIX PROTOCOL - REGEX PATTERNS V2.4
# V2.4: FIX KRITIK — hequr KPK|KPRK nga CASE_NUMBER_PATTERN. Ata jane
#       akronime LIGJESH, jo prefikse lendesh. Kjo parandalon qe
#       "KPRK.nr.06/L-074" (kod ligji) te klasifikohet si numer lende.
# V2.3: FIX DEADLINE + PERIOD për shumësin shqip.
# V2.2: Shtuar pattern-e për dispozitiv, mjekësi, dënime, kontradikta.

import re


# ═══════════════════════════════════════════════════════════════════════════
# ARTICLES
# ═══════════════════════════════════════════════════════════════════════════

ARTICLE_PATTERN = re.compile(
    r'\b(?:Neni|Nenit|Nenin|Nen[ëe]t|Artikulli|Art\.?)\s+'
    r'(\d+(?:[\.\/]\d+)*)'
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

LAW_NUMBER_WITH_NAME_PATTERN = re.compile(
    r'(?:Ligj(?:it|i|ji)?|Kodi)\s+'
    r'(?:Nr\.?\s*)?(\d{2}\s*[\/\-_\s]?\s*L\s*[\/\-_\s]?\s*\d{2,4})'
    r'(?:\s+(?:për|per|i|e)\s+([^.,;:()\n]{3,150}))?',
    re.IGNORECASE | re.UNICODE,
)


# ═══════════════════════════════════════════════════════════════════════════
# LAWS BY NAME
# ═══════════════════════════════════════════════════════════════════════════

LAW_NAME_PATTERN = re.compile(
    r'(?:Ligj(?:it|i|ji)?|Kodi)\s+'
    r'(?:për|per|i|të|te|e)\s+'
    r'([A-ZËÇ][^.,;:()\n]{4,150}?)'
    r'(?=\s*(?:,|\.|;|\(|\n|$|\s+i\s+|\s+dhe\s+))',
    re.IGNORECASE | re.UNICODE,
)


# ═══════════════════════════════════════════════════════════════════════════
# ABBREVIATIONS
# ═══════════════════════════════════════════════════════════════════════════

ABBREV_PATTERN = re.compile(r'\b([A-ZËÇ]{2,6})\b')


# ═══════════════════════════════════════════════════════════════════════════
# CASE NUMBERS — V2.4: pa KPK / KPRK (ata jane kode ligjesh)
# ═══════════════════════════════════════════════════════════════════════════

CASE_NUMBER_PATTERN = re.compile(
    r'\b('
    r'PML|Rev|REV|KMLP|ANR|A\.NR|PZR|'
    r'PA1|PKR|P|C|CA|KE|PN|KP|PP\.II'
    r')'
    r'\.?\s*[Nn]r\.?\s*'
    r'(\d+[\w\/\.\-]*)',
    re.IGNORECASE,
)


# ═══════════════════════════════════════════════════════════════════════════
# DATES
# ═══════════════════════════════════════════════════════════════════════════

DATE_PATTERN = re.compile(
    r'\b(\d{1,2})\s*[\.\/\-]\s*(\d{1,2})\s*[\.\/\-]\s*(\d{2,4})\b',
)

ALBANIAN_MONTHS = [
    'janar', 'shkurt', 'mars', 'prill', 'maj', 'qershor',
    'korrik', 'gusht', 'shtator', 'tetor', 'nëntor', 'dhjetor',
]

DATE_ALBANIAN_PATTERN = re.compile(
    r'(?<!\w)(\d{1,2})\s+(' + '|'.join(ALBANIAN_MONTHS) + r')(?:it|i|t)?\s+(\d{2,4})(?!\w)',
    re.IGNORECASE | re.UNICODE,
)


# ═══════════════════════════════════════════════════════════════════════════
# DEADLINES
# ═══════════════════════════════════════════════════════════════════════════

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


# ═══════════════════════════════════════════════════════════════════════════
# PARTIES
# ═══════════════════════════════════════════════════════════════════════════

PARTY_LABEL_PATTERN = re.compile(
    r'\b(?:Pala\s+e\s+mbrojtur|Pala\s+p[eë]rgjegj[eë]se|'
    r'I\s+padituri|E\s+paditura|Padit[eë]si|Kryesi\s+i\s+dhun[eë]s|'
    r'Pala\s+kliente)\s*[:\-]?\s*'
    r'([A-ZËÇ][a-zA-ZëçËÇ0-9\s\.\-\(\)]{2,80}?)'
    r'(?=\s*(?:,|\.|;|:|\s+nga\s+|\s*$))',
    re.IGNORECASE | re.UNICODE,
)


# ═══════════════════════════════════════════════════════════════════════════
# DISPOSITIVE POINTS
# ═══════════════════════════════════════════════════════════════════════════

DISPOSITIVE_POINT_PATTERN = re.compile(
    r'^\s*(I{1,3}V?|IV|V|VI{0,3}|IX|X{1,3})\s*\.\s*(.+?)$',
    re.MULTILINE,
)


# ═══════════════════════════════════════════════════════════════════════════
# MEDICAL FINDINGS
# ═══════════════════════════════════════════════════════════════════════════

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


# ═══════════════════════════════════════════════════════════════════════════
# PRIOR CONVICTIONS
# ═══════════════════════════════════════════════════════════════════════════

PRIOR_CONVICTION_PATTERN = re.compile(
    r'(?:Aktgjykim(?:i)?|Vendim(?:i)?|Dënuar|Denuar|'
    r'Dënuar\s+me\s+kusht|Gjykatë)\s+'
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


# ═══════════════════════════════════════════════════════════════════════════
# JUDGE / COURT / APPEAL
# ═══════════════════════════════════════════════════════════════════════════

JUDGE_NAME_PATTERN = re.compile(
    r'(?:gjyqtar(?:in|i)?|gjyqtarja)\s+'
    r'([A-ZËÇ][a-zëç]+(?:\s+[A-ZËÇ][a-zëç]+){1,3})',
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


# ═══════════════════════════════════════════════════════════════════════════
# CONTRADICTIONS
# ═══════════════════════════════════════════════════════════════════════════

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