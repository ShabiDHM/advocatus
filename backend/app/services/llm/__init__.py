# FILE: backend/app/services/llm/__init__.py
# PHOENIX PROTOCOL - LLM PACKAGE INIT

from app.services.llm.llm_client import (
    _call_llm,
    _call_llm_async,
    clean_and_parse_json,
    FAST_MODEL,
    DEEP_MODEL,
    get_embedding,
    stream_text_async,
)

from app.services.llm.prompt_templates import (
    build_dynamic_identity_header,
    _sanitize_and_disambiguate_prompt,
    AI_DISCLAIMER,
)

__all__ = [
    "_call_llm",
    "_call_llm_async",
    "clean_and_parse_json",
    "FAST_MODEL",
    "DEEP_MODEL",
    "get_embedding",
    "stream_text_async",
    "build_dynamic_identity_header",
    "_sanitize_and_disambiguate_prompt",
    "AI_DISCLAIMER",
]