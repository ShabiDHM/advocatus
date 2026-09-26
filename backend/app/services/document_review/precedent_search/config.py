# FILE: backend/app/services/document_review/precedent_search/config.py
# PHOENIX PROTOCOL - PRECEDENT SEARCH CONFIG V2.8
# V2.8: RERANK THRESHOLD — PRECEDENT_RERANK_MIN_SCORE 4.0 → 5.5.
#       Arsyetim: Matje V2.7 (case 6ab42c76) tregoi se kandidati P.Nr.533/2022
#       mori rerank_score=4.0 (pikërisht në kufi), u pranua si "precedent
#       i identifikuar", por nuk ka lidhje reale me dokumentin dhe u shfaq
#       si false-positive në raport. Rritja në 5.5 eliminohet rasti kufitar.
# V2.7: TOP_K 15 → 8.
# V2.6: RERANK INPUT_N 20 → 12.
# V2.5: CONSISTENCY FIX — Cohere 0.15.
# V2.4: Kalibrim per me shume rezultate.
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

# V2.7: Sa precedentë finalë (pas filtrim threshold).
PRECEDENT_TOP_K = int(os.getenv("PRECEDENT_TOP_K", "8"))

# Hybrid search
PRECEDENT_USE_HYBRID = os.getenv("PRECEDENT_USE_HYBRID", "true").lower() == "true"
PRECEDENT_CANDIDATES = int(os.getenv("PRECEDENT_CANDIDATES", "100"))
PRECEDENT_RRF_K = int(os.getenv("PRECEDENT_RRF_K", "60"))

# Reranker (deepseek | cohere | none)
PRECEDENT_RERANKER = os.getenv("PRECEDENT_RERANKER", "deepseek").lower()

# V2.6: Sa kandidate cohere/deepseek vlereson (input per reranker).
PRECEDENT_RERANK_INPUT_N = int(os.getenv("PRECEDENT_RERANK_INPUT_N", "12"))

# V2.4: Sa kthen reranker (top nga input).
PRECEDENT_RERANK_TOP_N = int(os.getenv("PRECEDENT_RERANK_TOP_N", "15"))

# Sa kandidate minimale që reranker të aktivizohet (skip nëse ka më pak)
PRECEDENT_RERANK_MIN_CANDIDATES = int(
    os.getenv("PRECEDENT_RERANK_MIN_CANDIDATES", "8")
)

# V2.8: Rerank score threshold — rritur nga 4.0 → 5.5 për të eliminuar
# false-positive të dokumentuar (P.Nr.533/2022 me score 4.0).
PRECEDENT_RERANK_MIN_SCORE = float(
    os.getenv("PRECEDENT_RERANK_MIN_SCORE", "5.5")
)  # DeepSeek: 0-10

# V2.5: Cohere threshold — 0.15 në shkallë 0-1.
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