# FILE: backend/app/services/document_review/patterns.py
# PHOENIX PROTOCOL - REGEX PATTERNS V2.1
# V2.1: FIX në PARTY_LABEL_PATTERN (lejon kllapa dhe numra).
#       FIX në DATE_ALBANIAN_PATTERN (word boundary i pastër).
# V2.0: Arkitekturë e re — vetëm regex për ekstraktim deterministik.

import re


# ═══════════════════════════════════════════════════════════════════════════
# ARTICLES — Nenet
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
# CASE NUMBERS
# ═══════════════════════════════════════════════════════════════════════════

CASE_NUMBER_PATTERN = re.compile(
    r'\b('
    r'PML|Rev|REV|KMLP|ANR|A\.NR|PZR|'
    r'PA1|PKR|P|C|CA|KE|PN|KP|PP\.II|'
    r'KPK|KPRK'
    r')'
    r'\.?\s*[Nn]r\.?\s*'
    r'(\d+[\w\/\.\-]*)',
    re.IGNORECASE,
)


# ═══════════════════════════════════════════════════════════════════════════
# DATES — V2.1 FIX: word boundary i pastër
# ═══════════════════════════════════════════════════════════════════════════

DATE_PATTERN = re.compile(
    r'\b(\d{1,2})\s*[\.\/\-]\s*(\d{1,2})\s*[\.\/\-]\s*(\d{2,4})\b',
)

ALBANIAN_MONTHS = [
    'janar', 'shkurt', 'mars', 'prill', 'maj', 'qershor',
    'korrik', 'gusht', 'shtator', 'tetor', 'nëntor', 'dhjetor',
]

# V2.1: Pa \b në fund (mund të ndodhë pas "2024" me pikë)
DATE_ALBANIAN_PATTERN = re.compile(
    r'(?<!\w)(\d{1,2})\s+(' + '|'.join(ALBANIAN_MONTHS) + r')(?:it|i|t)?\s+(\d{2,4})(?!\w)',
    re.IGNORECASE | re.UNICODE,
)


# ═══════════════════════════════════════════════════════════════════════════
# DEADLINES
# ═══════════════════════════════════════════════════════════════════════════

DEADLINE_PATTERN = re.compile(
    r'\b(\d+)\s*(dit[ëe]?|muaj|jav[ëe]?|vjet|vit)\b',
    re.IGNORECASE | re.UNICODE,
)

DEADLINE_CONTEXT_KEYWORDS = [
    "afat", "ankim", "kërkes", "padi", "rehabilitim", "ekspertiz",
    "mbrojtje", "zgjatje", "ndryshim", "refuzim", "pranim",
]


# ═══════════════════════════════════════════════════════════════════════════
# PARTIES — V2.1 FIX: lejon kllapa dhe numra
# ═══════════════════════════════════════════════════════════════════════════

PARTY_LABEL_PATTERN = re.compile(
    r'\b(?:Pala\s+e\s+mbrojtur|Pala\s+p[eë]rgjegj[eë]se|'
    r'I\s+padituri|E\s+paditura|Padit[eë]si|Kryesi\s+i\s+dhun[eë]s|'
    r'Pala\s+kliente)\s*[:\-]?\s*'
    r'([A-ZËÇ][a-zA-ZëçËÇ0-9\s\.\-\(\)]{2,80}?)'
    r'(?=\s*(?:,|\.|;|:|\s+nga\s+|\s*$))',
    re.IGNORECASE | re.UNICODE,
)