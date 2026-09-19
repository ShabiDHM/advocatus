# FILE: backend/app/services/document_review/constants.py
# PHOENIX PROTOCOL - DOCUMENT REVIEW CONSTANTS V2.1
# Arkitekturë e re: Regex + MongoDB + LLM vetëm për narrative.
# V2.1: Shtuar MAX_DATES për fact_extractor.
# V2.0: Hequr LLM-specific (max_tokens, similarity thresholds për KB filter).
#       Shtuar limits për ekstraktim deterministik.

# ═══════════════════════════════════════════════════════════════════════════
# MONGODB COLLECTIONS
# ═══════════════════════════════════════════════════════════════════════════

SYNTHESIS_COLLECTION = "case_synthesis"
EXTRACTION_COLLECTION = "case_extractions"
LEGAL_KB_COLLECTION = "legal_knowledge_base"
CASE_LAW_COLLECTION = "case_law"


# ═══════════════════════════════════════════════════════════════════════════
# EXTRACTION LIMITS
# ═══════════════════════════════════════════════════════════════════════════

MAX_ARTICLE_CITATIONS = 100         # Sa nene maksimumi të nxirren
MAX_CASE_NUMBERS = 50               # Sa numra lënde
MAX_DATES = 100                     # Sa data (për fact_extractor)
MAX_CONTEXT_CHARS = 300             # Sa karaktere konteksti për çdo citim


# ═══════════════════════════════════════════════════════════════════════════
# STREAMING
# ═══════════════════════════════════════════════════════════════════════════

STREAM_BATCH_CHARS = 30
STREAM_BATCH_INTERVAL_SEC = 0.15


# ═══════════════════════════════════════════════════════════════════════════
# ABBREVIATION VALIDATION
# ═══════════════════════════════════════════════════════════════════════════

LAW_CODE_MIN_LENGTH = 3
LAW_CODE_MAX_LENGTH = 5

ROMAN_NUMERALS = {
    'I', 'II', 'III', 'IV', 'V', 'VI', 'VII', 'VIII', 'IX', 'X',
    'XI', 'XII', 'XIII', 'XIV', 'XV', 'XVI', 'XVII', 'XVIII', 'XIX', 'XX',
}


# ═══════════════════════════════════════════════════════════════════════════
# SHQIP STOPWORDS
# ═══════════════════════════════════════════════════════════════════════════

ALBANIAN_STOPWORDS = {
    # Fjalë të përgjithshme ligjore
    "ligji", "ligjit", "ligjin", "ligje", "ligjeve", "ligj",
    "kodi", "kodit", "kodin", "kodet",
    "neni", "nenit", "nenin", "nenet", "neneve",
    "paragrafi", "paragrafit", "paragrafin",
    "pika", "pikës", "pikën",
    # Parafjalë dhe lidhëza
    "për", "per", "dhe", "ose", "me", "në", "ne", "nga", "të", "te",
    "e", "i", "së", "se", "si", "ka", "kjo", "ky", "këto", "këta",
    "ai", "ajo", "ata", "ato", "por", "kur", "ku", "si",
    # Kontekst i përgjithshëm
    "republikës", "republike", "republikë", "kosovës", "kosove", "kosovë",
    "numri", "numrit", "numër", "numer", "nr",
    "këtij", "ketij", "kësaj", "kesaj", "këtë", "kete",
    "kanë", "kane", "ishte", "ishin", "është", "eshte",
    "duhet", "mund", "nuk", "vetëm", "gjithashtu",
    # Fjalë nga konteksti gjyqësor
    "gjykata", "gjykatës", "gjykate", "gjykatë",
    "vendimi", "vendimit", "vendim", "aktgjykim",
    "aktgjykimi", "aktvendim", "aktvendimi",
    "lënda", "lenda", "lëndës", "lendes",
    "rasti", "rastit", "rast",
    "pala", "palë", "pales", "palës",
    "palët", "palet",
    "apelit", "apeli",
    "themelore", "supreme",
}