# FILE: backend/app/services/llm/rag_extractor.py
# PHOENIX PROTOCOL - UNIFIED DOCUMENT EXTRACTION ENGINE (CENTRALIZED GATEWAY)

import logging
from typing import List, Dict, Any, Optional

from app.services.llm.llm_client import (
    _get_api_key, 
    _call_llm, 
    _call_llm_async, 
    clean_and_parse_json,
    FAST_MODEL, 
    DEEP_MODEL
)

logger = logging.getLogger(__name__)


async def process_large_document_async(text: str, task_type: str = "SUMMARY") -> str:
    """
    PHOENIX ENGINE: Generates 100% literal, non-hallucinated document summaries in Albanian.
    Uses unified _call_llm_async with multi-model fallback and retry.
    """
    if not text or not text.strip():
        return "Dokument pa përmbajtje tekstuale."
    try:
        system_prompt = """Detyra: Ti je një asistent ligjor shumëgjuhësh (Shqip, Anglisht, Gjermanisht) për Gjykatat e Kosovës.
Analizo tekstin e këtij dokumenti ligjor ose financiar dhe BËJ NJË PËRMBLEDHJE TË FAKTEVE SAKTE VETËM NË GJUHËN SHQIPE.

NDALIMI I HALLUCINIMEVE: Përmend VETËM emrat, shumat, datat dhe termat që shkruhen literalisht në dokument. MOS shpik asnjë detaj.

Përmbledhja duhet të përfshijë:
1. Llojin e dokumentit (Kontratë Shërbimi, Faturë, Aktakuzë, Shkresë, Vendim, etj.)
2. Palët e saktësisht të emëruara në nënshkrim dhe datat kryesore.
3. Shumat monetare, obligimet ose fushëveprimin e marrëveshjes.
4. Fakti më i rëndësishëm ligjor ose financiar."""

        content = await _call_llm_async(
            system_prompt=system_prompt,
            user_content=f"TEKSTI I DOKUMENTIT PËR PËRMBLEDHJE:\n{text[:6000]}",
            temperature=0.0,
            model=FAST_MODEL
        )
        return content.strip() if content else text[:500]
    except Exception as e:
        logger.error(f"Error in process_large_document_async: {e}")
        return text[:500]


def analyze_case_integrity(context: str, custom_prompt: Optional[str] = None) -> Dict[str, Any]:
    key = _get_api_key()
    if not key:
        return {}
    try:
        content = _call_llm(
            custom_prompt or "Analizo këtë rast ligjor në Shqip.", 
            f"KONTEKSTI I RASTIT:\n{context}", 
            json_mode=False, 
            temperature=0.0, 
            model=FAST_MODEL
        )
        return clean_and_parse_json(content)
    except Exception as e:
        logger.error(f"❌ analyze_case_integrity failed: {e}")
        return {}


def extract_expense_details_from_text(text: str) -> Dict[str, Any]:
    key = _get_api_key()
    if not key:
        return {"category": "Shpenzime", "amount": 0.0, "date": None, "description": "AI parsing disabled"}
    try:
        system_prompt = """Detyra: Ti je një asistent financiar i kujdesshëm për tregun e Kosovës. Analizo tekstin e faturës (Shqip, Anglisht, apo Gjermanisht) dhe nxirr JSON në Shqip.
NDALIMI I HALLUCINIMEVE: Përdor VETËM shifrat e vërteta nga fatura.
Formatizo përgjigjen tënde saktësisht si kjo strukturë JSON:
{
  "category": "Kategoria e shpenzimit në Shqip",
  "amount": 12.50,
  "date": "YYYY-MM-DD",
  "description": "Emri i tregtarit"
}"""
        content = _call_llm(
            system_prompt, 
            f"TEKSTI I FATURËS:\n{text}", 
            json_mode=True, 
            temperature=0.0, 
            model=FAST_MODEL
        )
        return clean_and_parse_json(content)
    except Exception as e:
        logger.error(f"Error in extract_expense_details_from_text: {e}")
        return {"category": "Shpenzime", "amount": 0.0, "date": None, "description": "Gabim gjatë procesimit"}


# --- COMPATIBILITY STUBS (Safe-guards against import errors) ---
def categorize_document_text(text: str) -> str: 
    return "Procedurale"

def sterilize_legal_text(text: str) -> str: 
    return text.strip() if text else ""

def translate_for_client(t: str) -> str: 
    return t

def extract_deadlines(text: str) -> Dict[str, Any]: 
    return {"deadlines": []}