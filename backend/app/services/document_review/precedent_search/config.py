# FILE: backend/app/services/document_review/precedent_search/config.py
# PHOENIX PROTOCOL - PRECEDENT SEARCH CONFIG V2.5
# V2.5: CONSISTENCY FIX —
#       - PRECEDENT_RERANK_COHERE_MIN_SCORE: 0.10 → 0.15 (sipas header-it
#         V2.4 dhe komentit; kodi ishte në 0.10 — mospërputhje e rregulluar).
#       - PRECEDENT_RERANK_INPUT_N: 50 → 20 (sinkron me pre-filter
#         PRECEDENT_RERANK_PRE_FILTER_TOP_N në service.py; vlera 50 ishte
#         konfigurim i vdekur sepse asnjëherë nuk arrihej).
# V2.4: Kalibrim per me shume rezultate:
#       - PRECEDENT_TOP_K: 10 -> 15
#       - PRECEDENT_RERANK_TOP_N: 10 -> 15
#       - PRECEDENT_RERANK_COHERE_MIN_SCORE: 0.5 -> 0.15
# V2.3: Shtuar Cohere Reranker konfigurim.
# V2.2: Shtuar PRECEDENT_ENRICH_TOPIC.
# V2.1: Shtuar PRECEDENT_RERANK_MIN_SCORE.

import os
import re


# ===========================================================================
# KONFIGURIMI KRYESOR
# ===========================================================================

PRECEDENT_SIMILARITY_THRESHOLD = float(
    os.getenv("PRECEDENT_SIMILARITY_THRESHOLD", "0.70")
)

# V2.4: Sa precedentë finalë (pas filtrim threshold).
PRECEDENT_TOP_K = int(os.getenv("PRECEDENT_TOP_K", "15"))

# Hybrid search
PRECEDENT_USE_HYBRID = os.getenv("PRECEDENT_USE_HYBRID", "true").lower() == "true"
PRECEDENT_CANDIDATES = int(os.getenv("PRECEDENT_CANDIDATES", "100"))
PRECEDENT_RRF_K = int(os.getenv("PRECEDENT_RRF_K", "60"))

# Reranker (deepseek | cohere | none)
PRECEDENT_RERANKER = os.getenv("PRECEDENT_RERANKER", "deepseek").lower()

# V2.5: Sa kandidate cohere/deepseek vlereson (input per reranker).
# Sinkron me PRECEDENT_RERANK_PRE_FILTER_TOP_N në service.py (= 20).
# Vlera e mëparshme 50 ishte e vdekur sepse pre-filter nuk dorëzonte > 20.
PRECEDENT_RERANK_INPUT_N = int(os.getenv("PRECEDENT_RERANK_INPUT_N", "20"))

# V2.4: Sa kthen reranker (top nga input).
PRECEDENT_RERANK_TOP_N = int(os.getenv("PRECEDENT_RERANK_TOP_N", "15"))

# Sa kandidate minimale që reranker të aktivizohet (skip nëse ka më pak)
PRECEDENT_RERANK_MIN_CANDIDATES = int(
    os.getenv("PRECEDENT_RERANK_MIN_CANDIDATES", "8")
)

# Rerank score thresholds
PRECEDENT_RERANK_MIN_SCORE = float(
    os.getenv("PRECEDENT_RERANK_MIN_SCORE", "4.0")
)  # DeepSeek: 0-10

# V2.5: Cohere threshold — i sinkronizuar me header/koment V2.4 (= 0.15).
# Cohere rerank-v3.5 jep score 0.1-0.3 per query specifik (jo 0-1 plote).
# 0.5 filtronte te gjitha; 0.15 lejon top 3-10 te kalojne.
PRECEDENT_RERANK_COHERE_MIN_SCORE = float(
    os.getenv("PRECEDENT_RERANK_COHERE_MIN_SCORE", "0.15")
)  # Cohere: 0-1

# Cohere config (V2.3)
COHERE_API_KEY = os.getenv("COHERE_API_KEY", "").strip()
COHERE_RERANK_MODEL = os.getenv(
    "COHERE_RERANK_MODEL", "rerank-v3.5"
)
COHERE_RERANK_TIMEOUT = float(os.getenv("COHERE_RERANK_TIMEOUT", "30.0"))

# Enrichment me topic_label (V2.2)
PRECEDENT_ENRICH_TOPIC = os.getenv("PRECEDENT_ENRICH_TOPIC", "true").lower() == "true"

# Fallback
PRECEDENT_FALLBACK_SCAN_LIMIT = int(
    os.getenv("PRECEDENT_FALLBACK_SCAN_LIMIT", "200")
)
PRECEDENT_FALLBACK_BATCH_SIZE = int(
    os.getenv("PRECEDENT_FALLBACK_BATCH_SIZE", "20")
)

# Limite
PRECEDENT_MAX_EXCERPT_CHARS = 500
PRECEDENT_MAX_TEXT_FOR_QUERY = 6000
PRECEDENT_MAX_THEMATIC_TERMS = 10
PRECEDENT_MAX_KEY_TERMS = 5

# Koleksione / index
LEGAL_KB_COLLECTION = "legal_knowledge_base"
ATLAS_VECTOR_INDEX = "vector_index"


# ===========================================================================
# PATTERN PER NUMRAT E LENDEVE
# ===========================================================================

CASE_NO_PATTERN = re.compile(
    r'\b(?:PA1|PKR|PML|REV|KMLP|ANR|A\.NR|PZR|CP|AC|PN|KP|'
    r'A|P)\s*\.?\s*(?:nr|Nr|NR|N\.?R)\.?\s*'
    r'(\d+[\w\/\.\-]*)',
    re.IGNORECASE,
)

COVER_PAGE_TOKENS = (
    "permbledhje", "përmbledhje",
    "vendime te perzgjedhura", "vendime të përzgjedhura",
    "praktikes gjyqesore", "praktikës gjyqësore",
    "gjykates supreme", "gjykatës supreme",
    "republikes se kosoves", "republikës së kosovës",
)