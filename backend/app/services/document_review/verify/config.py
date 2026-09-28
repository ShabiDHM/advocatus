# FILE: backend/app/services/document_review/verify/config.py
# PHOENIX PROTOCOL - VERIFY CONFIG V1.1 (HAPI B2)
# V1.1: H3 — INTERNATIONAL_LAW_KEYWORDS tani lexohet nga dynamic_config.json
#       me fallback në default-in e hardcoduara.
# V1.0: Centralizon konstantet e shpërndara më parë në draft_verifier.py.

import os
import re

from ..dynamic_config import get_international_law_keywords


# ═══════════════════════════════════════════════════════════════════════════
# KONFIGURIM NGA ENV
# ═══════════════════════════════════════════════════════════════════════════

MAX_CONCURRENT_VERIFY_SECTIONS = int(
    os.getenv("VERIFY_MAX_WORKERS", os.getenv("DOC_REVIEW_MAX_WORKERS", "3"))
)

HALLUCINATION_GATE_ENABLED = os.getenv(
    "VERIFY_HALLUCINATION_GATE", "true"
).lower() == "true"


# ═══════════════════════════════════════════════════════════════════════════
# READINESS — ETIKETA DHE SKORË
# ═══════════════════════════════════════════════════════════════════════════

READINESS_LABELS_SQ: dict = {
    "READY":       "GATI",
    "NEEDS WORK":  "KËRKON PUNË",
    "INCOMPLETE":  "I PËRPLOTË",
    "UNKNOWN":     "I PANJOHUR",
}

READINESS_SCORES: dict = {
    "READY":       100,
    "NEEDS WORK":  65,
    "INCOMPLETE":  30,
    "UNKNOWN":     0,
}


# ═══════════════════════════════════════════════════════════════════════════
# CRITICAL RECOMMENDATIONS MARKER
# ═══════════════════════════════════════════════════════════════════════════

KRITIKE_MARKER_REGEX = re.compile(r'\[#K\d+\]')

CONCRETE_RECOMMENDATIONS_KEY = "concrete_recommendations"


# ═══════════════════════════════════════════════════════════════════════════
# INTERNATIONAL LAW KEYWORDS — V1.1 (H3)
# ═══════════════════════════════════════════════════════════════════════════
# Lexohet nga data/dynamic_config.json → "international_law_keywords".
# Fallback në default-in më poshtë nëse JSON mungon.

_DEFAULT_INTERNATIONAL_LAW_KEYWORDS = [
    "konvent",
    "kednj",
    "gjednj",
    "okb",
    "kombet e bashkuara",
    "kombeve te bashkuara",
    "njeriut",
    "femijes",
]

INTERNATIONAL_LAW_KEYWORDS = get_international_law_keywords(
    _DEFAULT_INTERNATIONAL_LAW_KEYWORDS
)