# FILE: backend/app/services/synthesis/constants.py
# PHOENIX PROTOCOL - SYNTHESIS CONSTANTS V1.0
# Ekstraktuar nga synthesis_service.py V3.8 — ZERO ndryshim funksional.

# ═══════════════════════════════════════════════════════════════════════════
# MONGODB COLLECTIONS
# ═══════════════════════════════════════════════════════════════════════════

SYNTHESIS_COLLECTION = "case_synthesis"
EXTRACTION_COLLECTION = "case_extractions"
CROSS_REF_COLLECTION = "case_cross_references"


# ═══════════════════════════════════════════════════════════════════════════
# DIGEST / OUTPUT LIMITS
# ═══════════════════════════════════════════════════════════════════════════

MAX_DIGEST_CHARS = 130_000
MAX_ENTITIES_PER_DOC = 60
MAX_ARTICLE_DESCRIPTIONS = 250


# ═══════════════════════════════════════════════════════════════════════════
# STREAMING
# ═══════════════════════════════════════════════════════════════════════════

STREAM_BATCH_CHARS = 30
STREAM_BATCH_INTERVAL_SEC = 0.15


# ═══════════════════════════════════════════════════════════════════════════
# LAW CONTEXT / SIMILARITY
# ═══════════════════════════════════════════════════════════════════════════

LAW_CONTEXT_WINDOW = 8000

SIMILARITY_THRESHOLD = 0.75
SIMILARITY_BOOST_FIRST_WORD = 0.15
SIMILARITY_AMBIGUITY_GAP = 0.05
INSTITUTION_CONTEXT_WINDOW = 300


# ═══════════════════════════════════════════════════════════════════════════
# CASE TYPE DETECTION
# ═══════════════════════════════════════════════════════════════════════════

CASE_TYPE_SCAN_CHARS_PER_DOC = 10000
CASE_TYPE_MAX_DOCS = 25