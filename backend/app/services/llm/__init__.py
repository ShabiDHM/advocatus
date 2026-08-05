# FILE: app/services/llm/__init__.py
from app.services.llm.prompt_templates import (
    build_dynamic_identity_header,
    UNBREAKABLE_IDENTITY_HEADER,
    _sanitize_and_disambiguate_prompt,
    AI_DISCLAIMER
)

from app.services.llm.llm_client import (
    _get_api_key,
    _get_sync_client,
    _get_async_client,
    clean_and_parse_json,
    _call_llm,
    get_embedding,
    stream_text_async,
    FAST_MODEL,
    DEEP_MODEL,
    EMBEDDING_MODEL,
    TEMP_DRAFTING,
    TEMP_ANALYSIS,
    TEMP_CHAT
)

from app.services.llm.rag_extractor import (
    process_large_document_async,
    extract_case_graph_ontology,
    forensic_interrogation,
    generate_adversarial_simulation,
    build_case_chronology,
    detect_contradictions,
    analyze_case_integrity,
    extract_expense_details_from_text,
    categorize_document_text,
    sterilize_legal_text,
    translate_for_client,
    extract_deadlines
)

__all__ = [
    "_get_api_key",
    "_get_sync_client",
    "_get_async_client",
    "_call_llm",
    "_sanitize_and_disambiguate_prompt",
    "clean_and_parse_json",
    "get_embedding",
    "stream_text_async",
    "build_dynamic_identity_header",
    "UNBREAKABLE_IDENTITY_HEADER",
    "AI_DISCLAIMER",
    "FAST_MODEL",
    "DEEP_MODEL",
    "EMBEDDING_MODEL",
    "TEMP_DRAFTING",
    "TEMP_ANALYSIS",
    "TEMP_CHAT",
    "process_large_document_async",
    "extract_case_graph_ontology",
    "forensic_interrogation",
    "generate_adversarial_simulation",
    "build_case_chronology",
    "detect_contradictions",
    "analyze_case_integrity",
    "extract_expense_details_from_text",
    "categorize_document_text",
    "sterilize_legal_text",
    "translate_for_client",
    "extract_deadlines"
]