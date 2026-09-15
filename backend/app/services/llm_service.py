# FILE: backend/app/services/llm_service.py
# PHOENIX PROTOCOL - UNIFIED LLM SERVICE HUB V5.0 (PURE SINGLE-MODEL ARCHITECTURE)
# 100% COMPLETE CODE • ZERO IMPORT ERRORS • EXCLUSIVE LLM_MODEL DEEPSEEK

# 1. Importo të gjitha simbolet nga nën-modulet e brendshme
from app.services.llm.llm_client import *
from app.services.llm.prompt_templates import *

try:
    from app.services.llm.rag_extractor import *
except Exception:
    pass

# 2. Eksporto në mënyrë eksplicite funksionet aktive të klientit
from app.services.llm.llm_client import (
    _call_llm,
    _call_llm_async,
    _get_sync_client,
    _get_async_client,
    clean_and_parse_json,
    get_embedding,
    stream_text_async
)

from app.services.llm.prompt_templates import (
    build_dynamic_identity_header,
    _sanitize_and_disambiguate_prompt,
    AI_DISCLAIMER
)

# 3. Mbrojtje e sigurt për funksionin e nxjerrjes së financave
try:
    from app.services.llm.rag_extractor import extract_expense_details_from_text
except ImportError:
    async def extract_expense_details_from_text(text: str) -> dict:
        """Nxjerrje e sigurt e detajeve të shpenzimeve financiare me DeepSeek."""
        sys_p = "Nxirr detajet e shpenzimit (shuma_eur, kategoria, data_iso, pershkrimi, subjekti) nga ky tekst si JSON."
        raw = await _call_llm_async(sys_p, text, json_mode=True)
        return clean_and_parse_json(raw)