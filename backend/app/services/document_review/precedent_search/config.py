# FILE: backend/app/services/document_review/precedent_search/config.py
# PHOENIX PROTOCOL - PRECEDENT SEARCH CONFIG V2.2
# V2.2: Shtuar PRECEDENT_ENRICH_TOPIC (default true) - enrichment me topic_label.

import os
import re


# ===========================================================================
# KONFIGURIMI KRYESOR
# ===========================================================================

PRECEDENT_SIMILARITY_THRESHOLD = float(
    os.getenv("PRECEDENT_SIMILARITY_THRESHOLD", "0.70")
)
PRECEDENT_TOP_K = int(os.getenv("PRECEDENT_TOP_K", "10"))

# Hybrid search
PRECEDENT_USE_HYBRID = os.getenv("PRECEDENT_USE_HYBRID", "true").lower() == "true"
PRECEDENT_CANDIDATES = int(os.getenv("PRECEDENT_CANDIDATES", "100"))
PRECEDENT_RRF_K = int(os.getenv("PRECEDENT_RRF_K", "60"))

# Reranker
PRECEDENT_RERANKER = os.getenv("PRECEDENT_RERANKER", "deepseek").lower()
PRECEDENT_RERANK_INPUT_N = int(os.getenv("PRECEDENT_RERANK_INPUT_N", "50"))
PRECEDENT_RERANK_TOP_N = int(os.getenv("PRECEDENT_RERANK_TOP_N", "10"))
PRECEDENT_RERANK_MIN_CANDIDATES = int(
    os.getenv("PRECEDENT_RERANK_MIN_CANDIDATES", "8")
)
PRECEDENT_RERANK_MIN_SCORE = float(
    os.getenv("PRECEDENT_RERANK_MIN_SCORE", "4.0")
)

# V2.2: Enrichment me topic_label
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