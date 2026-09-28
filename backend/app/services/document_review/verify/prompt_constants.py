# FILE: backend/app/services/document_review/verify/prompt_constants.py
# PHOENIX PROTOCOL - VERIFY PROMPT CONSTANTS V1.0
# Ekstraktuar nga verify_prompts.py V1.14 (pa ndryshim logjike).

VERIFY_SECTION_KEYS = (
    "formal_completeness",
    "legal_quality",
    "supporting_precedents",
    "weaknesses_risks",
    "concrete_recommendations",
    "readiness",
)

DEFAULT_VERIFY_MAX_TOKENS = 2500

DEFAULT_MAX_DRAFT_CHARS = 60000
DRAFT_HEAD_CHARS = 45000
DRAFT_TAIL_CHARS = 10000

MIN_PRECEDENT_SIMILARITY = 0.70

PRECEDENT_LLM_EXCERPT_CHARS = 250