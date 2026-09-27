# FILE: backend/app/services/rag/intent_helpers.py
# PHOENIX PROTOCOL - RAG INTENT HELPERS V1.0
# V1.0: EKSTRAKTUAR nga albanian_rag_service.py V282.25.
#       Përmban:
#       - is_valid_legal_report
#       - detect_requested_pillar
#       Zero varësi nga AlbanianRAGService.

from typing import Optional


def is_valid_legal_report(text: str) -> bool:
    if not text or len(text.strip()) < 150:
        return False
    lower_text = text.lower()
    error_markers = [
        "përkohësisht i ngarkuar", "error code:", "context_length_exceeded",
        "max_num_tokens", "upstream error", "not a valid model",
        "no endpoints found", "gabim teknik"
    ]
    for marker in error_markers:
        if marker in lower_text:
            return False
    return True


def detect_requested_pillar(query_lower: str) -> Optional[str]:
    if "shtjella 1" in query_lower or "shtjella_1" in query_lower or "ekzaminimi" in query_lower or "fakti" in query_lower:
        return "PILLAR_1"
    if "shtjella 2" in query_lower or "shtjella_2" in query_lower or "nenet" in query_lower or "shkeljet" in query_lower:
        return "PILLAR_2"
    if "shtjella 3" in query_lower or "shtjella_3" in query_lower or "kundërshtimet" in query_lower or "plani" in query_lower:
        return "PILLAR_3"
    return None