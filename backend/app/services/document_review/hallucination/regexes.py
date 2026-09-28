# FILE: backend/app/services/document_review/hallucination/regexes.py
# PHOENIX PROTOCOL - HALLUCINATION REGEXES V1.25
# Të gjitha pattern-et e kompiluara. Zero logjikë.

import re


# ═══════════════════════════════════════════════════════════════════════════
# LAW NAME WITH NUMBER (p.sh. "Ligji për Familjen Nr. 2004/32")
# ═══════════════════════════════════════════════════════════════════════════

LAW_NAME_WITH_NUMBER_RE = re.compile(
    r'((?:Ligj(?:i|it|in|ji)?|Kod(?:i|it|in)?)\s+'
    r'(?:(?:për|per|e|të|te|i)\s+)?'
    r'[A-Za-zëçËÇ\s\-]{4,80}?)'
    r'\s*[\(\[]?\s*(?:Nr\.?\s*)?'
    r'(\d{2,4}\s*/\s*[A-Za-z]\s*[\-–]?\s*\d{2,4}|\d{4}\s*/\s*\d{1,4})',
    re.IGNORECASE | re.UNICODE,
)


# ═══════════════════════════════════════════════════════════════════════════
# ABBREV REPLACEMENT (p.sh. "zëvendëso KPRK me KPK")
# ═══════════════════════════════════════════════════════════════════════════

ABBREV_REPLACEMENT_RE = re.compile(
    r'(?:[Zz]ëvendëso|[Zz]evendeso|ndrysho|kthe)\s+'
    r'["\'`«“]?([A-Z]{2,6})["\'`»”]?\s+'
    r'(?:me|në|ne)\s+["\'`«“]?([A-Z]{2,6})["\'`»”]?'
    r'|'
    r'["\'`«“]?([A-Z]{2,6})["\'`»”]?\s+'
    r'(?:në\s+vend\s+të|ne\s+vend\s+te|jo|→|->|=>)\s+'
    r'["\'`«“]?([A-Z]{2,6})["\'`»”]?'
    r'|'
    r'(?:duhet\s+të\s+jetë|duhet\s+te\s+jete|'
    r'është\s+shkruar\s+si|eshte\s+shkruar\s+si|'
    r'gabimisht\s+shkruar\s+si|gabimisht)\s+'
    r'["\'`«“]?([A-Z]{2,6})["\'`»”]?\s*'
    r'(?:\(?\s*jo\s+|\(\s*në\s+vend\s+të\s+|\(\s*ne\s+vend\s+te\s+)?'
    r'["\'`«“]?([A-Z]{2,6})["\'`»”]?',
    re.UNICODE,
)


# ═══════════════════════════════════════════════════════════════════════════
# ABBREV WITH LAW NUMBER (p.sh. "KPRK Nr. 06/L-074")
# ═══════════════════════════════════════════════════════════════════════════

ABBREV_WITH_LAW_NUMBER_RE = re.compile(
    r'\b([A-Z]{2,6})\b[\s\-–]*[\(\[]?\s*'
    r'(?:Nr\.?\s*)?'
    r'(\d{2,4}\s*/\s*[A-Za-z]\s*[\-–]?\s*\d{2,4})',
    re.UNICODE,
)


# ═══════════════════════════════════════════════════════════════════════════
# STRICT LAW OUTPUT FORMAT VALIDATION
# ═══════════════════════════════════════════════════════════════════════════

STRICT_LAW_OUTPUT_PATTERN = re.compile(
    r'^(\d{2}/L-\d+|\d{4}/\d{1,4})$'
)