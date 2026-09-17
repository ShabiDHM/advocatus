# FILE: backend/app/services/synthesis/patterns.py
# PHOENIX PROTOCOL - REGEX PATTERNS V1.0
# Ekstraktuar nga synthesis_service.py V3.8 — ZERO ndryshim funksional.
#
# ⚠️ KUJDES: ÇDO ndryshim këtu prek:
#   - Guardrail #2b (ekstraktim citimesh)
#   - Guardrail #4  (verifikim nenesh)
#   - Guardrail #5  (verifikim atribuimi)
#   - Guardrail #5b (kontradikta afatesh)
# Testo me sample real para çdo modifikimi.

import re


# ═══════════════════════════════════════════════════════════════════════════
# LAW DETECTION
# ═══════════════════════════════════════════════════════════════════════════

LAW_WITH_NUMBER_PATTERN = re.compile(
    r'\b('
    r'Ligji\s+Nr\.?\s+\d+\/[A-Za-z]-\d+'
    r'(?:\s+për\s+[^\n(]+?)?'
    r'|'
    r'(?:KPPRK|KPRK|KPPK|LPK|LMD|LFK|LSHT|LMDHF|KPK)\s+Nr\.?\s+\d+\/[A-Za-z]-\d+'
    r')',
    re.IGNORECASE
)

LAW_ABBREVIATION_PATTERN = re.compile(
    r'\b(KPPRK|KPRK|KPPK|LPK|LMD|LFK|LSHT|LMDHF|KPK|Kushtetuta)\b',
    re.IGNORECASE
)


# ═══════════════════════════════════════════════════════════════════════════
# ARTICLE PATTERNS
# ═══════════════════════════════════════════════════════════════════════════

SINGLE_ARTICLE_PATTERN = re.compile(
    r'\b(?:Neni|Nenit|Nenin|Artikulli|Art\.?)\s+'
    r'(\d+(?:[\.\/]\d+)*)'
    r'((?:\s*,?\s*par\.?\s*\d+(?:\s*(?:dhe|,)\s*\d+)*)?)'
    r'((?:\s+(?:i|të|te|e|së)\s+[A-ZËÇ][a-zA-ZëçËÇ\-]+(?:-[a-zëç]+)?)*)'
    r'(?:\s*[—\-:]\s*([^\n;•]+?))?'
    r'(?=\s*[;\.\n]|\s*$|\s+[A-ZËÇ][a-zëç]+\s+(?:nuk|ka|i|e)\s)',
    re.IGNORECASE | re.UNICODE,
)

MULTI_ARTICLE_PATTERN = re.compile(
    r'\bNenet\s+'
    r'(\d+(?:[\.\/]\d+)*)'
    r'((?:\s*,\s*\d+(?:[\.\/]\d+)*)*)'
    r'((?:\s+dhe\s+\d+(?:[\.\/]\d+)*)?)'
    r'(?:\s*[—\-:]\s*([^\n;•]+?))?'
    r'(?=\s*[;\.\n]|\s*$|•)',
    re.IGNORECASE | re.UNICODE,
)


# ═══════════════════════════════════════════════════════════════════════════
# GUARDRAIL #2b: Regex për ekstraktim deterministik
# ═══════════════════════════════════════════════════════════════════════════

LAW_NUMBER_PATTERN = re.compile(
    r'\b(\d{2}\s*\/\s*[A-Za-z]\s*-\s*\d{2,4})\b',
    re.IGNORECASE,
)

VERIFIED_ARTICLE_PATTERN = re.compile(
    r'\bNen(?:i|it|in|ët)\s+(\d+(?:[\.\/]\d+)*)'
    r'(?:\s*,?\s*par(?:\.|agrafi|agrafit)?\s*(\d+))?',
    re.IGNORECASE | re.UNICODE,
)

# Pattern për çifte (Neni X i LIGJI)
CITATION_WITH_LAW_PATTERN = re.compile(
    r'\bNen(?:i|it|in|ët)\s+(\d+(?:[\.\/]\d+)*)'
    r'(?:\s*,?\s*par(?:\.|agrafi|agrafit)?\s*(\d+))?'
    r'\s+(?:i|të|te|e|së)\s+'
    r'([A-ZËÇ][A-Za-zëçËÇ0-9\-]{2,25}|KPRK|KPK|KPPRK|LPK|LMD|LMDHF)',
    re.IGNORECASE | re.UNICODE,
)

# Pattern për datat (për detektimin e kontradiktave)
DATE_PATTERN = re.compile(
    r'\b(\d{1,2}[\.\/]\d{1,2}[\.\/]\d{2,4})\b'
)

# Pattern për afatet
DEADLINE_PATTERN = re.compile(
    r'\bafat[ie]?\s+(?:për\s+\w+\s+)?(?:është|prej|prej\s+)?\s*'
    r'(\d+)\s*(dit[ëe]?|muaj|jav[ëe]?|vjet)',
    re.IGNORECASE | re.UNICODE
)